# KM4/F151 Cross-Source Registration Baseline

## Route

`http://127.0.0.1:8898/assets/cross-source-registration/index.html`

## Implemented

- The F151 point-map plane is the normalized `0-1` geometry source.
- A reviewed four-anchor homography projects board coordinates onto the Service Manual installed-mainboard proxy image.
- Seven source-supported entities share stable identities across the proxy image, point map, schematic evidence, repair guidance, and Three.js 2.5D view.
- The 2.5D substrate uses an outline derived from the point map. Component footprints use normalized point-map geometry; visual heights are generic and explicitly not engineering dimensions.
- A deterministic raster extractor now converts the current high-resolution point map's red engineering layer into 323 additional source-driven geometry regions. Two large closed regions provide provisional shield polygons; unresolved regions do not receive invented designators.
- Selection is synchronized across view markers, the entity list, and 3D mesh picking.

## Repair-Grade 2.5D V2

The debug geometry view has been replaced by a layered repair model. Its reset state is a fitted orthographic top view, with a second constrained inspection angle for checking board thickness and package elevation.

- The current 204-point page-2 PCB silhouette remains the substrate boundary.
- The high-resolution point map is UV-mapped and clipped to the board surface, retaining pads, labels, and engineering structure.
- Only the 180 high-confidence footprint relationships become elevated package bodies.
- The 630 medium-confidence relationships remain flat reference outlines, and the 10 low-confidence candidates remain excluded from the physical layer.
- Reusable procedural profiles distinguish ICs, passive chips, inductors, crystals, connectors, test points, metal contacts, LEDs, diodes, and transistors.
- Package dimensions and heights are capped by conservative visual profiles; they are not represented as measured dimensions.
- Reviewed entities remain the primary click targets. Selection now uses a compact locator ring and restrained emissive feedback instead of replacing the component with an oversized solid block.
- The package-profile contract is ready for later Blender-authored GLB assets without changing normalized board data or repair interactions.

## Shield Anatomy Layer

- Installed, X-ray, and Removed modes show shield context, translucent covered geometry, or the exposed repair surface without changing component identities.
- Shield candidates use normalized convex polygons extracted from the current high-resolution engineering layer instead of coarse bounding boxes. They remain source-derived landmarks rather than measured mechanical dimensions.
- Source-backed functional-module polygons can follow the selected reviewed entity or be chosen directly from a compact menu.
- Reviewed designator labels appear only after the orthographic view reaches the repair zoom threshold.

## Repair Focus Checkpoint

- Reviewed entity selection now produces one side-aware repair target containing the active side, module, and normalized focus region.
- The orthographic camera animates to a bounded local view while retaining nearby board landmarks and the full engineering texture.
- Wide screens cap repair zoom at `1.9`; narrow screens may reach `2.2` so mobile targets remain operable without making desktop views lose orientation.
- Components outside the repair region remain visible at reduced emphasis. No black mask or destructive crop is used.
- Zoom-level labels are restricted to the selected or locally relevant reviewed entities.
- `显示全板` restores the fitted top view without clearing the selected component or evidence panel.

## Current Entities

`U2001`, `U4000`, `X2100`, `U0600`, `J6101`, `VBAT1`, and `VBUS1`.

## Dual-Side Model

- `km4-board-sides.json` is the explicit side manifest. It uses source-reviewed labels `第1面` and `第2面`; it does not infer front/back naming that the available material does not prove.
- 第1面 is compiled from PDF page 1 and its own engineering texture: 2,489 decoded text objects, 4,297 vector rectangles, 352 accepted designators, and a 161-point normalized outline.
- 第2面 remains the reviewed cross-source side: 3,665 decoded text objects, 3,719 vector rectangles, 820 accepted designators, all seven reviewed entities, and a 204-point normalized outline.
- The renderer replaces the active board scene at the edge-on midpoint of a single-board flip. Each destination scene uses its own outline, texture, components, module polygons, and available shield anatomy.
- Selecting a reviewed entity always makes it the current repair target. If its recommended side differs from the visible side, the model automatically flips there; the compact side control remains available for manual inspection.
- When a selected entity is not represented on the visible side, its evidence panel remains visible and explicitly states the side containing the target instead of drawing a false locator.

## U2001 Component Inspection Sample

- U2001 is the first explicit `inspection_profile` vertical slice. The capability is data-enabled rather than inferred from a designator, so unfinished components do not expose a misleading control.
- `单体查看` keeps the component at its registered board coordinate, raises and enlarges it, and turns the board and unrelated packages into a low-opacity context layer.
- Pointer drag rotates U2001 around its own center; wheel input uses inspection-specific zoom bounds. The board remains still during component manipulation.
- Return, full reset, entity change, side change, and view change all restore the original package transform, camera, opacity, shield state, module state, selected identity, and evidence context.
- The refined procedural PMIC/BGA profile uses a layered dark package, muted substrate, metal edge, restrained bevel, and pin-one cue. It explicitly does not claim measured dimensions, exact ball count, or engineering CAD fidelity.
- The evidence panel separates source-backed common faults and detection guidance from a visible model-fidelity boundary. No missing voltage, resistance, pin, or replacement values are invented.

## Evidence Boundary

The available proxy photograph shows the board installed with shields. It supports board-context registration but does not expose most chip bodies. Markers for concealed entities therefore indicate the registered position below the shield, not visual component detection. Standardized physical front/back photographs are still required to validate field-photo registration and exposed-component correspondence.

The first raster pass produced 112 anonymous regions because the normal page-text APIs did not expose designators. The current high-resolution rerun produces 323 anonymous regions, while the PDF compiler remains the primary component-identity and footprint source.

## Board Compiler Update

The PDF has now been parsed directly through its embedded Form XObject using the locally available `pypdf` content-stream API. The compiler decodes the embedded `/ToUnicode` font CMap, tracks PDF transformation matrices, extracts vector rectangles, and normalizes coordinates to the page's visible clipping bounds.

The first page-2 compile produced 3,665 decoded text objects, 3,719 vector rectangles, 820 accepted board designators, and recovered all seven reviewed entities. Candidate footprints now drive the 2.5D density layer instead of the earlier 112 anonymous raster regions. Every footprint remains explicitly provisional until the pairing confidence is reviewed.

The compiler now also derives the PCB silhouette from the rendered engineering-mark occupancy layer. Morphological closing, largest-component selection, hole filling, and contour simplification currently produce a 204-point normalized page-2 outline that replaces the manually approximated substrate. Footprint matching is graded as 180 high-confidence, 630 medium-confidence, and 10 low-confidence candidates; low-confidence geometry is excluded from the 2.5D workbench.

## Verification

- Six Node tests cover normalized coordinates, homography, inverse projection, polygon projection, selection state, and picking.
- Three Python tests plus the standalone validator cover assets, anchors, normalized board outline and entity geometry, stable identities, and source links.
- Desktop `1440x900` and mobile `390x844` browser paths cover all three views, seven markers, synchronized selection, nonblank WebGL pixels, responsive overflow, and runtime errors.
- Screenshots: `output/playwright/km4-cross-source-photo.png`, `km4-cross-source-pointmap.png`, `km4-cross-source-desktop.png`, and `km4-cross-source-mobile.png`.

V2 verification on 2026-07-13:

- 23 Node tests passed, including five model-profile tests written before the implementation.
- 33 Python compiler, outline, schematic, gallery, and registration tests passed.
- The standalone cross-source validator passed for seven entities and four anchors.
- Headed Chromium passed at `1600x900` and `390x844`: nonblank WebGL canvas, complete board framing, no horizontal overflow, inspection toggle, top-view reset, U4000 selection synchronization, and zero console/page errors.
- V2 screenshots are kept under ignored local `output/playwright/km4-v2-*-top.png` and `km4-v2-*-inspection.png`.
- Headless Chromium's first WebGL context can capture an empty initial compositing frame; this did not reproduce in headed Chromium and is retained as a test-runner limitation rather than a product defect.

Shield anatomy verification on 2026-07-13:

- 29 Node tests and 33 Python tests passed; the standalone validator passed for seven entities and four anchors.
- Headed Chromium passed at `1600x900` and `390x844`: Installed/X-ray/Removed state changes, U2001 selection under anatomy controls, seven module-menu options, zoom-level labels, drag rotation, reset, visible keyboard focus, no horizontal overflow, and zero console/page errors.
- Anatomy screenshots are kept under ignored local `output/playwright/km4-anatomy-*.png`.

Repair-focus verification on 2026-07-13:

- 39 Node tests and 33 Python tests passed; the standalone validator passed for seven entities and four anchors.
- Headed Chromium passed at `1600x900` and `390x844`: U2001, U4000, and U0600 produced distinct nonblank focus frames; full-board reset retained U2001 selection; controls remained in auto-module mode; no horizontal overflow or console/page errors occurred.
- Repair-focus screenshots are kept under ignored local `output/playwright/km4-repair-focus-*.png`.

Dual-side verification on 2026-07-13:

- 40 Node tests and 37 Python tests passed; both side artifacts and the manifest parsed successfully, and the standalone validator passed for seven entities and four anchors.
- Headed Chromium passed at `1600x900` and `390x844`: distinct nonblank side frames, automatic U2001 return to 第2面, manual flip in both directions, transition control locking, target preservation, side-specific module menus, 第2面 shield/X-ray mode, 第1面 module focus, drag, wheel zoom, full-board reset, keyboard-visible focus, no panel overlap, no horizontal overflow, and zero console/page errors.
- A regression path verifies that selecting U2001 still takes ownership of the repair target and flips to 第2面 after a manual 第1面 module selection.
- Dual-side screenshots are kept under ignored local `output/playwright/km4-sides-*.png`.

U2001 inspection verification on 2026-07-13:

- 46 Node tests and 37 Python tests passed; JSON and JavaScript syntax checks passed, and the standalone validator passed for seven entities and four anchors.
- Headed Chromium passed at `1600x900` and `390x844`: U2001 capability gating, enter/return animation, board ghosting, independent component drag, wheel zoom, source-backed fault/method copy, model-boundary copy, shield/module lockout, reset exit, entity-change exit, side-change exit, view-change exit, keyboard-visible focus, nonblank WebGL frames, no horizontal overflow, and zero console/page errors.
- U4000 remains correctly disabled for single-component inspection until it receives its own explicit profile.
- Inspection screenshots are kept under ignored local `output/playwright/u2001-inspection-*.png`.

Interaction-stability verification on 2026-07-14:

- Commit `65c45f4` replaces separate side/inspection locks with one model interaction state and blocks tabs, entity selection, side controls, model tools, and canvas input while a transition owns the scene.
- Initial data selection now updates the evidence panel without forcing an automatic camera focus; entering the model and full-board reset therefore produce the same settled frame.
- Repair focus and single-component inspection camera targets now follow the board's current tilt and rotation instead of using unrotated local coordinates.
- Selection feedback is a thin halo outside the package footprint, so the highlighted component remains visible.
- 50 Node tests, 37 Python tests, the standalone registration validator, and headed Chromium desktop/mobile interaction matrices passed. Rapid entity selection, rapid side switching, rotated-board focus, and mobile inspection enter/exit produced no console or page errors.
- QA screenshots are kept under ignored local `output/playwright/model-interaction-audit/`.

Bounded board-pan verification on 2026-07-14:

- Commit `9e74b29` adds an explicit `平移` / `旋转` drag mode. Pan is the default; rotation remains available without sharing the same pointer gesture.
- Orthographic pointer deltas are converted into zoom-aware world movement and clamped so the board cannot be lost completely outside the canvas.
- Manual panning preserves repair emphasis, component selection, wheel zoom, and resize state. Full-board reset restores the original frame and default pan mode.
- 53 Node tests, 37 Python tests, standalone registration validation, and headed Chromium desktop/mobile matrices passed. Canvas comparisons confirm pan movement and pixel-identical reset; component selection remains stable and the rotated-focus regression remains green.

Reviewed-component affordance verification on 2026-07-14:

- Commit `a1c2783` replaces the oversized coral selection ring and white/red callout with persistent amber corner brackets, compact constant-screen-size designator tags, subtle package emphasis, and a pointer-adjacent function tooltip.
- Only the seven source-reviewed entities receive these affordances. Nearby labels use reusable vertical lanes, and mobile does not depend on hover for discoverability.
- Each reviewed entity now owns a bounded transparent pick surface. This fixes the prior complex U2001 mesh bounds intercepting hover or click tests elsewhere on the board.
- Component inspection hides board-level affordances and restores them on exit; pan, rotate, repair focus, side switching, and reset retain their existing contracts.
- 57 Node tests, 37 Python tests, standalone validation, and headed Chromium desktop/mobile interaction matrices passed with seven affordances, correct tooltip identity, no runtime errors, and the existing rapid-transition regressions green.

Entity/module visual-ownership verification on 2026-07-14:

- Commit `3d8af66` stops entity targets from automatically rendering the source module polygon. Component selection now uses only its fitted corner markers, compact tag, and restrained material response.
- Source module membership remains attached to the entity target for evidence and camera context. A module polygon appears only after the technician explicitly selects a module from the focus control.
- The focus control now uses technician-facing `器件定位` and `全板视图` labels. Interactive hover switches the canvas cursor to a pointer, while drag retains the existing pan/rotate cursors.
- Selected-package emissive intensity was reduced so component surface geometry remains readable instead of appearing covered by an amber layer.
- 58 Node tests, 37 Python tests, standalone validation, and headed Chromium desktop/mobile interaction matrices passed. Browser evidence confirms empty entity overlay state, explicit module overlay state, deterministic restoration, pointer hover, and all existing rapid-transition paths.

Evidence-context verification on 2026-07-14:

- The desktop evidence panel now keeps the selected component identity, visibility status, and single-component inspection action in a compact sticky header while schematic and repair evidence scroll below it.
- The mobile layout retains normal document flow so the same header cannot cover content on narrow screens.
- Headed Chromium confirmed 529 px of evidence scrolling with zero header drift, a visible inspection action, the correct U2001 identity, and no console/page errors. The full desktop/mobile interaction matrix, 58 Node tests, 37 Python tests, and standalone registration validation remain green.

Compact model-control verification on 2026-07-14:

- The mobile model toolbar now occupies a complete second navigation row, keeping pan, rotate, inspection-angle, and full-board reset actions visible instead of clipping the final action.
- Shield/module state and board-side state share one horizontal control band at 390 px and 320 px without overlap. The narrow-screen dimensions preserve the full `器件定位` label and remove the page-level horizontal scrollbar.
- The redundant geometry legend was removed from the canvas. Source confidence remains available in the source note, while interactive-component discoverability is carried by the persistent fitted markers and tags.
- Headed Chromium passed desktop, 390 px, and 320 px layout and interaction checks with zero horizontal overflow or runtime errors. All 58 Node tests, 37 Python tests, and standalone registration validation passed.

Source-bounded repair-guidance interaction on 2026-07-14:

- All seven reviewed entities now expose an executable repair card when their source record contains a repair instruction. This capability is independent from the U2001-only single-component visual sample.
- The technician can select a documented fault symptom, read the exact source instruction and citation, and return `正常`, `异常`, or `无法确认`. Fault changes clear the prior observation; component changes keep session-local observations isolated and restore them when returning to the component.
- The interaction records observations only. It contains no generated diagnosis or component-replacement action, and it does not yet persist measurement values or case history to a backend.
- Explicit component changes reset the evidence panel to the new component's starting context. Sticky-header scroll margins prevent the repair card from being covered when it is brought into view.
- 62 Node tests, 37 Python tests, standalone validation, and headed Chromium desktop/390 px/320 px matrices passed. Browser evidence covers abnormal and uncertain results, U2001/U4000 state isolation, restoration, source-card visibility, model-boundary gating, zero overflow, and zero console/page errors.
