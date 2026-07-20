# Visual QC Server Architecture Design

## Status

Approved by Milo on 2026-07-20. This document is the canonical target architecture for visual QC, physical-photo registration, Golden Sample management, and visual evidence feedback. Older references to a technician-installed Python service, browser-only storage, or offline inference as the primary production path are superseded.

The current `assets/visual-qc-workbench/` implementation remains a valid local data-workbench baseline. Its `local_only` storage behavior describes current code, not the approved production architecture.

## Product Fit

The visual capability is one subsystem of the existing overseas mainboard repair platform. It is not a separate quality-inspection product and does not add a second technician entry.

The technician flow remains:

`select known model and board -> choose known fault or initial inspection -> capture/upload board image -> register image to the board coordinate system -> review visible anomaly candidates -> continue source-backed electrical checks and repair guidance -> record outcome -> sync the case`

Visual processing finds and locates visible anomaly candidates. The point map, schematic, repair guide, 2.5D model, and reviewed SOP explain what the location represents and what test is allowed next. Model output never directly authorizes a repair action.

## Deployment Decision

The production path is a server-led Web platform with asynchronous visual processing and manual fallback.

- Technicians use one responsive Web application through the existing controlled server.
- Physical-board photos may be uploaded to the controlled server.
- The server owns case identity, image provenance, Golden Sample review, processing jobs, candidate review, audit history, and dataset export.
- OpenCV runs in a server-side worker for image quality, contour detection, feature registration, homography validation, and difference candidates.
- Automatic registration failure returns the existing reviewed four-point registration workflow.
- Browser storage is a weak-network draft and retry mechanism, not the authoritative cross-site data store.
- PWA caching may later improve weak-network resilience, but it is not the primary architecture.
- Training runs in a separate compute environment. The current server does not train deep models.

## Current Server Boundary

The controlled beta server was inspected read-only on 2026-07-20:

- 4 x86_64 vCPU
- 7.3 GB RAM and 4 GB swap
- 19 GB free disk space on the single system volume
- Python 3.10 and Node.js 20
- no GPU
- no installed OpenCV
- no active PostgreSQL or Redis service
- Nginx and PM2 already route the motherboard repair beta under `/mb-repair-beta/`

This is sufficient for a bounded pilot with one or two CPU OpenCV workers. It is not sufficient for deep-model training, high-volume permanent image retention, or unrestricted synchronous image processing.

## Runtime Architecture

### Technician Web Application

The existing repair workbench remains the product shell. The visual flow adds:

- image capture/upload with progress and retry;
- known board and side identity inherited from the repair session;
- automatic registration status and evidence;
- manual four-point fallback;
- Golden Sample comparison;
- candidate heatmap review;
- confirm, reject, or retain-for-review decisions;
- synchronized image, point-map, schematic, and 2.5D coordinates;
- repair result and case feedback.

IndexedDB stores unfinished drafts, upload state, and temporary source blobs so a refresh or weak connection does not discard work. The server becomes authoritative after upload acceptance.

### QC API

A FastAPI application will replace the current simple HTTP server for new QC routes while retaining same-origin frontend and AI access.

Initial responsibilities:

- validate board, side, capture stage, MIME type, dimensions, and hash;
- create image and case records;
- persist upload and processing state;
- enqueue and expose visual jobs;
- manage Golden Sample review and version state;
- store model candidates separately from human labels;
- expose review and dataset-export operations;
- enforce authenticated, controlled access to engineering-linked assets.

### Storage

The pilot uses an explicit storage adapter:

- SQLite for cases, jobs, review state, Golden Sample metadata, and audit events;
- a dedicated server directory for originals, normalized derivatives, thumbnails, overlays, and heatmaps;
- SHA-256 for integrity and deduplication;
- retention limits and free-space checks before accepting new originals.

The interfaces must permit later migration from SQLite to PostgreSQL and from server disk to controlled S3-compatible object storage without changing the browser contract.

### OpenCV Worker

One or two CPU workers process jobs outside request handlers:

1. decode and normalize the image;
2. calculate image-quality metrics;
3. locate plausible board contours;
4. attempt ORB and AKAZE feature matching against the selected board-side reference;
5. estimate homography with RANSAC;
6. validate inlier count, coverage, projected board shape, and transform sanity;
7. return an automatic registration candidate or a structured fallback reason;
8. after human registration review, align the selected Golden Sample and produce difference candidates;
9. save artifacts and evidence without converting candidates into confirmed defects.

Requests return job identifiers instead of blocking until large-image processing completes. Jobs survive process restarts through persisted state.

## Evidence And Data Contract

`VISUAL-QC-CASE-V1` remains the current local baseline. The server increment must version the contract rather than silently changing V1 semantics.

Evidence roles are explicit:

- `synthetic_proxy`: generated from an engineering point map;
- `service_manual_proxy`: one of the reviewed installed-board or structure images;
- `physical_capture`: a real photographed board;
- `reviewed_golden_reference`: a physical capture approved as a normal reference.

Synthetic and Service Manual proxies may validate software and structural matching, but never count toward field accuracy. Only reviewed physical captures may become production Golden Samples or real defect-recognition evidence.

Automatic output uses `model_candidate`. A technician or reviewer must confirm or reject it before it contributes a human label. Repair guidance continues to come from reviewed point-map, schematic, repair-manual, and SOP sources.

## Golden Sample Rules

A Golden Sample is scoped to board identity, side, capture setup, and revision. It requires:

- physical-capture evidence;
- acceptable image-quality status;
- reviewed registration;
- confirmed normal-board status;
- reviewer identity and timestamp;
- immutable source hash;
- explicit version and retirement state.

Proxy or synthetic images cannot become Golden Samples. Replacing a Golden Sample creates a new version and does not rewrite historical cases.

## Weak-Network Behavior

- Save the case draft before upload.
- Display upload progress and a retryable failure state.
- Avoid losing annotations or manual anchors when upload fails.
- Generate a local preview immediately.
- Resume the case from server state after the upload is accepted.
- Keep manual registration and source-backed repair guidance available when automatic processing fails.

Offline-first operation is not promised for the complete system. The supported guarantee is recoverable local drafting plus retry when the network returns.

## Security Boundary

Physical board photos are authorized for upload to the existing controlled server. This does not authorize public distribution of schematics, point maps, Golden Sample data, repair parameters, or unreleased board information.

The production server must enforce authentication, role-based access, controlled download, audit logging, and separation between public code and internal data. Raw engineering materials remain in approved controlled storage and are exposed to the workbench only through the minimum derived assets required by the technician flow.

## Delivery Sequence

1. Generate deterministic synthetic transforms from high-resolution point-map references.
2. Build and benchmark server-side contour and feature registration with manual fallback.
3. Test all 21 reviewed Service Manual images as proxy structural evidence and label every result accordingly.
4. Add server upload, persistent jobs, Golden Sample review, difference candidates, and technician confirm/reject.
5. Publish capture and intake specifications.
6. Deploy the bounded pilot to the existing beta service.
7. Re-run acceptance with a known KM4/F151 bare-board front/back photo set.
8. Begin model training only after a separate audit confirms sufficient real labels and class distribution.

## Implementation Progress

The first four delivery items now have a local server implementation:

- deterministic synthetic transforms cover all ten sides in the five-board catalog;
- the CPU OpenCV core uses contour evidence, ORB with AKAZE fallback, RANSAC homography validation, and structured manual fallback;
- `VISUAL-QC-REGISTRATION-CANDIDATE-V1` keeps automatic output in a draft candidate state;
- the committed benchmark covers 20 synthetic cases and all 21 reviewed Service Manual proxy images.
- FastAPI accepts controlled, idempotent multipart uploads and persists cases, images, jobs, reviews, Golden versions, artifacts, and audit events in SQLite;
- one or two bounded workers recover interrupted jobs and return quality plus registration evidence outside request handlers;
- reviewed automatic or manual registration is required before a physical capture can become a Golden Sample;
- Golden Samples are versioned by board, side, and capture setup, while proxy evidence is rejected;
- reviewed cases can produce difference heatmaps and `model_candidate` regions;
- technician confirm/reject decisions are stored separately, and only a confirmed region receives `human_annotation`.
- the browser workbench now persists weak-network drafts, uploads with a stable idempotency key and byte progress, polls or retries jobs, restores interrupted synchronization after refresh, and keeps every automatic transform in draft until a person confirms it;
- automatic failure returns the operator to the existing four-point registration workflow, whose review is then persisted by the server.
- reviewer-gated Golden Sample approval, active-version lookup, difference heatmaps, and per-candidate confirm/reject/defer decisions are available in the same workbench;
- server-connected browser cases use `VISUAL-QC-CASE-V2`, while the local-only V1 contract retains its original meaning.

This progress does not imply production deployment. The controlled gateway/Nginx route, production authentication assertion, retention operations, and physical bare-board acceptance remain open.

## Acceptance Boundary

The first server increment is accepted when:

- uploads and processing jobs recover from normal retry and restart cases;
- synthetic transforms prove homography round trips and expected failure paths;
- the 21 reviewed images produce a committed proxy benchmark report;
- automatic registration exposes evidence and falls back safely;
- Golden Samples require reviewed physical evidence;
- difference candidates can be confirmed or rejected without becoming automatic repair conclusions;
- current server resource limits remain respected;
- no result is described as real-board defect accuracy before physical-photo acceptance.
