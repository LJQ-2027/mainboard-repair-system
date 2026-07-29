# Visual QC Server API V1

## Status

This document describes the **Local HEAD contract**. Milo is the only source of real visual photos; Codex operates intake, registration, annotation, Golden Sample management, and export as the data administrator. Overseas technicians do not upload photos and do not use the internal visual data workbench.

Production remains `f278061`. That deployed revision returns Create/Get `VISUAL-QC-SERVER-CASE-V1`, Admin List `VISUAL-QC-ADMIN-CASE-LIST-V1`, and Admin Detail `VISUAL-QC-SERVER-CASE-V2`; it predates qualified handoff, List V2, Detail V3, and browser physical-upload removal. The qualified-handoff CLI must not target production until a separately approved deployment and migration verification completes.

## Upgrade Preflight Boundary

Local HEAD includes `VISUAL-QC-UPGRADE-PREFLIGHT-V1`; deployed `f278061` does
not. Before a future deployment can switch the app directory or Visual-QC
virtualenv, the candidate runtime must rehearse its migration against the
deployment-owned consistent rollback snapshot and the persistent object root.

The rehearsal verifies the exact source snapshot SHA-256, additive SQLite
migration, shared legacy row digests, managed-object hashes, Health V2, Admin
List V2, Admin Detail V3, Dataset Audit V1, legacy dataset exclusions, and
old-runtime rollback readability. The deployment script fails closed unless
the report is passed and bound to the candidate commit. See
`docs/visual-qc-upgrade-preflight-2026-07-23.md`.

This is a deployment gate, not a production deployment record. Production
remains `f278061` until separately approved deployment and post-switch P4
verification are complete.

## Runtime

Install the pinned worker dependencies:

```powershell
python -m pip install -r requirements-visual-qc.txt
```

Start the QC API locally:

```powershell
python visual_qc_server.py
```

The default port is `3020`. Production paths are expected to be routed by Nginx under the existing controlled origin:

For split-port local development, allow only the explicit workbench origins:

```powershell
$env:VISUAL_QC_ALLOWED_ORIGINS='http://127.0.0.1:8899,http://localhost:8899'
python visual_qc_server.py
```

Open the workbench with `?qcApi=http://127.0.0.1:3020/api/v1/visual-qc`. Production should use the same origin and leave cross-origin access disabled. The allowlist is strict and does not use wildcard CORS.

```nginx
location /mb-repair-beta/api/v1/visual-qc/ {
    proxy_pass http://127.0.0.1:3020/api/v1/visual-qc/;
    proxy_set_header X-Actor-Id $authenticated_user_id;
    client_max_body_size 20m;
}
```

The example assumes the controlled gateway has already authenticated the request. Nginx must remove any client-supplied `X-Actor-Id` and set the verified identity itself. The current API refuses requests without that identity, but it does not replace the gateway's authentication system.

`GET /api/v1/visual-qc/identity` returns `VISUAL-QC-IDENTITY-V1` from those gateway headers. Unknown roles fail closed to `technician`; only the exact server-injected `reviewer` role enables data-administrator operations. `reviewer` is a temporary wire-compatibility value, not a second-person approval layer. The workbench uses this response instead of treating URL identity hints as authoritative.

The QC process defaults to `127.0.0.1:3020` through `VISUAL_QC_HOST=127.0.0.1`. It must not listen on a public interface. The bounded pilot uses per-user Nginx Basic Auth and may later replace that gateway with corporate SSO/OIDC without changing this API identity contract.

## Upload Contract

`POST /api/v1/visual-qc/cases`

Headers:

- `X-Actor-Id`: identity asserted by the authenticated gateway.
- `X-Actor-Role`: must be the gateway-asserted data-administrator compatibility value `reviewer`.
- `Idempotency-Key`: stable retry key generated from the acceptance-qualified handoff entry.

Multipart fields:

- `board_key`
- `side_id`
- `capture_stage`: `golden_reference`, `before_repair`, or `after_repair`
- `evidence_role`: `physical_capture`, `synthetic_proxy`, or `service_manual_proxy`
- `capture_session_id`: stable id for one physical board, capture stage, and setup
- `capture_setup_id`: stable optical setup id
- `capture_checklist`: JSON object containing the three physical-capture confirmations
- `intake_batch_id`: required validated batch id for `physical_capture`
- `intake_entry_id`: required entry id unique within that batch for `physical_capture`
- `qualified_handoff`: required closed JSON provenance object for `physical_capture`; it binds the source package, archived intake, acceptance report, and acceptance action by SHA-256
- `sha256`: lowercase or uppercase SHA-256 of the original bytes
- `file`: JPEG, PNG, or WebP

Acceptance validates:

- board and side identity against the current executable board catalog;
- declared hash against the uploaded bytes;
- declared MIME type against the file signature;
- decodability and minimum dimensions;
- configured upload size and free-space reserve;
- idempotency ownership and request fingerprint.
- capture-session identity consistency, including inside the database write transaction.
- complete and semantically valid acceptance-qualified handoff provenance for every physical capture.

The API rejects non-data-administrator upload attempts before multipart parsing. It also rejects a physical capture that does not carry the exact provenance created by `handoff_visual_qc_physical_package.py`. Accepted uploads return HTTP `202` with `VISUAL-QC-SERVER-CASE-V2`, an image record, the normalized qualified-handoff provenance, and a persisted queued job. Originals use content-addressed storage under the configured data root.

`GET /api/v1/visual-qc/capture-sessions/{capture_session_id}` returns the expected and captured board sides, `pair_in_progress` or `pair_complete`, and the accepted cases for the authenticated actor. A session is actor-scoped and cannot be read by another actor.

Physical captures use one controlled path. Run the acceptance-qualified handoff dry run first, inspect its receipt, and then repeat without `--dry-run` to transfer:

```powershell
python scripts/handoff_visual_qc_physical_package.py `
  source-package.json `
  physical-registration-run.json `
  --library-root D:\visual-qc-source-library `
  --handoff-root D:\visual-qc-handoffs\km4-physical-001 `
  --dry-run

python scripts/handoff_visual_qc_physical_package.py `
  source-package.json `
  physical-registration-run.json `
  --library-root D:\visual-qc-source-library `
  --handoff-root D:\visual-qc-handoffs\km4-physical-001 `
  --api-base http://127.0.0.1:3020/api/v1/visual-qc `
  --credential-file C:\secure\visual-qc-credential.json `
  --allow-http-localhost `
  --wait
```

This example targets an isolated local integration service. Do not substitute the production URL while production remains `f278061`. The handoff tool revalidates the immutable source package, archived intake, acceptance report, source images, and overlays before it calls the low-level resumable importer. The importer remains an internal transport primitive; it cannot synthesize qualified provenance and direct physical import fails closed. Credentials are never embedded in manifests or receipts. The browser does not create new physical server cases.

## Data-Administrator Case Catalog

- `GET /api/v1/visual-qc/admin/cases`
- `GET /api/v1/visual-qc/admin/cases/{case_id}`
- `GET /api/v1/visual-qc/admin/cases/{case_id}/image`

These routes require the data-administrator compatibility role and remain actor-scoped. List responses use `VISUAL-QC-ADMIN-CASE-LIST-V2` and provide stable board, side, state, evidence-role and pagination filters. Detail responses use `VISUAL-QC-SERVER-CASE-V3`, include qualified-handoff provenance plus the latest processing/registration/QC evidence, and verify that the content-addressed original still matches its stored hash before image recovery. The internal workbench restores the server case into IndexedDB and then uses the existing canvas workflow. Machine-readable response schemas are `knowledge-base/visual-qc-server-case-v2-schema.json`, `knowledge-base/visual-qc-server-case-v3-schema.json`, and `knowledge-base/visual-qc-admin-case-list-v2-schema.json`; V1 response documents are historical only.

## Job Contract

- `GET /api/v1/visual-qc/jobs/{job_id}`
- `POST /api/v1/visual-qc/jobs/{job_id}/retry`
- `GET /api/v1/visual-qc/cases/{case_id}`

Jobs move through `queued`, `running`, `succeeded`, or `failed`. A process restart returns interrupted `running` jobs to `queued`. Only failed jobs can be retried explicitly.

A successful processing job returns `VISUAL-QC-SERVER-JOB-RESULT-V1`:

- `quality`: `VISUAL-QC-IMAGE-QUALITY-V1` with raw resolution, luminance, clipping, contrast, and sharpness evidence.
- `registration`: `VISUAL-QC-REGISTRATION-CANDIDATE-V1`.

`registration.status = candidate` is still draft evidence and requires human review. `manual_required` is a successful safe business result, not a server failure. It directs the existing reviewed four-point workflow and never guesses a transform.

## Review, Golden, And Difference Contracts

- `POST /api/v1/visual-qc/cases/{case_id}/registration-reviews`
- `POST /api/v1/visual-qc/cases/{case_id}/qc-reviews`
- `POST /api/v1/visual-qc/golden-samples`
- `GET /api/v1/visual-qc/golden-samples/active`
- `POST /api/v1/visual-qc/cases/{case_id}/difference-jobs`
- `POST /api/v1/visual-qc/jobs/{job_id}/candidate-reviews`
- `GET /api/v1/visual-qc/artifacts/{artifact_id}`

Automatic registration review adopts the exact candidate matrix. Manual review requires four unique normalized board/image anchor pairs and a finite, non-degenerate normalized homography.

Final QC review requires a physical capture with a confirmed capture checklist, acceptable completed image quality, reviewed registration, resolved human annotations, and either `no_visible_anomaly` or `confirmed_anomaly`. Every accepted submission creates a new append-only `case_qc_reviews` version. A confirmed anomaly must contain at least one confirmed human annotation; a no-anomaly result cannot contain one. Proxy evidence and retake-quality images are rejected.

Golden approval additionally requires the gateway-asserted `reviewer` role, `physical_capture` evidence, `golden_reference` capture stage, a confirmed capture checklist, acceptable image quality, reviewed registration, explicit normal-board confirmation, and an immutable source hash. The requested Golden setup must equal the original capture setup. Golden scope is board, side, and capture setup. Activating a replacement increments the version and retires rather than rewrites the previous record.

The browser uses `allow_missing=true` when looking up an active Golden. That optional lookup returns a typed `VISUAL-QC-GOLDEN-LOOKUP-V1` `missing` result instead of turning a normal empty state into an HTTP error. Strict callers that omit the flag retain the original `404 golden_sample_not_found` behavior.

Difference jobs require reviewed current registration and an active Golden in the same scope. They align both images to the board coordinate plane, normalize broad luminance variation, and persist a controlled PNG heatmap plus normalized candidate boxes. These technical thresholds propose review regions; they are not industrial defect-acceptance thresholds.

Every region begins as `model_candidate`. The data administrator may mark it `confirmed`, `rejected`, or `needs_review`. Only `confirmed` plus a supported human defect category becomes `human_annotation`; model output never becomes a repair instruction.

## Persistence

The pilot stores:

- SQLite case, image, job, and audit records;
- actor-scoped capture-session identity and per-image capture checklists;
- content-addressed originals on controlled server disk;
- registration and quality evidence in the completed job record;
- append-only final human QC review versions and their exact registration-review identity.

The SQLite and object-storage classes are isolated behind service boundaries so later PostgreSQL and controlled object-storage migration does not require changing browser routes.

## Health And Retention

`GET /api/v1/visual-qc/health` returns `VISUAL-QC-SERVER-HEALTH-V2` with:

- `normal`, `warning`, or `critical` disk pressure;
- total, used, free, reserve, and warning bytes;
- physical original and artifact object counts and bytes;
- case totals, job-state counts, and active/retired Golden counts.

The upload path still rejects a write before it would cross `VISUAL_QC_MIN_FREE_BYTES`. `VISUAL_QC_WARNING_FREE_BYTES` provides an earlier operational warning. The defaults are 2 GB reserve and 4 GB warning; production may raise both after observing real capture sizes.

Retention is deliberately not exposed as a browser route. Run it on the controlled server while the QC service is stopped. The default command only reports the bounded plan:

```powershell
python -m scripts.maintain_visual_qc_server
```

Only cases older than `VISUAL_QC_RETENTION_DAYS` are eligible, up to `VISUAL_QC_RETENTION_BATCH_LIMIT` per run. Eligibility requires at least one job and requires every job to have the explicit terminal state `succeeded` or `failed`; missing, unknown, queued, and running states fail closed. Any registration review, final QC review, Golden version, or candidate review also protects the case. Content-addressed files are deleted only after the database case is removed and only when no remaining image or artifact references the same path.

## Training Dataset Export

- `GET /api/v1/visual-qc/datasets/training-manifest`
- `GET /api/v1/visual-qc/datasets/coco`
- `GET /api/v1/visual-qc/datasets/audit`
- `GET /api/v1/visual-qc/datasets/bundle`
- `GET /api/v1/visual-qc/datasets/images/{image_id}`

All five routes require the exact gateway-injected data-administrator compatibility role `reviewer`. The manifest uses `VISUAL-QC-TRAINING-MANIFEST-V1` and contains only the latest eligible final review for each physical case with valid qualified-handoff provenance, together with immutable board identity, capture setup, source hash, QC result, and reviewed annotations. The same physical-evidence and provenance gate protects the manifest, COCO, bundle, audit classification, and direct image route; malformed provenance fails closed. The COCO route builds `VISUAL-QC-COCO-V1` from that server-owned manifest on each request, sorts cases and annotations deterministically, keeps the nine fixed defect categories even for an empty dataset, and includes only confirmed human annotations. The bundle route packages a deterministic manifest snapshot, COCO, `VISUAL-QC-DATASET-BUNDLE-V1` index, and all eligible originals under stable case-derived archive paths. It verifies each source object against the governed SHA-256, streams image content into a fixed-metadata ZIP, preserves the server disk reserve, and deletes the temporary archive after the response. The read-only `VISUAL-QC-DATASET-AUDIT-V1` route evaluates every server case against one ordered primary blocker. These routes are the server-owned training-data boundary; browser drafts and proxy evidence never enter the eligible export.

Original and artifact writes hold the same data-root OS file lock from object creation through database reference commit. Retention holds that lock from its final transactional eligibility check through reference-aware object deletion. This closes the upload/cleanup race across API and CLI processes, but the operational procedure still stops the QC service before destructive maintenance.

Actual deletion requires both the execution flag and the exact confirmation phrase:

```powershell
python -m scripts.maintain_visual_qc_server `
  --execute `
  --confirm DELETE-EXPIRED-DRAFTS
```

Every executed run is recorded in `retention_runs` with its cutoff, candidate IDs, and deletion totals. Cleanup errors mark the run as failed with a bounded error message plus case, object, and byte totals already removed, so partial work is visible. A dry run never mutates cases, records, or job state.

## Current Boundary

Implemented:

- acceptance-qualified physical handoff with controlled multipart transport;
- owner-managed batch validation, resumable low-level CLI transport, and stable intake receipts;
- data-administrator-only upload enforcement before multipart parsing;
- actor-scoped admin case list, detail, original recovery, filtering, and pagination;
- SHA-256 integrity and deduplication;
- persisted cases and jobs;
- idempotent retry behavior;
- one or two bounded background workers;
- interrupted-job recovery;
- explicit failed-job retry;
- server-side image quality metrics;
- automatic registration candidate or reviewed-manual fallback;
- IndexedDB local-draft recovery and server-case restoration;
- stable handoff idempotency keys across retry and process restart;
- byte-level handoff progress, job polling, failed-job retry, and interrupted polling recovery;
- automatic candidate overlay with explicit human confirmation;
- safe return to the existing four-point workflow when automatic registration is unavailable;
- data-administrator Golden Sample approval and active-version lookup in the workbench;
- difference heatmap retrieval plus per-candidate confirm, reject, and needs-review decisions;
- versioned `VISUAL-QC-CASE-V2` browser drafts for server synchronization and comparison state;
- append-only final human QC review versions synchronized from the browser;
- data-administrator training manifest, deterministic COCO export, and eligible source-image download;
- data-administrator deterministic complete-dataset ZIP with manifest, COCO, index, and verified originals;
- data-administrator dataset-readiness audit with one actionable primary blocker per server case;
- disk-pressure health reporting, bounded old-draft retention planning, protected evidence rules, and audited explicit cleanup.

Still open:

- production scheduling and alert delivery for the implemented retention and health primitives;
- physical bare-board acceptance.

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
