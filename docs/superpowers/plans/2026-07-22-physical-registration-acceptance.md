# Physical Registration Acceptance Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert a validated Milo-supplied physical source package into deterministic image-quality, registration-candidate, and overlay evidence ready for human review.

**Architecture:** A focused Python core validates the existing controlled source package, reuses the existing quality and registration engines, and builds deterministic report/artifact output. A thin CLI publishes the complete run atomically and exposes stable exit codes without modifying or uploading source evidence.

**Tech Stack:** Python 3, OpenCV, NumPy, JSON Schema, `unittest`, existing visual-QC source-library/catalog/registration modules.

---

### Task 1: Lock the report contract

**Files:**
- Create: `knowledge-base/visual-qc-physical-registration-run-v1-schema.json`
- Create: `tests/test_visual_qc_physical_acceptance.py`

- [x] Write a failing schema test for a minimal candidate report and the required physical-evidence boundaries.
- [x] Run `python -m unittest tests.test_visual_qc_physical_acceptance.PhysicalAcceptanceSchemaTests -v` and confirm failure because the schema is missing.
- [x] Add the strict Draft 2020-12 schema with closed top-level, summary, entry, artifact, and status fields while referencing the existing registration-candidate shape inline.
- [x] Re-run the schema test and confirm it passes.

### Task 2: Build reports from validated packages

**Files:**
- Create: `scripts/visual_qc/physical_acceptance.py`
- Modify: `tests/test_visual_qc_physical_acceptance.py`

- [x] Write failing tests that stage a temporary two-side package, run acceptance, and assert package identity, hashes, quality, registration, action precedence, physical-evidence boundaries, and no absolute paths.
- [x] Run the focused tests and confirm failure because `build_physical_registration_run` is missing.
- [x] Implement package validation, catalog/reference loading, image decoding, quality analysis, registration execution, deterministic summary counts, and stable entry ordering.
- [x] Re-run the focused tests and confirm they pass.

### Task 3: Render and publish deterministic overlays

**Files:**
- Modify: `scripts/visual_qc/physical_acceptance.py`
- Modify: `tests/test_visual_qc_physical_acceptance.py`

- [x] Write failing tests for candidate and manual-fallback overlays, byte-identical repeated output, artifact hashes, source-tree immutability, rejected existing output, and output exclusion from the controlled library.
- [x] Run the focused tests and confirm the expected failures.
- [x] Implement fixed-size overlay rendering, artifact metadata, temporary-directory publication, fsync, and atomic rename.
- [x] Re-run the focused tests and confirm they pass.

### Task 4: Add the operator CLI and Markdown report

**Files:**
- Create: `scripts/run_visual_qc_physical_acceptance.py`
- Modify: `scripts/visual_qc/physical_acceptance.py`
- Modify: `tests/test_visual_qc_physical_acceptance.py`
- Modify: `README.md`
- Modify: `knowledge-base/README.md`

- [x] Write failing subprocess tests for success/attention, invalid-package exit `2`, existing-output exit `2`, stable JSON stdout, and a Markdown boundary statement.
- [x] Run the CLI tests and confirm failure because the entry point is missing.
- [x] Implement argument parsing, stable JSON stdout/stderr, exit-code mapping, Markdown generation, and concise operator documentation.
- [x] Re-run the focused tests and confirm they pass.

### Task 5: Regression, acceptance, and durable state

**Files:**
- Modify: `PROJECT_LEDGER.md` in the coordination repository
- Modify: project Vault `Overview.md`, `Task Index.md`, `Risks.md`, and daily architecture check when facts change.

- [x] Run the complete Python suite and confirm zero failures.
- [x] Run the complete Node suite and confirm zero failures.
- [x] Run `python -m py_compile` for new Python modules, JSON/Schema parsing, UTF-8/U+FFFD checks, and `git diff --check`.
- [x] Run a local temporary-library acceptance from staging through report publication, compare source snapshots before/after, and inspect report/overlay evidence.
- [x] Request an independent code review, fix any blocking finding with a new RED/GREEN test, and repeat targeted/full verification.
- [ ] Commit implementation changes locally, then update and commit coordination/Vault facts without attempting GitHub push under the current network constraint.
