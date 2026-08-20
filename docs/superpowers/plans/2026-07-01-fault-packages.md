# Fault Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a high-frequency fault package layer to organize Phase 1 knowledge construction.

**Architecture:** Add a new JSON knowledge file and extend the static web app with a fault package page using the existing loader and card/detail UI patterns.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, JSON.

---

## Tasks

### Task 1: Add Fault Package Data

- [ ] Create `knowledge-base/fault-packages.json`.
- [ ] Seed five high-priority fault packages from L4 report and current material gaps.
- [ ] Record required materials, related modules, related models, and next actions.

### Task 2: Add Front-End Page

- [ ] Add `故障包` navigation.
- [ ] Add search and status filter.
- [ ] Render readiness, related models, required materials, and expandable details.

### Task 3: Verify

- [ ] Parse all knowledge JSON.
- [ ] Parse inline scripts.
- [ ] Run P3 desktop and mobile checks.
- [ ] Commit locally.
