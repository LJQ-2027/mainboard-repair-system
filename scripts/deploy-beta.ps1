param(
  [string]$HostName = "8.217.28.36",
  [string]$User = "root",
  [string]$RemoteDir = "/opt/motherboard-repair-beta",
  [string]$ProcessName = "motherboard-repair-beta",
  [string]$Port = "3010",
  [string]$KeyPath = ""
)

$ErrorActionPreference = "Stop"

function Require-Command($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $name"
  }
}

Require-Command git
Require-Command ssh
Require-Command scp

if (-not $KeyPath) {
  throw "Pass -KeyPath with the SSH private key path. Do not store keys in the repo."
}

$resolvedKey = (Resolve-Path -LiteralPath $KeyPath).Path
$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$dirty = git status --porcelain
if ($dirty) {
  throw "Working tree has uncommitted changes. Commit or restore changes before deployment."
}

$deployRoot = Join-Path $repoRoot ".local\deploy"
New-Item -ItemType Directory -Force -Path $deployRoot | Out-Null
$artifact = Join-Path $deployRoot "motherboard-repair-beta.tar.gz"
if (Test-Path $artifact) {
  Remove-Item -LiteralPath $artifact -Force
}

$commit = (git rev-parse --short HEAD).Trim()
git archive --format=tar.gz -o $artifact HEAD

Write-Host "Uploading $artifact to ${User}@${HostName}:${RemoteDir}/deploy.tar.gz"
ssh -i $resolvedKey "${User}@${HostName}" "mkdir -p '$RemoteDir'"
scp -i $resolvedKey $artifact "${User}@${HostName}:${RemoteDir}/deploy.tar.gz"

$remoteScript = @"
set -euo pipefail
REMOTE_DIR='$RemoteDir'
APP_DIR="`$REMOTE_DIR/app"
PROCESS_NAME='$ProcessName'
PORT='$Port'

echo "== prepare directories =="
mkdir -p "`$REMOTE_DIR"
mkdir -p "`$REMOTE_DIR/logs"

echo "== preserve env =="
if [ -f "`$APP_DIR/.env" ]; then
  cp "`$APP_DIR/.env" "`$REMOTE_DIR/.env.preserved"
fi

echo "== replace app files =="
rm -rf "`$REMOTE_DIR/app.new"
mkdir -p "`$REMOTE_DIR/app.new"
tar -xzf "`$REMOTE_DIR/deploy.tar.gz" -C "`$REMOTE_DIR/app.new"
rm -rf "`$APP_DIR"
mv "`$REMOTE_DIR/app.new" "`$APP_DIR"

if [ -f "`$REMOTE_DIR/.env.preserved" ]; then
  mv "`$REMOTE_DIR/.env.preserved" "`$APP_DIR/.env"
elif [ ! -f "`$APP_DIR/.env" ]; then
  cp "`$APP_DIR/.env.example" "`$APP_DIR/.env"
  echo "Created placeholder .env. Configure ANTHROPIC_API_KEY before using AI features."
fi

echo '$commit' > "`$APP_DIR/VERSION"

echo "== configure pm2 =="
cd "`$APP_DIR"
if pm2 describe "`$PROCESS_NAME" >/dev/null 2>&1; then
  PORT="`$PORT" STATIC_ROOT="`$APP_DIR" INDEX_FILE="mainboard_repair_system_v7.4_updated.html" pm2 restart "`$PROCESS_NAME" --update-env
else
  PORT="`$PORT" STATIC_ROOT="`$APP_DIR" INDEX_FILE="mainboard_repair_system_v7.4_updated.html" pm2 start ai_proxy_server.py --name "`$PROCESS_NAME" --interpreter python3
fi
pm2 save

echo "== health check =="
sleep 2
curl -fsS "http://127.0.0.1:`$PORT/health" >/tmp/motherboard-repair-health.json
cat /tmp/motherboard-repair-health.json
echo
curl -fsSI "http://127.0.0.1:`$PORT/" | head -n 1
pm2 status "`$PROCESS_NAME"
"@

$remoteScript | ssh -i $resolvedKey "${User}@${HostName}" "bash -s"

Write-Host "Deployment finished:"
Write-Host "  http://${HostName}:${Port}/"
Write-Host "  http://${HostName}:${Port}/health"
