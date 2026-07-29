# Repair Case Supporting-Only Evidence Design

**Date:** 2026-07-29  
**Status:** Proposed written specification after Milo approved approach A  
**Owner:** Milo  
**Data operator:** Codex

## Goal

Allow a real repair case to preserve owner-supplied `维修中` photographs as
independent supporting evidence when the photographs cannot truthfully be
classified as `before_repair`, `after_repair`, or `golden_reference`.

The first real targets are F069 CASE003 and CASE004. Their HEIC originals must
enter the controlled repair-case library with the source-declared stage
`维修中` and board-area label `屏蔽罩内局部`, without creating a Visual-QC
source package or a visible-defect conclusion.

## Approved Product Boundary

Approach A is authoritative:

- preserve the exact repair-in-progress photo bytes;
- bind them to the independent repair-case fact record;
- keep source-declared stage and board-area wording;
- allow case symptoms, findings, actions, and outcomes only when supplied by
  the source record;
- do not relabel the photographs as before repair, after repair, supplemental
  Visual QC, or Golden reference;
- do not create registration, annotation, QC, Golden, training, repair
  causality, repair instruction, or field-accuracy evidence.

The feature is an internal data-administrator path. It adds no technician
upload, browser workflow, server API, or production deployment.

## Why The Existing Contract Is Insufficient

`VISUAL-QC-REPAIR-CASE-SOURCE-V2` currently requires at least one validated
Visual-QC source package. A source package can use only
`before_repair`, `after_repair`, or `golden_reference`. Reclassifying
`维修中` as one of those stages would alter the source fact.

The existing supporting-evidence path also rejects HEIC and does not carry
structured source stage or board-area context. Relaxing V2 in place would
silently change the meaning of an already published contract.

## Chosen Architecture

Add `VISUAL-QC-REPAIR-CASE-SOURCE-V3`. V1 and V2 remain byte-for-byte
unchanged, readable, and valid under their original rules.

V3 adds two top-level fields:

```json
{
  "evidence_mode": "supporting_only",
  "supporting_evidence_contexts": [
    {
      "evidence_id": "case003-repair-in-progress-photo",
      "evidence_role": "repair_in_progress_photo",
      "source_capture_stage": "维修中",
      "source_board_area": "屏蔽罩内局部"
    }
  ]
}
```

Allowed evidence modes:

- `package_linked`: retains the historical rule that at least one validated
  source package is present.
- `supporting_only`: requires zero package links and at least one contextual
  supporting-evidence object.

`supporting_only` is not a new Visual-QC capture stage. It is a repair-case
evidence mode and must never appear in source-package, physical-acceptance,
handoff, registration, Golden, QC, or dataset contracts.

## Supporting Evidence Context

Each context has exact fields:

- `evidence_id`: resolves to one supporting-evidence object in the same
  revision;
- `evidence_role`: initially only `repair_in_progress_photo`;
- `source_capture_stage`: non-empty source wording, preserved exactly;
- `source_board_area`: non-empty source wording, preserved exactly.

For the first release:

- every supporting-evidence object in `supporting_only` mode must have exactly
  one context;
- every context must resolve to exactly one evidence object;
- duplicate or dangling context IDs fail closed;
- `repair_in_progress_photo` requires PNG, JPEG, or HEIC evidence;
- source wording is descriptive provenance, not a Visual-QC enum and not an
  inferred board side;
- the operator may transcribe the wording from the authorized Base row but may
  not normalize it into a different capture stage.

The context list is append-only across revisions. Historical context cannot be
removed or rewritten.

## HEIC Evidence

V3 supporting evidence accepts `image/heic` with canonical object path:

```text
objects/case-evidence/<sha-prefix>/<sha256>.heic
```

HEIC behavior is deliberately different from
`VISUAL-QC-SOURCE-PACKAGE-V2`:

- the exact HEIC source bytes are stored as the supporting object;
- the existing HEIC inspector verifies that the file is a supported container
  with a valid primary image;
- no JPEG working derivative is required or published;
- no image-quality, registration, side, or Visual-QC claim is computed;
- V1 and V2 continue rejecting HEIC supporting evidence.

The existing 50-file and 100 MiB per-file limits remain unchanged.

## V3 Contract Rules

V3 retains the V2 device-identity object, append-only facts, correction rules,
completeness derivation, and fixed false boundaries.

For `package_linked`:

- `package_links` contains 1 to 100 validated links;
- supporting evidence remains optional;
- supporting evidence added under V3 may have context, but
  `supporting_only` rules do not apply.

For `supporting_only`:

- `package_links` is exactly empty;
- `supporting_evidence` contains 1 to 50 records;
- `supporting_evidence_contexts` covers every supporting-evidence ID exactly
  once;
- at least one context has role `repair_in_progress_photo`;
- package-entry evidence references are impossible because no package target
  exists;
- identity and case facts may reference contextual supporting evidence;
- completeness is still derived from supplied facts and may be
  `photos_only`, `symptom_linked`, `diagnosis_linked`, or
  `repair_outcome_linked`;
- completeness never changes a downstream boundary.

V3 adds no positive downstream permission. Its boundaries remain:

```json
{
  "visual_defect_confirmed": false,
  "golden_approved": false,
  "training_label_allowed": false,
  "repair_instruction_allowed": false,
  "field_accuracy_claim_allowed": false,
  "model_identity_resolved": false
}
```

`model_identity_resolved` continues to be derived from the V2 identity rules
and may be true only when those existing rules are independently satisfied.
The other five values are always false.

## Revision Compatibility

- V1 and V2 manifests are never rewritten.
- New supporting-only cases start at V3 revision 1.
- V3 revisions retain package links, supporting evidence, contexts, facts, and
  corrections as append-only prefixes.
- A V1/V2 case may move to V3 only in `package_linked` mode. Historical
  supporting evidence remains valid without retroactive context; every new V3
  contextual item follows V3 rules.
- A case cannot switch between `package_linked` and `supporting_only` after
  revision 1. Evidence mode is part of historical case identity.
- A supporting-only case cannot later acquire a package link through the same
  case history. A separately staged physical package may be connected only
  through a later, independently designed evidence-link path after physical
  acceptance.

This prevents a repair-in-progress photo from being silently promoted into
registered Visual-QC evidence by a later amendment.

## Operator Interface

The owner-only CLI keeps the existing command and arguments:

```text
scripts/stage_visual_qc_repair_case.py
```

Changes:

- `--source-package` becomes optional;
- the V3 case-record JSON explicitly supplies `evidence_mode` and
  `supporting_evidence_contexts`;
- `--supporting-file EVIDENCE_ID=PATH` remains the byte-source input;
- a request with neither source packages nor supporting files fails before
  publication;
- a request with no source package must use V3 `supporting_only`;
- V1/V2 requests continue requiring at least one source package;
- compact receipts add `evidence_mode` while retaining package and supporting
  evidence counts.

Milo does not prepare JSON or classify files. Codex assigns stable IDs,
transcribes authorized source wording, runs the command, validates the result,
and reports missing or conflicting facts.

## Storage And Security

Existing controlled-library protections remain mandatory:

- repository-external content-addressed objects;
- exact SHA-256 and byte-size validation;
- stable-file read and source-change detection;
- no hard links, symlinks, junctions, reparse paths, special files, or path
  escapes;
- no-clobber object publication;
- process lock, atomic revision publication, fsync, completion marker, and
  post-publication full validation;
- deterministic idempotent replay and typed conflict failure.

Supporting-only publication must leave no object or revision when contract,
HEIC, context, identity, revision, or storage validation fails.

## Downstream Isolation

No existing consumer may treat supporting-only evidence as physical Visual-QC
evidence.

Specifically:

- source-library audit continues auditing source packages separately;
- physical registration acceptance consumes source packages only;
- qualified handoff consumes accepted source packages only;
- server import, registration, Golden, difference heatmaps, QC, annotation,
  COCO, dataset bundle, and training-image routes remain unchanged;
- repair-evidence links continue requiring the repair case to reference the
  exact source package used by physical evidence, so CASE003/CASE004 cannot
  create such links from supporting-only photographs;
- no browser image route is added for supporting-only objects in this release.

The repair-case manifest and controlled object are the only outputs.

## CASE003 And CASE004 Publication

After implementation, publish two independent V3 revision-1 cases:

- `case-003-bg6-f069`
  - exact board `bg6h-f069` / `BOARD-F069-MAIN-V1.2`;
  - source-reported model `TECNO/BG6`;
  - one exact HEIC supporting object from `IMG_5604.HEIC`;
  - context `repair_in_progress_photo`, `维修中`, `屏蔽罩内局部`;
  - supplied symptom `无法充电`;
  - supplied finding `电源坏` with `claim_status=documented`, meaning only
    that the authorized case record contains the wording;
  - outcome `repair_completed` with source description `维修后已修复` and no
    invented verification description.

- `case-004-bg6-f069`
  - exact board `bg6h-f069` / `BOARD-F069-MAIN-V1.2`;
  - source-reported model `TECNO/BG6`;
  - one exact HEIC supporting object from `IMG_5602.HEIC`;
  - context `repair_in_progress_photo`, `维修中`, `屏蔽罩内局部`;
  - supplied symptom `无法充电`;
  - supplied finding `充电IC烧坏` with `claim_status=documented`, meaning only
    that the authorized case record contains the wording;
  - outcome `repair_completed` with source description `维修后已修复` and no
    invented verification description.

The Base reports repaired outcomes, so the exact available source wording is
stored without inferring how the result was verified. No repair action,
designator, board region, visible burn, or component association is invented.
The unresolved `TECNO/BG6` to `BG6H/BG6h` device-model alias remains governed
by the existing V2 identity rules.

Both cases remain outside Visual QC, Golden, training, repair instruction, and
field-accuracy claims. CASE004's text `充电IC烧坏` must not create a burn
annotation because the image review did not independently show an unambiguous
burn region.

## Tests

### Contract And Schema

- V1/V2 fixtures remain byte-valid under their historical rules.
- V3 package-linked and supporting-only happy paths validate.
- Supporting-only rejects nonempty package links, empty evidence, missing
  contexts, duplicate contexts, dangling contexts, unsupported roles, empty
  source wording, and non-image repair-photo evidence.
- V1/V2 continue rejecting HEIC.
- V3 accepts valid HEIC and rejects extension/content mismatch or invalid
  containers.
- Fixed boundaries, identity derivation, completeness, and exact fields remain
  enforced.

### Library And CLI

- CLI accepts V3 supporting-only without `--source-package`.
- CLI rejects no-evidence requests and V1/V2 no-package requests.
- Exact HEIC bytes, hash, size, MIME, object path, and context survive
  publication and replay.
- Idempotent replay returns the same revision; conflicting bytes fail.
- Source mutation, object corruption, publication failure, lock race, hard
  link, symlink, junction, reparse, and path escape fail closed.
- V3 revision transitions preserve evidence mode and append-only contexts.

### Downstream Boundaries

- Supporting-only cases cannot satisfy physical acceptance or qualified
  handoff inputs.
- Repair-evidence links reject a supporting-only case because it lacks the
  physical source-package link.
- Dataset, COCO, bundle, training-image, Golden, QC, and annotation exports
  remain unchanged and contain no supporting-only evidence.

### Real Evidence Acceptance

- Publish CASE003 and CASE004 into a temporary library first.
- Validate both manifests against the V3 Schema and the full revision loader.
- Compare the stored HEIC hashes and byte sizes with the preserved Feishu
  intake.
- Publish to the controlled library only after temporary acceptance passes.
- Run the controlled-library and repair-case audits.
- Update only the two cases' and two photo rows' Codex status/description
  fields in Feishu, then reread them.

## Non-Goals

- No new Visual-QC capture stage.
- No registration, image-quality verdict, point-map overlay, side inference,
  or component matching.
- No automatic visible-defect detection or annotation.
- No Golden Sample approval or difference heatmap.
- No model training or dataset admission.
- No technician upload or review workflow.
- No server, API, database, browser, production, or deployment change.
