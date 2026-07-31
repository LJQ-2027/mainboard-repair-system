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

## Component Inspection Contract

- U2001, U4000, X2100, U0600, and J6101 have explicit `inspection_profile` records. The capability is data-enabled rather than inferred from a designator, so test points and unfinished components do not expose a misleading control.
- `单体查看` keeps the selected package at its registered board coordinate, raises and enlarges it, and turns the board and unrelated packages into a low-opacity context layer.
- Pointer or single-touch drag rotates the package around its own center. Wheel and two-touch pinch input use inspection-specific zoom bounds while the board remains still.
- The canvas toolbar exposes component rotation as the active direct-manipulation mode. Its reset action restores the package angle, zoom, and center without leaving inspection.
- Return, entity change, side change, and view change restore the original package transform, camera, opacity, shield state, module state, selected identity, evidence context, and prior board drag mode.
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
- The WebGL canvas now declares touch-gesture ownership. A real vertical touch drag previously moved the model and scrolled the page by 105 px at the same time; it now changes the model frame with zero page movement. A gesture starting outside the canvas still scrolls the mobile document normally.
- Real touch regression covers canvas pan, outside-page scroll, tap-to-select, unchanged U2001 identity during pan, and pixel-identical full-board reset.
- Two-touch pinch now maps finger-distance change to the same bounded camera zoom used by desktop wheel navigation. Pinch owns both pointers, suppresses terminal taps, and releases cleanly back to single-finger pan.
- Real 390 px multi-touch evidence increased model zoom from 1.000 to 2.200 with zero page movement or selection change; single-finger pan worked immediately afterward, and full-board reset restored zoom 1.000 plus the original pixel frame.

Reviewed-component affordance verification on 2026-07-14:

- Commit `a1c2783` replaces the oversized coral selection ring and white/red callout with persistent amber corner brackets, compact constant-screen-size designator tags, subtle package emphasis, and a pointer-adjacent function tooltip.
- Only the seven source-reviewed entities receive these affordances. Nearby labels use reusable vertical lanes, and mobile does not depend on hover for discoverability.
- Each reviewed entity now owns a bounded transparent pick surface. This fixes the prior complex U2001 mesh bounds intercepting hover or click tests elsewhere on the board.
- Component inspection hides board-level affordances and restores them on exit; pan, rotate, repair focus, side switching, and reset retain their existing contracts.
- 57 Node tests, 37 Python tests, standalone validation, and headed Chromium desktop/mobile interaction matrices passed with seven affordances, correct tooltip identity, no runtime errors, and the existing rapid-transition regressions green.
- Touch hit areas now maintain a screen-space minimum: 24 px on desktop and 36 px below 620 px, independent of model zoom. Overlapping transparent targets resolve to the component whose projected center is closest to the pointer, while visible corner markers retain their fitted size.
- A real 390 px touch-context tap selected X2100 directly from the canvas and synchronized camera focus, selected affordance, evidence identity, and module context with zero overflow. Pan still wins after the existing movement threshold.

Entity/module visual-ownership verification on 2026-07-14:

- Commit `3d8af66` stops entity targets from automatically rendering the source module polygon. Component selection now uses only its fitted corner markers, compact tag, and restrained material response.
- Source module membership remains attached to the entity target for evidence and camera context. A module polygon appears only after the technician explicitly selects a module from the focus control.
- The focus control now uses technician-facing `器件定位` and `全板视图` labels. Interactive hover switches the canvas cursor to a pointer, while drag retains the existing pan/rotate cursors.
- Selected-package emissive intensity was reduced so component surface geometry remains readable instead of appearing covered by an amber layer.
- 58 Node tests, 37 Python tests, standalone validation, and headed Chromium desktop/mobile interaction matrices passed. Browser evidence confirms empty entity overlay state, explicit module overlay state, deterministic restoration, pointer hover, and all existing rapid-transition paths.

Unresolved-geometry marker refinement on 2026-07-14:

- Reviewed entities whose source geometry is too weak for a package body retain a thin location ring, but the ring now uses a neutral low-opacity technical color instead of the same amber used by selection.
- The marker continues to communicate an unresolved source position without fabricating component height. Persistent corner brackets, label emphasis, and restrained material response are now the only selected-component language.
- A model-profile test prevents unresolved markers from reusing selection amber or fault coral. Headed Chromium confirms all seven reviewed entities remain discoverable and selectable through pan, rotation, side changes, and component inspection paths.

Evidence-context verification on 2026-07-14:

- The desktop evidence panel now keeps the selected component identity, visibility status, and single-component inspection action in a compact sticky header while schematic and repair evidence scroll below it.
- The mobile layout retains normal document flow so the same header cannot cover content on narrow screens.
- Headed Chromium confirmed 529 px of evidence scrolling with zero header drift, a visible inspection action, the correct U2001 identity, and no console/page errors. The full desktop/mobile interaction matrix, 58 Node tests, 37 Python tests, and standalone registration validation remain green.
- A later full-board QA pass found the component-name line starting 15 px beneath the sticky heading. The desktop spacing now produces zero geometric overlap while preserving sticky identity, inspection controls, and normal mobile document flow.

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

Destructive reset protection on 2026-07-14:

- `重新开始` no longer clears measurements and answer history on one click. The first activation changes the same button to `确认重置`; only a second activation within four seconds resets the flow.
- `Escape`, timeout, or any flow rerender cancels the armed state. The confirmation remains inline instead of opening a modal that would hide the model and current repair context.
- The armed button uses a restrained warning treatment distinct from component selection, abnormal-result feedback, and yellow source-boundary states.
- Headed Chromium covers armed-without-reset, Escape cancellation, confirmed reset for both reviewed flows, prompt/target preservation before confirmation, and the full desktop/mobile regression matrix.

Terminal source-action execution record on 2026-07-14:

- A terminal with `kind: action` now accepts a reversible session-local `已执行` record. The state is preserved through temporary component/fault interruptions and cleared by back or confirmed restart.
- The interface explicitly says `维修结果仍需复检确认`; executing a source action is not represented as a successful repair or diagnosis.
- A `kind: boundary` terminal never exposes the execution control because an ambiguous source edge is not an executable repair instruction.
- Headed Chromium covers pending/executed action states, restored execution state, hidden boundary control, visible focus, mobile fit, and zero overflow/runtime errors.

Post-action recheck observation on 2026-07-14:

- After a source action is marked executed, the technician can record `现象消失`, `现象仍在`, or `无法确认`. The control is unavailable before execution and never appears at a source-boundary terminal.
- Recheck is an observation only. `现象消失` still states that final quality confirmation is required; no option automatically marks the repair successful or releases the board.
- Revoking execution, going back, or confirmed restart clears the recheck. Temporary component/fault interruption preserves it with the rest of the page-session flow state.
- Headed Chromium covers hidden/pending/three-result states, persisted recheck after interruption, semantic feedback colors, 390 px three-segment fit, and zero overflow/runtime errors.

Repair-flow lifecycle closure on 2026-07-14:

- A source action can end the current investigation only after the technician records both execution and a post-action observation. A reviewed source boundary can end directly because it has no executable action to confirm.
- `结束本次排查` freezes the page-session record. Action execution, recheck choices, back, and restart are no longer mutable; the completed record remains visible with an explicit ended status and a single `开始新一轮` action.
- The closed presentation replaces action-oriented wording with `已记录执行`, marks the step badge as `已结束`, and renders the selected recheck result as restrained read-only evidence instead of an active segmented choice.
- The completion area now states the missing prerequisite instead of relying on a disabled button alone: execution first, then post-action observation. Ready action terminals and reviewed source boundaries receive distinct one-line completion guidance.
- Ending an investigation never represents repair success. The existing recheck wording and the completion status keep repair outcome and final quality confirmation outside this page-session lifecycle.
- A completed flow no longer appears as `进行中的排查` when the technician inspects another component. Returning to its component shows the read-only record; starting a new round explicitly clears it and restores the source entry step.
- State tests cover close prerequisites, read-only mutation guards, source-boundary closure, and reset semantics. Headed Chromium covers desktop and 390 px closure, disabled controls, hidden navigation, cross-component return behavior, new-round reset, zero overflow, and zero runtime errors.

Pointer-anchored model zoom on 2026-07-14:

- Desktop wheel zoom now preserves the board point beneath the mouse pointer instead of pulling the model toward the canvas center.
- Mobile pinch zoom preserves the initial board point beneath the live finger midpoint. Moving the midpoint while changing finger distance therefore combines zoom and pan without a separate gesture transition.
- The anchor calculation is camera-frame based and remains inside the existing pan and zoom bounds. Tap suppression, component selection, single-finger pan, and full-board reset behavior are unchanged.
- Headed Chromium at 390 px verified that X2100 remained under the same screen coordinate after zooming to 4.2x, with X2100 still selected, no page scroll, and no runtime errors. The full desktop, 390 px, and 320 px interaction matrix also passed.

Readable component affordances on 2026-07-14:

- The seven reviewed interactive entities retain fitted corner brackets and compact designator tags only. No module polygon, large circle, or broad translucent selection overlay is used for ordinary entity selection.
- Fixed screen-space tags increased from 48 x 14 px to 68 x 20 px, with the hovered or selected identity at 76 x 22 px. The text is now readable in the whole-board desktop and 390 px views without enlarging component hit geometry.
- The raster tag treatment now uses a complete restrained border and a small amber locator square instead of an orange side stripe. Hover tooltips likewise use a uniform border, automatically flip around canvas edges, and remain fully inside the model surface.
- Wheel zoom recomputes hover against the anchored camera state, while touch input clears desktop-style hover feedback. Headed Chromium kept X2100 as the same hover target through wheel zoom, showed no touch tooltip residue, and passed the full desktop/390 px/320 px interaction matrix with no runtime errors.

Mobile model-control readability on 2026-07-15:

- Model view tabs and pan/rotate modes now render at 12 px on narrow screens. Shield states, module selection, side selection, and the source note render at 11 px with stronger control-label weight, without increasing toolbar height.
- The mobile `.view` padding rule no longer overrides the model surface's zero-padding contract. The WebGL canvas regains 18 px of horizontal space, and both floating control groups now sit fully inside the actual canvas rather than extending one pixel beyond each edge.
- At 320 px, side buttons use the compact visible labels `1面` and `2面` while retaining the full accessible names `第1面` and `第2面`. The original compact widths preserve a measured two-pixel gap between the anatomy and side-control groups.
- Headed Chromium at 390 px and 320 px verifies minimum font sizes, unwrapped labels, complete accessible side names, controls inside the WebGL canvas, no control overlap, no horizontal overflow, and correct selected states. The full interaction matrix passed with no runtime errors.

Neutral single-component inspection state on 2026-07-15:

- Entering or leaving single-component inspection is a normal model-navigation state, not a fault result. The active `返回主板` action now uses the restrained engineering green instead of the coral reserved for abnormal observations.
- The canvas inspection status no longer uses a coral side stripe. It uses a complete neutral border, a dark instrument surface, and 11 px supporting text while the isolated component keeps its precise amber edge treatment.
- No new module polygon, broad overlay, or selection circle was introduced. The existing low-opacity board context remains the only visual isolation layer around the extracted component.
- Headed Chromium on desktop and 390 px verifies non-fault active color, uniform status borders, readable status text, canvas containment, active/exit labels, entry and exit states, component interaction, and zero horizontal overflow. The full interaction matrix passed with no runtime errors.

Neutral source-evidence cards on 2026-07-15:

- Schematic and repair-reference cards no longer use a coral left stripe. Static source material is not a fault state, so both card types now use the same complete low-contrast neutral border.
- Source headings, two schematic images, repair instructions, filenames, and page references remain unchanged. The calmer container treatment preserves scan order while allowing actual abnormal observations to keep the coral semantic role.
- Headed Chromium on desktop and 390 px verifies two visible evidence cards, equal nonzero border widths, border colors distinct from the fault accent, card containment inside the evidence panel, retained schematic images and repair text, and zero horizontal overflow.
- The full interaction matrix passed with repair abnormal states, measurement classification, structured flows, single-component inspection, and mobile gestures intact and no runtime errors.

Semantic repair-result states on 2026-07-15:

- Generic measurement results and post-action recheck observations now share one three-state visual grammar: green for normal or symptom cleared, coral for abnormal or symptom persists, and yellow for uncertain.
- Result messages no longer use a colored left stripe. Each state uses a complete semantic border with a light matching background, so the status reads as a bounded outcome instead of another locator or source-card accent.
- Coral remains reserved for genuine abnormal feedback. Normal navigation, static evidence, and component inspection continue to use their neutral or engineering-green treatments.
- Headed Chromium verifies all six result states with equal border widths on every side, distinct semantic backgrounds, retained repair wording, desktop/mobile containment, and zero runtime errors. The full interaction matrix passed without regressions to model navigation, repair flows, or touch gestures.

Manual module-overlay control removal on 2026-07-15:

- The model no longer exposes the `器件定位` module selector. It duplicated reviewed-component highlighting, consumed the most space in the left canvas tool group, and could reintroduce the broad orange module overlay through an unrelated manual state.
- Source-driven repair targets remain intact. A documented repair step can still request a module target through the existing repair-focus contract, while ordinary component selection continues to produce no active module overlay.
- The anatomy tool now contains only the three shield states. This reduces the desktop group from roughly 280 px to 150 px and leaves a materially wider gap between the anatomy and side controls at 390 px and 320 px.
- A regression test prevents the manual selector and its independent application state from returning. Headed Chromium verifies no selector, no ordinary-selection module overlay, three retained shield controls, compact desktop/mobile layout, and the full interaction matrix with zero runtime errors.

Canvas-owned model controls on 2026-07-15:

- Pan, rotate, inspection-angle, and full-board reset now belong to the model canvas instead of the global view header. View tabs switch sources; model controls operate only on the model surface.
- The control group uses a compact bottom-left instrument panel. It remains separate from top-left shield anatomy, top-right side switching, and the bottom-right single-component status.
- On 390 px and 320 px screens, the view header returns from two rows to one and the model canvas gains about 39 px of height. The larger stage produces a visibly larger whole-board frame without reducing the established 12 px/11 px control readability.
- A structural test prevents `modelTools` from returning to the global header. Headed Chromium verifies canvas containment, no overlap with top controls or inspection status, compact view-head height, at least 440 px of mobile canvas height, and the full interaction matrix with zero runtime errors.

Screen-space component-label layout on 2026-07-15:

- Reviewed designator tags are no longer assigned once in board-world coordinates. Every render projects component anchors into the current canvas, resolves nearby label candidates in pixels, and unprojects the chosen positions back into the 3D scene.
- The layout keeps all seven reviewed labels visible. It selects nearby positions above, below, left, or right of each anchor, then uses a bounded fallback grid only when every local candidate is occupied.
- Collision and containment use the actual WebGL canvas size rather than the nominal browser viewport. At a 320 px browser width the drawable canvas is 304 px, so right-edge labels such as `VBAT1` and `VBUS1` now remain fully visible instead of being clipped.
- The renderer exposes measured overlap and outside counts for browser QA. Headed Chromium verifies both counts remain zero at desktop, 390 px, 320 px, and after anchored wheel zoom while selection, touch gestures, rotation, and inspection remain intact.

Selective component-label leaders on 2026-07-15:

- A reviewed designator tag receives a short leader only when collision avoidance moves its center at least 48 px from the projected component anchor. Nearby tags remain unconnected, preventing the whole-board view from becoming a line network.
- Each leader starts eight screen pixels away from the component anchor and ends at the nearest edge of the tag. It inherits the restrained amber component-affordance color and stays subordinate to hover and selection feedback.
- Leaders are hidden in single-component inspection because the isolated body already establishes identity. No module polygon, broad translucent overlay, or fault-coral treatment is used.
- Label layout now defers during the initial pre-layout frame when the canvas is too small to contain one tag. This prevents invalid Three.js geometry before the real ResizeObserver dimensions arrive.
- Headed Chromium verifies a selective leader count between one and six at 390 px and 320 px, zero leaders during inspection, zero label overlap or clipping, and the full desktop/mobile interaction matrix with no runtime errors.

Stable component-label placement on 2026-07-15:

- Each reviewed label now remembers its last valid compass slot relative to the projected component anchor. Rotation, pan, and zoom move the label with the component instead of restarting the placement search from the first candidate on every frame.
- A remembered slot is reused only while it remains inside the canvas and free of collisions. Real conflicts still trigger the existing bounded fallback search, preserving all seven visible identities without overlap.
- Full-board reset clears the slot memory together with camera and focus state. The reset frame is therefore deterministic rather than retaining a label arrangement created by an earlier edge collision.
- A headed Chromium rotation audit sampled 26 consecutive frames with zero slot transitions, zero label overlaps, zero clipping, and zero runtime errors. The strict full matrix also verifies pixel-identical desktop and 390 px pan/reset recovery.

Drag-path click suppression on 2026-07-15:

- Board interaction now records whether the pointer has exceeded the five-pixel drag threshold at any time during a gesture. Returning the pointer to its original coordinate no longer converts a completed pan or rotation into a component click.
- Pointer down continues to clear hover feedback, dragging keeps the tooltip hidden, and mouse hover returns only after the next pointer movement. Touch gestures never leave desktop hover residue.
- The same accumulated-travel rule applies to mouse and single-touch board gestures. Component inspection rotation remains non-selecting, while a genuine stationary tap still follows the existing component-pick path.
- Headed Chromium reproduces a drag from X2100 outward and back to X2100 with both mouse and touch: U2001 remains selected, dragging state clears, hover recovers correctly for mouse, and no runtime errors occur. The full desktop/mobile interaction matrix also passes.

Three-state component-tag hierarchy on 2026-07-15:

- Reviewed component tags now render separate idle, hovered, and selected CanvasTexture variants. Idle uses a neutral complete border, hover uses a light amber complete border, and selection uses a stronger amber complete border with brighter text.
- Tag dimensions and dark background area remain unchanged. The hierarchy does not introduce a side stripe, broad fill, module polygon, selection circle, or fault-coral treatment.
- Selection remains authoritative when the same entity is hovered. Moving selection from U2001 to X2100 transfers the selected texture with the shared identity state, while touch interaction clears the desktop hover variant.
- All three textures are owned by the sprite and disposed when a board side is replaced. Headed Chromium verifies selected/hovered variants on desktop, selected-without-hover on touch, visible mobile tag differentiation, and the full interaction matrix with no runtime errors.

Reviewed multi-component inspection on 2026-07-15:

- Repair-visual inspection profiles now explicitly cover U2001, U4000, X2100, U0600, and J6101. Each has a source-bounded profile identity, category-based fidelity, and a visible note that the package is a repair-recognition representation rather than measured engineering geometry.
- The same isolation state, camera transform, low-opacity board context, component rotation, status frame, and return action are reused across all five package entities. No parallel inspection implementation or model-specific UI branch was added.
- VBAT1 and VBUS1 remain test-point locations rather than component bodies. They retain measurement and repair guidance, do not receive inspection profiles, and no longer show an unavailable `单体查看` action.
- Dataset validation rejects an inspection profile attached to a test point. Headed Chromium enters and exits all five package entities, verifies zero label leaders in isolation, checks U4000 and J6101 visually, confirms X2100 mobile containment, and passes the strict full interaction matrix without runtime errors.

Direct component manipulation on 2026-07-15:

- Single-component inspection now presents `旋转` as the active drag mode instead of disabling both board interaction controls. `平移` remains unavailable because the drag gesture owns package rotation, not board movement.
- Mouse drag and one-finger touch rotate the isolated package. Wheel and two-finger pinch retain the inspection zoom bounds and do not change the selected identity or move the page.
- The focused WebGL surface also supports arrow-key rotation, plus/minus zoom, and Home-key reset. The active rotation mode button moves keyboard focus to that surface instead of acting as a no-op.
- The reset icon is repurposed in inspection to restore the initial package angle, camera center, and zoom without returning to the board. `返回主板` remains the sole explicit exit action and restores the prior board drag mode and camera center.
- Headed Chromium produced pixel-different rotation and pinch frames, pixel-identical reset frames on desktop and mobile, a responsive-threshold reset race matching the stable target, and a clean pan-mode restoration after return. The strict full interaction matrix, 90 Node tests, 49 Python tests, source validation, and inline-script compilation passed without runtime errors.

Canvas-local inspection return on 2026-07-15:

- The existing bottom-right inspection identity is now a native return button instead of a non-interactive status block. It keeps the designator visible and routes through the same inspection state machine as the evidence-panel `返回主板` action.
- Desktop click, keyboard Enter, and real mobile touch all leave isolation while preserving the selected component and restoring board context.
- At 390 px the button retains `← U4000 单体检视`. At 320 px it keeps the 40 px touch height and source identity while hiding only the redundant `单体检视` suffix, preventing overlap with the canvas toolbar.
- Headed Chromium verifies canvas containment, zero overlap with model/anatomy/side controls, zero horizontal overflow, and successful return at desktop, 390 px, and the actual 304 px drawable canvas inside a 320 px viewport. The strict full interaction matrix, 91 Node tests, 49 Python tests, source validation, and inline-script compilation passed without runtime errors.

Contextual inspection controls on 2026-07-15:

- Single-component inspection now shows only controls that operate on the isolated package: rotation, view reset, and canvas/evidence return. Board pan, board inspection angle, shield anatomy, and side switching leave the visual and accessibility trees while isolation is active.
- Returning to the board restores every board-level control, its prior interaction state, and side-switch availability without reloading or clearing the selected component.
- This removes four groups of disabled visual noise from the inspection canvas without adding an overlay, menu, or parallel interaction mode.
- Headed Chromium verifies the reduced control set and complete restoration at desktop, 390 px, and 320 px, with zero toolbar/return overlap and zero horizontal overflow. The strict full interaction matrix, 92 Node tests, 49 Python tests, source validation, and inline-script compilation passed without runtime errors.

Mobile entity-list model reveal on 2026-07-15:

- Selecting a component from the bottom `已关联实体` list now returns the 2.5D workspace to view on screens at or below 820 px, so the technician immediately sees the focused package instead of remaining at the list position.
- The scroll is deliberately owned by the entity-list event path rather than shared `selectEntity()` state. Canvas picks, image/point-map markers, repair-flow target changes, initial selection, desktop layouts, and non-model tabs do not move the page.
- The reveal uses smooth scrolling by default and an immediate scroll when the browser requests reduced motion. It aligns the workspace to the viewport start without changing the model camera or selected identity.
- Headed Chromium verifies desktop non-scrolling, mobile 390 px and 320 px model reveal, photo-view non-scrolling, reduced-motion behavior, 454 px of visible model canvas, zero horizontal overflow, and zero runtime errors. The strict full interaction matrix, 95 Node tests, and 49 Python tests passed.

View-aware source notes on 2026-07-15:

- Entity proxy, engineering point map, board model, and isolated package views now receive their source note through one tested state helper. The point-map tab no longer repeats the Service Manual proxy-image boundary.
- Reviewed `proxy_note` and `point_map_note` strings are stored in registration data and required by dataset validation. Model and inspection notes continue to derive the active board side, accepted designator count, and selected package identity from structured state.
- At 480 px and below, the source row uses its existing 11 px text size, wraps completely, and grows only when needed instead of hiding content behind an ellipsis. The fixed workspace height remains unchanged and the model/image stage owns the remaining space.
- Headed Chromium verifies the exact four source-note states at desktop, 390 px, and 320 px. Every note fits within both axes, each source row remains 42 px for the current reviewed copy, page overflow is zero, and there are no runtime errors. The strict full interaction matrix, 100 Node tests, and 50 Python tests passed.

Compact cross-view markers on 2026-07-15:

- Entity-proxy and engineering-point-map markers no longer use large coral circles or ambiguous designator prefixes. Ordinary navigation now uses a 12 px neutral locator, hover uses light amber, and selection uses strong amber; coral remains reserved for abnormal repair observations.
- A transparent 36 px button preserves mouse and touch acquisition without enlarging the visible mark. The complete designator appears only for hover, keyboard focus, or selection, and the selected identity remains synchronized across both image views and the evidence panel.
- Keyboard navigation exposes the same complete identity and adds a blue focus ring around the compact locator. The focus treatment does not resize the target or shift the registered coordinate.
- Headed Chromium verifies target/locator dimensions, final-state colors, complete U2001/U4000/X2100 labels, hover, Tab focus, synchronized photo/point-map selection, label containment, zero overflow, and zero runtime errors at desktop, 390 px, and 320 px. The strict full interaction matrix, 104 Node tests, and 50 Python tests passed.

Cross-view component inspection on 2026-07-15:

- `单体查看` now remains available for reviewed package entities selected in the proxy photo or engineering point map. One action serially opens the 2.5D view, switches to the entity's registered board side when needed, and enters package isolation.
- On mobile, this explicit action also aligns the model workspace to the viewport. Desktop pages do not scroll, shared selection state does not own page movement, and non-package test points still expose no inspection action.
- Point-map markers now receive pointer input before the pan surface. In dense marker groups, the target nearest the physical pointer position wins even when a neighboring 36 px acquisition area is visually above it; keyboard activation remains tied to the focused marker.
- Headed Chromium verifies photo and point-map entry, automatic side correction, package return, test-point exclusion, zero horizontal overflow, and zero runtime errors at desktop, 390 px, and 320 px. The strict full interaction matrix, 109 Node tests, 50 Python tests, source validation, syntax checks, and UTF-8 validation passed.

Adaptive narrow-screen board composition on 2026-07-15:

- At narrow portrait canvas ratios, the wide KM4 board now defaults to a 90-degree screen composition. The source coordinate system, package orientation relative to the board, picking, repair focus, and side identity remain unchanged.
- The orthographic frame is calculated from the rotated board bounds and reserves explicit top and bottom control-safe bands. At 390 px and 320 px the complete board occupies more than 70% of the model-canvas height while its conservative screen bounds remain disjoint from shield, side, and model-tool controls.
- Manual board rotation remains authoritative until reset. Reset restores the current viewport's default composition; side replacement preserves it, and responsive transitions between narrow portrait and wider layouts select portrait or landscape framing without reload.
- Reset label slots are now cleared only after the camera reaches its exact terminal frame. This removes animation-path-dependent slot assignment and restores pixel-identical pan and pinch reset frames.
- Headed Chromium verifies desktop, 390 px, and 320 px composition, both board sides, manual rotation/reset, 390-to-700-to-390 responsive transitions, inspection entry/return, zero control overlap, zero label overlap or clipping, and zero runtime errors. The strict full interaction matrix, 113 Node tests, 50 Python tests, source validation, syntax checks, diff checks, UTF-8 checks, and HTTP checks passed.

Repair-facing model toolbar clarity on 2026-07-15:

- The board-angle control now uses the explicit `斜视` label and a persistent pressed state instead of the ambiguous `◩` glyph. Its accessible action changes between `切换为斜视` and `恢复俯视` as the camera state changes.
- Full-board reset now uses the same familiar `↻` symbol as the point-map reset family instead of the crosshair-like `⌖`. Reset continues to restore pan mode, top view, board framing, and deterministic label placement.
- The toolbar retains stable button dimensions and remains one row at desktop, 390 px, and 320 px. No explanatory legend, overlay, or canvas obstruction was added.
- Headed Chromium verifies explicit labels, pressed state, reset state, canvas containment, complete button text, zero horizontal overflow, and zero runtime errors at all three widths. The strict full interaction matrix, 114 Node tests, 50 Python tests, source validation, syntax checks, diff checks, and HTTP checks passed.

Unified board-angle interaction on 2026-07-15:

- Button-driven and drag-driven board tilt now share renderer-owned angle state. Crossing the repair-view tilt threshold during a rotation gesture immediately synchronizes the `斜视` pressed state and accessible action instead of leaving stale toolbar feedback.
- The `斜视` action uses a cancellable 280 ms cubic ease and participates in the same exclusive interaction transition as inspection and side switching. Repeated controls, canvas gestures, and view changes cannot race the in-flight angle transition.
- Side replacement preserves the current X tilt together with Z orientation. Full-board reset remains the explicit path back to top view and pan mode.
- Browsers requesting reduced motion receive the exact terminal angle without animation. Renderer diagnostics expose the current board tilt and angled state for interaction verification.
- Headed Chromium sampled 22 monotonic animation frames, verified animation locking, manual-drag toolbar synchronization, side-preserved tilt, deterministic reset, reduced-motion behavior, and zero runtime errors. The strict full interaction matrix, 116 Node tests, 50 Python tests, source validation, syntax checks, diff checks, and HTTP checks passed.

Direct selected-component drill-down on 2026-07-16:

- Model activation now follows a deliberate two-stage contract. The first click or tap selects a component and updates repair context; activating the same selected package again enters its existing single-component inspection path directly from the model.
- Direct drill-down is capability-gated by the reviewed inspection profile. VBAT1 and VBUS1 remain measurement locations even when repeatedly activated and never become synthetic package inspections.
- A selected inspectable package adds a compact `单体查看` action row to its existing hover card. No permanent instruction, new overlay, broad highlight, or duplicate inspection runtime was added.
- Drag-return gestures retain accumulated-travel suppression and cannot become direct drill-down activations. Desktop and touch use the same activation state helper and the same inspection transition.
- Headed Chromium verifies select-then-inspect behavior, immediate default-selection drill-down, test-point exclusion, drag-return suppression, mobile two-tap entry, zero horizontal overflow, and zero runtime errors. The strict full interaction matrix, 118 Node tests, 50 Python tests, source validation, syntax checks, diff checks, and HTTP checks passed.

Free-browse versus guided-focus selection on 2026-07-16:

- Component activation inside the WebGL board is now a free-browse action. It updates the selected identity, precise package affordance, hover action, and repair evidence without changing camera center, zoom, tilt, or board screen bounds.
- Canvas selection cancels any in-flight focus camera animation and clears stale repair-region emphasis while preserving the technician's manual camera. This prevents ordinary exploration from retaining unrelated range dimming.
- Entity-list, cross-source, and repair-flow selections retain the existing guided-focus path. They may change side, move the camera, zoom to the source-backed repair region, and apply local emphasis because those actions explicitly request navigation.
- The stable free-browse frame lets desktop and touch users activate the same selected package again at the same screen coordinate to enter inspection. No timer, double-click dependency, or hidden coordinate cache was added.
- Headed Chromium verifies pixel-coordinate-stable board bounds and unchanged `1.000` zoom for canvas selection at desktop and mobile, same-coordinate drill-down, and retained guided focus from `1.000` to `1.900`. The strict full interaction matrix, 119 Node tests, 50 Python tests, source validation, syntax checks, diff checks, and HTTP checks passed.

Native-material component selection on 2026-07-16:

- Ordinary idle, hover, and selected affordances no longer modify package emissive color or intensity. The package body keeps its native category material while eight fitted corner segments and the compact designator tag communicate interactivity and selection.
- Entering and leaving single-component inspection no longer applies or restores an amber material tint. Isolation continues to use context opacity, camera framing, render order, and the existing return contract; abnormal repair observations retain their dedicated fault-color semantics.
- A fixed-camera browser comparison sampled 2,200 pixels inside U4000 before selection, after selection, and after an inspection round trip. All package-interior pixels remained identical while the external selected affordance stayed visible and the camera remained at `1.000` zoom with unchanged board bounds.
- The strict headed desktop/390 px/320 px interaction matrix, 120 Node tests, 50 Python tests, source validation, syntax checks, diff checks, and HTTP checks passed without runtime errors.

External interactive component labels on 2026-07-16:

- Reviewed designator tags now use the projected package bounds as layout obstacles. Tags remain outside their own package and every other reviewed interactive package at top, angled, zoomed, 390 px, and 320 px views while retaining collision-free, canvas-bounded placement.
- Leader lines begin outside the package edge and appear only when collision avoidance creates a meaningful gap. Adjacent tags no longer draw a line through the component body.
- Visible tags participate in the same raycast, selection, and direct-inspection path as package hit areas. Desktop hover/click and mobile tap can select a tag; reactivating an inspectable selected tag enters the existing isolation runtime, while test-point tags remain selection-only.
- Label placement order is independent of hover and selection styling, so tags do not move when input modality changes. Pointer activation captures the visible target at press time and activates it only after a no-drag release, preserving drag-return and pinch suppression while fixing mouse-hover-to-touch transitions.
- Headed Chromium verified zero label-to-label, label-to-own-package, label-to-other-interactive-package, and canvas-edge overlaps; desktop and mobile tag drill-down; mixed mouse/touch VBUS1 identity; and zero runtime errors. The strict full interaction matrix, 127 Node tests, 50 Python tests, source validation, syntax checks, diff checks, and HTTP checks passed.

Technician-facing component access status on 2026-07-16:

- The evidence heading no longer exposes the source-data phrase `代理图可见区域` or uses one yellow treatment for every visibility state. A single tested state adapter translates source visibility and active side into `需拆屏蔽罩`, `可直接观察`, or `位于第X面`.
- Yellow is reserved for the physical shield-removal caution, green identifies direct location access on the active side, and blue-gray identifies a side-location fact. Each state includes a technician-facing title and accessible description without changing the source `proxy_visibility` value.
- Selection and side switching share the same renderer path, removing duplicate copy rules and preventing stale heading status after manual side changes or repair-flow navigation.
- Headed Chromium verified all three states, distinct computed colors, complete text, action-button separation, zero overflow at desktop/390 px/320 px, and zero runtime errors. The strict full interaction matrix, 131 Node tests, 50 Python tests, source validation, syntax checks, diff checks, and HTTP checks passed.

Reusable J6101 component visual refinement on 2026-07-31:

- J6101 now resolves through a reusable, immutable `ComponentVisualSpec` catalog rather than connector-specific renderer geometry. The validator fails closed on malformed identity, metadata, stage order, structure ratios, detail-level parts, material tokens, and prohibited engineering claims.
- The procedural builder compiles four deterministic stages: blockout, structure, material, and polish. Its repair-facing hierarchy separates the base, surrounding frame, recessed opening, generic contact region, and isolated-view retention/edge treatment.
- Board and isolated detail levels use the same reviewed entity identity and source footprint. Entering `单体查看` transactionally replaces the board-level group, preserves transforms and selection maps, and restores board detail through the existing return and Escape paths.
- Replacement failures before commit retain the previous visual. Cleanup failures after commit keep the new visual authoritative, attempt every unique owned resource, detach stale objects, and publish a stable `componentVisualCleanup` browser diagnostic instead of reviving a partially disposed object.
- Invalid or unavailable specifications retain the existing generic connector fallback. U2001 and other legacy inspected packages continue to use their established rendering path and clear reusable-spec metadata.
- The model does not claim engineering CAD accuracy, millimeter dimensions, exact pin count or pitch, solder feet, vendor latch geometry, spring geometry, or connector internals. J6101 remains a source-bounded repair-recognition representation.
- Automated verification passed with 319 Node tests and 27 source-bound Python tests. The Python set covered cross-source registration, KM4 board compilation, and the actual static application route.
- Browser verification used `http://127.0.0.1:8899/assets/cross-source-registration/?board=km4-f151` at 1600x900 and 390x844. Desktop mouse, wheel, keyboard, reset, return, Escape, and U2001 legacy regression passed; native mobile one-finger rotation, two-finger pinch, reset, and touch return passed.
- Desktop document overflow was 0 px on both axes; mobile horizontal overflow was 0 px. Clean desktop and mobile sessions produced zero page errors and zero console errors. WebGL canvas entropy was 5.127 on desktop and 4.341 on mobile with broad channel ranges, confirming nonblank rendered content.
- Browser evidence is stored under the ignored `output/playwright/j6101-component-visual-refinement/` directory, including board, isolated, rotated, restored, desktop, mobile, and `qa-summary.md` records.
