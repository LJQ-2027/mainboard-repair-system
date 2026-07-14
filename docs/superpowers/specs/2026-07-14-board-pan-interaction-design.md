# Board Pan Interaction Design

## Goal

Allow technicians to reposition a zoomed 2.5D board freely in both axes without weakening component picking, board rotation, inspection isolation, or deterministic reset behavior.

## Interaction Contract

- The model opens in `pan` mode.
- The model toolbar exposes a compact two-state `平移` / `旋转` segmented control with an accessible selected state.
- In `pan` mode, pointer drag moves the camera target in both horizontal and vertical directions. A drag must not select a component.
- In `rotate` mode, pointer drag retains the current constrained board rotation and tilt behavior. A click without meaningful movement may still select a component.
- Mouse-wheel and touchpad scrolling retain bounded zoom in both modes.
- Component inspection keeps direct component rotation; the pan/rotate mode control is disabled while the isolated-component transition or view is active.
- Reset restores full-board camera position, zoom, top-view rotation, and `pan` mode.

## Camera And Bounds

Camera panning is represented as a world-space center independent from board rotation. Screen-space pointer deltas are converted using the orthographic frame dimensions and current zoom, so movement remains consistent at different viewport sizes and zoom levels.

The camera center is clamped to a board-relative boundary. The board may be moved far enough to inspect edge components, but a meaningful portion must remain visible and the model cannot be lost completely off-canvas.

Repair focus and single-component focus replace the current camera center with their source-backed target. A later manual pan starts from that focused center.

## State Boundaries

- Pan/rotate mode is renderer interaction state, not repair-domain data.
- Existing global model transition ownership continues to block canvas input and mode changes during side and inspection animations.
- Side replacement preserves the selected interaction mode unless reset is requested.
- Entering another top-level view does not mutate the mode; returning to the model still performs the existing full-board view reset.

## Verification

- Unit tests cover screen-delta conversion, zoom-aware movement, and pan bounds.
- Headed desktop QA covers horizontal and vertical drag, drag-versus-click separation, rotation mode, wheel zoom, repair focus followed by pan, and reset.
- Mobile QA covers touch drag in pan mode, switching to rotate mode, and no horizontal page overflow.
- Existing rapid entity, rapid side, rotated focus, and component-inspection regression paths must remain green with no console or page errors.

## Scope Boundary

This increment adds camera panning only. It does not add free-flight 3D navigation, inertial movement, multi-touch pinch implementation, or changes to model geometry and repair evidence.
