# Visual QC Upgrade Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a deterministic read-only rehearsal that proves production `f278061` data can migrate to Local HEAD and roll back safely before any deployment switch.

**Architecture:** A focused core module copies a read-only SQLite snapshot into an isolated temporary data root, validates logical data and object integrity, runs candidate and rollback runtime smokes, and returns a versioned report. A thin CLI validates paths and atomically publishes the report. The existing PowerShell deployment runs the same preflight against its consistent rollback snapshot before switching the app or virtualenv.

**Tech Stack:** Python 3.12, SQLite backup API, FastAPI service core, JSON Schema Draft 2020-12, PowerShell 7, `unittest`.

---

### Task 1: Lock The Report And Snapshot Contract

**Files:**
- Create: `tests/test_visual_qc_upgrade_preflight.py`
- Create: `scripts/visual_qc/upgrade_preflight.py`

- [x] **Step 1: Write failing tests for a read-only source snapshot**

Create a `f278061`-shape SQLite fixture with one proxy case and canonical image
object. Assert `audit_visual_qc_upgrade` returns
`VISUAL-QC-UPGRADE-PREFLIGHT-V1`, records the source backup SHA-256 and logical
digest, and leaves a recursive byte snapshot of the source root unchanged.

- [x] **Step 2: Run the targeted test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_upgrade_preflight.VisualQcUpgradePreflightTests.test_source_snapshot_is_read_only_and_bound -v
```

Expected: import failure for missing `scripts.visual_qc.upgrade_preflight`.

- [x] **Step 3: Implement minimal snapshot helpers**

Add:

```python
UPGRADE_PREFLIGHT_SCHEMA_VERSION = "VISUAL-QC-UPGRADE-PREFLIGHT-V1"
SUPPORTED_SOURCE_VERSIONS = {"f278061"}

def create_read_only_snapshot(source_database: Path, destination: Path) -> dict:
    """Back up source_database through a read-only SQLite connection."""

def database_projection(database: Path) -> dict:
    """Return deterministic schemas, row counts, rows, and logical digests."""

def audit_visual_qc_upgrade(
    *,
    project_root: Path,
    source_database: Path,
    source_data_root: Path,
    source_app_root: Path,
    target_version: str,
    clock: Callable[[], str] = utc_now,
) -> dict:
    """Rehearse migration and runtime compatibility on temporary copies."""
```

Use SQLite URI `mode=ro`, `Connection.backup`, deterministic JSON row encoding,
and SHA-256. Do not instantiate `VisualQcStore` on the source path.

- [x] **Step 4: Run the targeted test and verify GREEN**

Run the Step 2 command. Expected: PASS.

- [x] **Step 5: Commit**

```powershell
git add tests/test_visual_qc_upgrade_preflight.py scripts/visual_qc/upgrade_preflight.py
git commit -m "feat: bind visual qc upgrade snapshots"
```

### Task 2: Fail Closed On Migration Or Object Drift

**Files:**
- Modify: `tests/test_visual_qc_upgrade_preflight.py`
- Modify: `scripts/visual_qc/upgrade_preflight.py`

- [x] **Step 1: Write failing migration preservation tests**

Cover:

- exact `f278061` schema adds only `cases.qualified_handoff_json`;
- shared-column values and counts remain unchanged;
- legacy provenance remains `NULL`;
- an unexpected candidate column or changed legacy value fails;
- source or migrated `PRAGMA integrity_check` failure fails.

- [x] **Step 2: Run the migration tests and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_upgrade_preflight.VisualQcUpgradePreflightTests.test_candidate_migration_is_additive_and_preserves_legacy_rows tests.test_visual_qc_upgrade_preflight.VisualQcUpgradePreflightTests.test_unexpected_schema_drift_fails_closed -v
```

Expected: assertions fail because migration evidence and allowlist enforcement
do not exist.

- [x] **Step 3: Implement migration comparison**

Add stable check ids:

```python
"source_database_integrity"
"candidate_migration_integrity"
"candidate_schema_additive"
"candidate_rows_preserved"
"legacy_provenance_null"
```

Allow only:

```python
{"cases": {"qualified_handoff_json"}}
```

for source `f278061`.

- [x] **Step 4: Write failing object-integrity tests**

Cover canonical original/artifact success plus missing, hash-mismatched,
repository-escaping, and Windows reparse paths.

- [x] **Step 5: Implement canonical object validation and verify GREEN**

Derive managed paths from row SHA-256 and MIME type under:

```text
objects/originals/<prefix>/<sha256>.<ext>
objects/artifacts/<prefix>/<sha256>.<ext>
```

Run the complete test module. Expected: PASS.

- [x] **Step 6: Commit**

```powershell
git add tests/test_visual_qc_upgrade_preflight.py scripts/visual_qc/upgrade_preflight.py
git commit -m "feat: rehearse visual qc data migration"
```

### Task 3: Prove Candidate And Rollback Runtime Compatibility

**Files:**
- Modify: `tests/test_visual_qc_upgrade_preflight.py`
- Modify: `scripts/visual_qc/upgrade_preflight.py`

- [x] **Step 1: Write failing candidate-runtime tests**

Assert the migrated temporary data root returns:

```python
{
    "health": "VISUAL-QC-SERVER-HEALTH-V2",
    "admin_list": "VISUAL-QC-ADMIN-CASE-LIST-V2",
    "admin_detail": "VISUAL-QC-SERVER-CASE-V3",
    "dataset_audit": "VISUAL-QC-DATASET-AUDIT-V1",
}
```

Assert proxy cases remain `non_physical_evidence` and legacy physical cases
without provenance remain `qualified_handoff_provenance_required`.

- [x] **Step 2: Run and verify RED**

Run candidate-runtime tests. Expected: missing runtime evidence assertions.

- [x] **Step 3: Implement zero-worker candidate service smoke**

Instantiate `VisualQcService` only against the temporary data root with
`worker_count=0`, enumerate actors/cases from the migrated database, and compare
health/list/detail/audit totals and schemas.

- [x] **Step 4: Write failing rollback-runtime test**

Build a source app fixture containing `VERSION` and an old `store.py`, then
assert it initializes and reads every case from a second migrated database
copy. Add a failing fixture that rejects the new column.

- [x] **Step 5: Implement isolated rollback store loading and verify GREEN**

Load source `store.py` with `importlib.util.spec_from_file_location` under a
unique module name. Never add `source-app-root` to `sys.path`.

- [x] **Step 6: Commit**

```powershell
git add tests/test_visual_qc_upgrade_preflight.py scripts/visual_qc/upgrade_preflight.py
git commit -m "feat: verify visual qc runtime rollback"
```

### Task 4: Publish A Machine-Readable CLI Contract

**Files:**
- Create: `scripts/audit_visual_qc_upgrade.py`
- Create: `knowledge-base/visual-qc-upgrade-preflight-v1-schema.json`
- Modify: `tests/test_visual_qc_upgrade_preflight.py`
- Modify: `deploy/visual-qc-runtime-files.txt`

- [x] **Step 1: Write failing CLI and Schema tests**

Cover required arguments, source/target version mismatch, unsafe output
placement, no-overwrite publication, deterministic check ordering, Schema
validation, and exit codes `0`, `1`, and `2`.

- [x] **Step 2: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_upgrade_preflight.VisualQcUpgradePreflightCliTests -v
```

Expected: CLI file missing.

- [x] **Step 3: Implement CLI and atomic report publication**

The CLI calls:

```python
audit_visual_qc_upgrade(
    project_root=PROJECT_ROOT,
    source_database=args.source_database,
    source_data_root=args.source_data_root,
    source_app_root=args.source_app_root,
    target_version=args.target_version,
)
```

Write UTF-8 JSON to a sibling temporary file, flush/fsync, and publish with a
no-overwrite atomic operation.

- [x] **Step 4: Define and validate JSON Schema**

Require all identity, check, migration, runtime, dataset, and rollback fields;
disallow additional properties at contract boundaries.

- [x] **Step 5: Add the CLI to the bounded runtime manifest and verify GREEN**

Run the CLI test class and `tests.test_visual_qc_deployment`. Expected: PASS.

- [x] **Step 6: Commit**

```powershell
git add scripts/audit_visual_qc_upgrade.py scripts/visual_qc/upgrade_preflight.py tests/test_visual_qc_upgrade_preflight.py knowledge-base/visual-qc-upgrade-preflight-v1-schema.json deploy/visual-qc-runtime-files.txt
git commit -m "feat: publish visual qc upgrade preflight"
```

### Task 5: Enforce Preflight Before Deployment Switch

**Files:**
- Modify: `scripts/deploy-visual-qc-pilot.ps1`
- Modify: `tests/test_visual_qc_deployment.py`
- Modify: `docs/beta-deployment.md`

- [x] **Step 1: Write failing deployment contract tests**

Assert the remote script invokes the candidate preflight after
`DATABASE_SNAPSHOT_READY=1` and before `mv "$APP_DIR"`, verifies report status,
snapshot SHA-256, and target version, and stores the report in `ROLLBACK_DIR`.

- [x] **Step 2: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_deployment -v
```

Expected: required preflight invocation/order assertions fail.

- [x] **Step 3: Add the fail-closed remote invocation**

Use candidate Python and candidate source while the old app is still present:

```bash
"$VENV_NEW/bin/python" "$APP_NEW/scripts/audit_visual_qc_upgrade.py" \
  --source-database "$ROLLBACK_DIR/visual-qc.sqlite3" \
  --source-data-root "$DATA_DIR" \
  --source-app-root "$APP_DIR" \
  --target-version "__COMMIT__" \
  --output "$ROLLBACK_DIR/upgrade-preflight.json"
```

Parse the report with candidate Python and require `status == "passed"`,
matching snapshot SHA-256, and matching target version before switching files.

- [x] **Step 4: Verify PowerShell and deployment tests**

Parse the script with the PowerShell 7 parser and run
`tests.test_visual_qc_deployment`. Expected: PASS.

- [x] **Step 5: Document the new gate**

State that host `-PreflightOnly` remains a non-mutating infrastructure check,
while every actual deployment now performs a quiesced database rehearsal before
the switch. State that this change does not deploy Local HEAD.

- [x] **Step 6: Commit**

```powershell
git add scripts/deploy-visual-qc-pilot.ps1 tests/test_visual_qc_deployment.py docs/beta-deployment.md
git commit -m "feat: gate visual qc deployment on rehearsal"
```

### Task 6: Production-Like Rehearsal And Closeout

**Files:**
- Create: `docs/visual-qc-upgrade-preflight-2026-07-23.md`
- Modify: `README.md`
- Modify: `docs/visual-qc-server-api-2026-07-20.md`
- Modify: `docs/superpowers/plans/2026-07-23-visual-qc-upgrade-preflight.md`

- [x] **Step 1: Extract the exact rollback store**

Use `git archive f278061` into a temporary directory outside tracked files.
Construct a synthetic `f278061` database with proxy and legacy physical cases
plus canonical object files.

- [x] **Step 2: Run the standalone CLI**

Expected: exit `0`, Schema-valid report, only
`cases.qualified_handoff_json` added, proxy and legacy physical cases excluded,
and rollback smoke passed.

- [x] **Step 3: Prove source immutability**

Compare recursive SHA-256 snapshots before and after rehearsal. Expected:
byte-identical database, companions, and objects.

- [x] **Step 4: Run P0-P2 and local P4-like verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/*.test.mjs
.\.venv\Scripts\python.exe -m compileall scripts tests
git diff --check
```

Validate modified JSON and UTF-8 files. P3 is not required because no browser
or visible UI behavior changes.

- [x] **Step 5: Perform independent review and fix Important findings**

Review safety, no-write claims, TOCTOU boundaries, rollback behavior, report
contract, tests, and documentation against the approved design.

- [x] **Step 6: Update durable facts and commit**

Record implementation commit, verification counts, production unchanged at
`f278061`, and the remaining separate deployment approval gate in repository
and Vault project status. Mark all completed plan boxes.
