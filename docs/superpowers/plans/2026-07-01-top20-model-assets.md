# Top20 Model Board Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a model-level intake structure and front-end page for Top20 mainboard images and point-location maps.

**Architecture:** Extend the existing static knowledge-base loader with `model-board-assets.json`, then add one new single-page tab for model asset readiness.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, JSON.

---

## Tasks

### Task 1: Create Model Asset Registry

- [ ] Add `knowledge-base/model-board-assets.json`.
- [ ] Seed it with Top20 candidate models from the current L4 report.
- [ ] Use empty asset paths until Manufacturing Center provides real files.

### Task 2: Document Intake Rules

- [ ] Add `docs/top20-model-assets-intake.md`.
- [ ] Define the folder convention for board photos and point-location maps.
- [ ] Define required metadata to capture when files arrive.

### Task 3: Add Front-End Model Library Page

- [ ] Add `机型资料库` navigation entry.
- [ ] Add a `model-library` tab section.
- [ ] Load model assets through the existing knowledge-base loader.
- [ ] Render cards with status, image-slot readiness, related faults, and next action.

### Task 4: Verify

- [ ] Parse all JSON files.
- [ ] Check inline scripts.
- [ ] Run P3 desktop and mobile path checks.
- [ ] Commit locally without GitHub push.
