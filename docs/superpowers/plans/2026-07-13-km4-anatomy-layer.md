# KM4/F151 Shield Anatomy Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add source-backed shield anatomy modes, module focus, and zoom-level designator labels to the KM4/F151 V2 model.

**Architecture:** A DOM-free anatomy-state module converts source shield/module records into normalized render records and owns visibility rules. The existing Three.js renderer consumes those records, while the app controller binds compact controls and preserves one selected component identity across views.

**Tech Stack:** JavaScript ES modules, Three.js, HTML/CSS, Node test runner, Python validation, headed Chromium QA.

---

### Task 1: Anatomy State Contract

**Files:**
- Create: `assets/cross-source-registration/anatomy-state.js`
- Create: `tests/anatomy-state.test.mjs`

- [x] Write failing tests for shield extraction, anatomy-mode presentation, point coverage, module filtering, and zoom-label visibility.
- [x] Run the targeted Node test and confirm the missing-module failure.
- [x] Implement the pure state helpers and pass the targeted test.
- [x] Run the complete Node test suite.

### Task 2: Three.js Anatomy Layers

**Files:**
- Modify: `assets/cross-source-registration/board-renderer.js`
- Modify: `assets/cross-source-registration/app.js`

- [x] Load the existing shield geometry and board-atlas module datasets.
- [x] Build stamped-metal shield groups above the package layer.
- [x] Apply Installed, X-ray, and Removed presentation rules without changing component identities.
- [x] Build source-backed module polygons and synchronize them to reviewed-entity selection.
- [x] Build reviewed designator sprites and update their visibility from orthographic zoom.

### Task 3: Compact Controls

**Files:**
- Modify: `assets/cross-source-registration/index.html`
- Modify: `assets/cross-source-registration/styles.css`
- Modify: `assets/cross-source-registration/app.js`

- [x] Add a stable segmented anatomy control and module-focus menu.
- [x] Preserve keyboard focus, selected-state readability, and mobile layout.
- [x] Keep model controls hidden outside the model tab.

### Task 4: Verification And State Return

**Files:**
- Modify: `docs/km4-cross-source-registration-2026-07-13.md`
- Modify: project ledger and Vault cards after evidence exists.

- [x] Run JavaScript syntax checks, all Node tests, all Python tests, and standalone registration validation.
- [x] Verify desktop and mobile anatomy modes, module focus, labels, selection, zoom, drag, reset, focus states, overflow, and runtime logs in headed Chromium.
- [x] Record the source boundary, implementation commits, verification evidence, and remaining GLB/front-back work.
