# Visual-QC Repair Case Source Design

**Date:** 2026-07-24
**Status:** V1 and V2 implemented locally; first V2 case published

**Owner:** Milo
**Data operator:** Codex

## Goal

Preserve Milo-supplied real repair cases without mixing source-photo identity,
reported repair facts, human visual annotations, or model candidates.

The first release creates a local, append-only case evidence layer:

`immutable photo packages -> repair case revisions -> later acceptance and review`

It must accept complete cases, partial cases, and photo-only collections. Missing
facts remain missing; the system never fills them with inference.

## Existing Boundary

`VISUAL-QC-SOURCE-PACKAGE-V1` remains unchanged. It proves:

- Milo supplied the physical photos;
- board, side, capture stage, session, and setup were explicitly assigned;
- original image bytes are preserved in the controlled library;
- known manual/point-map proxies are rejected;
- the package and its intake manifest are deterministic.

One source package has one capture stage and at most one image per board side.
It is therefore intentionally not a repair-case record and cannot represent the
same side both before and after repair.

## Chosen Architecture

Add `VISUAL-QC-REPAIR-CASE-SOURCE-V1` as a separate contract. One stable
`repair_case_id` has one or more immutable revisions. Each revision:

- identifies one known board from the five-board catalog;
- references one or more validated source packages by exact manifest SHA-256;
- assigns every package a case role;
- preserves supplied case facts and optional supporting-record bytes;
- computes a completeness state without treating completeness as truth;
- links to the previous revision by exact manifest SHA-256.

This avoids changing or re-hashing existing source packages and supports later
case supplementation without overwriting history.

## Implemented V2 Evolution

The V1 design remains the historical baseline: V1 manifests remain immutable and readable.
`VISUAL-QC-REPAIR-CASE-SOURCE-V2` adds explicit device identity
without migrating or rewriting V1 bytes. A V2 revision may preserve
`unresolved_alias` only when the catalog `board_key` and `board_id` are exact
and complete identity evidence is present. Reported models, catalog models, and
resolved models remain separate, so an unresolved source alias is not silently
promoted to a confirmed catalog identity.

Identity status is revision history, not mutable metadata. It progresses
monotonically only through a complete revision with appended evidence. Only
`conflict -> confirmed_alias` requires a new correction record. A resolved
identity is immutable.

## Storage Layout

The case layer lives in the existing repository-external controlled library:

```text
cases/
  <repair_case_id>/
    revisions/
      0001/
        repair-case.json
        .complete
      0002/
        repair-case.json
        .complete
objects/
  case-evidence/
    <sha-prefix>/
      <sha256>.<extension>
```

There is no mutable `latest` file. The valid head is the highest contiguous
revision whose `previous_manifest_sha256` matches the exact prior manifest.
Publication uses the existing lock, temporary-directory, fsync, no-clobber, and
completion-marker patterns.

Symlinks, junctions, reparse paths, hard links, special files, path escapes,
missing revisions, forks, and hash drift fail closed.

## V1 Contract

The manifest has exact top-level fields:

```json
{
  "schema_version": "VISUAL-QC-REPAIR-CASE-SOURCE-V1",
  "repair_case_id": "case-km4-0001",
  "revision": 1,
  "previous_manifest_sha256": null,
  "source_origin": "milo_supplied",
  "board_key": "km4-f151",
  "board_id": "F151",
  "device_models": ["KM4"],
  "package_links": [],
  "supporting_evidence": [],
  "reported_symptoms": [],
  "findings": [],
  "repair_actions": [],
  "outcome": {},
  "corrections": [],
  "completeness": "photos_only",
  "boundaries": {}
}
```

`device_models` contains one or more sales models declared compatible with the
selected catalog board. The builder rejects an empty list, unknown model, or
duplicate model.

### Package Links

Every link contains:

- `package_id`;
- exact `source_package_manifest_sha256`;
- `capture_stage`;
- `role`;
- ordered `entry_ids`.

Allowed roles are:

- `before_repair`;
- `after_repair`;
- `golden_reference`;
- `supplemental`.

The referenced package must validate against the current proxy inventory and
controlled object store. Its board identity, stage, entries, and manifest hash
must exactly match the link. A package may appear only once in one revision.

`golden_reference` is only a source role. It does not grant Golden approval;
the existing explicit Golden review remains authoritative.

### Supporting Evidence

Optional supporting records preserve the exact bytes of repair sheets, PDFs,
spreadsheets, text exports, and screenshots. Each entry contains:

- `evidence_id`;
- original filename;
- MIME type;
- byte size;
- SHA-256;
- content-addressed object path;
- a supplied description.

V1 accepts only PDF, UTF-8 plain text, CSV, XLS, XLSX, PNG, and JPEG supporting
records. A revision may add at most 50 supporting files, each no larger than
100 MiB. Supporting files are stored as opaque regular files. V1 never
executes, extracts, renders, or automatically trusts their contents.
Executable formats, archives, unknown MIME types, empty files, and limit
violations are rejected.

### Evidence References

Every fact-level evidence reference uses one exact shape:

```json
{"kind": "package_entry", "package_id": "pkg-1", "entry_id": "session-main-top"}
```

or:

```json
{"kind": "supporting_evidence", "evidence_id": "repair-sheet-1"}
```

References must resolve within the same revision. Unreferenced evidence is
allowed; dangling or extra reference fields are rejected.

### Reported Symptoms

Each symptom contains:

- `symptom_id`;
- supplied text;
- optional source-side wording or fault code;
- evidence references.

Symptoms are always reported case facts. They do not become a diagnosis.

### Findings

Each finding contains:

- `finding_id`;
- `claim_status`: `reported`, `suspected`, or `documented`;
- supplied description;
- optional defect category;
- optional designator;
- optional board-side and normalized region;
- evidence references.

`documented` means the supplied case record documents the finding. It does not
mean the workbench visually confirmed a defect. A finding with no exact
designator remains board-level; the system does not guess a nearby component.

### Repair Actions

Each action contains:

- `action_id`;
- supplied action description;
- optional action category;
- optional target designator or board region;
- evidence references.

Actions record what the source case says was done. They do not create a repair
instruction or prove causality.

### Outcome

The outcome has:

- `status`: `unknown`, `repair_completed`, `not_repaired`,
  `non_repairable`, or `needs_followup`;
- supplied description;
- optional verification description;
- evidence references.

The outcome object always has the exact fields `status`, `description`,
`verification_description`, and `evidence_refs`. For `unknown`, both
descriptions may be null and evidence references may be empty.

Only Milo-supplied or source-recorded outcomes may be entered. The tool does
not infer success by comparing before/after photos.

### Boundaries

Every revision stores fixed false boundaries:

```json
{
  "visual_defect_confirmed": false,
  "golden_approved": false,
  "training_label_allowed": false,
  "repair_instruction_allowed": false,
  "field_accuracy_claim_allowed": false
}
```

These values cannot be overridden in V1. Existing workbench review, Golden,
dataset, and repair-source gates remain the only authorities that can produce
their respective downstream evidence.

## Completeness

Completeness is deterministically derived:

- `photos_only`: package links exist, but no reported symptom;
- `symptom_linked`: at least one symptom exists;
- `diagnosis_linked`: symptoms exist and at least one finding is `documented`;
- `repair_outcome_linked`: documented finding, repair action, and non-unknown
  outcome all exist.

Completeness reports available context only. It does not change any boundary
and cannot make a case training-eligible.

## Revision Rules

Revision 1 has `previous_manifest_sha256 = null`.

Every later revision must:

- increment the revision by exactly one;
- bind the exact prior manifest SHA-256;
- retain the same case, board, and source origin;
- retain all earlier package links and supporting evidence unchanged;
- retain earlier supplied facts unchanged;
- add new evidence or facts rather than silently editing history.

Incorrect facts are not deleted. A later revision adds an explicit correction
record that names the prior fact ID, explains the correction, and references
its evidence. Consumers show the latest correction while audits retain both.

Each correction has the exact fields:

- `correction_id`;
- `corrects_fact_id`;
- supplied correction text;
- replacement fact ID;
- evidence references.

The corrected and replacement IDs must resolve across the validated revision
chain. A correction cannot target another correction, and one fact cannot have
two active corrections.

For V2, device-identity transitions follow the same append-only rule. The
current identity may only move through a newly published complete revision with
appended evidence. A correction record is optional for other allowed
unresolved transitions and mandatory only for `conflict -> confirmed_alias`.
Historical V1 and V2 manifests are never rewritten, and resolved identity is
immutable.

## First V2 Publication

CASE005 is published in the repository-external controlled library as:

- repair case `case-005-bg6-f069`;
- revision `1`;
- board key `bg6h-f069`;
- board ID `BOARD-F069-MAIN-V1.2`;
- schema `VISUAL-QC-REPAIR-CASE-SOURCE-V2`;
- manifest SHA-256
  `85c8c64cb97cf1ea1e567e4d1f7fc62ec00ebf02719939c74a5e0faf46298177`;
- identity status `unresolved_alias`;
- `model_identity_resolved=false`;
- completeness `symptom_linked`;
- source-reported model `TECNO/BG6`;
- catalog models `BG6H/BG6h`.

The exact F069 V1.2 board identity is supported, but the source and catalog
model labels are not forcibly normalized. This publication records supplied
repair facts only. It is not visual diagnosis evidence, not confirmed defect evidence, not Golden Sample evidence, not training label evidence, not repair causality evidence, and not field accuracy evidence.

## Operator Flow

Add `scripts/stage_visual_qc_repair_case.py`.

Codex, not Milo, runs it. Inputs are:

- controlled library root;
- repair case ID;
- board key;
- one or more role-to-source-package paths;
- a UTF-8 case-record JSON file;
- optional supporting files;
- optional previous case manifest for an amendment.

The command:

1. validates every referenced source package;
2. hashes and stores allowed supporting records;
3. validates supplied facts and evidence references;
4. computes completeness and fixed boundaries;
5. validates the prior revision chain;
6. publishes one immutable revision atomically;
7. reopens and fully validates the published revision;
8. prints a compact typed receipt.

Validation failures publish no revision and do not modify prior evidence.
Re-running the exact request returns the existing revision; conflicting content
fails with a typed no-clobber error.

## Downstream Boundary

V1 and V2 are local only. They do not modify:

- `VISUAL-QC-SOURCE-PACKAGE-V1`;
- physical acceptance reports;
- qualified handoff;
- server SQLite or API contracts;
- browser workbench;
- Golden, annotation, QC, or dataset rules.

After the first real case is staged and audited, a separate design may bind the
case manifest SHA-256 into physical acceptance and controlled handoff. That
decision must be based on the actual material shape rather than proxy fixtures.

Production remains `f278061`. Publishing CASE005 did not change the server,
API, database, browser workbench, or production environment.

## Validation

### Contract Tests

- exact fields and Schema validity;
- all four completeness states;
- fixed false boundaries;
- invalid IDs, statuses, roles, MIME types, sizes, and references;
- board/package identity mismatch;
- package manifest hash drift;
- duplicated package, evidence, or fact IDs.

### Storage Tests

- content-addressed supporting objects;
- source and supporting-file immutability;
- no overwrite and idempotent replay;
- process-lock race;
- atomic failure cleanup;
- symlink, junction, reparse, hard-link, and path-escape rejection;
- revision gaps, forks, wrong prior hash, and historical mutation.

### Integration Tests

- photo-only case from one source package;
- before/after case from two source packages;
- partial case amended to a documented repair outcome;
- known proxy or revoked source rejected through referenced package validation;
- case facts never enter annotation, Golden, QC, COCO, bundle, or training
  exports.

### Real Evidence Gate

The first real case must provide enough information to assign:

- known board key and board side;
- original source image files;
- package role for each photo set;
- any supplied symptom, finding, action, and outcome text;
- supporting records, if present.

Codex performs the assignments and reports missing fields. Milo does not need
to identify components or prepare JSON.

No registration-accuracy, visible-defect, Golden, repair-causality, or training
claim is allowed until the corresponding existing review gate is completed on
the real evidence.
