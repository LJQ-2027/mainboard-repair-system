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

The normal path starts with `scripts/stage_visual_qc_source_package.py`. It preserves the incoming bytes in a repository-external content-addressed library, writes `VISUAL-QC-SOURCE-PACKAGE-V1`, and creates `VISUAL-QC-INTAKE-BATCH-V1` from the archived objects. `scripts/create_visual_qc_intake_batch.py` remains the lower-level command for originals that are already in controlled storage. `knowledge-base/visual-qc-intake-batch.example.json` is a contract example, not the normal authoring path. Each intake entry contains:

- `entry_id` and `file_path`;
- `board_key` and `side_id` from the five-board catalog;
- `capture_stage`;
- `capture_session_id` and `capture_setup_id`;
- all three true capture-checklist booleans;
- optional expected SHA-256.

The validator rejects the complete batch before upload when it finds an unsafe id, duplicate entry/path/session-side, unknown board/side, mixed session identity, incomplete checklist, unsupported signature, extension/MIME mismatch, decode failure, dimensions outside bounds, or hash mismatch. It never infers model or side from image content.

The staging command requires every board side to be assigned explicitly as `side_id=path`, leaves the incoming file unchanged, stores exact bytes under a canonical MIME-derived object path, computes `expected_sha256`, and validates the completed source package and intake manifest before publishing the immutable package directory. The library root must be supplied explicitly and resolve outside the Git repository. Controlled child paths containing symbolic links or Windows reparse points are rejected. Package publication is serialized by a local file lock; `.complete` is written only after both manifests are durable, so interrupted or partial packages cannot be consumed. Project assets, point maps, and manual proxy images are rejected so they cannot become `physical_capture`; known engineering and reviewed manual-proxy SHA-256 fingerprints remain rejected after exact copy or rename. A batch may contain one side when photos arrive incrementally.

The canonical `knowledge-base/visual-qc-proxy-inventory-v1.json` stores the reviewed path and SHA-256 for every configured point map and approved manual proxy. Missing files, changed bytes, unregistered configured proxies, malformed hashes, and path mismatches fail closed. The source package records `proxy_inventory_sha256`, but validation does not trust that historical snapshot alone. Package validation and intake import re-read the current canonical proxy inventory, so an older package is immediately revoked if one of its object hashes is later classified as proxy material. The fingerprint gate is exact-byte protection, not image forensics. Recompression, cropping, editing, or screenshots change the SHA-256 and therefore still require Codex to verify that Milo supplied a physical photo. Every newly approved proxy asset must be deliberately added to the canonical inventory with its reviewed hash. Server evidence-role, Golden, and training gates remain authoritative.

The source library is an integrity-preserving operator workflow, not a sandbox against a hostile local administrator. It rejects existing reparse/symlink paths and rechecks newly created object/package paths immediately before publication; the library root must also be protected by normal Windows account and filesystem permissions.

## Capture Identity

`capture_setup_id` names one repeatable optical arrangement, including camera/lens, stand, background, light arrangement, orientation, and approximate distance. Changing that arrangement creates a new setup id.

`capture_session_id` names one physical board during one capture stage. All entries in that session must retain one board identity and setup; each board side may appear at most once. `pair_complete` means all source-declared sides are present, not that quality, registration, normality, or defects have been confirmed.

## Intake Procedure

Preserve the source package after Codex has confirmed that Milo supplied the physical photos and checked the stated board/side, focus and lens cleanliness, and lighting/occlusion conditions:

```powershell
.\.venv\Scripts\python.exe scripts\stage_visual_qc_source_package.py `
  --library-root D:\Visual-QC-Controlled-Source `
  --package-id km4-physical-001-source `
  --batch-id km4-physical-001-batch `
  --board-key km4-f151 `
  --capture-session-id km4-unit-001 `
  --capture-stage golden_reference `
  --capture-setup-id standard-bench `
  --image "main_page_1=C:\incoming\km4-front.jpg" `
  --image "main_page_2=C:\incoming\km4-back.jpg" `
  --confirm-milo-physical-source `
  --confirm-capture-checklist
```

The command returns the committed `source-package.json` and intake-manifest paths. An identical rerun returns `reused`; the same package id with different content or metadata fails as a conflict. `--confirm-milo-physical-source` records operator-confirmed provenance, while `--confirm-capture-checklist` records the completed intake check; neither is an automatic classifier or quality score. The command does not infer which image is front/back and does not require both sides in one batch. Use the source-declared `side_id` values from the board catalog.

Run the deterministic read-only library audit before physical acceptance:

```powershell
.\.venv\Scripts\python.exe scripts\audit_visual_qc_source_library.py `
  --library-root D:\Visual-QC-Controlled-Source
```

`healthy` and orphan-only `attention` return exit code `0`; integrity `issues` return `1`; invalid arguments or a missing/invalid library root return `2`. Orphaned content-addressed objects are informational because a failed no-clobber package publish may leave safe reusable bytes. The audit never deletes, repairs, uploads, or changes evidence.

Generate the physical acceptance report and overlays, then run the acceptance-qualified handoff without network writes:

```powershell
.\.venv\Scripts\python.exe scripts\run_visual_qc_physical_acceptance.py `
  --library-root D:\Visual-QC-Controlled-Source `
  --package D:\Visual-QC-Controlled-Source\packages\km4-physical-001-source\source-package.json `
  --output D:\visual-qc-acceptance\km4-physical-001

.\.venv\Scripts\python.exe scripts\handoff_visual_qc_physical_package.py `
  D:\Visual-QC-Controlled-Source\packages\km4-physical-001-source\source-package.json `
  D:\visual-qc-acceptance\km4-physical-001\physical-registration-run.json `
  --library-root D:\Visual-QC-Controlled-Source `
  --handoff-root D:\visual-qc-handoffs\km4-physical-001 `
  --dry-run
```

Production remains `f278061` and does not yet implement the qualified-handoff contract. Do not target production until a separately approved deployment and migration verification completes. For isolated local integration, transfer the same qualified handoff to the loopback API:

```powershell
.\.venv\Scripts\python.exe scripts\handoff_visual_qc_physical_package.py `
  D:\Visual-QC-Controlled-Source\packages\km4-physical-001-source\source-package.json `
  D:\visual-qc-acceptance\km4-physical-001\physical-registration-run.json `
  --library-root D:\Visual-QC-Controlled-Source `
  --handoff-root D:\visual-qc-handoffs\km4-physical-001 `
  --api-base http://127.0.0.1:3020/api/v1/visual-qc `
  --credential-file C:\secure\visual-qc-credential.json `
  --allow-http-localhost `
  --wait
```

The handoff revalidates the source package, archived intake, acceptance report, source images, and overlays before transfer. It records the three governing document hashes and the acceptance action in closed qualified-handoff provenance. Retake, processing error, hash drift, or damaged overlays block the complete handoff. Automatic candidates and manual-registration-required cases may transfer, but neither is reviewed registration.

The low-level importer uploads sequentially under the handoff command, uses deterministic idempotency keys, writes its receipt atomically after every transition, and resumes only rows without matching server ids. It cannot create qualified provenance by itself, so direct physical import fails closed. The handoff and intake receipts store file evidence, transfer state, server case/job ids, and typed errors; neither stores credentials or authorization headers. HTTP is permitted only for localhost with the explicit development flag.

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
