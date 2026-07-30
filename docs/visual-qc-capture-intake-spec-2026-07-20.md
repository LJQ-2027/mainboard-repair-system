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

The controlled server accepts JPEG, PNG, and WebP up to its configured 20 MB limit. Owner-side source staging additionally accepts HEIC through the pinned administration toolchain; it preserves the exact HEIC bytes and supplies a manifest-bound JPEG working image to the existing server and OpenCV paths. The hard 64 px minimum only rejects invalid thumbnails and is not the target quality.

## Batch Manifest

The normal path starts with `scripts/stage_visual_qc_source_package.py`. It preserves the incoming bytes in a repository-external content-addressed library and creates `VISUAL-QC-INTAKE-BATCH-V1` from the archived working objects. JPEG, PNG, and WebP-only packages remain `VISUAL-QC-SOURCE-PACKAGE-V1`; a package containing HEIC uses `VISUAL-QC-SOURCE-PACKAGE-V2` and binds each exact HEIC original to its deterministic JPEG working derivative. `scripts/create_visual_qc_intake_batch.py` remains the lower-level command for originals that are already in controlled storage. `knowledge-base/visual-qc-intake-batch.example.json` is a contract example, not the normal authoring path. Each intake entry contains:

- `entry_id` and `file_path`;
- `board_key` and `side_id` from the current executable board catalog;
- `capture_stage`;
- `capture_session_id` and `capture_setup_id`;
- all three true capture-checklist booleans;
- optional expected SHA-256.

The validator rejects the complete batch before upload when it finds an unsafe id, duplicate entry/path/session-side, unknown board/side, mixed session identity, incomplete checklist, unsupported signature, extension/MIME mismatch, decode failure, dimensions outside bounds, or hash mismatch. It never infers model or side from image content.

The staging command requires every board side to be assigned explicitly as `side_id=path` and leaves every incoming file unchanged. JPEG, PNG, and WebP retain the V1 exact-byte object contract. A package containing HEIC uses `VISUAL-QC-SOURCE-PACKAGE-V2`: the exact HEIC source is stored under `objects/source-originals/`, while a deterministic oriented RGB JPEG is stored under the existing `objects/originals/` working-image layout. Each V2 entry binds both SHA-256 values, the pinned `pillow-heif`/libheif/Pillow versions, primary-image selection, EXIF-orientation handling, ICC policy, and fixed JPEG parameters. Downstream intake and registration consume only the working image, but the source-package manifest hash binds the unchanged original.

The command computes `expected_sha256` from the working image and validates the completed source package and intake manifest before publishing the immutable package directory. The library root must be supplied explicitly and resolve outside the Git repository. Controlled child paths containing symbolic links or Windows reparse points are rejected. Package publication is serialized by a local file lock; `.complete` is written only after both manifests are durable, so interrupted or partial packages cannot be consumed. Project assets, point maps, and manual proxy images are rejected so they cannot become `physical_capture`; known engineering and reviewed manual-proxy SHA-256 fingerprints remain rejected after exact copy or rename. A batch may contain one side when photos arrive incrementally.

The owner-side decoder dependencies are pinned separately in `requirements-visual-qc-admin.txt`; production workers do not need HEIC decoding. `VISUAL-QC-SOURCE-AUDIT-V2` audits working objects and HEIC source originals separately, while preserving aggregate object and reference counts. A valid derivative still does not confirm board identity, side, capture stage, defect, Golden status, repair outcome, or training eligibility.

The canonical `knowledge-base/visual-qc-proxy-inventory-v1.json` stores the reviewed path and SHA-256 for every configured point map and approved manual proxy. Missing files, changed bytes, unregistered configured proxies, malformed hashes, and path mismatches fail closed. The source package records `proxy_inventory_sha256`, but validation does not trust that historical snapshot alone. Package validation and intake import re-read the current canonical proxy inventory, so an older package is immediately revoked if one of its object hashes is later classified as proxy material. The fingerprint gate is exact-byte protection, not image forensics. Recompression, cropping, editing, or screenshots change the SHA-256 and therefore still require Codex to verify that Milo supplied a physical photo. Every newly approved proxy asset must be deliberately added to the canonical inventory with its reviewed hash. Server evidence-role, Golden, and training gates remain authoritative.

The source library is an integrity-preserving operator workflow, not a sandbox against a hostile local administrator. It rejects existing reparse/symlink paths and rechecks newly created object/package paths immediately before publication; the library root must also be protected by normal Windows account and filesystem permissions.

## Repair Case Source

Milo-supplied repair cases are preserved as an independent repair-case fact source. Historical `VISUAL-QC-REPAIR-CASE-SOURCE-V1` manifests remain immutable and readable. `VISUAL-QC-REPAIR-CASE-SOURCE-V2` is used when exact board identity is supported but device-model identity needs an explicit state such as `unresolved_alias`. Neither version extends `VISUAL-QC-CASE-V1/V2`, and its presence in the controlled library does not create a server case, annotation, QC result, Golden Sample, COCO record, training-manifest row, or governed dataset member.

V2 permits `unresolved_alias` only with an exact catalog `board_key` and `board_id` plus complete identity evidence. Reported models, catalog models, and resolved models stay separate. An unresolved or conflicting identity cannot be forced into a catalog model. Identity progresses monotonically only through a complete revision with appended evidence. Only `conflict -> confirmed_alias` requires a new correction record. A resolved identity is immutable.

The owner-only sequence is:

```text
stage source package(s)
-> audit source library
-> stage repair case revision
-> validate append-only case chain
-> later run physical acceptance on selected photo package
```

Milo supplies the original material and known context. Codex assigns stable ids and package roles, transcribes only supported facts, and reports missing fields. The command never infers model, board, side, diagnosis, action, or outcome from the image. Case `completeness` reports context availability only; it is not an accuracy score, review decision, Golden approval, or training-eligibility state.

Create a strict UTF-8 case-record JSON and bind it to one or more already validated source packages:

```powershell
.\.venv\Scripts\python.exe scripts\stage_visual_qc_repair_case.py `
  --library-root D:\Visual-QC-Controlled-Source `
  --repair-case-id case-km4-0001 `
  --board-key km4-f151 `
  --case-record C:\incoming\case-km4-0001.json `
  --source-package "before_repair=D:\Visual-QC-Controlled-Source\packages\km4-before\source-package.json" `
  --source-package "after_repair=D:\Visual-QC-Controlled-Source\packages\km4-after\source-package.json" `
  --supporting-file "repair-note=C:\incoming\repair-note.pdf"
```

V3 `supporting_only` accepts repair-case supporting evidence without a source-package link:

```powershell
.\.venv\Scripts\python.exe scripts\stage_visual_qc_repair_case.py `
  --library-root G:\Programming\_Data\Visual-QC-Controlled-Source\library `
  --repair-case-id case-003-bg6-f069 `
  --board-key bg6h-f069 `
  --case-record <case-record-v3.json> `
  --supporting-file repair-in-progress-photo=<IMG_5604.HEIC>
```

Absence of `--source-package` is valid only for V3 `supporting_only`. The `source_capture_stage` value preserves the source wording; it is not a Visual-QC stage. This path creates no derivative, registration, Golden, QC, annotation, training, API, server, or production record. V1/V2 package-linked behavior is unchanged. Milo remains the sole real-material source, and Codex remains the sole data operator inside the owner-operated boundary; this is not technician upload.

An exact replay returns `existing`. A later revision must provide the complete cumulative case record and package list plus `--previous-manifest`; the publisher increments the revision, binds the exact prior manifest SHA-256, and rejects forks, gaps, historical mutation, unsafe paths, and conflicting replays. Supporting PDF, UTF-8 TXT/CSV, XLS/XLSX, PNG, and JPEG evidence is content-addressed and integrity checked. Corrections reference a historical fact and a current replacement instead of deleting either record.

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

The first governed physical milestone was completed with F069 V1.2 CASE005
after-repair photos on 2026-07-24:

- exact HEIC originals and deterministic JPEG derivatives were retained in a
  `VISUAL-QC-SOURCE-PACKAGE-V2`;
- the source-library audit was healthy and the qualified handoff transferred
  both board sides to an isolated local server;
- both images were usable without retake;
- automatic point-map feature matching safely returned
  `manual_registration_required`;
- both sides completed reviewed manual four-point registration with an
  independent check point and reached `ready_for_human_qc`.
- the independent repair case was published as `case-005-bg6-f069` revision
  1, with `board_key=bg6h-f069`, `board_id=BOARD-F069-MAIN-V1.2`, and
  `model_identity_resolved=false`; its manifest SHA-256 is
  `85c8c64cb97cf1ea1e567e4d1f7fc62ec00ebf02719939c74a5e0faf46298177`,
  using `VISUAL-QC-REPAIR-CASE-SOURCE-V2`, `unresolved_alias`, and
  `symptom_linked`;
- the source-reported `TECNO/BG6` and catalog `BG6H/BG6h` identities remain
  deliberately unresolved rather than forcibly normalized.

See `docs/visual-qc-f069-first-physical-acceptance-2026-07-24.md` for exact
case ids, board-side assignments, errors, and evidence boundaries.

The V2 repair-case publication is not visual diagnosis evidence, not confirmed defect evidence, not Golden Sample evidence, not training label evidence, not repair causality evidence, and not field accuracy evidence. The
remaining real-data gates are human QC conclusions tied through a separately
approved evidence link, annotation-to-footprint verification, a Milo-confirmed
normal Golden Sample, and production deployment of the qualified-handoff
contract. Production remains `f278061`; this local case publication did not
modify production.
Synthetic transforms and 21 Service Manual images remain proxy software
evidence only; they must not be described as physical accuracy or used to
train a production defect model.

## 2026-07-29 Current Supplement: Repair Evidence Links

The controlled library is the authoritative source of truth for each immutable
repair-evidence-link revision. The server stores only a read-only projection
that can be rebuilt by validating and replaying that exact library revision.
The contract enforces one photo per binding; one link revision may contain
separate bindings for separate photos.

Repair-evidence detail is exposed only through the administrator/reviewer
detail API. Technicians have no repair-evidence detail route. A binding records
an evidence association only and carries no annotation, QC, Golden Sample,
training-label, repair-causality, or repair-action authority.

CASE005 keeps the source-reported U4000 association as `possibly_related` and
`not_assessed`. It has no visual defect conclusion and does not establish that
U4000 caused the reported symptom or that any repair action is required.

The owner-operated chain is:

```text
repair case revision
-> export linkable physical evidence
-> stage repair evidence link revision
-> validate/replay
-> sync read-only projection
-> inspect in internal workbench
```

This implementation and the local CASE005 projection are local evidence only.
Production remains unchanged at `f278061`; no production deployment, database,
or route was changed by this work.
