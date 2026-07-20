# Visual QC Capture And Intake Specification

## Purpose

This specification gives global repair sites one repeatable way to collect board images that can be registered, compared, audited, and later used as reviewed training evidence. It does not require the technician to identify the board model: model, board version, and board side are inherited from the repair session.

## Required Capture Set

For a new board-side baseline:

1. Select the known model, board version, and board side in the repair workbench.
2. Remove the board from the device when the repair procedure permits it.
3. Capture the complete first side.
4. Turn the board over without changing the camera setup and capture the complete second side.
5. Keep both sides in one `capture_session_id` and record the stable `capture_setup_id`.
6. Confirm complete-board framing, focus/lens cleanliness, and even unobstructed lighting for each image.
7. Upload each side as `golden_reference`.
8. A reviewer checks image quality, registration, and normal-board status before activation.

For a repair case:

1. Capture `before_repair` before component action.
2. Keep the same board side and capture setup.
3. Capture `after_repair` after the action and cleaning.
4. Confirm or reject every retained difference candidate.
5. Continue the source-backed electrical and functional verification path.

## Physical Setup

- Use a stable phone stand or fixed camera where available.
- Use the main rear camera at its native resolution; avoid digital zoom and portrait filters.
- Prefer a source image whose short edge is at least 2,000 pixels.
- Keep the complete board outline visible with a small margin on every side.
- Let the board occupy most of the frame without clipping connectors or corners.
- Use a plain, matte background that contrasts with the PCB.
- Use diffuse light from more than one direction when possible.
- Move direct reflections away from shields, connectors, and solder joints.
- Keep the camera approximately perpendicular to the board.
- Remove hands, tools, loose screws, labels, and unrelated parts from the board area.
- Clean only according to the approved repair process; do not alter evidence merely to improve the photograph.

The service accepts JPEG, PNG, and WebP up to the configured 20 MB pilot limit. The hard minimum dimension protects against thumbnails; it is not the recommended field capture quality.

## Capture Setup Identity

`capture_setup_id` identifies a repeatable optical arrangement, not a technician or country. Use a stable site-defined id such as:

`NBO-RC01-BENCH-A-PHONE01-1X-DIFFUSE`

The site record behind this id should retain:

- site and bench;
- phone or camera model;
- selected rear lens and zoom mode;
- stand or jig;
- background;
- light arrangement;
- approximate camera distance;
- image orientation policy;
- date the setup was checked.

Changing the camera, lens, stand, background, or light arrangement creates a new capture setup id. Golden Samples from different setups must not be silently mixed.

## Capture Session Identity

`capture_session_id` identifies one physical board during one capture stage. The server binds it to:

- actor;
- board key and board id;
- capture stage;
- evidence role;
- capture setup id.

The first accepted side establishes that identity. Later sides must match it. The binding is checked inside the database write transaction, so concurrent uploads cannot reuse the same session for a different board, stage, evidence role, or setup.

`pair_in_progress` means at least one required side is still missing. `pair_complete` means all source-declared sides are present. Neither status confirms registration, image quality, a normal board, or a defect.

Each physical image carries three boolean capture checks:

- complete board is visible and the selected side is correct;
- lens is clean and the board is in focus;
- lighting is even and the board is unobstructed.

The browser blocks upload until all three are confirmed. The server derives the checklist status from the booleans instead of trusting a submitted status string. Proxy evidence is always `not_applicable`.

## Intake States

The browser creates a local draft before network transfer:

`draft -> hashing -> uploading -> accepted -> queued -> running -> succeeded`

Recoverable states:

- `upload_failed`: retain the local blob and retry with the same idempotency key.
- `failed`: preserve the server job and expose explicit retry.
- `manual_required`: keep the case and open reviewed four-point registration.
- `retake`: retain the rejected evidence record but request a better photograph.

The server becomes authoritative only after returning HTTP `202` with the case, image, and job ids. A retry must reuse the same `Idempotency-Key` and SHA-256.

## Evidence Roles

- `physical_capture`: a real photographed board.
- `reviewed_golden_reference`: a physical capture approved as normal.
- `synthetic_proxy`: generated from an engineering reference.
- `service_manual_proxy`: an installed-board or structural image extracted from a reviewed manual.

Only a reviewed `physical_capture` may become a Golden Sample or field-accuracy sample. Proxy evidence remains useful for software validation and must retain its proxy role in exports.

## Reviewer Gate

A Golden Sample requires:

- known board and side identity;
- immutable SHA-256;
- acceptable image-quality status;
- reviewed automatic or manual registration;
- confirmed normal-board status;
- reviewer identity and timestamp;
- capture setup id;
- confirmed physical-capture checklist;
- active version.

Replacing a Golden Sample creates a new version. Historical cases continue to reference the version used when their difference job ran.

## Global Network Behavior

- Generate the preview and SHA-256 locally before upload.
- Keep the original browser draft until server acceptance.
- Show byte progress and a retry action.
- Do not restart the repair case when upload fails.
- Poll the persisted job rather than holding one long request.
- Use thumbnails for list views and fetch originals or heatmaps only when opened.
- Preserve manual registration and repair guidance when automatic processing is unavailable.

This is recoverable weak-network operation, not a promise that the complete repair system works offline.
