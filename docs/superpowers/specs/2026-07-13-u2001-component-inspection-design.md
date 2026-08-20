# U2001 Component Inspection Vertical Slice

## Goal

Turn U2001 into the first repair-grade component inspection sample. A technician can select it on the KM4 board, isolate it without losing board context, rotate and zoom it independently, and read source-backed fault and test guidance beside the model.

## Scope

- U2001 is the only component enabled for the first inspection sample.
- The existing board, side switching, repair focus, shields, evidence links, and normalized identities remain the source of truth.
- The package is visually refined with a layered PMIC/BGA profile, restrained beveling, substrate edge, and pin-one cue.
- The visual package remains category-based. It does not claim measured dimensions, exact ball count, or an engineering CAD package.
- No Blender or GLB dependency is introduced in this checkpoint. The interaction contract must be stable before reusable GLB assets are authored.

## Interaction

1. Selecting U2001 keeps the current contextual repair focus.
2. A compact `单体查看` command becomes available in the evidence heading.
3. Entering inspection keeps U2001 at its registered board coordinate, lifts and enlarges it, and reduces the board and unrelated structures to a low-opacity context layer.
4. Dragging rotates U2001 around its own center while the board remains still. Wheel input zooms the inspection camera.
5. Shields and module overlays are suppressed during inspection so they cannot occlude the component.
6. `返回主板` restores all transforms, opacity, shield/module presentation, camera framing, and selected identity.
7. Selecting another entity or switching side exits inspection before the existing navigation behavior continues.

## Information

The evidence panel adds three explicit source-backed blocks for U2001:

- `常见故障`: values already present in `repair_links[].faults`.
- `检测方法`: the existing `repair_links[].instruction` text.
- `模型边界`: a fixed statement that appearance and height are repair-visual approximations, not measured package dimensions or pin geometry.

No voltage, resistance, pin, or replacement instruction is invented when the supplied sources do not contain it.

## Architecture

- `component-inspection-state.js` owns DOM-free capability, ghosting, transform, and exit-state decisions.
- `BoardRenderer` owns the U2001 package profile, material snapshots, inspection animation, independent pointer rotation, and camera changes.
- `app.js` owns selected entity, inspection UI state, source-backed copy, and coordination with side/view changes.
- The data record marks U2001 with an explicit `inspection_profile`; capability is not inferred from its designator in controller code.

## Verification

- Node tests cover capability, state transitions, ghosting, and bounded visual transform.
- Existing Node and Python suites remain green.
- Headed Chromium at 1600x900 and 390x844 covers enter, ghosting, independent drag, wheel zoom, return, entity-switch exit, side-switch exit, keyboard focus, text readability, canvas pixels, overflow, and runtime errors.

## Remaining Boundary

This checkpoint proves one component end to end. It does not batch-enable all components, author a GLB library, infer electrical connectivity, or replace the need for physical-board photographs.
