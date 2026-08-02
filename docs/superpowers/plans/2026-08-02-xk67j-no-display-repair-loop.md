# XK67J No-Display Repair Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first source-controlled XK67J technician path from `无显示` selection to synchronized U2411 navigation, a recorded location check, and an explicit source boundary.

**Architecture:** Extend the existing generated XK67J cross-source dataset with one privacy-reduced evidence record, one U2411 entity, and one boundary-only repair flow. Reuse the existing repair-flow state machine and three-view navigation, adding only the flow-to-photo selection bridge needed to open the exact annotated evidence image.

**Tech Stack:** Python 3 builders and `unittest`; browser-native JavaScript ES modules and Node test runner; Canvas/Three.js workbench already present in the repository.

---

### Task 1: Lock the source evidence contract

**Files:**
- Modify: `tests/test_build_xk67j_registration.py`
- Modify: `scripts/build_xk67j_registration.py`
- Regenerate: `knowledge-base/xk67j-cross-source-registration.json`

- [ ] **Step 1: Write failing Python tests** requiring entity `XK67J-MAIN-U2411`, SCH page 9 and part `OCP2130WPAD-G`, privacy-reduced cases `CASE-0022` and `CASE-0025`, photo hash `28a193...`, `repair_coverage.status = source_boundary_only`, and one flow with only boundary outcomes.
- [ ] **Step 2: Run the focused test** with `python -m unittest tests.test_build_xk67j_registration -v` and confirm failures report the missing U2411/evidence/flow data.
- [ ] **Step 3: Add minimal builder helpers** for case evidence and U2411 source links. Do not include IMEI, operator, country, inferred thresholds, inferred causality, or repair actions.
- [ ] **Step 4: Generate the dataset** with `python scripts/build_xk67j_registration.py` and assert the builder reports 13 entities and 1 repair flow.
- [ ] **Step 5: Run focused Python tests** and confirm they pass.
- [ ] **Step 6: Commit** the builder, generated dataset, and tests with `feat: add XK67J no-display source path`.

### Task 2: Add boundary-only flow and photo synchronization state

**Files:**
- Modify: `tests/repair-flow-state.test.mjs`
- Modify: `assets/cross-source-registration/repair-flow-state.js`
- Modify: `tests/photo-navigation-state.test.mjs`
- Modify: `assets/cross-source-registration/photo-navigation-state.js`

- [ ] **Step 1: Write failing Node tests** proving the compiled XK67J flow targets U2411, records `location_match` or `location_unconfirmed`, reaches only a boundary terminal, and never exposes action execution.
- [ ] **Step 2: Write a failing photo-state test** for resolving an exact `source_photo_sha256` to the matching photo ID on the active side while failing closed for unknown hashes.
- [ ] **Step 3: Run** `node --test tests/repair-flow-state.test.mjs tests/photo-navigation-state.test.mjs` and confirm the new hash resolver and XK67J assertions fail for missing behaviour.
- [ ] **Step 4: Implement the minimal pure-state resolver** and preserve existing flow semantics; no global browser state belongs in these modules.
- [ ] **Step 5: Re-run the focused Node tests** and confirm all pass.
- [ ] **Step 6: Commit** with `feat: synchronize repair flow photo evidence`.

### Task 3: Wire the workbench interaction

**Files:**
- Modify: `assets/cross-source-registration/app.js`
- Modify: `assets/cross-source-registration/index.html` only if an accessibility label is missing
- Modify: `assets/cross-source-registration/styles.css` only for boundary/evidence readability
- Modify: relevant static workbench tests under `tests/`

- [ ] **Step 1: Add failing static tests** requiring flow start to select U2411, side 2, and the exact annotated photo; require the terminal to be labelled `资料边界`, not `维修处理`.
- [ ] **Step 2: Run the focused static tests** and confirm the expected integration hooks are absent.
- [ ] **Step 3: Update `startRepairEntry`/flow application** to resolve `source_photo_sha256`, switch to the declared side, and activate the matching photo before focusing U2411.
- [ ] **Step 4: Render source records** from the flow without turning their field finding into a system diagnosis. Keep action execution and post-action recheck hidden because both declared outcomes are boundaries.
- [ ] **Step 5: Run focused Node and Python tests** and confirm the selected photo and boundary rendering are stable.
- [ ] **Step 6: Commit** with `feat: add XK67J technician boundary workflow`.

### Task 4: Regression, browser QA, and evidence

**Files:**
- Modify: `docs/engineering-source-intake-2026-07-31-km5-xk67j.md`
- Modify: `reports/board-catalog-batch-acceptance.md`
- Modify: generated acceptance JSON if required by the existing report builder
- Create: browser QA screenshots under the repository's existing ignored/output path

- [ ] **Step 1: Run full Python regression** using the repository's established unittest discovery command and record pass/skip counts.
- [ ] **Step 2: Run full Node regression** with `node --test tests/*.test.mjs` and record the pass count.
- [ ] **Step 3: Start a local static server** on a free loopback port and open `assets/cross-source-registration/index.html?board=xk67j-shared`.
- [ ] **Step 4: Desktop QA** fault selection, photo B activation, U2411 focus in photo/point-map/2.5D, location result, boundary close/reset, pan/zoom, and side switching.
- [ ] **Step 5: 390 px QA** repeat the repair path and verify no overlap, clipped labels, unreadable controls, or accidental action controls.
- [ ] **Step 6: Update source audit and acceptance report** to say `source_boundary_only`; explicitly retain the missing electrical-test-standard gap.
- [ ] **Step 7: Commit** with `docs: record XK67J repair loop acceptance`.

### Task 5: Independent review and project return

**Files:**
- Modify: implementation repository project ledger if present
- Modify: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md` or its current equivalent
- Modify: relevant Vault project status note under `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/`

- [ ] **Step 1: Request an independent code review** focused on source contamination, unsupported diagnosis/action claims, state regressions, and missing tests.
- [ ] **Step 2: Address every valid finding with TDD** and rerun focused plus full tests.
- [ ] **Step 3: Run `git diff --check` and inspect `git status --short`** to ensure only intended changes remain.
- [ ] **Step 4: Write back** the achieved capability, exact evidence boundary, validation counts, commits, and next required material: an XK67J-approved no-display electrical test/repair instruction.
- [ ] **Step 5: Commit local ledger/Vault changes** in their owning repositories. Do not push or deploy.

