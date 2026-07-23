# Owner-Managed Visual QC Intake Design

## Status

Historical foundation approved by Milo on 2026-07-21. This specification replaced the earlier assumption that overseas technicians or other colleagues upload visual-QC photos. Its direct generic-import transport and browser-upload details are superseded by `2026-07-23-physical-acceptance-qualified-handoff-design.md` and `2026-07-23-server-qualified-handoff-provenance-design.md`. Milo remains the only source of real visual photos; Codex operates the intake, registration, annotation, Golden Sample, and dataset-building workflow.

## Product Boundary

The visual-QC data path is an internal dataset-production capability, not a technician photo-submission workflow and not a technical-support approval layer.

The authoritative flow is:

`Milo supplies photos -> Codex stages and audits the source package -> physical acceptance -> acceptance-qualified handoff -> server validates and stores originals -> OpenCV produces quality/registration evidence -> Codex reviews or corrects registration and labels -> Codex approves Golden Samples where appropriate -> governed dataset export`

Overseas technicians consume reviewed repair knowledge and future visual capabilities. They do not upload training/reference photos, approve labels, or enter the internal data workbench. A future technician-side inference device or capture policy is a separate product decision and is not implied by this intake system.

## Alternatives Considered

### Browser-Only Multi-File Intake

This would add a multi-file selector and metadata table to the existing workbench. It is visually convenient but weak for large batches, resumability, deterministic receipts, and source-controlled metadata. A browser refresh or metadata mistake would be harder to audit.

### Owner Manifest Plus Resumable Import CLI

This is the selected approach. A local UTF-8 manifest binds each supplied file to a known board, board side, capture stage, physical-board session, and capture setup. A Python CLI performs dry-run validation, hashes the source, uploads sequentially with deterministic idempotency keys, resumes partial batches, and writes a receipt. The Web workbench then lists and opens server cases for visual review.

### Server ZIP Upload

A single server-side ZIP endpoint would simplify transport but would concentrate decompression, path-safety, disk-reserve, partial-failure, and metadata validation risks on the shared pilot server. It is unnecessary while Codex controls intake from the same Windows environment.

## Roles And Authorization

The existing gateway value `reviewer` remains the compatibility role in the first migration, but its product-facing name becomes **data administrator**. Renaming the external role string immediately would create avoidable gateway and credential churn without changing security.

- `reviewer` / data administrator may create cases, upload originals, review registration, finalize human QC, manage Golden Samples, inspect dataset gates, and export datasets.
- `technician` may not create or upload visual-QC cases and does not see intake, Golden, or dataset-management controls.
- The API, not only the browser, enforces the upload restriction.
- No second-person review is introduced. The same data administrator may confirm registration, annotations, final QC, and Golden status; each action remains append-only and traceable.
- Existing historical cases are preserved. The known Service Manual proxy remains proxy evidence and does not become physical data.

This design does not create an employee review queue, cross-site assignment system, or technician upload inbox.

## Intake Contracts

### `VISUAL-QC-INTAKE-BATCH-V1`

The local manifest contains:

- `schema_version`;
- stable `batch_id`;
- `created_at` and an optional non-sensitive note;
- one or more entries with stable `entry_id`;
- repository-external local `file_path`;
- `board_key`, `side_id`, and `capture_stage`;
- `capture_session_id` identifying one physical board instance;
- `capture_setup_id` identifying the optical setup;
- explicit capture checklist booleans;
- optional expected SHA-256 for source handoff verification.

The manifest never stores credentials. It may live under ignored local storage; a sanitized example and JSON Schema are committed.

### `VISUAL-QC-INTAKE-RECEIPT-V1`

The import CLI writes one deterministic receipt beside the local manifest. Each entry records:

- source entry id and computed SHA-256;
- validated MIME type, width, and height;
- deterministic idempotency key;
- server case, image, and processing-job ids after acceptance;
- terminal import state: `validated`, `uploaded`, `processing`, `succeeded`, or `failed`;
- a typed, bounded error when an entry fails.

The receipt contains no password or authorization header. Re-running the same batch resumes incomplete entries and relies on the existing server idempotency contract instead of creating duplicates.

## Validation Rules

Dry-run validation completes before any network write:

1. The manifest and every entry satisfy the versioned schema.
2. `batch_id`, `entry_id`, `capture_session_id`, and setup identifiers use bounded safe characters.
3. Every file resolves to an existing regular file outside the Git contract and is never interpreted as an archive member or URL.
4. File signature, declared MIME, decodable dimensions, and optional expected SHA-256 agree.
5. `board_key` and `side_id` resolve through the committed five-board catalog.
6. Every capture session uses one board, stage, evidence role, and setup.
7. A side occurs at most once per capture session.
8. Physical intake requires all three capture confirmations.
9. Duplicate entry ids, duplicate source paths, and duplicate board/session/side identities fail before upload.

No component identity, defect class, board side, or physical normal/abnormal status is guessed from the photo. Milo's supplied metadata and the approved engineering catalog remain authoritative.

## Upload And Processing Flow

The CLI uses the existing same-origin FastAPI API through authenticated HTTPS:

1. Validate the complete batch locally and write the initial receipt atomically.
2. Hash and inspect each source without re-encoding it.
3. Upload entries sequentially with `X-Actor-Role: reviewer` asserted by the gateway and an idempotency key derived from `batch_id`, `entry_id`, and SHA-256.
4. Store `intake_batch_id` and `intake_entry_id` on each server case for traceability.
5. Poll the existing durable processing job when requested; interruption leaves a resumable receipt.
6. Continue after an individual failure only when `--continue-on-error` is explicitly supplied.
7. Never convert automatic registration output into reviewed registration or a defect conclusion.

The server keeps its current upload-size, free-space, MIME, board-side, capture-session, and SHA-256 gates. A new data-admin role check occurs before reading the request body so unauthorized users cannot consume upload bandwidth.

## Data Administrator Workbench

The existing `assets/visual-qc-workbench/` route remains internal and is renamed on screen from an employee-facing QC tool to **主板视觉数据工作台**.

The first implementation adds a compact server-case catalog rather than a new administration application:

- status counts for processing, manual-registration-required, ready for human QC, completed, and excluded;
- filters for board, side, capture stage, and processing state;
- case rows showing board, source-facing side, stage, image hash suffix, and current state;
- open action that downloads the governed original and reconstructs the existing canvas state;
- refresh and retry for interrupted processing;
- existing registration, annotation, final QC, Golden, audit, and export tools remain in the same route;
- user-facing labels use `数据管理`, not `审核员工具` or `维修员上传`.

The catalog is bounded and paginated at the API. It returns only the authenticated data administrator's cases in the pilot. Cross-owner administration is deliberately absent because Milo is the sole source.

## Server Data Changes

SQLite receives additive, migration-safe fields on `cases`:

- nullable `intake_batch_id`;
- nullable `intake_entry_id`;

The server adds:

- an actor-scoped, data-admin-only paginated case-list query;
- a data-admin-only case-original download route;
- filters with fixed enumerations and bounded page size;
- stable newest-first ordering with `case_id` as the tie-breaker.

No new approval table is created. Existing registration reviews, final QC reviews, candidate decisions, and Golden versions remain the evidence trail. Training eligibility remains based on the current quality, capture, registration, and final-human-QC gates.

## Error And Recovery Behavior

- Invalid manifests fail locally before uploading any entry.
- A changed source file invalidates its previous receipt row because the SHA-256 no longer matches.
- Network interruption preserves accepted server ids and retries only incomplete entries.
- Server idempotency conflicts return the existing case rather than duplicate it.
- A missing server original appears as a typed catalog/detail error and cannot be reviewed or exported.
- Automatic registration failure remains `manual_required` and opens the existing four-point workflow.
- Partial front/back intake remains visible as `pair_in_progress`; it is not treated as a complete board pair.
- Proxy and synthetic evidence remain excluded from Golden and training gates.

## Security And Privacy

- Credentials stay in the existing external sensitive directory and are never accepted in the manifest or receipt.
- The CLI must not print authorization values or passwords.
- Local source paths are not persisted to the server.
- Server responses expose original bytes only to the data administrator who owns the case.
- Dataset ZIP exports retain their current reviewer/data-admin gate and hash verification.
- Deployment continues through the existing immutable runtime archive, backup, rollback, loopback-service, and Nginx validation path.

## Testing And Acceptance

### P0 And P1

- manifest schema and local validator tests;
- safe identifier, duplicate, MIME/signature, dimensions, hash, catalog, side, and capture-session tests;
- dry-run proves zero API calls;
- partial receipt resume and deterministic idempotency tests;
- technician upload rejected before body processing;
- data administrator upload, case catalog pagination/filtering, and original download tests;
- actor isolation and historical-case migration tests;
- existing quality, registration, Golden, dataset audit, COCO, and ZIP tests remain green.

### P2

- full Python and Node suites;
- Python compile, JavaScript syntax, JSON Schema parse, `git diff --check`, strict UTF-8, and U+FFFD scans.

### P3

- headed Chrome on desktop and 390 px;
- data-admin catalog empty, populated, processing, failure, and completed states;
- board/side/status filters, refresh, open case, original rendering, retry, and return to catalog;
- technician route shows no upload/data-management controls;
- default, hover, active, focus-visible, loading, disabled, and error states remain readable;
- no horizontal overflow, overlap, blank canvas, failed request, or console error.

### P4

- deploy through the current controlled-server script;
- verify production technician upload returns 403 and data-admin identity retains existing export access;
- verify migration preserves the one known proxy case and current dataset audit;
- perform no fake physical upload before Milo supplies a real photo;
- when the first real batch arrives, run dry-run, import, processing, manual fallback if needed, front/back pairing, Golden review, dataset gate, and exported-hash acceptance end to end.

## Explicit Non-Goals

- technician or colleague photo submission;
- a multi-user review or approval queue;
- automatic board/model/side classification;
- automatic defect confirmation;
- direct model training on the pilot server;
- public engineering-asset or dataset access;
- changing the main repair workbench into an administrative application;
- claiming real-board accuracy before the first physical front/back acceptance batch.

## Superseded Statements

After implementation, project documentation must remove or qualify statements that describe overseas technicians as visual-photo uploaders, the visual workbench as a technician intake route, or the `reviewer` role as a second-person approval layer. Historical implementation records may remain, but current architecture summaries must identify Milo/Codex as the only intake path and `reviewer` as the compatibility name for the data-administrator capability.
