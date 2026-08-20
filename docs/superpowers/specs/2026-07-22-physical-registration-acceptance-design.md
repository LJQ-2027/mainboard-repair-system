# Physical Registration Acceptance Run Design

## Status

Implemented as the offline acceptance layer. Direct server import after this run is superseded by `2026-07-23-physical-acceptance-qualified-handoff-design.md`; the report must pass through the qualified handoff before a physical server case can be created.

## Purpose

Build a deterministic, offline acceptance run for the first Milo-supplied physical mainboard photo package. The run validates the controlled source package, executes the existing image-quality and automatic-registration cores for every entry, and produces reviewable evidence without uploading, mutating, or approving anything.

This closes the operational gap between controlled source staging and the server/workbench review path. It does not replace the acceptance-qualified handoff, manual four-point fallback, or human registration review.

## Scope

The first version accepts one `VISUAL-QC-SOURCE-PACKAGE-V1` path plus its external controlled-library root. It resolves each declared board side through the five-board catalog and generates:

- one deterministic `VISUAL-QC-PHYSICAL-REGISTRATION-RUN-V1` JSON report;
- one deterministic PNG overlay per entry;
- one concise Markdown summary for human review.

It does not upload files, alter source objects, create server cases, accept a registration, create a Golden Sample, or infer a defect.

## Evidence Semantics

Every run records:

- `evidence_role: physical_capture` because the source package was explicitly staged as Milo-supplied physical evidence;
- `physical_source_confirmed: true` copied from the validated package;
- `field_accuracy_claim_allowed: false` because no surveyed geometric ground truth exists;
- `registration_review_status: pending` for every entry;
- the exact source package identity and manifest SHA-256, current proxy-inventory digest, board identity, image hash, image dimensions, capture stage/session/setup, quality evidence, and complete automatic-registration candidate.

The per-entry action is derived without an industrial threshold:

1. `image_retake_required` when the existing quality core returns `retake`;
2. `manual_registration_required` when automatic registration has no valid candidate;
3. `automatic_candidate_review_required` when a technical candidate exists.

No action means accepted, reviewed, repairable, normal, or defective.

## Architecture

`scripts/visual_qc/physical_acceptance.py` owns pure report construction and deterministic overlay rendering. It reuses `validate_source_package`, `BoardCatalog`, `analyze_image_quality`, and `register_board_image` rather than duplicating intake, catalog, or CV rules.

`scripts/run_visual_qc_physical_acceptance.py` owns CLI argument handling, atomic output publication, stable exit codes, and machine-readable failure output.

`knowledge-base/visual-qc-physical-registration-run-v1-schema.json` defines the durable report contract and locks candidate/manual/processing states to their human-review semantics. Runtime consistency checks independently recompute summary counts, entry actions, and overall status. Successful runs are byte-stable for identical package, code configuration, and image bytes; reports contain no timestamps or absolute paths.

## Overlay Contract

Each overlay uses the original capture dimensions capped at 1600 pixels on the longest edge. For an automatic candidate, the engineering reference is perspective-warped into capture space at fixed opacity and the projected reference quadrilateral is drawn. For manual fallback, the unmodified capture is shown with a fixed border and status label only. The overlay is evidence for human inspection, not a registration approval artifact.

Overlay filenames are `<entry_id>.registration-overlay.png`. The report records a relative artifact path, SHA-256, MIME type, width, height, and byte size. Each PNG and report file is flushed and file-synced before publication. Atomic publication writes a complete temporary output directory under a per-output cross-thread/process lock and renames it into place; an existing output directory is rejected, and a post-rename parent-sync failure rolls the output back.

## Status And Exit Codes

The report status is:

- `review_required`: all entries processed and at least one automatic candidate awaits review;
- `attention`: all entries processed, but at least one image needs retake or manual registration;
- `issues`: an entry could not be processed after package validation.

CLI exit codes are `0` for `review_required` or `attention`, `1` for a completed report with `issues`, and `2` for invalid arguments, invalid/revoked source package, unsafe output placement, or publication failure.

## Safety Boundaries

- Source objects and package manifests are opened read-only.
- The source-package manifest SHA-256 is computed from the exact byte string parsed by package validation, not from a later path read.
- Source image bytes are SHA-256 checked again after package validation and decoded from that same in-memory byte string, closing the validation/read race.
- Lock and precreated publishing paths reject symlinks and Windows reparse points; the `mkdtemp` directory is populated in place instead of being deleted and recreated.
- The controlled library must remain outside the project tree and cannot contain the project tree.
- Output must be outside the controlled source library.
- Current proxy-inventory validation remains mandatory, so a package is revoked if its evidence becomes known proxy material.
- The report never stores absolute paths.
- Synthetic fixtures may test behavior only in temporary directories and never become committed physical evidence.

## Verification

Targeted tests cover schema and runtime consistency, deterministic report and overlay bytes, quality/manual/candidate action precedence, package revocation, object/manifest read races, source immutability, output containment, Windows reparse paths, cross-process locking, durable publication rollback, and CLI exit codes. Full Python and Node regressions remain required. Because this increment has no user-visible browser change and no server deployment, P3 and production P4 are not triggered; local filesystem acceptance is the relevant P4-like boundary check.
