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

Source-defined measurement capture on 2026-07-14:

- Four reviewed measurement profiles are now structured in the cross-source dataset and tied to exact repair-link indices: U4000 `VDDEMMCCORE` voltage (record only), X2100 output frequency (26 MHz nominal without tolerance), VBAT1 voltage (3.4 V to 4.35 V range), and VBUS1 voltage (5 V nominal without tolerance).
- The repair card exposes a numeric input, source unit, source reference, record action, and measurement feedback only for those four entities. U2001 and other entities do not receive invented measurement controls.
- VBAT1 is the only profile that automatically maps a value to normal/abnormal because it is the only source with complete lower and upper bounds. Nominal and record-only profiles remain unclassified and explicitly state that no tolerance was supplied.
- Dataset validation rejects missing/duplicate measurement identities, missing units, invalid source indices, nonpositive input steps, inverted ranges, nominal references without values, and unsupported reference kinds.
- 65 Node tests, 41 Python tests, standalone validation, and headed Chromium desktop/390 px/320 px interaction matrices passed. Browser evidence covers within-range, below-range, nominal-only, hidden-control, and mobile measurement states with zero overflow and zero runtime errors.
- Measurement records remain page-session state. Backend persistence, case linkage, and source-backed next-step branching are still open.

First source-reviewed multi-step branch on 2026-07-14:

- A visual/text audit of repair-guide pages 9, 10, 11, 14, and 15 is recorded in `docs/km4-repair-flow-source-audit-2026-07-14.md`.
- J6101 `无法充电` now exposes the unambiguous page-14 sequence: charger condition, USB solder condition, and FPC seating condition. Each answer follows an explicit source arrow and can produce the exact source action, advance, go back, or reset.
- The later FPC-defect Y/N labels conflict with their displayed actions. The runtime deliberately stops at a yellow source-boundary terminal and shows the reviewed ambiguity note instead of guessing the next edge.
- Generic normal/abnormal/uncertain controls are hidden only while this exact fault/flow pair is active. Selecting `USB 无响应` restores the generic source-guidance interaction.
- U4000 `VDDEMMCCORE` was corrected from record-only to a 3.3 V nominal reference without tolerance based on the page-11 signal table.
- Repair-flow validation rejects graph edges outside declared steps, unresolved component targets, duplicate identities, unsupported outcomes, and boundary terminals without reviewed-partial status plus a note.
- Headed Chromium desktop/mobile matrices passed the three-step path, boundary terminal, back, reset, source action, alternate-fault restoration, history, and zero-overflow checks with no console/page errors.

Composite measurement and cross-component repair flow on 2026-07-14:

- The page-10 small-current no-power path is now structured as a second source-reviewed repair flow. Its first decision cannot advance until both `VDDCORE` and `VDDEMMCCORE` have been recorded in the same step.
- Nominal references remain technician-reviewed because pages 10-11 provide values but no tolerance. Recording a value never silently decides normal or abnormal.
- Flow state owns step-scoped measurement records. Required-field completeness is enforced in the state module and in the interface, so future composite checks can reuse the same data contract.
- Editing a previously recorded value immediately makes the step incomplete again and locks its outcome choices until the technician records the revised values.
- The model follows the source target across the graph: U4000 rail check, X2100 26 MHz check, U2001 power-management action, and X2100 crystal action. Back and reset move both the graph and selected model entity together.
- 71 Node tests, 46 Python tests, and standalone dataset validation passed. Headed Chromium desktop and 390 px checks cover locked choices, dual measurement capture, dirty-value relocking, cross-entity advance, both abnormal terminals, back, reset, source copy, model focus, and zero horizontal overflow with no console/page errors.

Repair-sidebar hierarchy refinement on 2026-07-14:

- Active source flows now appear before the passive source summary, so the technician reaches the current action before supporting evidence.
- Every reviewed flow step has a short source-owned label. The interface renders a persistent trail with completed, current, and pending states and identifies the component currently targeted by the graph.
- Answer history remains visible as a secondary result log. Exact PDF citations remain available in a collapsed `资料依据` disclosure, reducing visual competition without removing traceability.
- Ordinary progress uses ink and restrained green states; coral remains reserved for abnormal/fault feedback and yellow remains reserved for reviewed source boundaries.
- Headed Chromium desktop and 390 px evidence verifies flow-before-source order, trail-state transitions, target/model agreement, collapsed source detail, responsive fit, and no console/page errors.

Repair-flow continuity cleanup on 2026-07-14:

- The outer generic progress counter is hidden while a structured repair flow is active. The flow trail and its own step counter are now the single progress source, removing the prior duplicated `1 / 2` state.
- Mobile cross-component advancement was exercised from U4000 rail checks to X2100 frequency inspection. The selected entity, source summary, trail, and prompt update together while the new question remains fully inside the existing viewport.
- No forced page scroll was added: the current layout already preserves task continuity, and an automatic jump would unnecessarily disturb the technician's reading position.

Interrupted-flow recovery on 2026-07-14:

- A started repair flow remains visible as a compact `进行中的排查` return strip when the technician temporarily selects another component or switches to a different fault on the same component.
- The return action restores the flow's documented fault, current target component, model focus, measurements, answer history, and active prompt instead of restarting the graph.
- Flow target resolution is now part of the tested state module, so active-step targets, explicit terminal targets, model navigation, and the recovery strip share one rule.
- Headed Chromium verifies U4000 -> X2100 progression, temporary U0600 inspection, return to X2100, same-component fault interruption, keyboard-visible focus, 390 px fit, and zero runtime errors.
