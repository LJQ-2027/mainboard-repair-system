# Technician Pilot Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a technician-testable eight-board entry that validates model and repair intent, opens the existing workbench at the strongest source-supported state, groups H897 cases by symptom, and records privacy-reduced local pilot feedback.

**Architecture:** Add a small static entry application that reads the existing board catalog and cross-source datasets. Share a pure URL intent contract with the existing workbench, extend the H897 case-navigation state with deterministic symptom groups, and keep feedback in a separate versioned local-storage module. Existing board rendering, repair flows, source evidence, and photo/model synchronization remain authoritative.

**Tech Stack:** Static HTML/CSS, browser ES modules, Node built-in test runner, existing Three.js workbench, localStorage, Blob download, Playwright CLI.

---

## File Map

- Create `assets/technician-pilot/index.html`: technician entry document.
- Create `assets/technician-pilot/styles.css`: dense responsive entry styling.
- Create `assets/technician-pilot/app.js`: catalog/dataset loading and entry rendering.
- Create `assets/technician-pilot/pilot-catalog-state.js`: flatten board aliases and derive capability tiers.
- Create `assets/cross-source-registration/pilot-intent-state.js`: shared intent validation and URL serialization.
- Create `assets/cross-source-registration/pilot-feedback-state.js`: feedback validation, persistence, and export.
- Modify `assets/cross-source-registration/case-navigation-state.js`: deterministic symptom groups and filtered cases.
- Modify `assets/cross-source-registration/app.js`: consume validated intent, preselect flow/group, and render feedback.
- Modify `assets/cross-source-registration/index.html`: pilot context and feedback controls.
- Modify `assets/cross-source-registration/styles.css`: compact context/feedback states and mobile layout.
- Create `tests/pilot-catalog-state.test.mjs`, `tests/pilot-intent-state.test.mjs`, `tests/pilot-feedback-state.test.mjs`, and `tests/technician-pilot-ui.test.mjs`.
- Modify `tests/case-navigation-state.test.mjs` and `tests/photo-navigation-ui.test.mjs` for workbench integration.

### Task 1: Catalog And Capability State

**Files:**
- Create: `assets/technician-pilot/pilot-catalog-state.js`
- Test: `tests/pilot-catalog-state.test.mjs`

- [ ] **Step 1: Write failing catalog tests**

Test explicit alias flattening, exact board retention, tier derivation (`reviewed_flow`, `case_navigation`, `reference_only`), deterministic model ordering, and unknown model rejection through a wished-for API:

```js
const entries = buildPilotCatalog(catalog, datasetsByBoard);
assert.equal(entries.find((item) => item.model === 'KM4n').boardKey, 'xk67j-shared');
assert.equal(entries.find((item) => item.model === 'KJ6').capabilityTier, 'case_navigation');
assert.equal(resolvePilotModel(entries, 'missing'), null);
```

- [ ] **Step 2: Verify RED**

Run `node --test tests/pilot-catalog-state.test.mjs` and confirm module-not-found failure.

- [ ] **Step 3: Implement minimal pure catalog state**

Export `buildPilotCatalog(catalog, datasetsByBoard)` and `resolvePilotModel(entries, model, boardKey)`; derive tiers only from declared `repair_flows` and valid `case_navigation.cases`.

- [ ] **Step 4: Verify GREEN**

Run `node --test tests/pilot-catalog-state.test.mjs`; expected all tests pass.

### Task 2: Shared Pilot Intent Contract

**Files:**
- Create: `assets/cross-source-registration/pilot-intent-state.js`
- Test: `tests/pilot-intent-state.test.mjs`

- [ ] **Step 1: Write failing intent tests**

Cover exact repair-flow validation, H897 symptom-group validation, initial-check flow resolution, unsupported initial-check boundary, query round-trip, cross-board model rejection, and no silent fallback:

```js
const intent = resolvePilotIntent({ boardKey, board, dataset, query });
assert.deepEqual(intent, {
  valid: true,
  kind: 'repair_flow',
  flowId: 'no-power-reviewed',
  label: '无法开机',
});
```

- [ ] **Step 2: Verify RED**

Run `node --test tests/pilot-intent-state.test.mjs`; confirm missing module failure.

- [ ] **Step 3: Implement contract helpers**

Export `buildPilotIntentOptions(dataset)`, `encodePilotIntent(boardEntry, option)`, and `resolvePilotIntent({ boardKey, board, dataset, query })`. Initial check must select a declared `entry_type` containing `unknown` or `initial`; otherwise return a valid boundary intent with no flow ID.

- [ ] **Step 4: Verify GREEN**

Run the targeted test and confirm every intended fail-closed case passes.

### Task 3: H897 Symptom-First Case Navigation

**Files:**
- Modify: `assets/cross-source-registration/case-navigation-state.js`
- Modify: `tests/case-navigation-state.test.mjs`

- [ ] **Step 1: Add failing grouping tests**

Require a stable normalized group key, grouped case/photo counts, preferred-group filtering, first-case selection inside a group, stale preference fallback within that group, and preservation of declared candidate IDs.

```js
const grouped = buildCaseNavigationState(contract, null, '重启-卡-logo');
assert.equal(grouped.activeGroup.caseCount, 1);
assert.ok(grouped.options.every((item) => item.symptoms.includes('重启')));
```

- [ ] **Step 2: Verify RED**

Run `node --test tests/case-navigation-state.test.mjs`; confirm missing group behavior.

- [ ] **Step 3: Implement grouping without changing source cases**

Add `buildCaseSymptomGroups(contract)` and an optional preferred group argument. Group labels use source symptom order; unique photo counts derive from SHA-256 sets. Keep unsafe contract rejection unchanged.

- [ ] **Step 4: Verify GREEN**

Run catalog, intent, and case-navigation tests together.

### Task 4: Technician Entry Application

**Files:**
- Create: `assets/technician-pilot/index.html`
- Create: `assets/technician-pilot/styles.css`
- Create: `assets/technician-pilot/app.js`
- Create: `tests/technician-pilot-ui.test.mjs`

- [ ] **Step 1: Write failing static UI contract tests**

Require a model selector, exact board/version status, one intent selector, capability label, disabled launch state, loading/error region, and module imports. Reject separate known/unknown entry buttons and marketing hero markup.

- [ ] **Step 2: Verify RED**

Run `node --test tests/technician-pilot-ui.test.mjs`; confirm missing files fail.

- [ ] **Step 3: Build the entry document and application**

Fetch the catalog plus every declared dataset, build model entries, render one selected model and one intent list, disable launch on any invalid state, and navigate only with `encodePilotIntent`. Fetch failure names the board and leaves launch disabled.

- [ ] **Step 4: Implement responsive operational styling**

Use a compact header, model rail and intent workspace at desktop, one column at `max-width: 760px`, minimum 40 px touch targets, visible focus rings, no gradients, no nested cards, and no horizontal overflow.

- [ ] **Step 5: Verify GREEN**

Run the four new state/UI test files together.

### Task 5: Workbench Intent And Feedback Integration

**Files:**
- Create: `assets/cross-source-registration/pilot-feedback-state.js`
- Modify: `assets/cross-source-registration/index.html`
- Modify: `assets/cross-source-registration/styles.css`
- Modify: `assets/cross-source-registration/app.js`
- Test: `tests/pilot-feedback-state.test.mjs`
- Modify: `tests/photo-navigation-ui.test.mjs`

- [ ] **Step 1: Write failing feedback tests**

Require valid enums, nonempty feedback, 500-character notes, generated IDs, immutable context, privacy-key rejection, corrupted-storage recovery, deterministic export order, and no board/QC mutation.

```js
const record = createPilotFeedback(context, {
  targetLocation: 'found',
  sourceUsefulness: 'insufficient',
  note: '缺少测量位置',
}, '2026-08-03T00:00:00.000Z');
assert.equal(record.schema_version, 'TECHNICIAN-PILOT-FEEDBACK-V1');
```

- [ ] **Step 2: Verify RED**

Run `node --test tests/pilot-feedback-state.test.mjs`; confirm missing module failure.

- [ ] **Step 3: Implement feedback state**

Export validation, `loadPilotFeedback(storage)`, `savePilotFeedback(storage, records)`, `createPilotFeedback`, and `serializePilotFeedback`. Use one versioned key and fixed JSON property construction; reject identity/privacy fields.

- [ ] **Step 4: Add workbench pilot context and intent preselection**

After loading board data, validate the current URL with `resolvePilotIntent`. Preselect the exact flow or H897 symptom group only when valid. Render an explicit initial-check boundary when no flow exists. Legacy URLs retain current behavior.

- [ ] **Step 5: Add feedback UI and export**

Add compact segmented controls, optional note, save status, count, and download button. Save only after one feedback dimension is selected. Preserve records across reload. Use current board/model/intent/selected entity/case as immutable context.

- [ ] **Step 6: Verify GREEN**

Run feedback, intent, case, and workbench UI tests; then run all Node tests.

### Task 6: Browser QA And Closeout

**Files:**
- Modify generated project acceptance/status documentation only if actual counts change.
- Update Vault project entries after the Git commit.

- [ ] **Step 1: Start a local static server**

Run `.venv/Scripts/python.exe -m http.server 51701 --bind 127.0.0.1` from the repository.

- [ ] **Step 2: Desktop P3**

At 1440x900 verify KM4 reviewed flow, H897 grouped case navigation to a candidate on both photos/point maps/2.5D, and BG6M reference-only initial-check boundary. Capture screenshots and inspect hover, focus, selected, disabled, loading, and boundary readability.

- [ ] **Step 3: Mobile P3**

At 390x844 repeat entry, H897 candidate navigation, view switching, feedback save/reload/export, keyboard/touch controls, no overlap, and no horizontal overflow. Verify the WebGL canvas is visible and nonblank.

- [ ] **Step 4: Final automated gates**

Run:

```powershell
node --test tests/*.test.mjs
.venv\Scripts\python.exe -m unittest tests.test_board_batch_acceptance tests.test_validate_cross_source_registration tests.test_build_h897_registration
.venv\Scripts\python.exe scripts\board_batch_acceptance.py
git diff --check
```

Expected: zero failures and eight-board acceptance passes all seven gates.

- [ ] **Step 5: Encoding and privacy gates**

Strictly decode every changed text file as UTF-8, reject U+FFFD/mojibake, and scan pilot feedback output/contracts for IMEI, technician identity, country, phone number, electrical values, repair verdicts, and training flags.

- [ ] **Step 6: Commit and update durable project facts**

Commit the implementation, update the Mainboard Repair Enablement Vault `Agent Entry`, `Overview`, `Task Index`, and `Risks`, close local runtime processes, and report any P4/deployment gap truthfully.
