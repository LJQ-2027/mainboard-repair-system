# XK67J Technician Photo Navigation Design

Date: 2026-08-02

## Objective

Turn the three reviewed XK67J/KM4n physical photographs into a technician-facing
navigation surface synchronized with the existing point map and 2.5D model.
This increment supports board-level location only. It does not create visual
defects, Golden Samples, training labels, industrial accuracy, or repair
causality.

## User Flow

1. Open `xk67j-shared`; the workbench starts on the physical photo for the
   default board side.
2. Switch among `实物图`, `点位图`, and `2.5D 模型` without losing the active
   board side or selected component.
3. Use one board-side segmented control shared by all three views.
4. On side 2, switch between the two reviewed photographs. Side 1 exposes its
   single reviewed photograph without a redundant selector.
5. Click a reviewed marker in either image view or a component in the model.
   Selection identity and evidence update together; the active image viewport
   centers the projected location.
6. Zoom, pan, and reset the physical photo with mouse, touch, or toolbar
   controls. The marker layer moves with the photograph.

## Asset Boundary

Original photographs remain under the controlled source library and never enter
Git. `scripts/build_xk67j_photo_navigation.py` locates source files by exact
SHA-256 beneath an operator-supplied root, verifies each source hash, applies the
reviewed registration orientation, strips metadata, scales the image to a
browser-sized derivative, and writes deterministic WebP assets under
`assets/board-atlas/xk67j/physical/`.

The generated `XK67J-PHOTO-NAVIGATION-V1` manifest records source hash,
derivative hash, dimensions, board side, display label, source-annotation flag,
and reviewed board-to-image matrix. It stores no controlled source path, person,
case narrative, defect, or repair conclusion.

## Runtime Contract

`registration.reference_mode` becomes
`reviewed_physical_photo_navigation`. Its `photo_navigation` object contains the
generated manifest payload. The existing `physical_evidence` remains the audit
source and must agree with every photo source hash and matrix.

`photo-navigation-state.js` owns side filtering, active-photo selection,
matrix validation, technician labels, and empty-side behavior. `image-viewport.js`
owns zoom, pan, reset, and focus for both physical photos and point maps. The app
coordinates these modules but does not hard-code photo paths or matrices.

## Interaction And Layout

- Rename the first tab to `实物图`.
- Move the single board-side segmented control into the shared view header so it
  applies to every view.
- Show photo selectors only when the active side has multiple photos.
- Keep photo controls compact: photo selector, zoom out, zoom in, reset.
- Preserve compact neutral markers and existing amber selection language.
- Show the original annotation boundary in the source note and photo selector;
  do not add red detection overlays.
- Keep all controls usable at 390 px with no horizontal overflow.

## Failure Behavior

- A board without reviewed photo navigation hides the photo tab and starts on
  the point map, preserving current behavior.
- A side without a reviewed photo shows an explicit no-photo state and keeps the
  point map/model available; it never borrows another side's photo.
- Missing or malformed matrices, source-hash mismatches, derivative-hash
  mismatches, or unreviewed registration fail the build or contract tests.
- Image load failure remains local to the photo view and does not disable point
  map, model, or evidence navigation.

## Acceptance

- All three exact source hashes produce tracked metadata-stripped derivatives.
- Side 1 shows one image; side 2 shows two switchable images.
- Component selection stays synchronized across photo, point map, model, and
  evidence.
- Board-side switching updates all three views.
- Photo zoom, pan, reset, and selected-component focus work on desktop and touch.
- Desktop and 390 px browser QA show readable controls, no overlap/overflow, and
  no related runtime errors.
