# XK67J No-Display Repair Loop Design

## Objective

Add the first source-controlled technician repair path for the shared XK67J
board platform. Selecting `无显示` must focus the same physical location in the
photo, point map, and 2.5D model, expose the matching schematic evidence, let
the technician record a location-check result, and stop at the exact point
where the current sources no longer support an electrical test or repair
action.

## Selected Evidence

The path is limited to KM4n physical-board revision `XK67J_MAIN V1.0` and the
accepted shared-platform engineering reference `XK67J_MAIN_PCB V1.0B`.

- Feishu cases `CASE-0022` and `CASE-0025` both record symptom `无显示`, finding
  `显示IC坏`, and board state `维修后已修复`.
- Both cases link photo record `recvqMSU2K5nvW`. Its annotated image has SHA-256
  `28a193f9bbd0750240fb20477f5ec0497de7f279868b408eab7c872dcd0273d6`.
- The annotation center inverse-projects to normalized board coordinate near
  `(0.508, 0.816)` and the nearest exact Placement designator is `U2411`.
- SCH page 9 identifies `U2411` as `OCP2130WPAD-G` in the `LCM BIAS` circuit and
  includes `AVDD_LCM` and `AVEE_LCM`.

These facts support prioritised navigation to U2411. They do not prove that
U2411 is the cause of every no-display fault.

## Source Boundaries

The current sources do not contain an XK67J-approved probe location, numeric
reference, pass/fail tolerance, branch decision, rework method, replacement
instruction, or post-repair acceptance procedure. Generic display guidance and
other-model manuals are not promoted into this model-specific path.

Consequently the first path has one executable check: verify that the board and
the displayed U2411 location correspond to the unit being inspected. The
technician records either `位置一致` or `无法确认`. Both outcomes are terminal
source boundaries:

- `位置一致`: show the exact evidence and state that an XK67J electrical test
  standard is required before continuing.
- `无法确认`: stop and require board/revision/source verification.

Neither outcome is a diagnosis, defect label, repair action, or claim of repair
causality.

## Data Contract

The generated cross-source dataset gains:

- entity `XK67J-MAIN-U2411`, with Placement location, SCH page 9, part identity,
  and case-evidence links;
- one repair flow `xk67j-no-display-u2411-location-check`;
- explicit source records for the two privacy-reduced case IDs and one exact
  photo hash;
- `repair_coverage.status = source_boundary_only` so the UI distinguishes this
  path from a fully executable repair procedure.

Case records intentionally exclude IMEI, technician identity, country, and
unneeded Base fields. Source record IDs remain only as traceability keys.

## Workbench Behaviour

Selecting `无显示` starts the path and selects `U2411`. The workbench switches
to board side 2 and keeps U2411 focused while the technician changes among
physical photo, point map, and 2.5D views. The source-annotated photo B is used
as the initial photo for this flow because its exact hash is part of the path
evidence. Existing pan, zoom, side switching, and component inspection remain
available.

The flow panel labels the task as a source location check, lists the two case
records and SCH page 9, and avoids action-oriented language. Closing a boundary
stores the result only in the in-memory flow state used by the current demo;
server persistence is outside this increment.

## Validation

- Python tests prove the privacy-reduced evidence contract, U2411 identity,
  exact hash, source boundary, and shared registration validation.
- Node tests prove boundary-only flow progression and exact photo selection.
- Static/UI tests prove that flow activation synchronizes U2411 across all
  three views without exposing unsupported repair controls.
- Desktop and 390 px browser QA covers fault selection, photo B activation,
  view switching, location result recording, boundary closure, pan/zoom, and
  readable source-boundary copy.

