# Board Atlas Guided Repair Design

## Goal

Build a technician-first 2.5D board atlas that turns mainboard repair materials into a visual, clickable repair workflow.

## Product Position

The system should not be a text-heavy knowledge base. For overseas repair technicians, the primary experience should be:

```text
Select model
-> Select board version
-> Open board atlas
-> Select known fault or start basic board check
-> See suspected modules highlighted on the board
-> Click a module or test point
-> Follow measurement instructions
-> Enter result
-> Receive the next SOP step or stop/escalation boundary
```

The board atlas is the technician-facing surface for the existing knowledge base, SOP drafts, and Top20 engineering materials.

## Recommended Technical Path

Use a web app, not a desktop app.

Stage 1 uses:

- React/Next-style frontend architecture when the app is modernized.
- Current single HTML app integration for short-term beta compatibility.
- High-resolution rendered board images from point-map PDFs.
- SVG overlay for modules, hotspots, test points, and SOP step markers.
- JSON data under `knowledge-base/` as the source of truth.
- A build script that renders point-map PDFs into web-ready PNG assets.

Stage 2 may add:

- OpenSeadragon for high-resolution zoom and pan.
- Konva if an internal annotation editor is needed.
- OpenCV-based alignment when real board photos are available.

Stage 3 may add:

- Three.js only for optional true 3D training or presentation views.

True WebGPU/CAD-style 3D is not required for the overseas repair MVP.

## MVP Scope

The first implementation should cover one sample board well instead of covering all 11 in-house packages superficially.

MVP board:

- Model: KM4.
- Board: F151_MAIN_PCB_V1.2.
- Source package: `TOP20-INHOUSE-KM4-F151`.
- Source point map: `F151_MAIN_PCB_V1.2_位号图.pdf`.
- Rendered sides: page 1 and page 2.

MVP flow:

1. User selects KM4 / F151.
2. Atlas opens with side switcher.
3. User selects a known fault or "start basic board check".
4. Board highlights suspected modules.
5. User clicks a highlighted module.
6. Side panel shows measurement guidance, expected result, and next-step rule.

## Data Model

Add `knowledge-base/board-atlas-mvp.json` with these top-level sections:

- `library_id`
- `status`
- `assets_root`
- `boards`
- `material_audit`

Each board entry has:

- `board_id`
- `model_id`
- `model_name`
- `board_version`
- `source_package_id`
- `source_materials`
- `sides`
- `modules`
- `test_points`
- `fault_paths`
- `sop_steps`
- `open_material_gaps`

All overlay coordinates use normalized coordinates from 0 to 1 relative to the rendered image:

```json
[[0.12, 0.30], [0.30, 0.30], [0.30, 0.50], [0.12, 0.50]]
```

This keeps overlays stable even if the rendered image resolution changes later.

## Materials Assessment

Current Top20 in-house materials are sufficient for a point-map-driven 2.5D MVP.

They are not yet sufficient for:

- Fully automatic real-photo alignment.
- AI visual defect detection training.
- Production technician repair decisions without engineering review.

The missing material priority is:

1. Real board front/back photos for the selected board version.
2. Engineering confirmation of board version and model applicability.
3. A small list of technician-approved modules and test points.
4. One confirmed high-frequency SOP path.
5. A few real repair examples with measurement values.

## Safety Boundaries

- Do not present unconfirmed SOP drafts as final repair instruction.
- Keep source engineering documents referenced by path; do not expose sensitive values in public-facing copy.
- Label all MVP guidance as draft or engineering-pending until confirmed.
- AI may summarize or guide navigation, but must not invent measurement values, repair boundaries, or replacement decisions.

## Verification

For the data and asset layer:

- JSON parse check for `knowledge-base/board-atlas-mvp.json`.
- Asset render script smoke test for KM4.
- Confirm rendered PNG files exist and are readable.

For the later frontend layer:

- P3 desktop and mobile browser check.
- Side switching, module click, fault selection, initial-check path, and SOP next-step interaction.
- Visual check that overlays align with the board image and text remains readable.

