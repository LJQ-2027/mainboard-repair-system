# XK67J Technician Photo Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a hash-bound, multi-photo physical-board navigation view synchronized with the XK67J point map and 2.5D model.

**Architecture:** Generate metadata-stripped browser derivatives and a strict photo-navigation manifest from the controlled originals. Keep side/photo selection and image viewport behavior in pure modules, then coordinate them from the existing cross-source workbench.

**Tech Stack:** Python 3, Pillow, SHA-256, JSON, browser ES modules, Canvas/DOM markers, Pointer Events, Node test runner, unittest, Playwright/Chrome.

---

### Task 1: Photo Asset Contract And Builder

**Files:**
- Create: `scripts/build_xk67j_photo_navigation.py`
- Create: `tests/test_build_xk67j_photo_navigation.py`
- Create: `knowledge-base/xk67j-photo-navigation.json`
- Create: `assets/board-atlas/xk67j/physical/*.webp`
- Modify: `scripts/build_xk67j_registration.py`
- Modify: `tests/test_build_xk67j_registration.py`

- [ ] Write failing tests requiring three unique reviewed source hashes, one side-1 image, two side-2 images, exact source/derivative hashes, stripped metadata, registration dimensions, and no source paths.
- [ ] Run `python -m unittest tests.test_build_xk67j_photo_navigation tests.test_build_xk67j_registration` and confirm the missing builder/manifest failure.
- [ ] Implement source discovery by exact SHA-256, orientation normalization, 2000 px maximum WebP generation, derivative hashing, manifest validation, and registration-dataset embedding.
- [ ] Generate the three derivatives from the controlled 2026-07-31 intake root.
- [ ] Re-run the focused Python tests and confirm they pass.

### Task 2: Photo Navigation State

**Files:**
- Create: `assets/cross-source-registration/photo-navigation-state.js`
- Create: `tests/photo-navigation-state.test.mjs`
- Modify: `assets/cross-source-registration/registration-view-state.js`
- Modify: `tests/registration-view-state.test.mjs`

- [ ] Write failing tests for reviewed-photo availability, side filtering, preferred-photo retention, deterministic fallback, source-annotation copy, malformed matrix rejection, and no-photo failure state.
- [ ] Run `node --test tests/photo-navigation-state.test.mjs tests/registration-view-state.test.mjs` and confirm the missing module/new-state failures.
- [ ] Implement the smallest pure state API that returns active photo, side items, selector visibility, matrix, asset URL, and boundary copy.
- [ ] Re-run the focused Node tests and confirm they pass.

### Task 3: Shared Image Viewport

**Files:**
- Create: `assets/cross-source-registration/image-viewport.js`
- Modify: `assets/cross-source-registration/point-map-viewport.js`
- Modify: `tests/point-map-viewport.test.mjs`
- Create: `tests/image-viewport.test.mjs`

- [ ] Write failing tests for shared zoom bounds, pointer-safe pan, component focus, state reset on image replacement, and touch-compatible pointer tracking.
- [ ] Run the two viewport test files and confirm the new module behavior fails.
- [ ] Extract the current point-map viewport into `ImageViewport`; preserve `PointMapViewport` as a compatibility alias.
- [ ] Re-run both viewport suites and confirm existing point-map behavior is unchanged.

### Task 4: Three-View Workbench Integration

**Files:**
- Modify: `assets/cross-source-registration/index.html`
- Modify: `assets/cross-source-registration/app.js`
- Modify: `assets/cross-source-registration/styles.css`
- Modify: `assets/cross-source-registration/point-map.css`
- Modify: `assets/cross-source-registration/source-note-state.js`
- Modify: `tests/source-note-state.test.mjs`
- Create: `tests/photo-navigation-ui.test.mjs`

- [ ] Write failing static/state tests requiring one shared board-side control, photo selector visibility only for side 2, photo toolbar controls, synchronized source note, and no legacy single-proxy dependency for XK67J.
- [ ] Run the focused UI tests and confirm the expected failures.
- [ ] Move side selection to the shared header, add the photo toolbar and load/error state, and render side-specific photo/point-map markers from data.
- [ ] Update board-side switching to refresh photo, point map, model, source note, and selected-component focus in one transition.
- [ ] Re-run focused tests, then run all Node and related Python suites.

### Task 5: Browser QA And Closeout

**Files:**
- Modify: `docs/engineering-source-intake-2026-07-31-km5-xk67j.md`
- Modify: `PROJECT_LEDGER.md` in the enablement repository
- Modify: project Vault `Agent Entry.md`, `Overview.md`, `Task Index.md`, and relevant risks

- [ ] Start a local static server on an available loopback port and open `assets/cross-source-registration/index.html?board=xk67j-shared`.
- [ ] At desktop width, verify all three tabs, both sides, both side-2 photos, marker selection, photo zoom/pan/reset/focus, model interaction regression, focus visibility, and source-boundary copy.
- [ ] At 390 px, verify the same route, touch/pointer navigation, wrapped controls, readable labels, and zero horizontal overflow.
- [ ] Inspect screenshots and console/runtime output; fix any visual or interaction issue and repeat QA.
- [ ] Run relevant Python tests, all Node tests, compile/syntax, JSON, batch acceptance, diff, and UTF-8 checks.
- [ ] Request independent code review, resolve valid findings, update Git/Vault/ledger facts, commit locally, and do not push or deploy.

