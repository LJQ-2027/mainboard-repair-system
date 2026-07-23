# Visual-QC Deployment Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind every Visual-QC migration rehearsal and runtime switch to one full Git commit and the exact uploaded runtime archive bytes.

**Architecture:** A small Python contract module and CLI deterministically build and validate `VISUAL-QC-DEPLOYMENT-MANIFEST-V1`. The PowerShell deployment uploads the manifest beside the archive, verifies both before extraction, verifies the extracted runtime boundary, and passes the same evidence into the existing upgrade report before any switch.

**Tech Stack:** Python 3 standard library, JSON Schema Draft 2020-12, PowerShell 7, Bash, Git archive, SHA-256, `unittest`.

---

### Task 1: Define And Build The Deployment Manifest

**Files:**
- Create: `scripts/visual_qc/deployment_manifest.py`
- Create: `scripts/build_visual_qc_deployment_manifest.py`
- Create: `knowledge-base/visual-qc-deployment-manifest-v1-schema.json`
- Create: `tests/test_visual_qc_deployment_manifest.py`

- [x] **Step 1: Write failing contract tests**

Add tests that call:

```python
manifest = build_deployment_manifest(
    archive=archive,
    runtime_manifest=runtime_manifest,
    commit_sha="a" * 40,
)
```

Require the exact six fields, archive SHA-256, byte count, raw runtime-manifest
SHA-256, normalized path count, and Schema validity. Add rejection tests for a
short or uppercase commit, empty archive, duplicate/unsafe runtime paths, and
extra manifest properties.

- [x] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_deployment_manifest -v
```

Expected: import failure because `deployment_manifest.py` does not exist.

- [x] **Step 3: Implement the contract**

Implement:

```python
DEPLOYMENT_MANIFEST_SCHEMA_VERSION = "VISUAL-QC-DEPLOYMENT-MANIFEST-V1"
FULL_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")

def normalized_runtime_paths(runtime_manifest: Path) -> list[str]:
    """Return unique, safe, non-comment POSIX runtime paths."""

def build_deployment_manifest(
    *,
    archive: Path,
    runtime_manifest: Path,
    commit_sha: str,
) -> dict:
    """Return deterministic archive and runtime-bound deployment evidence."""

def validate_deployment_manifest(manifest: dict) -> dict:
    """Fail closed unless manifest shape and scalar values match V1."""
```

The CLI accepts `--archive`, `--runtime-manifest`, `--commit-sha`, and
`--output`, writes UTF-8 JSON atomically without overwrite, prints the compact
manifest, and returns `0`; validation/publication failures print typed JSON and
return `2`.

- [x] **Step 4: Verify GREEN**

Run the Task 1 test command. Expected: all tests pass.

- [x] **Step 5: Commit**

```powershell
git add scripts/visual_qc/deployment_manifest.py scripts/build_visual_qc_deployment_manifest.py knowledge-base/visual-qc-deployment-manifest-v1-schema.json tests/test_visual_qc_deployment_manifest.py
git commit -m "feat: define visual qc deployment manifest"
```

### Task 2: Bind Upgrade Reports To Deployment Evidence

**Files:**
- Modify: `scripts/visual_qc/upgrade_preflight.py`
- Modify: `scripts/audit_visual_qc_upgrade.py`
- Modify: `knowledge-base/visual-qc-upgrade-preflight-v1-schema.json`
- Modify: `tests/test_visual_qc_upgrade_preflight.py`

- [x] **Step 1: Write failing upgrade-binding tests**

Require:

```python
report["target"] == {
    "version": "b" * 40,
    "archive_sha256": "c" * 64,
    "archive_bytes": 4096,
    "runtime_manifest_sha256": "d" * 64,
}
```

Add CLI rejection tests for short commits, uppercase/short hashes, zero archive
bytes, and omitted target evidence. Validate the resulting report through the
existing V1 Schema.

- [x] **Step 2: Run tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_upgrade_preflight -v
```

Expected: target evidence arguments and fields are missing.

- [x] **Step 3: Implement strict target evidence**

Change `audit_visual_qc_upgrade` to require:

```python
target_version: str
target_archive_sha256: str
target_archive_bytes: int
target_runtime_manifest_sha256: str
```

Require a full commit, lowercase SHA-256 values, and positive bytes. Add CLI
arguments:

```text
--target-archive-sha256
--target-archive-bytes
--target-runtime-manifest-sha256
```

Update the report Schema target object with the four required values and no
additional properties.

- [x] **Step 4: Verify GREEN**

Run the Task 2 test command. Expected: all upgrade tests pass.

- [x] **Step 5: Commit**

```powershell
git add scripts/visual_qc/upgrade_preflight.py scripts/audit_visual_qc_upgrade.py knowledge-base/visual-qc-upgrade-preflight-v1-schema.json tests/test_visual_qc_upgrade_preflight.py
git commit -m "feat: bind upgrade report to runtime archive"
```

### Task 3: Verify Archive Identity Before Extraction

**Files:**
- Modify: `scripts/deploy-visual-qc-pilot.ps1`
- Modify: `tests/test_visual_qc_deployment.py`
- Modify: `deploy/visual-qc-runtime-files.txt`

- [x] **Step 1: Write failing deployment-order tests**

Assert the script:

- resolves `git rev-parse HEAD`, never `--short HEAD`, for identity;
- creates `deployment-manifest.json` with the builder CLI;
- uploads archive and manifest;
- embeds full and short commits separately;
- validates exact manifest keys, archive bytes, and archive SHA-256 with system
  Python before `tar -xzf`;
- rejects mismatch before app staging.

- [x] **Step 2: Run tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_deployment -v
```

Expected: assertions fail because the manifest and remote verification are
absent.

- [x] **Step 3: Implement local build and remote pre-extraction verification**

Use the full commit:

```powershell
$commit = (git rev-parse HEAD).Trim()
$shortCommit = $commit.Substring(0, 12)
```

Run the builder after `git archive`, upload both immutable inputs, and inject
only validated hexadecimal/integer evidence into the remote script. Before
`tar -xzf`, system Python must:

```python
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if set(manifest) != EXPECTED_KEYS:
    raise SystemExit("Deployment manifest keys are invalid.")
if hashlib.sha256(archive_path.read_bytes()).hexdigest() != expected_hash:
    raise SystemExit("Runtime archive SHA-256 mismatch.")
if archive_path.stat().st_size != expected_bytes:
    raise SystemExit("Runtime archive byte-size mismatch.")
```

Stream the hash in the actual implementation rather than loading the archive
into memory.

- [x] **Step 4: Verify GREEN and commit**

Run deployment tests and the PowerShell parser, then commit:

```powershell
git add scripts/deploy-visual-qc-pilot.ps1 tests/test_visual_qc_deployment.py deploy/visual-qc-runtime-files.txt
git commit -m "feat: verify visual qc archive before extraction"
```

### Task 4: Verify Extracted Runtime And Preflight Binding

**Files:**
- Modify: `scripts/deploy-visual-qc-pilot.ps1`
- Modify: `tests/test_visual_qc_deployment.py`
- Modify: `.local/upgrade-preflight-rehearsal/run_rehearsal.py` (ignored evidence helper)

- [x] **Step 1: Write failing extracted-boundary tests**

Assert that, after extraction and before migration rehearsal, the script:

- hashes the extracted runtime manifest;
- checks normalized path count and every listed path;
- writes full commit to `APP_NEW/VERSION`;
- passes all target manifest evidence to the upgrade CLI;
- verifies all report target values before `mv "$APP_DIR"`.

- [x] **Step 2: Run tests and verify RED**

Run deployment and upgrade test modules. Expected: extracted-boundary and
report-binding assertions fail.

- [x] **Step 3: Implement the boundary**

Use system Python for extracted-path verification, candidate Python for the
upgrade preflight, and the already validated embedded values for all CLI
arguments and report comparisons. Copy the deployment manifest into the
commit-versioned rollback directory before input cleanup.

- [x] **Step 4: Verify GREEN and commit**

Run focused tests, PowerShell parser, and one synthetic local manifest build.
Commit:

```powershell
git add scripts/deploy-visual-qc-pilot.ps1 tests/test_visual_qc_deployment.py
git commit -m "feat: bind visual qc switch to verified runtime"
```

### Task 5: Documentation, Rehearsal, Review, And Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/beta-deployment.md`
- Modify: `docs/visual-qc-upgrade-preflight-2026-07-23.md`
- Modify: `docs/superpowers/plans/2026-07-23-visual-qc-deployment-manifest.md`

- [ ] **Step 1: Update operator and evidence documentation**

Document the V1 deployment manifest, full commit, archive/runtime hashes,
pre-extraction failure behavior, unsigned boundary, and unchanged production
state.

- [ ] **Step 2: Run focused and full verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_deployment_manifest tests.test_visual_qc_upgrade_preflight tests.test_visual_qc_deployment -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
$files = rg --files tests | Where-Object { $_ -match '\.test\.mjs$' }; node --test $files
.\.venv\Scripts\python.exe -m compileall -q scripts tests
```

Also parse modified JSON and PowerShell, run `git diff --check`, and scan
modified durable files as strict UTF-8 without U+FFFD.

- [ ] **Step 3: Run production-like local evidence**

Build the real bounded runtime archive from final HEAD, generate and validate
its deployment manifest, then run the exact `f278061` rollback rehearsal with
the same full commit/archive/runtime evidence. Require ten passed checks,
old-store readability, and source immutability.

- [ ] **Step 4: Request independent review**

Review archive verification order, shell/Python argument safety, report
binding, rollback mutation boundaries, no-clobber publication, tests, and
documentation. Fix every Critical or Important issue and rerun affected
verification.

- [ ] **Step 5: Update durable facts and commit**

Record final implementation commit, verification counts, independent review,
production unchanged at `f278061`, and the remaining separately approved
deployment/P4 gate in the coordination ledger, Vault project files, and daily
architecture check. Mark every plan checkbox complete.
