# Phase 1A Knowledge Workbench Design

## Goal

Build the first usable knowledge-base experience in the internal beta: current structured materials should be searchable and readable in the web app, instead of only existing as JSON files.

## User Need

Milo is still collecting source materials from technical support and Manufacturing Center. The project should not wait passively for a complete document set. The current beta should already help the team answer:

- What materials have been collected?
- What can be queried today?
- Which MTK module signals are already extracted?
- What does the L4 repair report tell us about high-frequency models and faults?
- Which missing materials should Milo ask for next?
- Which SOP items are drafts and still need engineering confirmation?

## Scope

Phase 1A adds a knowledge workbench layer to the existing single-page app.

Included:

- Data loader for `knowledge-base/*.json`.
- New sidebar entries for knowledge pages.
- Source material overview page.
- MTK signal reference query page.
- L4 repair report insight page.
- Material gap request page.
- SOP draft entry page.
- Loading, empty, and error states for these knowledge pages.
- P3 visual and interaction QA for desktop and mobile viewports.

Excluded:

- AI diagnosis as a primary workflow.
- Upload or edit backend.
- Permission system.
- Hardware diagnostic box workflow.
- Formal overseas technician production release.
- Treating unconfirmed extracted material as final repair instruction.

## Architecture

The current product is a single HTML app with local JavaScript data files. To avoid a disruptive rewrite, Phase 1A adds a focused knowledge module inside `mainboard_repair_system_v7.4_updated.html`.

The module will fetch JSON files from `knowledge-base/` using relative paths so it works both locally and under `/mb-repair-beta/` on the beta server.

The UI keeps the current left-sidebar pattern, but turns several planned modules into active pages:

- `资料总览`
- `MTK 信号查询`
- `L4 报告洞察`
- `资料缺口清单`
- `SOP 草案`

## Data Flow

1. On page load, the app starts loading required knowledge JSON files.
2. Each page renders from the loaded in-memory object.
3. Search/filter controls only affect local state.
4. If a file fails to load, the affected page shows a clear error state and the rest of the app remains usable.

## UX Rules

- Keep AI visually secondary in this phase.
- Clearly label draft and unconfirmed material.
- Favor dense operational cards and tables over marketing-style presentation.
- Do not bury the material gaps; they are now a first-class project progress driver.
- All active/selected cards and nav items must keep readable text/background contrast.

## Verification

- P0: JSON parse and data-shape smoke checks.
- P2: Python server syntax check if touched, static file smoke where possible.
- P3: Open the app in a real browser or Playwright, check desktop and mobile routes, navigation, search, filters, populated/empty/error states, and selected-state readability.
- P4: Beta deployment smoke check only if deployed in this task. GitHub push is not part of this phase under current network status.
