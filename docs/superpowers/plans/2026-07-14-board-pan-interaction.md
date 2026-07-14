# Board Pan Interaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bounded two-axis camera panning as the default 2.5D board interaction while preserving explicit rotation, picking, zoom, inspection, and reset behavior.

**Architecture:** Put mode validation and screen-to-world pan math in a small pure module. `BoardRenderer` owns camera/pointer mechanics and exposes mode setters; `app.js` owns toolbar state and global transition lock integration. Existing repair targets remain intact while a manual pan center takes temporary camera precedence.

**Tech Stack:** JavaScript ES modules, Three.js orthographic camera, Node test runner, headed Playwright QA.

---

### Task 1: Pan Math And Mode State

**Files:**
- Create: `assets/cross-source-registration/board-pan-state.js`
- Create: `tests/board-pan-state.test.mjs`

- [ ] **Step 1: Write failing tests for mode validation, zoom-aware pointer conversion, and bounds**

```js
assert.equal(resolveBoardInteractionMode('rotate'), 'rotate');
assert.equal(resolveBoardInteractionMode('invalid'), 'pan');
assert.deepEqual(screenDeltaToPan({ dx: 100, dy: 50, width: 1000, height: 500, frameWidth: 2, frameHeight: 1, zoom: 2 }), { x: -0.1, y: 0.05 });
assert.deepEqual(clampPanCenter({ x: 3, y: -2 }), { x: 0.92, y: -0.62 });
```

- [ ] **Step 2: Run `node --test tests/board-pan-state.test.mjs` and verify the missing-module failure**

- [ ] **Step 3: Implement pure helpers with `pan` as fallback, orthographic zoom conversion, and fixed board-relative limits**

```js
export function screenDeltaToPan(input) {
  return {
    x: -(input.dx / input.width) * (input.frameWidth / input.zoom),
    y: (input.dy / input.height) * (input.frameHeight / input.zoom),
  };
}
```

- [ ] **Step 4: Run the targeted test and verify all pan-state tests pass**

### Task 2: Renderer And Toolbar Integration

**Files:**
- Modify: `assets/cross-source-registration/board-renderer.js`
- Modify: `assets/cross-source-registration/app.js`
- Modify: `assets/cross-source-registration/index.html`
- Modify: `assets/cross-source-registration/styles.css`

- [ ] **Step 1: Add a `平移` / `旋转` segmented control with `pan` initially pressed**

```html
<div class="model-interaction-modes" role="group" aria-label="模型拖拽模式">
  <button type="button" data-model-drag-mode="pan" aria-pressed="true">平移</button>
  <button type="button" data-model-drag-mode="rotate" aria-pressed="false">旋转</button>
</div>
```

- [ ] **Step 2: Connect toolbar state to `renderer.setInteractionMode(mode)` and disable both controls during model transitions and component inspection**

- [ ] **Step 3: Change renderer pointer ownership so isolated components rotate directly, pan mode updates a bounded manual camera center, and rotate mode retains constrained board rotation**

```js
const delta = screenDeltaToPan({
  dx: event.clientX - this.drag.x,
  dy: event.clientY - this.drag.y,
  width: this.container.clientWidth,
  height: this.container.clientHeight,
  frameWidth: this.camera.right - this.camera.left,
  frameHeight: this.camera.top - this.camera.bottom,
  zoom: this.camera.zoom,
});
this.manualPanCenter = clampPanCenter({ x: this.drag.cx + delta.x, y: this.drag.cy + delta.y });
```

- [ ] **Step 4: Make focus operations clear the manual override, resize preserve it, and reset restore center/top view/zoom plus pan mode**

- [ ] **Step 5: Run Node and Python regressions and verify no existing interaction contract fails**

### Task 3: Real Browser Interaction QA And Closeout

**Files:**
- Modify: `.local/audit_model_interactions.mjs` (ignored QA harness)
- Modify: `docs/km4-cross-source-registration-2026-07-13.md`
- Modify: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`

- [ ] **Step 1: Add headed Playwright assertions for desktop horizontal/vertical pan, drag-versus-click, rotate mode, wheel zoom, focused pan, reset, and mobile touch drag**

- [ ] **Step 2: Run the complete headed interaction matrix and inspect desktop/mobile screenshots for framing, control contrast, overlap, and nonblank WebGL pixels**

- [ ] **Step 3: Run syntax checks, all Node tests, all Python tests, standalone source validation, UTF-8 health checks, and Git diff checks**

- [ ] **Step 4: Record verification evidence in implementation docs, project ledger, and Vault status**

- [ ] **Step 5: Commit implementation and closeout documentation without pushing while remote sync is unavailable**
