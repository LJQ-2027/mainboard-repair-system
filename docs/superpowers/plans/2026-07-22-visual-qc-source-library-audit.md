# Visual QC Source Library Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, read-only audit for controlled visual source packages and content-addressed originals.

**Architecture:** Keep scan/report logic in a new `scripts/visual_qc/source_audit.py` module and expose it through a thin JSON CLI. Reuse `validate_source_package`, canonical proxy inventory, image evidence, and controlled-path checks; do not add cleanup, upload, or inference behavior.

**Tech Stack:** Python standard library, existing OpenCV-backed image evidence, `unittest`, existing source-package contracts.

---

### Task 1: Audit Contract And Healthy Library

**Files:**
- Create: `scripts/visual_qc/source_audit.py`
- Create: `tests/test_visual_qc_source_audit.py`

- [ ] **Step 1: Write failing healthy-library and determinism tests**

Stage a two-side temporary package with `stage_source_package`, snapshot every library file byte-for-byte, and assert two calls to `audit_source_library(project_root, library_root)` return identical `VISUAL-QC-SOURCE-AUDIT-V1` reports with `status=healthy`, one valid package, two referenced objects, no invalid objects, and no orphans. Assert the before/after snapshots are identical.

- [ ] **Step 2: Run focused test and verify RED**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_visual_qc_source_audit -v`

Expected: import failure because `scripts.visual_qc.source_audit` does not exist.

- [ ] **Step 3: Implement the deterministic report skeleton**

Implement `audit_source_library(project_root: Path, library_root: Path) -> dict`. Require an existing external directory, enumerate non-`.locks` package directories in name order, call `validate_source_package`, collect valid package records and referenced object paths, and return exact top-level fields `schema_version`, `status`, `counts`, `packages`, `invalid_objects`, and `orphaned_objects`.

- [ ] **Step 4: Run focused test and verify GREEN**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_visual_qc_source_audit -v`

Expected: healthy-library and non-mutation tests pass.

### Task 2: Package And Object Findings

**Files:**
- Modify: `scripts/visual_qc/source_audit.py`
- Modify: `tests/test_visual_qc_source_audit.py`

- [ ] **Step 1: Write failing finding-category tests**

Add independent fixtures for: removed `.complete`, corrupt source manifest, current proxy revocation, valid orphan object, malformed object filename, corrupt canonical object bytes, unexpected package file in place of a directory, and object-prefix/package junction. Assert stable sorted records and that only orphan-only output uses `attention`; every integrity defect uses `issues`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_visual_qc_source_audit -v`

Expected: failures for missing categories and object enumeration.

- [ ] **Step 3: Implement package and object classification**

Catch validation failures per package and map them to stable `incomplete_package`, `invalid_package`, or `unsafe_path` codes. Enumerate `objects/originals` without following links; require lowercase canonical filename, two-character hash prefix, supported canonical extension, decoded image evidence, and exact SHA-256. Count references only from valid package entries and classify valid unreferenced objects as informational orphans.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_visual_qc_source_audit -v`

Expected: all report-category tests pass and fixtures remain unchanged.

### Task 3: Machine-Readable CLI And Closeout

**Files:**
- Create: `scripts/audit_visual_qc_source_library.py`
- Modify: `tests/test_visual_qc_source_audit.py`
- Modify: `README.md`
- Modify: `docs/visual-qc-capture-intake-spec-2026-07-20.md`
- Modify: `docs/superpowers/plans/2026-07-22-visual-qc-source-library-audit.md`

- [ ] **Step 1: Write failing direct CLI tests**

Invoke the script from outside the repository. Assert one stdout JSON object, empty stderr, exit `0` for healthy/attention, exit `1` for integrity issues/unexpected failures, exit `2` for missing/invalid root, and no filesystem mutation.

- [ ] **Step 2: Run CLI tests and verify RED**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_visual_qc_source_audit -v`

Expected: failure because the CLI does not exist.

- [ ] **Step 3: Implement the thin CLI and documentation**

Add required `--library-root`, use the repository root derived from the script location, print the complete report for successful audits, and print `status=validation_failed` or `status=failed` JSON for handled failures. Document the command immediately after staging and state that it never cleans up or uploads.

- [ ] **Step 4: Run full verification**

Run:

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
$files = rg --files tests | Where-Object { $_ -match '\.test\.mjs$' }; node --test $files
./.venv/Scripts/python.exe -m py_compile scripts/audit_visual_qc_source_library.py scripts/visual_qc/source_audit.py
git diff --check
```

Expected: all tests and checks pass.

- [ ] **Step 5: Run local CLI acceptance and commit**

Stage a temporary two-image package, audit it as healthy, add one valid unreferenced content-addressed object and audit it as attention, then remove a completion marker and audit it as issues. Confirm all snapshots remain unchanged and no network call occurs. Commit implementation, docs, tests, and the checked plan.
