# KM4/F151 Side-Aware Repair Focus Design

## Objective

Extend the accepted KM4/F151 repair-grade 2.5D model with one side-aware repair interaction system. The technician can select a fault, module, or reviewed entity; the workbench chooses the relevant board side, focuses the local repair area, preserves surrounding board context, and allows manual front/back flipping at any time.

This milestone combines two priorities:

1. Repair focus is the primary technician-facing value.
2. Front/back structure is the supporting model capability that prevents repair focus from becoming page-2-only behavior.

Pure material polish remains outside this milestone.

## Source Boundary

The existing source package contains high-resolution point maps for `main_page_1` and `main_page_2`. The board atlas contains three source-overlay modules on page 1 and five on page 2. The detailed board compiler currently covers page 2 only, so page 1 must be compiled through the same PDF extraction and confidence pipeline before it receives package bodies.

No geometry is mirrored from page 2 to simulate page 1. Until page-1 compilation succeeds, page 1 may appear only as its source-clipped engineering surface with source-backed module overlays. The interface must not imply that page-2 component bodies are valid page-1 geometry.

Side identities remain `main_page_1` and `main_page_2` in data. The technician control uses `第1面` / `第2面` until a reviewed manual relationship confirms which source page is the physical front or back. It may use `正面` / `背面` only after that mapping is recorded for KM4, and it never infers a universal TOP/BOT convention for other boards.

## Unified Selection State

The current single `component_id` selection expands into one side-aware repair target:

```text
board_id
side_id
target_type: entity | module | fault
target_id
focus_region
recommended_side_id
```

One controller owns this state across the point map, 2.5D model, evidence panel, module menu, and later fault workflow. Renderers consume the state but do not independently decide which side is active.

When a target has source evidence on one side, the controller automatically activates that side. When evidence exists on both sides, the current side remains active if valid; otherwise the target's explicit source-backed `recommended_side_id` is used. Without an explicit recommendation, the controller does not guess. Manual flipping changes only `side_id`, preserving the selected fault or entity when that target remains meaningful on the destination side.

## Repair Focus Behavior

Repair focus is a local camera and emphasis state, not a crop that removes board context.

- Selecting a reviewed entity focuses its source-backed module polygon or a conservative local region around its normalized center.
- Selecting a module focuses that module polygon and lists its reviewed entities and test points.
- Selecting a fault will later use ranked suspected modules from the board atlas; this milestone prepares the contract without inventing new fault relationships.
- The camera animates to a bounded orthographic zoom that keeps the focused region and nearby orientation landmarks visible.
- Unrelated package bodies remain visible but are visually subdued. They are never covered by a black mask.
- The active region uses a clear outline and light surface tint. Selection remains the strongest local signal.
- A compact reset action returns to the full-board view without clearing the selected repair target.

The current Installed, X-ray, and Removed shield modes remain available. If an automatically focused target is concealed, the selected anatomy mode is preserved; the locator remains visible on the shield surface.

## Front/Back Interaction

The model represents one physical board with two side scenes sharing a normalized board contract.

- A compact side control shows the reviewed side labels and exposes a familiar flip icon for manual switching.
- Automatic side changes use the same transition as manual switching.
- The transition rotates the board around its vertical screen axis, swaps the side scene near edge-on, and finishes with readable source orientation. It does not display two boards simultaneously.
- Camera zoom and repair target are retained where valid. Free drag rotation is normalized after a side change so the model does not finish upside down.
- Each side owns its engineering texture, compiled descriptors, modules, shield candidates, labels, and evidence availability.
- Side-specific controls and legends update from active-side data rather than static page-2 assumptions.

The first implementation may keep one Three.js renderer and swap side groups. It does not require separate canvases or a general multi-board scene framework.

## Data And Compiler Changes

The compiler output becomes side-addressable without breaking existing page-2 consumers:

```text
board
  sides
    main_page_1
      board_outline
      components
      engineering_texture
      compile_summary
    main_page_2
      board_outline
      components
      engineering_texture
      compile_summary
```

The initial migration may retain `km4-board-compiled.json` as the page-2 compatibility artifact and add a side manifest that references both compiled outputs. Shared package profiles remain unchanged.

Page 1 must pass the same safeguards as page 2:

- decoded designators only;
- confidence-graded footprint relationships;
- capped procedural package dimensions and heights;
- exclusion of low-confidence physical geometry;
- explicit unresolved geometry rather than invented component identities.

## Failure And Loading States

- If the destination side texture loads but compiled geometry is unavailable, render the source surface and source-backed module overlays, and label the component layer unavailable.
- If a requested target has no evidence on the destination side, retain the selected target in the information panel but do not fabricate a board locator.
- If automatic side switching fails, remain on the current valid side and show a compact nonblocking status message.
- Side changes are disabled while the edge-on swap is in progress to prevent overlapping transitions.
- A failed page-1 compile must not degrade the existing validated page-2 model.

## Delivery Sequence

### Checkpoint 1: Page-2 Repair Focus

Implement the unified target state, bounded camera focus, context-preserving visual emphasis, and reset behavior on the existing page-2 model.

### Checkpoint 2: Page-1 Compilation

Run the existing source compiler against page 1, produce confidence summaries and a side manifest, and render the page-1 engineering surface without borrowing page-2 bodies.

### Checkpoint 3: Side-Aware Integration

Add automatic recommended-side selection, manual flip control, one-board flip transition, side-specific modules and labels, and target preservation rules.

## Acceptance Criteria

- Selecting U2001 automatically focuses a bounded local repair area without losing full-board orientation.
- Unrelated geometry is subdued without black masking, label occlusion, or removal of source context.
- Full-board reset preserves selection and active side.
- Both KM4 point-map sides render from their own source images.
- Page-1 package bodies appear only if they pass the same compiler and confidence rules as page 2.
- Selecting a side-specific target automatically activates the correct side.
- Manual flipping remains available after automatic switching and preserves valid target state.
- Installed, X-ray, and Removed anatomy states remain consistent across focus and side changes.
- Desktop and mobile layouts keep controls readable with no overlap or horizontal overflow.
- Headed Chromium verifies focus animation, automatic switching, manual flipping, selection preservation, drag, zoom, reset, focus states, nonblank WebGL pixels, and zero runtime errors.

## Deferred Work

- Blender/GLB material and package polish.
- Copper-layer, trace-level, and tiny passive reconstruction.
- Physical-photo registration and defect recognition.
- New electrical connectivity inferred from visual proximity.
- Complete no-power branching beyond source relationships already present in the board atlas.
