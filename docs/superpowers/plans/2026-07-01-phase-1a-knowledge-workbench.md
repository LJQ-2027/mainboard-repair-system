# Phase 1A Knowledge Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current structured knowledge-base materials visible and searchable inside the beta web app.

**Architecture:** Extend the existing single-page HTML app with a focused knowledge module. Fetch JSON files from `knowledge-base/` with relative paths so local and `/mb-repair-beta/` deployment both work.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, JSON files, Python static server for verification.

---

## File Structure

- Modify `mainboard_repair_system_v7.4_updated.html`: add sidebar entries, tab sections, CSS, JSON loader, render functions, and search/filter handlers.
- Read `knowledge-base/*.json`: source records, training materials, platform manuals, MTK signals, report summaries, SOP drafts, gap requests.
- Optionally update `README.md`: mention Phase 1A knowledge workbench after implementation.

## Tasks

### Task 1: Add Knowledge Navigation And Sections

- [ ] Add active sidebar buttons for source overview, MTK signal query, L4 report insights, gap requests, and SOP drafts.
- [ ] Add matching `tab-content` sections with loading placeholders.
- [ ] Preserve existing resources, diagnosis, and log-analysis tabs.

### Task 2: Add Knowledge Data Loader

- [ ] Add a `knowledgeBaseState` object for loading status, data, and errors.
- [ ] Fetch required JSON files using relative paths.
- [ ] Render a recoverable error state if one file fails.

### Task 3: Render Source Overview

- [ ] Show material counts by category.
- [ ] Show source cards with summary, status, related tools/components, and target knowledge base.
- [ ] Show original source path only as internal trace text, not as a primary CTA.

### Task 4: Render MTK Signal Query

- [ ] Add keyword search across module, signal name, function, and reference value.
- [ ] Add module filter chips.
- [ ] Render results in compact cards with module, signal, function, reference value, and status.

### Task 5: Render L4 Report Insights

- [ ] Show report summary cards.
- [ ] Render top models, symptoms, fault categories, service types, and model-fault combinations from structured summary data.
- [ ] Keep this page positioned as prioritization evidence, not as a repair diagnosis result.

### Task 6: Render Gap Requests And SOP Drafts

- [ ] Show gap request cards with priority, needed provider, source relation, and reason.
- [ ] Add filters for priority/provider where data exists.
- [ ] Show SOP draft cards with clear draft/unconfirmed labels.

### Task 7: Verification

- [ ] Run JSON parse smoke check for all knowledge-base files.
- [ ] Start local server and open the app.
- [ ] Perform P3 desktop checks: navigation, search, filters, populated states, selected-state readability.
- [ ] Perform P3 mobile checks for layout and text overflow.
- [ ] Check console errors.
- [ ] Commit implementation locally. Do not push to GitHub unless Milo explicitly asks.
