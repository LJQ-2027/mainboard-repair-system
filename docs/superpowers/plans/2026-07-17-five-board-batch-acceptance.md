# Five-Board Batch Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate an executable five-board acceptance report that proves whether the current source-driven modeling baseline covers the material and degradation risks already encountered.

**Architecture:** A focused Python module loads the board catalog, resolves repository-relative assets, applies cross-file identity and source-boundary gates, and returns a deterministic audit object. Separate renderers publish JSON and Markdown only after every board and aggregate coverage rule passes.

**Tech Stack:** Python 3, JSON, pathlib, unittest, existing cross-source validator.

---

### Task 1: Board-Level Audit Contract

**Files:**
- Create: `tests/test_board_batch_acceptance.py`
- Create: `scripts/board_batch_acceptance.py`

- [ ] **Step 1: Write failing tests**

Test catalog path resolution, cross-file board-id agreement, side-set agreement, non-empty geometry, entity-side resolution, validator reuse, and explicit repair/reference boundaries with temporary fixtures.

- [ ] **Step 2: Verify the focused test fails**

Run: `py -3 -m unittest tests.test_board_batch_acceptance -v`

Expected: import failure because `scripts.board_batch_acceptance` does not exist.

- [ ] **Step 3: Implement minimal board audit**

Expose `audit_board(root, board_key, entry)` and return a JSON-serializable board result containing `status`, `errors`, source counts, reference mode, repair coverage, side ids, compatible models, and confidence-limited entity count.

- [ ] **Step 4: Verify focused tests pass**

Run: `py -3 -m unittest tests.test_board_batch_acceptance -v`

Expected: all board-level tests pass.

### Task 2: Aggregate Sufficiency Coverage

**Files:**
- Modify: `tests/test_board_batch_acceptance.py`
- Modify: `scripts/board_batch_acceptance.py`

- [ ] **Step 1: Add failing aggregate tests**

Assert that `audit_catalog(root)` reports every catalog board and computes the seven declared risk classes. Remove each representative capability in fixture data and require the corresponding coverage gate to fail.

- [ ] **Step 2: Verify aggregate tests fail**

Run: `py -3 -m unittest tests.test_board_batch_acceptance -v`

Expected: failures because aggregate coverage is not implemented.

- [ ] **Step 3: Implement aggregate evaluation**

Compute coverage only from audited source data. Set `sufficient_for_current_pipeline` only when every board passes and all seven coverage gates are true. Include an explicit scope-boundary list in the result.

- [ ] **Step 4: Verify focused tests pass**

Run: `py -3 -m unittest tests.test_board_batch_acceptance -v`

Expected: all focused tests pass.

### Task 3: Deterministic Reports and CLI

**Files:**
- Modify: `tests/test_board_batch_acceptance.py`
- Modify: `scripts/board_batch_acceptance.py`
- Create: `reports/five-board-batch-acceptance.json`
- Create: `reports/five-board-batch-acceptance.md`

- [ ] **Step 1: Add failing renderer and atomic-publication tests**

Require stable board order, Markdown coverage tables, explicit scope boundaries, nonzero exit behavior, and no output publication when an audit fails.

- [ ] **Step 2: Verify renderer tests fail**

Run: `py -3 -m unittest tests.test_board_batch_acceptance -v`

Expected: failures because rendering and CLI publication do not exist.

- [ ] **Step 3: Implement renderers and CLI**

Add `render_markdown(audit)`, atomic UTF-8 JSON/Markdown writes, `--catalog`, `--json-output`, and `--markdown-output`. Default to the committed catalog and report paths.

- [ ] **Step 4: Generate and inspect reports**

Run: `py -3 scripts/board_batch_acceptance.py`

Expected: five passing boards, seven covered risk classes, and `sufficient_for_current_pipeline: true` only if the committed evidence proves it.

### Task 4: Full Verification and Project Return

**Files:**
- Modify: `PROJECT_LEDGER.md` in `G:/Programming/mainboard-repair-enablement`

- [ ] **Step 1: Run all automated verification**

Run Python discovery, Node tests, the batch CLI, strict UTF-8/U+FFFD checks, and `git diff --check`.

- [ ] **Step 2: Review the generated acceptance evidence**

Confirm counts and risk coverage against the five committed datasets. Treat any uncertain or indirect gate as not covered.

- [ ] **Step 3: Commit implementation and coordination updates**

Commit the audit implementation and generated reports in the implementation repository, then record the proven sufficiency scope and remaining visual-QC/field gaps in the coordination ledger.

