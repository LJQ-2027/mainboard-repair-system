param(
  [string]$HostName = "8.217.28.36",
  [string]$User = "root",
  [string]$RemoteDir = "/opt/motherboard-repair-beta",
  [string]$KeyPath = "",
  [string]$HtpasswdPath = "",
  [string]$ReviewerMapPath = "",
  [PSCredential]$TechnicianCredential,
  [PSCredential]$ReviewerCredential,
  [switch]$PreflightOnly
)

$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -lt 7) {
  throw "Run deployment with PowerShell 7 or newer."
}
$PSNativeCommandUseErrorActionPreference = $true

function Require-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $Name"
  }
}

function Get-BasicAuthorization([PSCredential]$Credential) {
  $plainPassword = $Credential.GetNetworkCredential().Password
  $bytes = [Text.Encoding]::UTF8.GetBytes(
    "$($Credential.UserName):$plainPassword"
  )
  return [Convert]::ToBase64String($bytes)
}

function Invoke-RemoteBash(
  [string]$Script,
  [string[]]$SshArguments
) {
  $normalized = $Script.Replace("`r", "")
  $payload = [Convert]::ToBase64String(
    [Text.Encoding]::UTF8.GetBytes($normalized)
  )
  $payload | ssh @SshArguments (
    "set -o pipefail; tr -d '\r\n' | base64 -d | bash"
  )
}

foreach ($command in @("git", "ssh", "scp")) {
  Require-Command $command
}
if (-not $KeyPath) {
  throw "Pass -KeyPath with the SSH private key path."
}
if ($RemoteDir -notmatch '^/[A-Za-z0-9._/-]+$') {
  throw "RemoteDir must be an absolute path containing only safe path characters."
}

$resolvedKey = (Resolve-Path -LiteralPath $KeyPath).Path
$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

if (git status --porcelain) {
  throw "Working tree has uncommitted changes. Commit before deployment."
}

$target = "${User}@${HostName}"
$sshArguments = @(
  "-o", "BatchMode=yes",
  "-o", "ConnectTimeout=10",
  "-i", $resolvedKey,
  $target
)

Write-Host "== read-only preflight =="
$preflight = @'
set -euo pipefail
test -d /opt/motherboard-repair-beta/app
test -f /etc/nginx/sites-available/sikayetvar
command -v python3
command -v pm2
command -v nginx
command -v curl
df -Pk /opt/motherboard-repair-beta
free -m
pm2 describe motherboard-repair-beta >/dev/null
nginx -t
'@
Invoke-RemoteBash $preflight $sshArguments
if ($PreflightOnly) {
  Write-Host "Preflight complete; no server files were changed."
  exit 0
}

if (
  -not $HtpasswdPath -or
  -not $ReviewerMapPath -or
  $null -eq $TechnicianCredential -or
  $null -eq $ReviewerCredential
) {
  throw "Deployment requires auth files and technician/reviewer credentials."
}
$resolvedHtpasswd = (Resolve-Path -LiteralPath $HtpasswdPath).Path
$resolvedReviewerMap = (Resolve-Path -LiteralPath $ReviewerMapPath).Path
foreach ($credential in @($TechnicianCredential, $ReviewerCredential)) {
  if ($credential.UserName -notmatch '^[A-Za-z0-9._@-]+$') {
    throw "Pilot usernames may contain only letters, digits, dot, underscore, @, and hyphen."
  }
}
$technicianAuth = Get-BasicAuthorization $TechnicianCredential
$reviewerAuth = Get-BasicAuthorization $ReviewerCredential

$deployRoot = Join-Path $repoRoot ".local\deploy\visual-qc"
New-Item -ItemType Directory -Force -Path $deployRoot | Out-Null
$artifact = Join-Path $deployRoot "motherboard-repair-visual-qc.tar.gz"
$deploymentManifest = Join-Path $deployRoot "deployment-manifest.json"
foreach ($generatedInput in @($artifact, $deploymentManifest)) {
  if (Test-Path -LiteralPath $generatedInput) {
    Remove-Item -LiteralPath $generatedInput -Force
  }
}
$commit = (git rev-parse HEAD).Trim()
if ($commit -notmatch '^[0-9a-f]{40}$') {
  throw "Git HEAD must resolve to a full lowercase commit SHA."
}
$shortCommit = $commit.Substring(0, 12)
$runtimeManifest = Join-Path $repoRoot "deploy\visual-qc-runtime-files.txt"
$runtimePaths = @(
  Get-Content -LiteralPath $runtimeManifest -Encoding UTF8 |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -and -not $_.StartsWith("#") }
)
if (-not $runtimePaths) {
  throw "Visual-QC runtime manifest is empty."
}
if (($runtimePaths | Select-Object -Unique).Count -ne $runtimePaths.Count) {
  throw "Visual-QC runtime manifest contains duplicate entries."
}
foreach ($runtimePath in $runtimePaths) {
  if ($runtimePath -match '(^/|^\.\.|\\)') {
    throw "Unsafe Visual-QC runtime path: $runtimePath"
  }
  git cat-file -e "${commit}:$runtimePath"
}
git archive --format=tar.gz -o $artifact $commit -- @runtimePaths
$manifestBuilderPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $manifestBuilderPython -PathType Leaf)) {
  throw "Project virtualenv Python is required to build deployment evidence."
}
& $manifestBuilderPython `
  (Join-Path $repoRoot "scripts\build_visual_qc_deployment_manifest.py") `
  --archive $artifact `
  --runtime-manifest $runtimeManifest `
  --commit-sha $commit `
  --output $deploymentManifest
$deploymentEvidence = (
  Get-Content -LiteralPath $deploymentManifest -Raw -Encoding UTF8 |
    ConvertFrom-Json
)
$archiveSha256 = [string]$deploymentEvidence.archive_sha256
$archiveBytes = [long]$deploymentEvidence.archive_bytes
$runtimeManifestSha256 = [string]$deploymentEvidence.runtime_manifest_sha256
$runtimePathCount = [int]$deploymentEvidence.runtime_path_count
$deploymentVerifier = Join-Path (
  $repoRoot
) "scripts\visual_qc\deployment_verifier.py"
$deploymentContract = Join-Path (
  $repoRoot
) "scripts\visual_qc\deployment_manifest.py"
$deploymentVerifierSha256 = (
  Get-FileHash -LiteralPath $deploymentVerifier -Algorithm SHA256
).Hash.ToLowerInvariant()
$deploymentContractSha256 = (
  Get-FileHash -LiteralPath $deploymentContract -Algorithm SHA256
).Hash.ToLowerInvariant()
$uploadId = "$shortCommit-$([Guid]::NewGuid().ToString('N'))"
$remoteInputDir = "$RemoteDir/deploy-input/$uploadId"
$artifactSizeMb = [Math]::Round(
  (Get-Item -LiteralPath $artifact).Length / 1MB,
  1
)
Write-Host "Runtime archive: $artifactSizeMb MB from $($runtimePaths.Count) paths."

$stagingStarted = $false
try {
  Write-Host "== upload immutable inputs =="
  ssh @sshArguments "install -d -m 0700 '$remoteInputDir'"
  $stagingStarted = $true
  scp -i $resolvedKey $artifact "${target}:$remoteInputDir/app.tar.gz"
  scp -i $resolvedKey $deploymentManifest `
    "${target}:$remoteInputDir/deployment-manifest.json"
  scp -i $resolvedKey $deploymentVerifier `
    "${target}:$remoteInputDir/deployment_verifier.py"
  scp -i $resolvedKey $deploymentContract `
    "${target}:$remoteInputDir/deployment_manifest.py"
  scp -i $resolvedKey `
    (Join-Path $repoRoot "deploy\nginx\mb-repair-beta.locations.conf") `
    "${target}:$remoteInputDir/mb-repair-beta.locations.conf"
  scp -i $resolvedKey `
    (Join-Path $repoRoot "deploy\nginx\mb-repair-beta-role-map.conf") `
    "${target}:$remoteInputDir/mb-repair-beta-role-map.conf"
  scp -i $resolvedKey $resolvedReviewerMap `
    "${target}:$remoteInputDir/mb-repair-beta-reviewers.map"
  scp -i $resolvedKey $resolvedHtpasswd `
    "${target}:$remoteInputDir/.htpasswd-mb-repair-beta"
  ssh @sshArguments (
    "chmod 0400 '$remoteInputDir'/* " +
    "'$remoteInputDir/.htpasswd-mb-repair-beta' && " +
    "chmod 0500 '$remoteInputDir'"
  )

  $remoteScript = @'
set -Eeuo pipefail

REMOTE_DIR="__REMOTE_DIR__"
APP_DIR="$REMOTE_DIR/app"
APP_NEW="$REMOTE_DIR/app.new"
INPUT_DIR="__INPUT_DIR__"
VENV_LINK="$REMOTE_DIR/venv-visual-qc"
DEPLOY_ID="__COMMIT_SHORT__-$(date +%Y%m%d_%H%M%S)-$$"
VENV_NEW="$REMOTE_DIR/venvs/visual-qc-__COMMIT_SHORT__-$(date +%Y%m%d_%H%M%S)-$$"
DATA_DIR="$REMOTE_DIR/data/visual-qc"
DATABASE="$DATA_DIR/visual-qc.sqlite3"
ROLLBACK_DIR="$REMOTE_DIR/rollback/$DEPLOY_ID"
UPGRADE_PREFLIGHT_REPORT="$ROLLBACK_DIR/upgrade-preflight.json"
DEPLOYMENT_MANIFEST="$INPUT_DIR/deployment-manifest.json"
DEPLOY_LOCK="$REMOTE_DIR/.visual-qc-deploy.lock"
SITE_FILE="/etc/nginx/sites-available/sikayetvar"
SNIPPET_FILE="/etc/nginx/snippets/mb-repair-beta.locations.conf"
ROLE_MAP_FILE="/etc/nginx/conf.d/mb-repair-beta-role-map.conf"
REVIEWERS_FILE="/etc/nginx/mb-repair-beta-reviewers.map"
HTPASSWD_FILE="/etc/nginx/.htpasswd-mb-repair-beta"
OLD_APP_MOVED=0
VENV_SWITCHED=0
VENV_LEGACY_MOVED=0
QC_EXISTED=0
DATABASE_EXISTED=0
DATABASE_SNAPSHOT_READY=0
DATABASE_MAY_BE_MUTATED=0
SERVICE_STATE_CAPTURED=0
OLD_VENV_TARGET=""

mkdir -p "$ROLLBACK_DIR" "$REMOTE_DIR/logs" "$DATA_DIR" "$REMOTE_DIR/venvs"
exec 9>"$DEPLOY_LOCK"
flock -n 9 || {
  echo "Another visual-QC deployment is already running." >&2
  exit 1
}

backup_optional() {
  local source="$1"
  local name="$2"
  if [ -f "$source" ]; then
    cp -a "$source" "$ROLLBACK_DIR/$name"
  else
    : > "$ROLLBACK_DIR/$name.missing"
  fi
}

restore_optional() {
  local target="$1"
  local name="$2"
  if [ -f "$ROLLBACK_DIR/$name" ]; then
    cp -a "$ROLLBACK_DIR/$name" "$target"
  elif [ -f "$ROLLBACK_DIR/$name.missing" ]; then
    rm -f "$target"
  fi
}

remove_staged_secrets() {
  rm -f "$INPUT_DIR/.htpasswd-mb-repair-beta"
  rm -f "$INPUT_DIR/mb-repair-beta-reviewers.map"
}

restore_database() {
  if [ "$DATABASE_MAY_BE_MUTATED" -ne 1 ]; then
    return
  fi
  if [ "$DATABASE_SNAPSHOT_READY" -ne 1 ]; then
    echo "Database may be mutated but no rollback snapshot is available." >&2
    return 1
  fi
  rm -f "$DATABASE-wal" "$DATABASE-shm"
  if [ "$DATABASE_EXISTED" -eq 1 ]; then
    cp -a "$ROLLBACK_DIR/visual-qc.sqlite3" "$DATABASE"
  else
    rm -f "$DATABASE"
  fi
}

restore_venv_link() {
  if [ "$VENV_LEGACY_MOVED" -eq 1 ]; then
    if [ "$VENV_SWITCHED" -eq 1 ]; then
      rm -f "$VENV_LINK"
    fi
    mv "$ROLLBACK_DIR/venv-visual-qc" "$VENV_LINK"
    return
  fi
  if [ "$VENV_SWITCHED" -eq 1 ]; then
    rm -f "$VENV_LINK"
    if [ -n "$OLD_VENV_TARGET" ]; then
      ln -s "$OLD_VENV_TARGET" "$VENV_LINK"
    fi
  fi
}

rollback() {
  local exit_code=$?
  trap - ERR
  echo "== rollback after deployment failure =="
  if [ "$SERVICE_STATE_CAPTURED" -eq 1 ]; then
    pm2 delete motherboard-repair-visual-qc >/dev/null 2>&1 || true
  fi
  restore_database
  restore_venv_link
  if [ "$OLD_APP_MOVED" -eq 1 ] && [ -d "$ROLLBACK_DIR/app" ]; then
    rm -rf "$APP_DIR"
    mv "$ROLLBACK_DIR/app" "$APP_DIR"
  fi
  restore_optional "$SITE_FILE" "sikayetvar"
  restore_optional "$SNIPPET_FILE" "mb-repair-beta.locations.conf"
  restore_optional "$ROLE_MAP_FILE" "mb-repair-beta-role-map.conf"
  restore_optional "$REVIEWERS_FILE" "mb-repair-beta-reviewers.map"
  restore_optional "$HTPASSWD_FILE" ".htpasswd-mb-repair-beta"
  rm -rf "$APP_NEW" "$VENV_NEW"
  if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR"
    pm2 startOrRestart ecosystem.config.js \
      --only motherboard-repair-beta --update-env || true
    if [ "$SERVICE_STATE_CAPTURED" -eq 1 ] &&
      [ "$QC_EXISTED" -eq 1 ] &&
      [ -x "$VENV_LINK/bin/python" ]; then
      pm2 startOrRestart ecosystem.config.js \
        --only motherboard-repair-visual-qc --update-env || true
    fi
  fi
  nginx -t && systemctl reload nginx || true
  remove_staged_secrets
  exit "$exit_code"
}
trap rollback ERR

echo "== verify immutable deployment inputs =="
python3 - \
  "$INPUT_DIR/deployment_verifier.py" \
  "__DEPLOYMENT_VERIFIER_SHA256__" \
  "$INPUT_DIR/deployment_manifest.py" \
  "__DEPLOYMENT_CONTRACT_SHA256__" <<'PY'
import hashlib
from pathlib import Path
import sys

for index in (1, 3):
    path = Path(sys.argv[index])
    expected = sys.argv[index + 1]
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise SystemExit(f"Deployment verifier input hash mismatch: {path.name}")
PY
python3 "$INPUT_DIR/deployment_verifier.py" inputs \
  --manifest "$DEPLOYMENT_MANIFEST" \
  --archive "$INPUT_DIR/app.tar.gz" \
  --commit-sha "__COMMIT_FULL__" \
  --archive-sha256 "__ARCHIVE_SHA256__" \
  --archive-bytes "__ARCHIVE_BYTES__" \
  --runtime-manifest-sha256 "__RUNTIME_MANIFEST_SHA256__" \
  --runtime-path-count "__RUNTIME_PATH_COUNT__"

echo "== stage application and runtime =="
rm -rf "$APP_NEW" "$VENV_NEW"
mkdir -p "$APP_NEW"
tar -xzf "$INPUT_DIR/app.tar.gz" -C "$APP_NEW"
python3 "$INPUT_DIR/deployment_verifier.py" extracted \
  --app-root "$APP_NEW" \
  --commit-sha "__COMMIT_FULL__" \
  --archive-sha256 "__ARCHIVE_SHA256__" \
  --archive-bytes "__ARCHIVE_BYTES__" \
  --runtime-manifest-sha256 "__RUNTIME_MANIFEST_SHA256__" \
  --runtime-path-count "__RUNTIME_PATH_COUNT__"
cp -a "$DEPLOYMENT_MANIFEST" "$ROLLBACK_DIR/deployment-manifest.json"
if [ -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env" "$APP_NEW/.env"
fi
echo "__COMMIT_FULL__" > "$APP_NEW/VERSION"

if ! dpkg -s python3-venv >/dev/null 2>&1; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
fi
python3 -m venv "$VENV_NEW"
"$VENV_NEW/bin/python" -m pip install --upgrade pip
"$VENV_NEW/bin/python" -m pip install -r "$APP_NEW/requirements-visual-qc.txt"

echo "== quiesce service and create consistent database backup =="
if pm2 describe motherboard-repair-visual-qc >/dev/null 2>&1; then
  QC_EXISTED=1
fi
SERVICE_STATE_CAPTURED=1
if [ "$QC_EXISTED" -eq 1 ]; then
  pm2 stop motherboard-repair-visual-qc
fi
if [ -f "$DATABASE" ]; then
  DATABASE_EXISTED=1
  python3 - "$DATABASE" "$ROLLBACK_DIR/visual-qc.sqlite3" <<'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
destination = sqlite3.connect(sys.argv[2])
try:
    source.backup(destination)
finally:
    destination.close()
    source.close()
PY
fi
DATABASE_SNAPSHOT_READY=1

echo "== rehearse database migration and runtime rollback =="
if [ "$DATABASE_EXISTED" -ne 1 ]; then
  echo "Visual-QC upgrade preflight requires an existing database snapshot." >&2
  false
fi
"$VENV_NEW/bin/python" "$APP_NEW/scripts/audit_visual_qc_upgrade.py" \
  --source-database "$ROLLBACK_DIR/visual-qc.sqlite3" \
  --source-data-root "$DATA_DIR" \
  --source-app-root "$APP_DIR" \
  --target-version "__COMMIT_FULL__" \
  --target-archive-sha256 "__ARCHIVE_SHA256__" \
  --target-archive-bytes "__ARCHIVE_BYTES__" \
  --target-runtime-manifest-sha256 "__RUNTIME_MANIFEST_SHA256__" \
  --output "$UPGRADE_PREFLIGHT_REPORT" \
  >"$ROLLBACK_DIR/upgrade-preflight.stdout.json"

"$VENV_NEW/bin/python" "$INPUT_DIR/deployment_verifier.py" report \
  --report "$UPGRADE_PREFLIGHT_REPORT" \
  --schema "$APP_NEW/knowledge-base/visual-qc-upgrade-preflight-v1-schema.json" \
  --snapshot "$ROLLBACK_DIR/visual-qc.sqlite3" \
  --commit-sha "__COMMIT_FULL__" \
  --archive-sha256 "__ARCHIVE_SHA256__" \
  --archive-bytes "__ARCHIVE_BYTES__" \
  --runtime-manifest-sha256 "__RUNTIME_MANIFEST_SHA256__" \
  --runtime-path-count "__RUNTIME_PATH_COUNT__"

echo "== back up current application and gateway =="
backup_optional "$SITE_FILE" "sikayetvar"
backup_optional "$SNIPPET_FILE" "mb-repair-beta.locations.conf"
backup_optional "$ROLE_MAP_FILE" "mb-repair-beta-role-map.conf"
backup_optional "$REVIEWERS_FILE" "mb-repair-beta-reviewers.map"
backup_optional "$HTPASSWD_FILE" ".htpasswd-mb-repair-beta"
if [ -L "$VENV_LINK" ]; then
  OLD_VENV_TARGET="$(readlink "$VENV_LINK")"
elif [ -e "$VENV_LINK" ]; then
  mv "$VENV_LINK" "$ROLLBACK_DIR/venv-visual-qc"
  VENV_LEGACY_MOVED=1
fi
mv "$APP_DIR" "$ROLLBACK_DIR/app"
OLD_APP_MOVED=1
mv "$APP_NEW" "$APP_DIR"
ln -sfn "$VENV_NEW" "$VENV_LINK"
VENV_SWITCHED=1

echo "== install protected gateway files =="
install -m 0644 "$INPUT_DIR/mb-repair-beta.locations.conf" "$SNIPPET_FILE"
install -m 0644 "$INPUT_DIR/mb-repair-beta-role-map.conf" "$ROLE_MAP_FILE"
install -m 0640 -o root -g www-data \
  "$INPUT_DIR/mb-repair-beta-reviewers.map" "$REVIEWERS_FILE"
install -m 0640 -o root -g www-data \
  "$INPUT_DIR/.htpasswd-mb-repair-beta" "$HTPASSWD_FILE"

python3 - "$SITE_FILE" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
include = "    include /etc/nginx/snippets/mb-repair-beta.locations.conf;"
if include not in text:
    pattern = re.compile(
        r"\n\s*location = /mb-repair-beta\s*\{.*?\n\s*\}"
        r"\s*\n\s*location /mb-repair-beta/\s*\{.*?\n\s*\}\s*",
        re.DOTALL,
    )
    text, count = pattern.subn(f"\n{include}\n\n", text, count=1)
    if count != 1:
        raise SystemExit("Expected existing mb-repair-beta location block was not found.")
    path.write_text(text, encoding="utf-8")
PY
nginx -t

echo "== start bounded services =="
cd "$APP_DIR"
pm2 startOrRestart ecosystem.config.js \
  --only motherboard-repair-beta --update-env
DATABASE_MAY_BE_MUTATED=1
pm2 startOrRestart ecosystem.config.js \
  --only motherboard-repair-visual-qc --update-env

echo "== internal and authenticated gateway smoke =="
sleep 3
curl -fsS http://127.0.0.1:3010/health
curl -fsS http://127.0.0.1:3010/ >/tmp/mb-repair-index.html
grep -q "aiStatusInline" /tmp/mb-repair-index.html
curl -fsS http://127.0.0.1:3020/api/v1/visual-qc/health \
  >/tmp/mb-repair-visual-qc-health.json
grep -q "VISUAL-QC-SERVER-HEALTH-V2" \
  /tmp/mb-repair-visual-qc-health.json

systemctl reload nginx
base_url="https://cccsat.top/mb-repair-beta"

wait_for_gateway_identity() {
  local authorization="$1"
  local expected_actor="$2"
  local expected_role="$3"
  local output="$4"
  local attempt
  local status
  for attempt in $(seq 1 30); do
    status="$(curl -ksS --resolve cccsat.top:443:127.0.0.1 \
      -H "Authorization: Basic $authorization" \
      -H "X-Actor-Id: forged-actor" \
      -H "X-Actor-Role: reviewer" \
      -o "$output" -w '%{http_code}' \
      "$base_url/api/v1/visual-qc/identity")"
    if [ "$status" = "200" ] &&
      grep -Fq "\"actor_id\":\"$expected_actor\"" "$output" &&
      grep -Fq "\"role\":\"$expected_role\"" "$output"; then
      return 0
    fi
    sleep 1
  done
  echo "Gateway identity did not converge for $expected_actor." >&2
  cat "$output" >&2 || true
  return 1
}

wait_for_gateway_identity \
  "__TECH_AUTH__" "__TECH_USER__" "technician" \
  /tmp/mb-repair-technician-identity.json
wait_for_gateway_identity \
  "__REVIEWER_AUTH__" "__REVIEWER_USER__" "reviewer" \
  /tmp/mb-repair-reviewer-identity.json

for attempt in 1 2 3; do
  status="$(curl -ksS --resolve cccsat.top:443:127.0.0.1 \
    -o /dev/null -w '%{http_code}' "$base_url/")"
  test "$status" = "401"
  sleep 1
done

curl -kfsS --resolve cccsat.top:443:127.0.0.1 \
  -H "Authorization: Basic __TECH_AUTH__" \
  "$base_url/" >/tmp/mb-repair-authenticated-index.html
grep -q "aiStatusInline" /tmp/mb-repair-authenticated-index.html

pm2 save
remove_staged_secrets
trap - ERR
echo "Deployment __COMMIT_FULL__ completed."
pm2 status motherboard-repair-beta
pm2 status motherboard-repair-visual-qc
cat /tmp/mb-repair-visual-qc-health.json
'@
  $remoteScript = $remoteScript.Replace("__REMOTE_DIR__", $RemoteDir)
  $remoteScript = $remoteScript.Replace("__INPUT_DIR__", $remoteInputDir)
  $remoteScript = $remoteScript.Replace("__COMMIT_FULL__", $commit)
  $remoteScript = $remoteScript.Replace("__COMMIT_SHORT__", $shortCommit)
  $remoteScript = $remoteScript.Replace(
    "__ARCHIVE_SHA256__",
    $archiveSha256
  )
  $remoteScript = $remoteScript.Replace(
    "__ARCHIVE_BYTES__",
    [string]$archiveBytes
  )
  $remoteScript = $remoteScript.Replace(
    "__RUNTIME_MANIFEST_SHA256__",
    $runtimeManifestSha256
  )
  $remoteScript = $remoteScript.Replace(
    "__RUNTIME_PATH_COUNT__",
    [string]$runtimePathCount
  )
  $remoteScript = $remoteScript.Replace(
    "__DEPLOYMENT_VERIFIER_SHA256__",
    $deploymentVerifierSha256
  )
  $remoteScript = $remoteScript.Replace(
    "__DEPLOYMENT_CONTRACT_SHA256__",
    $deploymentContractSha256
  )
  $remoteScript = $remoteScript.Replace("__TECH_AUTH__", $technicianAuth)
  $remoteScript = $remoteScript.Replace(
    "__REVIEWER_AUTH__",
    $reviewerAuth
  )
  $remoteScript = $remoteScript.Replace(
    "__TECH_USER__",
    $TechnicianCredential.UserName
  )
  $remoteScript = $remoteScript.Replace(
    "__REVIEWER_USER__",
    $ReviewerCredential.UserName
  )
  Invoke-RemoteBash $remoteScript $sshArguments

  Write-Host "Visual-QC pilot deployment finished at commit $commit."
  Write-Host "External route requires per-user Basic Auth:"
  Write-Host "  https://cccsat.top/mb-repair-beta/"
}
finally {
  if ($stagingStarted) {
    try {
      ssh @sshArguments "rm -rf '$remoteInputDir'"
    }
    catch {
      Write-Warning "Could not confirm removal of staged authentication inputs."
    }
  }
}
