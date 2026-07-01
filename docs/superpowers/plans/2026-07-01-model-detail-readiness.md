# Model Detail And Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add model readiness scoring and expandable model details to the knowledge workbench.

**Architecture:** Extend `model-board-assets.json` with readiness/material metadata and update the existing model-library front-end renderer.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, JSON.

---

## Tasks

### Task 1: Extend Model Data

- [ ] Add model-level metadata fields to `knowledge-base/model-board-assets.json`.
- [ ] Add a `required_materials` structure covering image assets, SOP, cases, boundary, and confirmation.
- [ ] Keep current candidate models valid with empty assets.

### Task 2: Add Readiness UI

- [ ] Add readiness bar and score to model cards.
- [ ] Render missing material groups and next actions.
- [ ] Add an expandable detail area per model.

### Task 3: Validate

- [ ] Parse all knowledge JSON.
- [ ] Parse front-end script.
- [ ] Run P3 desktop and mobile checks for model library and detail expansion.
- [ ] Commit locally.
