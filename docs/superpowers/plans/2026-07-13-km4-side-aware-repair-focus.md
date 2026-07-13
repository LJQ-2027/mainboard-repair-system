# KM4/F151 Side-Aware Repair Focus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add context-preserving repair focus to the current KM4 model, compile its second source side, and integrate automatic recommended-side switching with manual one-board flipping.

**Architecture:** A DOM-free repair-target module owns side-aware target and focus-region decisions. `BoardRenderer` gains bounded orthographic camera focus and reversible visual emphasis, then evolves from one side group to side-addressable groups loaded through a compatibility manifest. The app controller remains the single owner of target, active side, and anatomy state.

**Tech Stack:** JavaScript ES modules, Three.js, Python board compiler, JSON manifests, Node test runner, Python unittest, headed Chromium QA.

---

### Task 1: Pure Repair Target And Focus Contract

**Files:**
- Create: `assets/cross-source-registration/repair-focus-state.js`
- Create: `tests/repair-focus-state.test.mjs`

- [x] Write failing tests for entity/module target construction, polygon bounds, conservative point focus, side recommendation, and reset-preserved selection.

```js
assert.deepEqual(buildEntityTarget(entity, modules, 'main_page_2'), {
  boardId: 'BOARD-KM4-F151-MAIN-V1.2',
  sideId: 'main_page_2',
  targetType: 'entity',
  targetId: entity.component_id,
  focusRegion: { center: { x: 0.5, y: 0.5 }, size: { x: 0.2, y: 0.2 } },
  recommendedSideId: 'main_page_2',
});
```

- [x] Run `node --test tests/repair-focus-state.test.mjs` and confirm failure because the module does not exist.
- [x] Implement `polygonBounds`, `buildEntityTarget`, `buildModuleTarget`, `resolveTargetSide`, and `resetFocusView` without DOM or Three.js dependencies.
- [x] Run the targeted test and then `node --test tests/*.test.mjs`; expect all tests to pass.
- [x] Commit the pure state contract as part of the complete Checkpoint 1 commit.

### Task 2: Page-2 Context-Preserving Camera Focus

**Files:**
- Modify: `assets/cross-source-registration/board-renderer.js`
- Modify: `assets/cross-source-registration/model-profiles.js`
- Test: `tests/model-profiles.test.mjs`

- [x] Add failing tests for a focus camera frame that keeps normalized regions within a responsive bounded zoom and computes a world-space camera center.

```js
const frame = buildFocusFrame({ center: { x: 0.5, y: 0.5 }, size: { x: 0.2, y: 0.16 } }, 1.6);
assert.equal(frame.zoom >= 1.35 && frame.zoom <= 2.8, true);
assert.deepEqual(frame.center, { x: 0, y: 0 });
```

- [x] Run `node --test tests/model-profiles.test.mjs` and confirm the missing export failure.
- [x] Implement `buildFocusFrame(region, aspect)` using `BOARD_WORLD_SIZE`, region padding, and responsive zoom clamps.
- [x] Add `focusRegion(region)`, `clearRepairFocus()`, and an animation that interpolates `camera.position.x/y` and `camera.zoom` while cancelling any prior animation frame.
- [x] Preserve the selected halo and current shield mode during focus and reset.
- [x] Run the targeted and complete Node suites.

### Task 3: Page-2 Repair Emphasis And Controller Integration

**Files:**
- Modify: `assets/cross-source-registration/board-renderer.js`
- Modify: `assets/cross-source-registration/app.js`
- Modify: `assets/cross-source-registration/index.html`
- Modify: `assets/cross-source-registration/styles.css`

- [x] On reviewed entity selection, build one repair target and pass its `focusRegion` to the renderer.
- [x] On module-menu selection, build a module target and focus its polygon bounds.
- [x] Add a compact full-board icon action whose accessible label is `显示全板` and which resets the camera without clearing selection.
- [x] Emphasize the active module with its existing outline/tint and reduce unrelated package material opacity only to `0.52`; do not add a screen mask or hide source texture.
- [x] Ensure manual wheel or drag cancels camera animation without clearing repair emphasis.
- [x] Verify U2001, U4000, and U0600 focus regions visually at desktop and mobile sizes.
- [x] Commit Checkpoint 1 as a complete runnable feature.

### Task 4: Compile And Validate Main Page 1

**Files:**
- Refactor: `scripts/compile_km4_board.py`
- Create: `knowledge-base/km4-board-compiled-page-1.json`
- Create: `knowledge-base/km4-board-sides.json`
- Modify: `tests/test_compile_km4_board.py`

- [x] Extract `compile_side(page, side_id, image_path, output_path, required_designators)` from the current page-2-only script.
- [x] Add tests proving each output retains its own `side_id`, source page, engineering texture, outline, confidence audit, and components.
- [x] Compile page 1 against `main-point-map-page-1.png` without requiring the page-2 reviewed designator set.
- [x] Preserve `km4-board-compiled.json` as the validated page-2 compatibility artifact.
- [x] Write a manifest with explicit source labels `第1面` and `第2面`, compiled-data paths, and texture paths.
- [x] Run all Python tests and both output validators; commit Checkpoint 2.

### Task 5: Side-Aware Renderer And One-Board Flip

**Files:**
- Modify: `assets/cross-source-registration/app.js`
- Modify: `assets/cross-source-registration/board-renderer.js`
- Modify: `assets/cross-source-registration/index.html`
- Modify: `assets/cross-source-registration/styles.css`
- Modify: `assets/cross-source-registration/repair-focus-state.js`
- Test: `tests/repair-focus-state.test.mjs`

- [ ] Load the side manifest and build one Three.js group per side from its own texture, outline, descriptors, modules, shields, and labels.
- [ ] Add tests for current-side preservation, explicit recommended-side switching, and no-guess behavior when a target has no recommendation.
- [ ] Add a two-option side control and flip icon using reviewed `第1面` / `第2面` labels.
- [ ] Animate the board group to edge-on, swap visible groups once, finish the rotation, and lock side controls during the transition.
- [ ] Preserve valid selected targets and anatomy state; retain the information panel without a locator when the destination side lacks target geometry.
- [ ] Verify automatic U2001 side selection, manual flip in both directions, target preservation, drag, zoom, reset, focus states, and mobile layout.
- [ ] Commit Checkpoint 3.

### Task 6: Full Verification And Project State Return

**Files:**
- Modify: `docs/km4-cross-source-registration-2026-07-13.md`
- Modify: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`
- Modify: Vault project `Overview.md`, `Task Index.md`, `Decisions.md`, and `Risks.md` only where current facts changed.

- [ ] Run JavaScript syntax checks, all Node tests, all Python tests, JSON parsing, and standalone cross-source validation.
- [ ] Run headed Chromium at `1600x900` and `390x844` through focus, reset, automatic side change, manual flip, anatomy modes, selection, drag, zoom, focus visibility, overflow, WebGL pixels, and runtime logs.
- [ ] Record implementation commits, source boundaries, browser evidence, and remaining material-polish and physical-photo gaps.
- [ ] Run the Project Closeout Check and commit the ledger update.
