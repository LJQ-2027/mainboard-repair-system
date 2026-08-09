# Technician Repair Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one existing reviewed repair task recoverable across refresh and exportable as a privacy-reduced technician session without changing any repair decision.

**Architecture:** Add a pure session-state module beside the existing repair-flow state. The workbench snapshots its existing `repairFlowById` map after every accepted mutation, restores only an exact board/model/version/entry-flow match, and renders a compact status/export strip inside the current repair panel.

**Tech Stack:** Browser ES modules, localStorage, JSON, Node `node:test`, existing HTML/CSS/JavaScript workbench, Playwright browser QA.

---

### Task 1: Versioned Repair Session Contract

**Files:**
- Create: `assets/cross-source-registration/repair-session-state.js`
- Create: `tests/repair-session-state.test.mjs`

- [ ] Write failing tests for `createRepairSession`, `updateRepairSession`, `abandonRepairSession`, exact-identity recovery, 50-record retention, malformed-record rejection and deterministic privacy-reduced export.
- [ ] Run `node --test tests/repair-session-state.test.mjs` and confirm failure because the module does not exist.
- [ ] Implement `TECHNICIAN-REPAIR-SESSION-V1` normalization. Accept only exact board/model/version/intent/entry-flow identity; normalize `flowStates` as a string-keyed object containing the existing state fields and finite numeric measurements; derive terminal status only from closed flow state.
- [ ] Implement `loadRepairSessions`, `saveRepairSessions`, `recoverRepairSession` and `serializeRepairSessions`. Drop unknown fields, retain the newest 50 valid records and sort exported records by creation time then session id.
- [ ] Run the focused test and commit the green state.

### Task 2: Existing Flow Integration

**Files:**
- Modify: `assets/cross-source-registration/app.js`
- Create: `tests/repair-session-integration.test.mjs`

- [ ] Write a failing integration test that starts a reviewed flow, snapshots a measurement/choice, serializes it, reloads it and reconstructs the exact existing repair-flow state without changing the branch outcome.
- [ ] Run `node --test tests/repair-session-integration.test.mjs` and confirm the missing integration helper fails.
- [ ] Import the session module in `app.js`; create or recover the exact session in `startRepairEntry`; restore `repairFlowById` and `activeRepairFlowId`; snapshot after every `applyRepairFlowState` mutation and handoff.
- [ ] On explicit reset, mark the prior session `abandoned`, persist it, create a new session and then apply the existing reset state. On storage failure, keep the in-memory flow active and expose a non-blocking persistence message.
- [ ] Run focused session and existing repair-flow tests and commit.

### Task 3: Session Status And Export Surface

**Files:**
- Modify: `assets/cross-source-registration/index.html`
- Modify: `assets/cross-source-registration/styles.css`
- Modify: `assets/cross-source-registration/app.js`
- Modify: `tests/pilot-workbench-integration.test.mjs`

- [ ] Add failing static/integration assertions for a `repairSessionStatus`, `repairSessionSavedAt` and `exportRepairSession` control contained by the existing repair-flow panel and hidden when no reviewed flow is active.
- [ ] Add one compact separator-based session strip below the flow header. Show `进行中`, `已恢复`, `已完成`, `已在资料边界停止` or `保存失败`, plus last-saved time and export command; do not add a new page or card.
- [ ] Wire export to the currently validated session and use `technician-repair-session-YYYY-MM-DD.json`. Disable export only when no valid session exists.
- [ ] Run the focused UI and session tests and commit.

### Task 4: Browser And Project Closeout

**Files:**
- Modify: `README.md`
- Modify: `PRODUCT.md`
- Modify: `docs/superpowers/plans/2026-08-09-technician-repair-session.md`
- Modify: project ledger and Vault entries outside the implementation repository

- [ ] Run the complete relevant Node repair-flow/session/pilot suite, JavaScript syntax checks, `git diff --check`, JSON and strict UTF-8 checks.
- [ ] Start the local app and use installed-Chrome Playwright at desktop and 390 px to complete: entry selection, measurement/choice, refresh recovery, terminal completion, reset/abandonment and export affordance. Check readable interaction states, zero horizontal overflow and zero runtime errors.
- [ ] Document that sessions remain local, privacy-reduced and non-authoritative; H897 case navigation remains non-executable.
- [ ] Request independent review, fix every P1/P2, update project facts, commit and retain the feature worktree. Do not deploy production without a separate owner request.
