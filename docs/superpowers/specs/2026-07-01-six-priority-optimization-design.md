# Six Priority Optimization Design

## Goal

Implement the six next-priority product foundations in order:

1. Board image / point-map intake and viewer.
2. Material readiness dashboard.
3. Fault package SOP planning page.
4. Repair case feedback template.
5. Interactive SOP step-tree prototype.
6. Beta deployment update.

## Scope

This is a foundation release. It does not require real Top20 images to be present. Empty and pending states must be useful and explicit.

Included:

- A static image/point-map viewer surface for each model asset card.
- A readiness dashboard aggregating model and fault package gaps.
- SOP planning information inside fault package detail cards.
- A repair case template page and data schema.
- A simple interactive SOP prototype based on the existing leakage/current SOP draft.
- P3 browser validation and P4 beta smoke check if deployment succeeds.

Excluded:

- Upload backend.
- Server database.
- Authentication or permission system.
- Real AI diagnosis changes.
- Hardware diagnostic box integration.

## Verification

- JSON parse.
- Front-end script parse.
- P3 desktop and mobile paths for all new tabs.
- P4 deployment smoke check for `/mb-repair-beta/` if server deployment is attempted.
