# J6101 Component Visual Refinement Design

## Goal

Deliver J6101 as the first visually refined connector sample while establishing
a reusable, source-bounded component visual pipeline. The result must improve
repair recognition in the existing board and isolated-component views without
changing board identity, normalized geometry, repair evidence, or interaction
semantics.

## Product Boundary

The existing point map, schematic, service manual, and reviewed registration
remain authoritative for:

- component identity and board side;
- normalized center and footprint;
- repair-flow relationships;
- source citations and technical guidance;
- the explicit limits of the available evidence.

The visual system may improve shape hierarchy, materials, lighting response,
and level of detail. It must not infer or overwrite engineering facts.

J6101 remains a repair-recognition representation. The current evidence does
not establish the exact pin count, pin pitch, vendor latch design, solder-foot
array, internal spring geometry, physical dimensions, manufacturer part
number, or wear state. Those details must not be rendered or implied.

## Architecture

Introduce a component visual layer between source-backed render descriptors and
the Three.js board renderer:

1. `component-visual-specs.js` defines immutable visual specifications and a
   catalog that maps an existing `inspection_profile.profile_id` to a visual
   specification.
2. `component-visual-validator.js` validates schema shape, ratios, material
   references, stage ordering, named parts, and prohibited unsupported detail.
3. `component-visual-builder.js` compiles one validated specification into a
   named `THREE.Group` through explicit incremental stages.
4. `board-renderer.js` requests a component visual from the builder and remains
   responsible for placement, picking, interaction, context opacity, camera
   state, and disposal.

The renderer must not contain J6101-specific geometry. The existing
`j6101-connector-v1` inspection profile selects the new specification through
the catalog. Unknown, invalid, or unsupported specifications use the current
generic connector package and do not prevent the board from rendering.

The specification contract reserves `asset_type: "procedural" | "glb"`.
This iteration implements only `procedural`. A later evidence-backed GLB may
replace the visual asset without changing the component identity, board data,
or technician interaction contract.

## ComponentVisualSpec Contract

Each specification contains:

- `spec_id`: stable visual specification identity;
- `version`: positive integer specification version;
- `asset_type`: `procedural` for this iteration;
- `family`: component package family;
- `inspection_profiles`: explicit compatible profile IDs;
- `source_status`: evidence classification;
- `fidelity`: technician-facing visual fidelity classification;
- `boundary_note`: visible source-limit statement;
- `materials`: references to approved semantic material tokens;
- `structure`: normalized dimensions and named component parts;
- `detail_levels`: named parts enabled in board and isolated views;
- `stages`: ordered build stages;
- `acceptance`: machine-checkable bounds and prohibited detail claims.

All structural dimensions are normalized relative to the source-backed
footprint. They are visual ratios, not millimeter measurements.

The first semantic material catalog contains restrained engineering plastic,
recessed dark polymer, plated metal, contact-area metal, and edge-line
materials. Specifications reference these tokens instead of embedding arbitrary
colors and material values.

## J6101 Visual Structure

The refined J6101 model contains five repair-recognition layers:

1. A low-profile dark substrate/base that preserves the registered footprint.
2. A plated outer frame with visible wall thickness and restrained beveling.
3. A recessed central opening with enough depth contrast to remain readable in
   the board view.
4. A generic contact-area band that communicates connector function without
   asserting a pin count or pitch.
5. Two end-retention structures that clarify package orientation without
   copying an unsupported vendor latch.

The board view uses the stable silhouette, opening, and material hierarchy.
The isolated-component view additionally enables wall thickness, retention
relief, controlled bevels, and deeper recess shading. Neither view adds
individual pins, solder feet, internal springs, or fabricated markings.

## Build Stages

The procedural builder runs four deterministic stages:

1. `blockout`: footprint-preserving base and overall connector volume.
2. `structure`: outer frame, central opening, end retention, and contact-area
   region.
3. `material`: semantic material assignment and approved contrast hierarchy.
4. `polish`: bounded bevels, edge lines, render-order metadata, shadows, and
   named-part metadata.

Each stage adds named parts to one group and records the completed stage in
`group.userData.visualStages`. The builder accepts a detail level and excludes
isolated-only parts from the board-level result.

The group exposes stable metadata for tests and browser QA:

- `visualSpecId`;
- `visualSpecVersion`;
- `visualAssetType`;
- `visualDetailLevel`;
- `visualStages`;
- `visualPartNames`;
- `visualFallbackReason`, when fallback occurs.

## Rendering And Interaction

The refined group uses the existing footprint dimensions and world position.
It participates in the existing component picking, affordance, board rotation,
side switching, context opacity, isolated-component animation, direct
component rotation, keyboard controls, zoom, reset, and return paths.

Entering isolated-component inspection may rebuild or upgrade the component to
the isolated detail level while preserving component identity and current
interaction state. Leaving inspection restores the board detail level without
camera drift, duplicate geometry, leaked materials, or lost selection.

No new technician control is required. The visual upgrade appears through the
existing `单体查看` flow.

## Error Handling

The validator rejects:

- missing or duplicate identities;
- incompatible inspection-profile mappings;
- unknown material tokens;
- missing or reordered build stages;
- non-finite or out-of-range ratios;
- duplicate named parts;
- unsupported `asset_type`;
- prohibited detail claims such as exact pins, pitch, solder feet, or internal
  spring geometry.

Validation failure is fail-soft at render time: the renderer records a stable
fallback reason and renders the existing generic connector package. It must not
produce a blank board, throw an uncaught error, or partially render an invalid
specification.

Development and test builds expose validation failures. Technician-facing
screens do not show schema internals.

## Visual Acceptance

J6101 passes visual acceptance only when:

- it is immediately recognizable as a low-profile board connector in the
  board and isolated-component views;
- the base, outer frame, opening, contact region, and end-retention structures
  remain visually separable;
- no unsupported individual pin, pitch, solder-foot array, or vendor latch is
  visible;
- the model remains inside the source-backed footprint bounds at board level;
- the isolated view presents materially better depth, edge, and orientation
  cues than the current recessed package;
- selection, drag rotation, wheel/pinch zoom, keyboard rotation, reset, and
  return remain stable;
- the board context remains coherent and no component, label, toolbar, or
  evidence text overlaps;
- desktop and 390 px layouts show a nonblank WebGL canvas with readable
  controls and no console or page errors.

Visual comparison evidence must include the current baseline, the refined board
view, and the refined isolated-component view. Canvas pixel checks must prove
that each tested render is nonblank and contains meaningful component-region
contrast.

## Tests

### Unit Tests

- catalog resolution and unknown-profile behavior;
- valid J6101 specification acceptance;
- schema, ratio, material, stage, part-name, and prohibited-detail rejection;
- deterministic build-stage and named-part metadata;
- board versus isolated detail-level output;
- fallback behavior and fallback-reason stability;
- footprint-bound preservation.

### Integration Tests

- the model profile resolves J6101 to the reusable visual catalog;
- the renderer uses the reusable builder instead of J6101-specific geometry;
- entering and leaving inspection swaps detail levels without changing identity;
- disposal covers generated geometries, materials, edge lines, and replacements;
- existing board, interaction, inspection, and repair-flow suites remain green.

### Browser QA

Run headed Chromium against the actual KM4/F151 workbench at desktop and
390 px touch viewports. Verify:

- board rendering and source texture loading;
- J6101 selection and direct entry into `单体查看`;
- mouse and touch component rotation;
- wheel and pinch zoom;
- keyboard rotation, zoom, Home reset, and Escape/return;
- board-detail to isolated-detail transition and restoration;
- no layout overflow, overlap, blank canvas, console errors, or page errors;
- screenshot and canvas-pixel evidence for baseline and refined states.

## Non-Goals

- exact engineering CAD reconstruction;
- Blender or GLB authoring in this iteration;
- physical dimensions or package-part identification;
- individual pins, solder joints, copper routing, or hidden internals;
- changes to board registration, repair flows, visual QC, or AI diagnosis;
- batch refinement of every component family.

## Completion Criteria

This iteration is complete when the J6101 sample uses a validated reusable
`ComponentVisualSpec`, the procedural stages and fallback path are covered by
tests, the existing application behavior remains green, and browser evidence
proves the refined board and isolated views meet the visual and interaction
acceptance criteria.
