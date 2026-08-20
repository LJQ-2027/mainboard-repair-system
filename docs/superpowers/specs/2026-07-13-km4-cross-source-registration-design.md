# KM4/F151 Cross-Source Registration Baseline

## Objective

Build the first repair-oriented board registration baseline for a known model and board version. The technician already knows KM4/F151. The system aligns a physical or proxy board image with the point map and uses one shared coordinate system to connect selectable components to schematic evidence, repair-manual guidance, and the 2.5D board view.

## Product Boundary

This baseline does not classify the phone model, score photo quality, reconstruct copper layers, or claim millimeter-accurate CAD geometry. Its success criterion is that a repair-relevant component can be selected consistently across the board image, point map, 2.5D view, schematic evidence, and repair guidance.

The first scope is one KM4/F151 mainboard face and approximately ten source-supported components or test points. The Service Manual installed-board image is a proxy physical image until standardized field photographs are available.

## Coordinate System

The point map is the canonical geometry source. Board outline, anchors, component centers, component footprints, module regions, and test points use normalized coordinates:

- top-left: `(0, 0)`
- bottom-right: `(1, 1)`
- width, height, and rotation are expressed relative to the normalized board plane

Millimeter coordinates are intentionally not required. The same normalized board coordinates drive the point-map overlay and the 2.5D model. A registration transform maps the normalized board plane into proxy-photo pixels. Future physical photos can add their own transform without changing component identities or source relationships.

## Data Model

Each entity has a stable identifier and source evidence:

- `board_id`: known model, board version, and side
- `component_id`: stable identity shared by every view
- `designator`: source label such as `U2001` or `X2100`
- `geometry`: normalized center, footprint, and rotation
- `registration`: image asset, anchor pairs, transform, and confidence
- `schematic_links`: source page, symbol, network names, and supported relationships
- `repair_links`: fault path, inspection step, expected result, and source page
- `visual_profile`: generic component category and visual height, clearly separated from engineering facts

Unknown fields remain explicit and are never inferred without source evidence.

## Registration Method

The first version stores four or more reviewed anchor pairs between the normalized point-map plane and the proxy board image. Anchors should use persistent structures such as PCB corners, screw holes, large connectors, and shield edges. A homography projects component and test-point coordinates into the image.

The UI exposes the resulting alignment, not a technician-facing calibration workflow. Registration evidence and residual error remain available in the data for internal review. Automatic keypoint detection is a later enhancement for real field photos.

## Technician Experience

The workbench provides synchronized board-image, point-map, and 2.5D views. Selecting an entity in any view:

1. highlights the same `component_id` in all views;
2. centers the relevant location;
3. displays designator, category, module, and board side;
4. displays schematic networks and source page;
5. displays repair steps, test references, and source page;
6. distinguishes source facts from generic visual modeling parameters.

The interface stays compact and repair-focused. It does not include model recognition, quality scoring, engineering approval, or technician calibration controls.

## 2.5D Baseline

The initial model contains a normalized PCB substrate and parameterized component meshes for the selected entities. Footprint dimensions come from the point map where visible. Height comes from a small generic visual category library and is not presented as an engineering measurement. Rotation, tilt, zoom, side switching, picking, and synchronized highlighting use the same entity data as the 2D views.

## Validation

- Unit tests cover normalized coordinate conversion, homography projection, inverse projection, entity lookup, and cross-view selection state.
- Data validation rejects missing identities, out-of-range coordinates, unsupported source links, and insufficient registration anchors.
- Browser QA covers point-map selection, proxy-image selection, synchronized highlighting, source panel updates, 2.5D picking, desktop layout, mobile layout, and runtime errors.
- Visual inspection checks that projected markers land on the intended structures. Field-photo robustness remains unvalidated until physical front/back photos arrive.

## Deferred Work

- automatic field-photo registration;
- complete board-wide component extraction;
- exact package dimensions and physical height;
- board-side recognition;
- visual defect detection;
- production fault conclusions.
