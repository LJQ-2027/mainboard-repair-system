# Technician Pilot Entry · 2026-08-03

## Delivered scope

- Added `assets/technician-pilot/` as the technician-facing entry for the eight-board catalog and 14 declared model aliases.
- Kept known symptoms and `不确定，先做初步排查` in one intent selector and one workbench route.
- Added a strict `board + model + intent + optional flow/symptom` URL contract. Unknown board/model/flow/symptom combinations fail closed.
- Starts a declared reviewed repair flow automatically, including the KM4 initial precheck.
- Groups KJ6/H897 cases by source-declared symptoms before showing individual cases. Case navigation remains candidate-only and never asserts defect, causality, electrical limits, or repair action.
- Keeps photo, high-resolution point map, 2.5D model, component detail, schematic evidence, manual evidence, and case context in the existing cross-source workbench.
- Adds local, privacy-reduced pilot feedback with deterministic JSON export. Feedback is usability evidence, not knowledge-base evidence.

## Capability boundary

The entry derives its labels from existing reviewed contracts:

- `reviewed_flow`: one or more declared repair flows are available.
- `case_navigation`: valid `H897-CASE-NAVIGATION-V1` cases are available without an executable repair flow.
- `reference_only`: structure and source evidence are available, but no executable flow or case contract exists.

An initial-check intent without a declared precheck is valid only as a boundary view. It opens the board sources and explicitly states that no reviewed initial procedure exists.

## Verification

- P0-P2: `node --test tests/*.test.mjs` passed 425/425 tests; six modified JavaScript entry/state files also passed `node --check`.
- Desktop route: loaded all 14 model entries; checked disabled, selected, enabled, and keyboard-focus states.
- KJ6 route: selected `不开机`, entered the exact symptom group, switched to `摄像头异常`, verified the URL/task context update, and navigated to candidate `J6202`.
- KM4 route: selected unknown-fault initial check and verified automatic entry into `初步主板排查`.
- BG6M route: verified explicit source boundary with no flow or case UI.
- Feedback: selected controlled statuses, saved one local record, and invoked JSON export. The in-app browser displayed export success but did not expose a download event; serialization and persistence are covered by unit tests.
- Responsive route: checked 390 x 844 layout, touch target height, no horizontal overflow, stacked workspace/evidence layout, and visible source boundary.
- Runtime: normal entry routes produced no new console errors. A deliberately invalid model/board combination produced the expected fail-closed load error.

## Not claimed

- Production deployment `7ed316c07130ef1488037f537c5968c832e16668` and authenticated global-network P4 completed on 2026-08-03. The tested routes were the unified entry, KM4 initial check, and KJ6 no-power source-case group at desktop and 390 px widths.
- No field technician usability result yet.
- No new electrical standard, repair causality, visual defect label, or repair action was inferred.
- Feedback remains local until a later, separately designed controlled collection endpoint exists.
