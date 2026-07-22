# Visual QC Intake Batch Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local command that converts explicitly assigned board-side photos into a hash-bound, validated visual-QC intake manifest.

**Architecture:** Add a focused builder module beside the existing intake validator and a thin executable CLI at `scripts/create_visual_qc_intake_batch.py`. The builder resolves canonical board sides, reuses intake image evidence and final validation, writes atomically, and leaves the existing upload importer unchanged.

**Tech Stack:** Python 3, argparse, pathlib, OpenCV through the existing intake module, unittest, JSON.

---

### Task 1: Builder Contract

**Files:**
- Create: `scripts/visual_qc/intake_builder.py`
- Create: `tests/test_visual_qc_intake_builder.py`

- [ ] **Step 1: Write failing tests for assignment parsing and deterministic manifest generation**

Cover `parse_image_assignment("main_page_1=C:/photos/front.jpg")`, malformed assignments, duplicate sides, duplicate resolved paths, canonical side lookup, deterministic `<session>-<side>` entry IDs, sorted input order, absolute paths, computed SHA-256 values, and all-true confirmed checklist fields.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m unittest tests.test_visual_qc_intake_builder -v`

Expected: FAIL because `scripts.visual_qc.intake_builder` does not exist.

- [ ] **Step 3: Implement the builder boundary**

Expose these functions:

```python
def parse_image_assignment(raw: str) -> tuple[str, Path]: ...

def build_intake_manifest(
    *,
    project_root: Path,
    batch_id: str,
    board_key: str,
    capture_session_id: str,
    capture_stage: str,
    capture_setup_id: str,
    image_assignments: list[tuple[str, Path]],
    capture_checklist_confirmed: bool,
) -> dict: ...

def create_validated_intake_manifest(
    *,
    output_path: Path,
    force: bool = False,
    **builder_options: object,
) -> dict: ...
```

Use `BoardCatalog`, `_image_evidence`, `_require_safe_id`, `CAPTURE_STAGES`, `BATCH_SCHEMA_VERSION`, `validate_intake_batch`, and `write_json_atomic` from existing modules. Reject missing confirmation, duplicates, unknown sides, and existing output unless `force=True`. Delete a newly written output if final validation fails.

- [ ] **Step 4: Run focused tests and verify pass**

Run: `python -m unittest tests.test_visual_qc_intake_builder -v`

Expected: all builder tests PASS.

- [ ] **Step 5: Commit the builder core**

```bash
git add scripts/visual_qc/intake_builder.py tests/test_visual_qc_intake_builder.py
git commit -m "feat: build validated visual QC intake manifests"
```

### Task 2: Command-Line Interface

**Files:**
- Create: `scripts/create_visual_qc_intake_batch.py`
- Modify: `tests/test_visual_qc_intake_builder.py`

- [ ] **Step 1: Write failing direct-invocation CLI tests**

Invoke the script through `subprocess` from a temporary working directory. Assert exit code `0` and a JSON summary for a valid image; assert exit code `2` and no manifest for missing checklist confirmation, malformed assignment, unknown side, invalid image, and protected existing output.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m unittest tests.test_visual_qc_intake_builder -v`

Expected: FAIL because the command does not exist.

- [ ] **Step 3: Implement argparse and typed error output**

Provide `--batch-id`, `--board-key`, `--capture-session-id`, `--capture-stage`, repeatable `--image`, `--confirm-capture-checklist`, `--capture-setup-id`, `--output`, and `--force`. Bootstrap the repository root into `sys.path` for direct invocation. Print one JSON object with `status`, `batch_id`, `manifest`, `entry_count`, and evidence rows on success; print `status=validation_failed` and `message` on operator/input errors.

- [ ] **Step 4: Run focused tests and verify pass**

Run: `python -m unittest tests.test_visual_qc_intake_builder -v`

Expected: all builder and CLI tests PASS.

- [ ] **Step 5: Commit the CLI**

```bash
git add scripts/create_visual_qc_intake_batch.py tests/test_visual_qc_intake_builder.py
git commit -m "feat: add visual QC intake batch command"
```

### Task 3: End-To-End Compatibility And Documentation

**Files:**
- Modify: `docs/visual-qc-capture-intake-spec-2026-07-20.md`
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-07-22-visual-qc-intake-batch-builder.md`

- [ ] **Step 1: Run the builder against two existing proxy images**

Use KM4's two known board-side engineering textures and write the generated manifest under a temporary directory. Do not add the generated manifest or receipt to Git.

- [ ] **Step 2: Run the existing importer in dry-run mode**

Run: `python scripts/import_visual_qc_batch.py <manifest> --dry-run`

Expected: exit code `0`, two `validated` receipt entries, correct board/side identities, and no server upload.

- [ ] **Step 3: Document the exact owner workflow**

Add a concise command example showing builder creation, local dry-run, and subsequent authenticated import. State that explicit checklist confirmation records Codex's completed intake check and that proxy images prove plumbing only, not physical QC accuracy.

- [ ] **Step 4: Run regression and repository checks**

Run:

```bash
python -m unittest discover -s tests -p "test_*.py"
npm test
python -m py_compile scripts/create_visual_qc_intake_batch.py scripts/visual_qc/intake_builder.py
git diff --check
```

Expected: all Python and Node tests PASS; compilation and diff checks return exit code `0`.

- [ ] **Step 5: Commit documentation and plan closeout**

```bash
git add README.md docs/visual-qc-capture-intake-spec-2026-07-20.md docs/superpowers/plans/2026-07-22-visual-qc-intake-batch-builder.md
git commit -m "docs: add visual QC batch creation workflow"
```
