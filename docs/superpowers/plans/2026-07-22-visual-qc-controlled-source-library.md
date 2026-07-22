# Visual QC Controlled Source Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve Milo-supplied physical-board photos in a deterministic content-addressed local library and generate the existing validated intake manifest from archived originals.

**Architecture:** Add a focused source-library module that validates all input through the current physical-intake boundary, publishes hash-addressed originals without replacement, and atomically publishes one immutable package directory. Add a thin CLI and a V1 JSON schema; leave server upload and the existing importer unchanged.

**Tech Stack:** Python 3, argparse, pathlib, hashlib, tempfile, JSON, OpenCV through the existing intake evidence helper, unittest.

---

### Task 1: Source Package Contract And Core

**Files:**
- Create: `knowledge-base/visual-qc-source-package-v1-schema.json`
- Create: `scripts/visual_qc/source_library.py`
- Create: `tests/test_visual_qc_source_library.py`

- [ ] **Step 1: Write failing tests for deterministic source-package construction**

Create two temporary JPEG/PNG inputs outside the repository and assert:

```python
payload = build_source_package(
    project_root=ROOT,
    library_root=library,
    package_id="km4-unit-001-source",
    batch_id="km4-unit-001-batch",
    board_key="km4-f151",
    capture_session_id="km4-unit-001",
    capture_stage="before_repair",
    capture_setup_id="standard-bench",
    image_assignments=[("main_page_1", front), ("main_page_2", back)],
    milo_physical_source_confirmed=True,
    capture_checklist_confirmed=True,
)
```

Assert schema version, fixed source origin, canonical board id, sorted sides, original filename, MIME-derived relative object path, dimensions, byte size, and SHA-256. Add failures for missing physical-source confirmation, repository-contained library root, duplicate sides/paths, malformed image, and copied known proxy bytes.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_source_library -v`

Expected: import failure because `scripts.visual_qc.source_library` does not exist.

- [ ] **Step 3: Implement deterministic package construction**

Expose:

```python
SOURCE_PACKAGE_SCHEMA_VERSION = "VISUAL-QC-SOURCE-PACKAGE-V1"

def build_source_package(...) -> dict: ...
def validate_source_package(package_path: Path, project_root: Path, library_root: Path) -> dict: ...
```

Call `build_intake_manifest` first so board identity, explicit side assignment, capture checklist, image evidence, repository separation, and known-proxy fingerprints retain one implementation. Build library-relative paths from detected MIME and SHA-256. Validate the committed package root, exact required fields, safe identifiers, object containment, object existence, MIME/dimensions/size/hash, side uniqueness, and canonical board identity.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_source_library -v`

Expected: package-construction and validation tests PASS.

- [ ] **Step 5: Commit the contract and core**

```bash
git add knowledge-base/visual-qc-source-package-v1-schema.json scripts/visual_qc/source_library.py tests/test_visual_qc_source_library.py
git commit -m "feat: define visual QC controlled source packages"
```

### Task 2: Atomic Staging And Idempotency

**Files:**
- Modify: `scripts/visual_qc/source_library.py`
- Modify: `tests/test_visual_qc_source_library.py`

- [ ] **Step 1: Write failing storage and package-publication tests**

Assert `stage_source_package(...)`:

- copies exact source bytes to canonical object paths;
- produces `source-package.json` and `<batch-id>.intake.json`;
- returns `created` on first run and `reused` for an identical rerun;
- rejects the same package id with changed bytes or metadata;
- rejects a corrupted existing object;
- leaves an existing package unchanged under conflict;
- does not publish a partial package when intake creation fails;
- never modifies the incoming files.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_source_library -v`

Expected: FAIL because staging behavior is absent.

- [ ] **Step 3: Implement no-clobber object and package publication**

Expose:

```python
def stage_source_package(*, project_root: Path, library_root: Path, **options: object) -> dict: ...
```

Validate the complete requested package before creating library paths. Copy each source through a same-directory temporary file, fsync it, verify SHA-256, and publish via no-clobber hard link. Reuse an existing object only after integrity verification. Build the intake manifest from archived object paths. Write both manifests in a temporary package directory and rename it to the final safe package id. Existing packages are reusable only after exact manifest and object validation; all other reuse is a typed conflict.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_source_library -v`

Expected: all staging and idempotency tests PASS.

- [ ] **Step 5: Commit staging**

```bash
git add scripts/visual_qc/source_library.py tests/test_visual_qc_source_library.py
git commit -m "feat: stage immutable visual QC source packages"
```

### Task 3: CLI, Dry-Run Compatibility, And Documentation

**Files:**
- Create: `scripts/stage_visual_qc_source_package.py`
- Modify: `tests/test_visual_qc_source_library.py`
- Modify: `README.md`
- Modify: `docs/visual-qc-capture-intake-spec-2026-07-20.md`
- Modify: `docs/superpowers/plans/2026-07-22-visual-qc-controlled-source-library.md`

- [ ] **Step 1: Write failing direct-invocation CLI tests**

Run the script from outside the repository. Verify success JSON includes package manifest, intake manifest, entry count and `created/reused`; parser and validation errors return exit code 2 with JSON and no stderr; no command path performs upload.

- [ ] **Step 2: Run CLI tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_source_library -v`

Expected: FAIL because the CLI does not exist.

- [ ] **Step 3: Implement the thin CLI**

Add required `--library-root`, `--package-id`, `--batch-id`, board/session/stage parameters, repeatable `--image`, `--confirm-milo-physical-source`, and `--confirm-capture-checklist`. Use the existing validation-argument-parser pattern and print one JSON object.

- [ ] **Step 4: Run a real local plumbing acceptance**

Generate temporary images outside the repository, stage them into a temporary library, run the resulting intake manifest through `scripts/import_visual_qc_batch.py --dry-run`, and confirm two validated entries. Copy a known manual proxy to an external path and confirm staging rejects it. Do not upload or retain the synthetic package as evidence.

- [ ] **Step 5: Document the single-command owner workflow**

Replace direct temporary-photo examples with source staging first, followed by optional importer dry-run and controlled upload. State the exact-hash proxy limitation and canonical inventory requirement.

- [ ] **Step 6: Run full verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
node --test tests/*.test.mjs
.\.venv\Scripts\python.exe -m py_compile scripts/stage_visual_qc_source_package.py scripts/visual_qc/source_library.py
git diff --check
```

Expected: all suites pass and both worktrees remain clean after commits.

- [ ] **Step 7: Commit documentation and closeout**

```bash
git add scripts/stage_visual_qc_source_package.py tests/test_visual_qc_source_library.py README.md docs/visual-qc-capture-intake-spec-2026-07-20.md docs/superpowers/plans/2026-07-22-visual-qc-controlled-source-library.md
git commit -m "docs: add controlled visual source staging workflow"
```
