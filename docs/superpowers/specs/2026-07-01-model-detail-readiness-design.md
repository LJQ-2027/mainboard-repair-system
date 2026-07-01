# Model Detail And Readiness Design

## Goal

Upgrade the model library from a simple Top20 intake list into a model-level planning surface. Before board images arrive, the system should already show material completeness, missing items, and the next actions needed for each model.

## Scope

Included:

- Readiness scoring for each model based on required material groups.
- Model detail view inside the model card.
- Required-material groups for assets, SOPs, cases, repair boundaries, and engineering confirmation.
- Clear "what is missing next" guidance.
- Front-end rendering that works with empty asset paths.

Excluded:

- Real image viewer.
- Upload backend.
- Multi-page routing.
- Editing model records from the browser.
- AI recommendations.

## Data Model Additions

Each model may contain:

- `platform`
- `board_versions`
- `region_scope`
- `readiness`
- `required_materials`
- `linked_sops`
- `linked_cases`
- `linked_training`
- `repair_boundary`
- `engineering_confirmation`

The front-end also computes a fallback readiness score from asset slots and material groups, so existing records remain usable even if some fields are missing.

## UX

The model library should support two modes:

- Scan mode: cards show readiness, priority source, L4 volume, related faults, and missing asset slots.
- Detail mode: clicking "查看详情" expands a model into material groups, missing items, linked knowledge, and suggested next actions.

This keeps the page useful before Top20 images arrive and becomes more valuable after each file is added.

## Verification

- JSON parse check.
- Front-end script parse check.
- P3 desktop path: open model library, search model, expand detail.
- P3 mobile path: same page without horizontal overflow.
