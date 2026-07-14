# Component Interaction Affordance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent reviewed-component affordances, hover guidance, and a fitted non-obscuring selection treatment.

**Architecture:** A pure affordance module owns geometry and semantic state. `BoardRenderer` builds one board-space corner frame and compact label per reviewed entity, applies hover/selection state, and uses a DOM tooltip only for pointer detail. Existing repair and interaction state remain unchanged.

**Tech Stack:** JavaScript ES modules, Three.js lines/sprites/raycasting, DOM tooltip, Node test runner, headed Playwright.

---

### Task 1: Affordance Geometry And State

**Files:**
- Create: `assets/cross-source-registration/component-affordance-state.js`
- Create: `tests/component-affordance-state.test.mjs`

- [ ] Write failing tests for eight outside-footprint corner segments and idle/hover/selected semantic styles.
- [ ] Run the targeted test and verify the module-missing failure.
- [ ] Implement `buildCornerSegments(dimensions)` and `resolveAffordancePresentation(state)` with amber interaction colors and no coral selection state.
- [ ] Run the targeted test and verify it passes.

### Task 2: Renderer Affordance Layer

**Files:**
- Modify: `assets/cross-source-registration/board-renderer.js`
- Modify: `assets/cross-source-registration/styles.css`
- Modify: `assets/cross-source-registration/model-profiles.js`
- Modify: `tests/model-profiles.test.mjs`

- [ ] Replace the generated ring with persistent corner frames for reviewed entities only.
- [ ] Redesign label sprites as compact dark tags with an amber status edge.
- [ ] Add raycast hover state and a pointer-adjacent DOM tooltip without changing selection.
- [ ] Hide affordances in component inspection and restore them on exit.
- [ ] Remove the obsolete selection-halo helper and retain restrained package emissive selection.
- [ ] Run syntax and complete Node tests.

### Task 3: Browser QA And Closeout

**Files:**
- Modify: `.local/audit_model_interactions.mjs` (ignored)
- Modify: `docs/km4-cross-source-registration-2026-07-13.md`
- Modify: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`

- [ ] Assert seven visible affordance tags on page 2, hover tooltip content, click selection, no red ring, pan/rotate continuity, and inspection restoration.
- [ ] Inspect desktop full-board/focused screenshots and mobile screenshots for overlap and readability.
- [ ] Run 53+ Node tests, 37 Python tests, standalone validation, UTF-8 checks, and clean Git checks.
- [ ] Commit implementation and closeout records without remote push.
