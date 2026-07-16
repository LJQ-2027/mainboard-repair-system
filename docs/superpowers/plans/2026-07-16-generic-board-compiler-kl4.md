# Generic Board Compiler and KL4 Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile KM4 and KL4 through one profile-driven source pipeline and run KL4's reviewed small-current no-power flow in the existing workbench.

**Architecture:** A validated JSON profile registry supplies board identity, source paths, side pages, crop bounds, reviewed identities, and output locations. Shared Python pipeline modules render and compile point maps and schematics; thin legacy wrappers preserve KM4 commands. A board catalog replaces hardcoded frontend URLs and selects the dataset through `?board=` without adding board-specific UI logic.

**Tech Stack:** Python 3, pypdf, Pillow, NumPy, Poppler, JSON, browser-native ES modules, Node test runner, unittest, Playwright/Chromium.

---

### Task 1: Board Profile Registry

**Files:**
- Create: `knowledge-base/board-compiler-profiles.json`
- Create: `scripts/board_compiler/profiles.py`
- Create: `tests/test_board_profiles.py`

- [ ] **Step 1: Write failing profile tests**

Test that `load_profile(ROOT, "km4-f151")` and `load_profile(ROOT, "kl4-f201")` return ordered dual-side profiles, resolve existing source PDFs, and reject duplicate side IDs, invalid normalized crops, unresolved default sides, and output traversal.

```python
profile = load_profile(ROOT, "kl4-f201")
self.assertEqual(profile["board_id"], "BOARD-KL4-F201-MAIN-V1.2")
self.assertEqual([side["source_pdf_page"] for side in profile["sides"]], [1, 2])
with self.assertRaisesRegex(ValueError, "source_crop"):
    validate_profile(ROOT, {**profile, "sides": [{**profile["sides"][0], "source_crop": {"x": 0, "y": 0, "width": 2, "height": 1}}]})
```

- [ ] **Step 2: Run the focused tests and confirm missing-module failure**

Run: `python -m unittest tests.test_board_profiles -v`

Expected: FAIL because `scripts.board_compiler.profiles` does not exist.

- [ ] **Step 3: Implement profile loading and validation**

Expose `load_registry(root)`, `load_profile(root, profile_id)`, and `validate_profile(root, profile)`. Validation must check identities, path containment, source existence, side uniqueness, normalized positive crop boxes, default-side membership, and output uniqueness.

- [ ] **Step 4: Add KM4 and KL4 profiles**

Keep current KM4 inputs and outputs. Configure KL4 with `F201_MAIN_V1.2_零件位号.pdf`, `K6735_F201_MAIN_SCH_V1.2维修原理图20240614.pdf`, two ordered main-board pages, deterministic `assets/board-atlas/kl4-f201/` textures, and reviewed identities `U1001`, `U2001`, `X2100`, `VDDCORE`, and `VDDEMMCCORE`.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_board_profiles -v`

Commit: `git commit -m "add board compiler profiles"`

### Task 2: Generic Point-Map Pipeline

**Files:**
- Create: `scripts/board_compiler/pipeline.py`
- Create: `scripts/compile_board.py`
- Modify: `scripts/compile_km4_board.py`
- Create: `tests/test_board_pipeline.py`
- Modify: `tests/test_compile_km4_board.py`

- [ ] **Step 1: Write failing pipeline contract tests**

Use temporary PNG fixtures and mocked primitive extraction to verify that `compile_side()` carries profile board IDs and prefixes, enforces required designators, writes no output on gate failure, and builds an ordered side manifest.

```python
result = compile_side(root, profile, profile["sides"][0], primitives=fake_primitives)
self.assertEqual(result["board_id"], profile["board_id"])
self.assertTrue(result["audit"]["required_recovery_complete"])
self.assertTrue(result["components"][0]["component_id"].startswith(profile["component_prefix"]))
```

- [ ] **Step 2: Confirm the tests fail**

Run: `python -m unittest tests.test_board_pipeline -v`

- [ ] **Step 3: Extract shared geometry compilation**

Move profile-independent behavior from `compile_km4_board.py` into `pipeline.py`: source primitive extraction, texture rendering/cropping, board outline extraction, designator compilation, audit construction, atomic JSON publication, and side manifest generation.

- [ ] **Step 4: Add the generic CLI and KM4 wrapper**

`compile_board.py` must accept `--profile`, `--side`, `--geometry-only`, and `--schematic-only`. The KM4 wrapper must load `km4-f151`, expose its existing `SIDE_CONFIGS` and `build_side_manifest()` compatibility API, and delegate compilation.

- [ ] **Step 5: Prove KM4 semantic compatibility**

Compile KM4 into a temporary output root and compare board ID, side order, source pages, accepted designators, required recovery, component identities, normalized geometry, and outline against the committed outputs.

- [ ] **Step 6: Run focused and legacy tests, then commit**

Run: `python -m unittest tests.test_board_pipeline tests.test_compile_km4_board tests.test_board_compiler -v`

Commit: `git commit -m "extract generic board pipeline"`

### Task 3: Generic Schematic Compilation

**Files:**
- Modify: `scripts/board_compiler/pipeline.py`
- Modify: `scripts/compile_km4_schematic.py`
- Modify: `tests/test_schematic_compiler.py`
- Modify: `tests/test_board_pipeline.py`

- [ ] **Step 1: Add failing schematic pipeline tests**

Assert exact standalone matching, normalized origins, reviewed recovery, board-ID consistency, deterministic occurrence ordering, and atomic publication. Use a temporary PDF fixture or injected extracted pages rather than a model-specific branch.

- [ ] **Step 2: Implement `compile_schematic()`**

The function reads the compiled side identities, indexes exact schematic runs, normalizes origins, builds audit counts, and fails when profile-required schematic identities are absent. Preview generation is optional per profile and remains enabled for KM4's reviewed entities.

- [ ] **Step 3: Convert the KM4 schematic script into a wrapper**

Preserve `knowledge-base/km4-schematic-compiled.json` and existing preview paths while delegating extraction and audit logic.

- [ ] **Step 4: Run tests and commit**

Run: `python -m unittest tests.test_board_pipeline tests.test_schematic_compiler -v`

Commit: `git commit -m "generalize schematic compilation"`

### Task 4: Compile KL4 Source Assets

**Files:**
- Create: `assets/board-atlas/kl4-f201/main-point-map-page-1.png`
- Create: `assets/board-atlas/kl4-f201/main-point-map-page-2.png`
- Create: `knowledge-base/kl4-board-compiled-page-1.json`
- Create: `knowledge-base/kl4-board-compiled.json`
- Create: `knowledge-base/kl4-board-sides.json`
- Create: `knowledge-base/kl4-schematic-compiled.json`
- Create: `tests/test_compile_kl4_board.py`

- [ ] **Step 1: Write failing KL4 output tests**

Require both source pages, nonzero decoded designators and candidate footprints, valid outlines, normalized geometry, matching board IDs, exact source paths, and complete recovery of the reviewed identities declared by the profile.

- [ ] **Step 2: Determine and record source crops**

Render both point-map pages and calculate source-relative crop boxes that contain the complete board while excluding page furniture. Store the reviewed normalized crop values in the KL4 profile; do not derive them from the KM4 crop.

- [ ] **Step 3: Run the generic compiler**

Run: `python scripts/compile_board.py --profile kl4-f201`

Expected: two textures, two geometry outputs, one manifest, one schematic index, and a zero exit code with complete reviewed recovery.

- [ ] **Step 4: Inspect generated textures and audit counts**

Visually verify both images contain the complete board without clipping or unrelated page text. Confirm output JSON contains no absolute local paths and no replacement characters.

- [ ] **Step 5: Run KL4 and full Python tests, then commit**

Run: `python -m unittest tests.test_compile_kl4_board -v`

Run: `python -m unittest discover -s tests -p "test_*.py"`

Commit: `git commit -m "compile kl4 board sources"`

### Task 5: KL4 Reviewed Repair Dataset

**Files:**
- Create: `knowledge-base/kl4-cross-source-registration.json`
- Create: `scripts/validate_repair_board_dataset.py`
- Modify: `scripts/validate_cross_source_registration.py`
- Create: `tests/test_validate_repair_board_dataset.py`
- Modify: `tests/repair-flow-state.test.mjs`

- [ ] **Step 1: Extract the shared validator with failing tests**

Move the current KM4 validator into `validate_repair_board_dataset.py` with a dataset-path argument. Test board-ID consistency, source asset existence, normalized geometry, flow graph validity, measurement references, and target resolution for both datasets.

- [ ] **Step 2: Build the reviewed KL4 entity subset**

Create entities only for source-recovered U1001, U2001, X2100, VDDCORE, and VDDEMMCCORE. Use geometry from compiled KL4 data, exact schematic occurrences, and repair-guide citations. Keep rail identities as non-inspectable measurement locations.

- [ ] **Step 3: Encode the page 10-11 repair flow**

Add one known-fault entry for `不开机`. The first step records VDDCORE and VDDEMMCCORE nominal references and keeps normal/abnormal technician-judged choices. The normal branch advances to X2100's 26 MHz check. Every terminal action must quote the reviewed guide action or stop at a documented boundary.

- [ ] **Step 4: Add flow-state regression coverage**

Load the KL4 flow fixture and assert required-measurement locking, technician judgment for nominal values, target advancement to X2100, and terminal/back/reset behavior.

- [ ] **Step 5: Validate and commit**

Run: `python scripts/validate_repair_board_dataset.py knowledge-base/kl4-cross-source-registration.json`

Run: `node --test tests/repair-flow-state.test.mjs`

Commit: `git commit -m "add kl4 reviewed repair path"`

### Task 6: Board-Catalog Workbench Loading

**Files:**
- Create: `knowledge-base/repair-workbench-boards.json`
- Create: `assets/cross-source-registration/board-catalog-state.js`
- Modify: `assets/cross-source-registration/app.js`
- Modify: `assets/cross-source-registration/index.html`
- Create: `tests/board-catalog-state.test.mjs`
- Modify: `tests/model-toolbar.test.mjs`

- [ ] **Step 1: Write failing board-catalog tests**

Assert default KM4 resolution, exact KL4 resolution, unknown-key errors, required asset URL validation, and URL parsing without model-specific conditionals.

```js
assert.equal(resolveBoardKey(new URL('http://local/workbench?board=kl4-f201')), 'kl4-f201');
assert.equal(resolveBoardKey(new URL('http://local/workbench')), 'km4-f151');
assert.throws(() => resolveBoardAssets(catalog, 'missing'), /Unknown board key/);
```

- [ ] **Step 2: Add the catalog and loader**

Catalog entries provide cross-source, default geometry, schematic, shield or empty geometry, atlas, side-manifest, and optional page-one geometry URLs. Resolve all fetch URLs before loading data and keep the current KM4 key as the no-query default.

- [ ] **Step 3: Replace hardcoded app constants**

Load the catalog first, then fetch the selected board package. Unknown keys and asset failures must publish a model-local status error containing the board key. Do not add a second board selector to the workbench.

- [ ] **Step 4: Run frontend tests and commit**

Run: `node --test tests/board-catalog-state.test.mjs tests/model-toolbar.test.mjs tests/repair-flow-state.test.mjs`

Commit: `git commit -m "load repair boards from catalog"`

### Task 7: End-to-End Verification and Project Return

**Files:**
- Create: `.local/audit_kl4_workbench.mjs` (ignored local evidence script)
- Modify: `PROJECT_LEDGER.md` in the coordination repository
- Modify: Vault `Overview.md` and `Task Index.md`

- [ ] **Step 1: Run all automated validation**

Run `node --test tests/*.test.mjs`, all Python unittests, both dataset validators, syntax checks, `git diff --check`, and strict UTF-8/U+FFFD scans.

- [ ] **Step 2: Run headed Chromium KL4 QA**

At desktop and 390 px, open `?board=kl4-f201`, verify title and source notes, switch both sides, select every reviewed entity, enter supported inspection, start `不开机`, record both rail values, advance to X2100, interrupt/resume, and assert zero horizontal overflow or runtime errors.

- [ ] **Step 3: Run KM4 regression QA**

Open the default URL and `?board=km4-f151`, then run the complete existing interaction matrix to prove the catalog and compiler migration did not change KM4 behavior.

- [ ] **Step 4: Record evidence and commit**

Update implementation HEAD, generated counts, repair-flow boundary, test totals, browser evidence, and remaining physical-photo gap in Git/Vault project records.

Commit implementation changes and coordination changes separately with concise messages.
