# Component Interaction Affordance Design

## Goal

Make every reviewed interactive component discoverable before selection and replace the oversized red selection treatment with repair-tool-grade visual states that do not cover package geometry.

## Visual Semantics

- Interactive idle: restrained amber corner brackets and a compact designator tag remain visible at full-board scale.
- Hover: brackets brighten and a small pointer-adjacent tooltip shows designator and component function.
- Selected: fitted corner brackets become stronger, the package receives a subtle amber emissive lift, and its compact tag remains emphasized.
- Fault or warning: coral red is reserved for future diagnosis results and is not used for ordinary selection.

## Behavior

- Only reviewed entities registered in `data.entities` receive interactive affordances; compiled context geometry does not pretend to be actionable.
- Persistent markers survive pan, rotate, zoom, repair focus, side changes, and resize because they live in board coordinates.
- Pointer hover never changes selection or repair evidence.
- Pointer drag clears hover feedback and keeps the existing pan/rotate ownership rules.
- Mobile relies on persistent corner brackets and tags; no hover is required to discover or select an entity.
- Single-component inspection hides board-level affordances while the isolated package is active and restores them on exit.

## Layout

- Corner brackets sit just outside the package footprint and use short legs instead of a surrounding circle or filled overlay.
- Designator tags use a compact dark field, white type, and a narrow amber status edge.
- Tags remain materially smaller than the current white/red label and must not scale into large callouts at repair zoom.
- Overlapping tags may reduce opacity when idle, but selected and hovered tags retain full contrast.

## Verification

- Pure tests cover corner geometry and idle/hover/selected presentation rules.
- Desktop browser QA covers all seven reviewed affordances, hover tooltip, click selection, pan-versus-hover, focused zoom, and absence of the old red ring.
- Mobile QA confirms all reviewed components remain discoverable without hover and that controls and tags do not cause horizontal overflow.
- Existing navigation, inspection, side switching, and rapid-transition regressions remain green.

## Scope Boundary

This change identifies reviewed interactive entities only. It does not make all 820 compiled designators clickable and does not infer new component semantics from geometry.
