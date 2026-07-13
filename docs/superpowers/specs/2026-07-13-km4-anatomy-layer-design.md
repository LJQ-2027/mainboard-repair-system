# KM4/F151 Shield Anatomy Layer Design

## Objective

Add a source-honest anatomy layer to the accepted repair-grade 2.5D model. A technician can compare installed shields, see through them, or remove them while keeping the same component identities, module regions, and repair evidence.

## Source Boundary

The shield candidates come from `km4-point-map-geometry.json` and are classified as `shield_region` by the point-map engineering-layer extractor. Re-running the extractor against the current high-resolution point map yields two large closed regions. Their normalized polygons are useful repair landmarks but remain unresolved engineering geometry, not measured shield-can dimensions.

Module polygons come from `board-atlas-mvp.json` and are restricted to `main_page_2` source overlays. No new module boundary or hidden component relationship is invented in the renderer.

## Anatomy Modes

The model exposes one compact segmented control:

- Installed: shield bodies are opaque and package bodies covered by a shield region are hidden. A selected concealed entity remains locatable on the shield surface.
- X-ray: shield bodies are translucent and covered package bodies remain visible.
- Removed: shield bodies are hidden and package bodies are visible.

Removed remains the default because component-level diagnosis is the primary repair task. Mode changes do not alter coordinates, evidence, selection, zoom, or camera orientation.

## Module Focus And Labels

Selecting one of the seven reviewed entities highlights its source-backed module polygon automatically. A compact module menu can also focus a module directly or clear the module overlay.

Designator labels are limited to reviewed entities. They remain hidden at overview zoom and appear only after the technician zooms into the board. Labels use camera-facing sprites and do not resize the canvas or evidence panel.

## Visual Treatment

Shield bodies use a restrained stamped-metal treatment with a thin rim and edge line. Module focus uses a translucent fill plus a high-contrast outline so it remains distinguishable without relying on color alone. Selection remains the smallest, strongest signal.

## Acceptance Criteria

- All three anatomy modes change both shield appearance and covered-body visibility consistently.
- Selected concealed entities remain locatable in Installed mode.
- Module selection highlights only source-backed page-2 polygons.
- Reviewed designator labels appear only beyond the zoom threshold.
- Existing rotation, inspection angle, zoom, reset, picking, and evidence synchronization continue working.
- Desktop and mobile layouts remain stable with no overlap or horizontal overflow.
