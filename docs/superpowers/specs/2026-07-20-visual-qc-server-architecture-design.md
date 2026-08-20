# Visual QC Server Architecture Design

## Status

Approved server-led architecture, updated by Milo on 2026-07-21 for the owner-managed evidence path. This document is the canonical architecture for photo intake, registration, Golden Sample management, visible-defect annotation, and governed training export.

The previous proposal in which overseas technicians captured or uploaded visual photos is superseded. Milo is the only source of real visual photos. Codex operates the internal data-administrator intake and evidence-building workflow. Overseas technicians do not upload photos and do not enter `assets/visual-qc-workbench/`.

The backend wire value `reviewer` remains temporarily as the compatibility identifier for data-administrator capability. It does not represent a second-person approval layer.

## Product Fit

Visual QC remains one subsystem of the overseas mainboard repair platform, not a separate technician entry. Its evidence is later consumed by the same repair flow:

`known model and board -> known fault or initial inspection -> model highlights likely modules -> technician follows source-backed tests -> technician records result`

The internal visual data path is separate:

`Milo supplies known-board photos -> Codex validates and batch-imports -> server quality/registration -> Codex corrects registration and labels -> Golden/defect evidence -> governed training export`

Visual processing may locate visible anomaly candidates. Point maps, schematics, repair guides, the 2.5D model, and reviewed SOPs remain the source of component meaning and permitted repair checks. A model candidate never authorizes a repair action.

## Deployment Decision

The production path is a server-led Web platform with asynchronous CPU visual processing and manual four-point fallback.

- The existing controlled server hosts the same-origin static workbench and FastAPI QC service.
- Only the data administrator can create or reopen visual cases, manage Golden Samples, or export datasets.
- Technician identities fail closed and receive no visual intake or data-management controls.
- The server owns case identity, image provenance, processing jobs, registration evidence, final QC evidence, Golden versions, audit history, and dataset export.
- IndexedDB is a recoverable local working copy, not the cross-user source of truth.
- OpenCV performs image quality, contour evidence, ORB/AKAZE matching, homography validation, and difference candidate generation.
- Training runs in a separate compute environment after real-data audit; the pilot server does not train deep models.

## Runtime Architecture

### Owner-Managed Intake

Milo is the only source of real visual photos, and Codex is the only data operator. `VISUAL-QC-SOURCE-PACKAGE-V1` and its archived `VISUAL-QC-INTAKE-BATCH-V1` bind every local file to an explicit board, side, capture stage, session, setup, checklist, and immutable SHA-256. The controlled sequence is `stage -> source audit -> physical acceptance -> acceptance-qualified handoff dry-run -> controlled transfer -> server registration review`.

The physical transfer command is:

```powershell
python scripts/handoff_visual_qc_physical_package.py `
  C:\controlled-source\packages\km4-physical-001\source-package.json `
  C:\controlled-acceptance\km4-physical-001\physical-registration-run.json `
  --library-root C:\controlled-source `
  --handoff-root C:\controlled-handoffs\km4-physical-001 `
  --api-base http://127.0.0.1:3020/api/v1/visual-qc `
  --credential-file C:\secure\visual-qc-credential.json `
  --allow-http-localhost `
  --wait
```

Run the same command with `--dry-run` first. This example is for isolated local integration. Production remains `f278061` and must not receive qualified handoff until a separately approved deployment and migration verification completes. The handoff revalidates the source package, archived intake, acceptance report, originals, and overlays, then attaches closed `VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1` to each admitted physical case. The low-level importer is only an internal resumable transport and cannot synthesize provenance. Credentials never enter the source package, evidence, or receipts.

### Internal Visual Data Workbench

The browser workbench provides:

- server case catalog with board, side, stage, state, and bounded pagination;
- verified original-image recovery;
- image quality evidence and automatic registration candidate;
- manual four-point registration and independent check points;
- visible-defect rectangles/polygons and component-footprint suggestions;
- Golden Sample and difference candidate management;
- final human evidence and deterministic dataset exports.
- no direct creation of physical server cases.

The catalog list uses `VISUAL-QC-ADMIN-CASE-LIST-V2`, and detail restoration requires `VISUAL-QC-SERVER-CASE-V3` after the original SHA-256 and decoded dimensions match. Qualified handoff is preserved only as trace metadata; it never marks registration or QC as reviewed. Registration and final QC reviews must link to the current case/job/review ids; stale evidence is rejected instead of being opened as a plausible draft.

### QC API And Worker

FastAPI validates identity, board/side, capture stage, MIME/signature, dimensions, hash, checklist, qualified handoff provenance, idempotency, storage reserve, and capture-session consistency. SQLite persists cases, images, jobs, compact provenance, reviews, Golden versions, artifacts, and audit events. One or two CPU workers process persisted jobs outside request handlers and recover interrupted work after restart.

Automatic registration returns a draft candidate or a structured `manual_required` result. Difference regions remain `model_candidate` until Codex records a human decision.

### Storage

- SQLite for structured state and append-only evidence.
- Dedicated controlled-server object directories for originals and generated artifacts.
- SHA-256 content addressing and integrity checks.
- Explicit disk warning/reserve thresholds and bounded retention.
- Adapter boundaries preserve a later PostgreSQL/object-storage migration path.

## Evidence Contract

Evidence roles are explicit:

- `physical_capture`: a real board photo supplied by Milo;
- `synthetic_proxy`: generated from an engineering point map;
- `service_manual_proxy`: an installed-board or structure image extracted from a reviewed manual.

Proxy images may validate software and structural matching but never count toward physical registration accuracy, Golden Samples, or defect-model training. Only reviewed physical captures can enter those paths.

Training-ready evidence requires immutable image identity, confirmed capture checklist, acceptable quality, reviewed registration, legal normalized coordinates, final human QC, and matching server review linkage. Automatic output remains separate as `model_candidate`.

## Golden Sample Rules

A Golden Sample is scoped to board, side, capture setup, and version. It requires physical evidence, acceptable quality, reviewed registration, explicit normal-board confirmation, data-administrator identity/timestamp, and immutable source hash. Replacing a Golden creates a new version and retires rather than rewrites the previous one.

## Security And Roles

- Nginx authenticates the controlled route and replaces client-supplied actor headers.
- `reviewer` is the compatibility role for the single data-administrator capability.
- `POST /cases`, admin catalog/original routes, Golden management, and dataset exports require that role.
- Different actor ids cannot read one another's cases or originals.
- The QC service binds to loopback and raw engineering archives remain outside the runtime package.
- Physical photos are authorized only for this controlled owner-managed workflow, not for public distribution.

## Current Server Boundary

The server has 4 x86_64 vCPU, 7.3 GB RAM, 4 GB swap, a single system volume, no GPU, and no PostgreSQL/Redis service. This supports the bounded CPU pilot, not deep-model training, high-volume permanent retention, or unrestricted synchronous processing.

## Delivery State

Implemented:

1. High-resolution point-map references and deterministic transforms for all five board platforms.
2. OpenCV contour/feature registration with structured manual fallback.
3. A 21-image Service Manual proxy benchmark that remains explicitly non-physical evidence.
4. Persistent FastAPI jobs, registration/QC evidence, Golden versions, difference candidates, retention and governed datasets.
5. Owner-only source staging, audit, physical acceptance, qualified handoff, and resumable controlled transfer.
6. Actor-scoped server case catalog, original integrity recovery, and data-administrator workbench.
7. Technician upload rejection, browser physical-upload removal, and fail-closed governed training exits.

Still open:

- the first known KM4/F151 bare-board front/back photo set;
- physical-photo registration and component-link acceptance;
- reviewed normal Golden Samples and real defect labels;
- model training after a separate quantity/class-distribution audit;
- production health alert delivery and retention scheduling;
- eventual corporate SSO/OIDC replacement for pilot Basic Auth.

No current result is a claim of real-board defect-recognition accuracy.
