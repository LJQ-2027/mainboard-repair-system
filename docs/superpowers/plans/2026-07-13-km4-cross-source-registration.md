# KM4/F151 Cross-Source Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local technician workbench where one KM4/F151 entity stays synchronized across a proxy board image, point map, 2.5D view, schematic evidence, and repair guidance.

**Architecture:** A standalone browser module reads a source-traceable JSON dataset. A pure JavaScript coordinate engine handles normalized geometry and projective transforms; a Canvas renderer provides the first parameterized 2.5D board; a controller owns one selected `component_id` shared by all views.

**Tech Stack:** HTML/CSS, ES modules, Canvas 2D, Node built-in test runner, Python data validator, local static HTTP server.

---

### Task 1: Normalized Registration Engine

**Files:**
- Create: `assets/cross-source-registration/registration-core.js`
- Create: `tests/registration-core.test.mjs`

- [ ] Write failing tests for normalized coordinate validation, four-point homography projection, inverse projection, and polygon projection.
- [ ] Run `node --test tests/registration-core.test.mjs` and confirm failure because the module does not exist.
- [ ] Implement `validateNormalizedPoint`, `solveHomography`, `projectPoint`, `invertHomography`, and `projectPolygon` without DOM dependencies.
- [ ] Run the targeted test and confirm all registration tests pass.

### Task 2: Source-Linked KM4 Dataset

**Files:**
- Create: `knowledge-base/km4-cross-source-registration.json`
- Create: `scripts/validate_cross_source_registration.py`
- Create: `tests/test_validate_cross_source_registration.py`

- [ ] Write failing validation tests for stable entity identities, normalized geometry, at least four registration anchors, valid schematic and repair links, and resolvable local assets.
- [ ] Run `python -m unittest tests.test_validate_cross_source_registration -v` and confirm failure because the validator is absent.
- [ ] Add one KM4/F151 mainboard-side record using the reviewed installed-mainboard image as proxy, point-map page 2 as canonical geometry, and source-supported entities `U2001`, `U4000`, `X2100`, `U0600`, `J6101`, `VBAT1`, and `VBUS1`.
- [ ] Preserve page references and distinguish engineering facts from generic 2.5D visual profiles.
- [ ] Run the targeted Python tests and validator and confirm they pass.

### Task 3: Synchronized Workbench

**Files:**
- Create: `assets/cross-source-registration/index.html`
- Create: `assets/cross-source-registration/styles.css`
- Create: `assets/cross-source-registration/app.js`
- Create: `assets/cross-source-registration/board-renderer.js`
- Create: `tests/selection-state.test.mjs`

- [ ] Write failing tests for selecting one entity and deriving consistent photo marker, point-map marker, 2.5D entity, and evidence-panel state.
- [ ] Run `node --test tests/selection-state.test.mjs` and confirm failure because selection helpers are absent.
- [ ] Implement pure selection projection helpers, then make the tests pass.
- [ ] Build compact synchronized tabs for proxy photo, point map, and 2.5D model; selecting markers or meshes updates the shared entity state and evidence panel.
- [ ] Implement 2.5D tilt, rotation, zoom, reset, and mesh picking using stable Canvas dimensions and normalized geometry.
- [ ] Show source evidence, unresolved fields, and the proxy-photo limitation without model recognition or quality-scoring controls.

### Task 4: Integration Validation And Documentation

**Files:**
- Modify: `knowledge-base/README.md`
- Create: `docs/km4-cross-source-registration-2026-07-13.md`

- [ ] Run all Node and Python tests plus `git diff --check`.
- [ ] Start the local server and open `/assets/cross-source-registration/index.html`.
- [ ] Verify desktop and mobile layouts, all three views, marker selection, 2.5D picking, evidence updates, hover/focus/selected states, image loading, overflow, and console errors.
- [ ] Record the implemented scope, source limitations, route, and validation evidence in project documentation.
- [ ] Update the Vault task status only after browser QA succeeds.
- [ ] Commit the implementation as `feat: add km4 cross-source registration baseline`.
