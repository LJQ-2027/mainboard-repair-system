# Technician Pilot Entry Design

Date: 2026-08-03
Status: Approved for implementation
Owner: Milo
Implementation owner: Codex

## Objective

Deliver the first technician-testable entry for the eight-board repair atlas. A technician selects a known sales model and board, chooses either a known symptom or `Initial board check` in the same workflow, and then enters the existing synchronized physical-photo, point-map, and 2.5D workbench at the strongest source-supported state.

This increment improves navigation and pilot usability. It does not create electrical standards, repair causality, visual defect labels, Golden approval, training admission, or repair actions that are absent from the source material.

## Current Capability Tiers

The catalog contains eight board platforms and must preserve their unequal evidence coverage.

1. `reviewed_flow`: the board has one or more declared repair flows. The pilot may open an exact flow by ID.
2. `case_navigation`: H897 has source-bounded repair cases. The pilot may select a symptom group and open its cases and cautious component candidates.
3. `reference_only`: the board has structure, entities, and source evidence but no executable flow for the selected intent. The workbench remains available and stops at an explicit source boundary.

The entry must never present these tiers as equivalent repair capability.

## Chosen Architecture

Use a new static route at `assets/technician-pilot/` and reuse the existing `assets/cross-source-registration/` workbench.

Rejected alternatives:

- A link-only board directory would be quick but would not provide one known/unknown workflow, intent validation, or pilot feedback.
- Rebuilding the workbench as one new application would duplicate mature model, image, source-evidence, and repair-flow behavior and create unnecessary regression risk.

The pilot route owns model and intent selection. The workbench owns board interaction and source evidence. They communicate only through a validated URL intent contract.

## Pilot Entry

The first screen is the usable technician tool, not a marketing page.

- Load `repair-workbench-boards.json` and each board's cross-source dataset.
- Flatten compatible sales models into explicit model choices while retaining one canonical board key.
- Never silently choose a different board for an unknown model or stale URL value.
- Show the selected model, exact board version, evidence tier, available source views, and available intent count.
- Use one intent selector containing:
  - declared known-fault repair flows;
  - grouped H897 source-case symptoms;
  - one `不确定，先做初步排查` choice.
- The primary action opens the workbench only after model, board, and intent are valid.

No model classifier, photo intake, AI diagnosis, or technician account is added.

## Intent Contract

The entry writes only these query values:

- `board`: exact catalog board key;
- `model`: one compatible sales model declared by that board;
- `intent`: `repair_flow`, `case_symptom`, or `initial_check`;
- `flow`: required only for `repair_flow` and must exist in the selected dataset;
- `symptom`: required only for `case_symptom` and must match a deterministic case group key.

The workbench validates all values against the loaded catalog and dataset. Invalid or cross-board values fail closed into the normal unselected workbench state with a visible boundary; they must never fall back to another model, flow, or case.

## H897 Case Organization

H897 cases are organized by deterministic symptom group before individual case identity.

- Group key: normalized ordered symptom strings from the source case.
- Group label: source symptom labels joined for technician display.
- Group count: number of source cases and unique photo hashes represented.
- Selecting a group shows only its cases.
- Selecting a case exposes only its declared board-level or component-candidate scope.
- Individual case IDs remain visible as provenance, not as the primary fault taxonomy.

The reported finding remains source transcription. It is never converted into a system diagnosis.

## Initial Board Check

`Initial board check` is one intent inside the same selector, not a second product entrance.

- If the selected board has a declared initial-check repair flow, open that exact flow.
- Otherwise open the board workbench with the model, board, entity list, and source views available, and show `当前资料未形成可执行初步排查步骤`.
- The boundary state contains no measurement control, action control, pass/fail conclusion, or suggested component.

## Workbench Integration

The workbench adds a compact pilot context row above the existing repair coverage area.

- Show selected sales model and selected intent label.
- Provide one back action to return to the pilot entry without destroying local feedback.
- Preselect the exact repair flow or H897 symptom group only after contract validation.
- Keep physical photo, point map, 2.5D, side selection, entity details, schematic evidence, and source boundaries on the existing shared state.
- Direct legacy board URLs remain supported and do not require a pilot intent.

## Pilot Feedback

Feedback describes usability, not hardware truth.

Each record contains:

- schema version and generated feedback ID;
- board key, selected model, board version, and intent descriptor;
- selected component ID or selected case ID when present;
- `target_location`: `found`, `uncertain`, or `not_found`;
- `source_usefulness`: `enough_to_continue`, `insufficient`, or `not_applicable`;
- optional note limited to 500 characters;
- local creation timestamp.

The browser stores records in local storage under one versioned key and supports deterministic JSON export. It does not collect technician identity, country, IMEI, phone number, image, electrical value, or repair verdict. Feedback cannot mutate board data, case data, repair-flow state, QC state, or training eligibility.

## UI Direction

- Quiet operational layout with a compact top bar, model/board rail, intent work area, and fixed-size controls.
- No hero, marketing copy, decorative cards, gradients, or nested cards.
- Model and intent choices use list rows or native selects; selected, hover, focus, disabled, loading, empty, and boundary states must remain readable.
- Desktop uses a dense two-column entry layout. At 390 px it becomes one column without horizontal overflow.
- All interactive controls meet touch sizing without enlarging information panels.

## Failure Behavior

- Catalog or dataset fetch failure identifies the affected board and keeps all launch actions disabled.
- Unknown board, model, flow, or symptom never falls back silently.
- A board without a reviewed flow remains navigable but cannot expose executable controls for that intent.
- Local-storage failure keeps the workbench usable and reports that feedback was not saved.
- Empty feedback cannot be submitted.
- Export contains only validated feedback records and uses a deterministic field order.

## Testing And Acceptance

### Automated

- Catalog flattening, alias handling, evidence-tier derivation, and unknown identity rejection.
- Intent generation and validation for repair flow, H897 symptom group, and initial check.
- H897 grouping, case filtering, candidate preservation, and unsafe-contract rejection.
- Query encoding/decoding and cross-board mismatch rejection.
- Feedback validation, local persistence recovery, privacy-field exclusion, and deterministic export.
- Existing board catalog, repair flow, photo navigation, and model interaction regressions.

### Browser P3

- Desktop and 390 px entry selection for one reviewed-flow board, H897 case navigation, and one reference-only board.
- Known-fault and initial-check paths through the same selector.
- H897 symptom group to case to candidate component to side/photo/point-map/2.5D synchronization.
- Feedback save, reload recovery, export, invalid/empty states, keyboard focus, touch controls, and no horizontal overflow.
- Nonblank WebGL canvas and zero console errors or warnings.

### P4 Boundary

This goal does not deploy a new server endpoint or production release. Feedback is local/exportable pilot evidence. Centralized feedback ingestion and production publication require a separate approved contract and deployment gate.

## Completion Boundary

The goal is complete when the static pilot route, validated workbench intent integration, H897 symptom grouping, feedback recording/export, automated tests, desktop/mobile P3 evidence, Git commit, and Vault status are complete. It is not blocked by missing electrical SOP fields because unsupported intents must stop truthfully at their source boundary.
