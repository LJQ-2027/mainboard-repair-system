# Visual QC Owner-Managed Capture And Intake Specification

## Current Ownership

Milo is the only source of real visual photos. Codex is the data administrator that validates, imports, registers, labels, and packages the evidence. Overseas technicians do not take part in photo upload and do not use the internal visual data workbench.

The server role string `reviewer` is retained only as a compatibility identifier for data-administrator permissions. It is not a second-person review or approval workflow.

## Required Photo Package

For each physical board supplied to Codex:

1. State the known model, board version, and board side for every file.
2. Prefer a bare board with the full outline visible.
3. Capture both source-declared sides without changing the optical setup.
4. Use one `capture_session_id` for the same board/stage/setup.
5. Select `golden_reference`, `before_repair`, or `after_repair` explicitly.
6. Confirm full-board framing, focus/lens cleanliness, and even unobstructed lighting.
7. Keep the originals unchanged; do not pre-crop, annotate, or recompress them for intake.

Recommended capture conditions:

- stable stand or fixed camera;
- main rear camera at native resolution, without digital zoom or portrait filters;
- short edge at least 2,000 pixels where practical;
- matte contrasting background;
- diffuse lighting from multiple directions;
- camera approximately perpendicular to the board;
- no hands, tools, labels, loose parts, or unrelated objects over the board.

The pilot accepts JPEG, PNG, and WebP up to its configured 20 MB limit. The hard 64 px minimum only rejects invalid thumbnails and is not the target quality.

## Batch Manifest

Create `VISUAL-QC-INTAKE-BATCH-V1` with `scripts/create_visual_qc_intake_batch.py`. `knowledge-base/visual-qc-intake-batch.example.json` remains a contract example, not the normal authoring path. Each entry contains:

- `entry_id` and `file_path`;
- `board_key` and `side_id` from the five-board catalog;
- `capture_stage`;
- `capture_session_id` and `capture_setup_id`;
- all three true capture-checklist booleans;
- optional expected SHA-256.

The validator rejects the complete batch before upload when it finds an unsafe id, duplicate entry/path/session-side, unknown board/side, mixed session identity, incomplete checklist, unsupported signature, extension/MIME mismatch, decode failure, dimensions outside bounds, or hash mismatch. It never infers model or side from image content.

The builder requires every board side to be assigned explicitly as `side_id=path`, leaves the source file unchanged, computes `expected_sha256` from the current bytes, and validates the completed manifest before publishing it. Physical source photos must be stored outside the Git repository; project assets, point maps, and manual proxy images are rejected so they cannot become `physical_capture`. Known engineering and reviewed manual-proxy SHA-256 fingerprints remain rejected after copy or rename. A batch may contain one side when photos arrive incrementally. Existing output is protected unless `--force` is supplied, and even forced output can never replace a source image.

## Capture Identity

`capture_setup_id` names one repeatable optical arrangement, including camera/lens, stand, background, light arrangement, orientation, and approximate distance. Changing that arrangement creates a new setup id.

`capture_session_id` names one physical board during one capture stage. All entries in that session must retain one board identity and setup; each board side may appear at most once. `pair_complete` means all source-declared sides are present, not that quality, registration, normality, or defects have been confirmed.

## Intake Procedure

Create the manifest after Codex has checked the stated board/side, focus and lens cleanliness, and lighting/occlusion conditions:

```powershell
.\.venv\Scripts\python.exe scripts\create_visual_qc_intake_batch.py `
  --batch-id km4-physical-001 `
  --board-key km4-f151 `
  --capture-session-id km4-unit-001 `
  --capture-stage golden_reference `
  --capture-setup-id standard-bench `
  --image "main_page_1=C:\controlled-source\km4-front.jpg" `
  --image "main_page_2=C:\controlled-source\km4-back.jpg" `
  --confirm-capture-checklist `
  --output C:\controlled-source\km4-physical-001.intake.json
```

`--confirm-capture-checklist` records an explicit completed intake check; it is not an automatic quality score. The command does not infer which image is front/back and does not require both sides in one batch. Use the source-declared `side_id` values from the board catalog.

Run validation without network writes:

```powershell
.\.venv\Scripts\python.exe scripts\import_visual_qc_batch.py C:\controlled-source\km4-physical-001.intake.json `
  --receipt C:\controlled-source\km4-physical-001.receipt.json `
  --dry-run
```

Then import through the controlled HTTPS API:

```powershell
.\.venv\Scripts\python.exe scripts\import_visual_qc_batch.py C:\controlled-source\km4-physical-001.intake.json `
  --receipt C:\controlled-source\km4-physical-001.receipt.json `
  --api-base https://cccsat.top/mb-repair-beta/api/v1/visual-qc `
  --credential-file C:\secure\visual-qc-credential.json `
  --actor-id OWNER_ID `
  --wait
```

The importer uploads sequentially, uses a deterministic idempotency key, writes the receipt atomically after every transition, stops on the first transfer failure by default, and resumes only rows without matching server ids. `--continue-on-error` is an explicit batch-operations choice. HTTP is permitted only for localhost with `--allow-http-localhost`.

The receipt stores file evidence, transfer state, server case/job ids, and typed errors. It never stores credentials or authorization headers. If source bytes change, the new SHA-256 invalidates previous server ids.

## Data-Administrator Procedure

1. Open the server case catalog in the internal workbench.
2. Filter by board, side, capture stage, or processing state.
3. Open the case; the browser verifies original SHA-256 and decoded dimensions.
4. Inspect image quality and automatic registration.
5. Accept the automatic transform or complete manual four-point registration plus an independent check point.
6. Mark a confirmed-normal physical reference as a versioned Golden when applicable.
7. Confirm/reject difference candidates or add human visible-defect annotations.
8. Complete final QC evidence and inspect the dataset gate.
9. Export the deterministic manifest/COCO/bundle only after all server gates pass.

There is no organizational approval queue. “Reviewed” fields in data contracts mean that Codex explicitly confirmed technical evidence rather than accepting an automatic candidate silently.

## First Real Batch Acceptance

The first physical milestone is one known KM4/F151 bare-board front/back set. Codex must:

- complete dry-run and import with a retained receipt;
- verify server case/original recovery;
- record quality metrics and any retake reason;
- validate automatic or manual registration on both sides;
- verify annotation projection and visible component-footprint association;
- create a Golden only if Milo identifies the board as known-normal;
- confirm the dataset audit distinguishes eligible physical evidence from the existing manual proxy.

Until this is complete, synthetic transforms and 21 Service Manual images remain proxy software evidence only. They must not be described as physical accuracy or used to train a production defect model.
