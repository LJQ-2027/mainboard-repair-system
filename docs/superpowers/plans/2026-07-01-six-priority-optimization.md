# Six Priority Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the six requested optimization foundations in priority order.

**Architecture:** Extend the existing static HTML knowledge workbench and JSON knowledge-base files. Avoid new backend dependencies.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, JSON, Python static/proxy server.

---

## Tasks

### Task 1: Image Viewer Foundation

- [ ] Add model image preview areas for board front/back and point-map front/back.
- [ ] Render pending states when paths are empty.
- [ ] Add zoom controls and open-file affordances for future image paths.

### Task 2: Readiness Dashboard

- [ ] Add dashboard tab.
- [ ] Aggregate model and fault package readiness.
- [ ] Surface top missing items and immediate next actions.

### Task 3: Fault Package SOP Planning

- [ ] Show symptom split, modules, signals, required data, draft SOP status, and next action in fault package detail.

### Task 4: Case Feedback Template

- [ ] Create `knowledge-base/repair-case-template.json`.
- [ ] Add case template tab with required fields and evidence checklist.

### Task 5: Interactive SOP Prototype

- [ ] Create `knowledge-base/interactive-sop-prototypes.json`.
- [ ] Add interactive SOP tab for the leakage/current SOP draft.
- [ ] Support next-step navigation and simple branch selection.

### Task 6: Verify And Deploy

- [ ] Run JSON/script checks.
- [ ] Run P3 desktop/mobile browser checks.
- [ ] Commit locally.
- [ ] Deploy beta if server access works and run smoke check.
