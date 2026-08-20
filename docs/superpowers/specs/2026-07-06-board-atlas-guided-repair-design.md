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

## Iteration 2: 2.5D Inspection Baseline

The first interactive pass proved the data path but still looked like a flat PDF with oversized annotation boxes. The second pass establishes the reusable visual baseline for later boards:

- Crop rendered point-map pages to the actual board content so the board fills the working area.
- Keep the point map and SVG coordinates in one transformable scene so zoom and focus never break alignment.
- Separate the scene into four visible layers: board base, source modules, active fault path, and inspection focus.
- Use compact numbered hotspots and precise outlines instead of large translucent rectangles.
- Selecting a fault shows a ranked module rail; selecting a module smoothly focuses its local area and opens an inline inspection panel.
- Provide fit, zoom in, zoom out, and reset controls suitable for repeated bench use.
- Preserve a top-down inspection mode. Any depth treatment is shallow and must not distort test-point coordinates.

Acceptance criteria:

1. The board occupies most of the atlas canvas at the default desktop view.
2. No overlay hides component labels in the source point map.
3. Active modules remain distinguishable without relying on color alone.
4. Clicking a suspected module focuses the correct local region and exposes its related test point or instruction.
5. The desktop and mobile layouts have no horizontal page overflow; the board canvas may pan internally when zoomed.

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

Current Top20 in-house materials are sufficient for the point-map-driven 2.5D atlas and its source-based repair guidance. The supplied point map, schematic, and repair guide are the accepted source for this product layer; the technician flow does not add engineering confirmation or manual calibration steps.

Real board photos are useful later for photo-to-map matching and visual defect recognition, but they are not a blocker for this 2.5D atlas. Training a visual defect model will additionally require labeled good-board and bad-board image sets.

## Safety Boundaries

- Keep source engineering documents referenced by path; do not expose sensitive values in public-facing copy.
- AI may summarize or guide navigation, but must not invent measurement values, repair boundaries, or replacement decisions.
- Treat supplied in-house point maps, schematics, and repair guides as the atlas source of truth. When a value is absent, ask the technician to record the observed value rather than inventing a threshold.

## Verification

For the data and asset layer:

- JSON parse check for `knowledge-base/board-atlas-mvp.json`.
- Asset render script smoke test for KM4.
- Confirm rendered PNG files exist and are readable.

For the later frontend layer:

- P3 desktop and mobile browser check.
- Side switching, module click, fault selection, initial-check path, and SOP next-step interaction.
- Visual check that overlays align with the board image and text remains readable.
