# Visual-QC Repair Case Device Identity V2 Design

**Date:** 2026-07-24  
**Status:** Approved direction; written-spec review pending  
**Owner:** Milo  
**Data operator:** Codex

## Goal

Allow a real repair case to enter the append-only evidence library when its
physical board identity is exact but the source-reported sales-model name is
not yet proven to be a catalog alias.

The first real case exposes this distinction:

- physical and engineering identity: `F069_MAIN_PCB_V1.2`;
- canonical board: `bg6h-f069` / `BOARD-F069-MAIN-V1.2`;
- engineering-source models: `BG6H`, `BG6h`, and project `J6563`;
- source-reported model: `TECNO/BG6`;
- current relationship: unresolved.

The system must preserve all of those facts without asserting that `BG6` is
`BG6H`, without discarding the case, and without weakening board identity.

## Chosen Architecture

Add `VISUAL-QC-REPAIR-CASE-SOURCE-V2`. V1 manifests remain byte-for-byte
immutable and readable. New revisions are written as V2 only when the
device-identity object is needed; no bulk migration is performed.

V2 keeps the V1 top-level board fields and replaces `device_models` with one
exact `device_identity` object:

```json
{
  "reported_models": ["TECNO/BG6"],
  "catalog_models": ["BG6H", "BG6h"],
  "mapping_status": "unresolved_alias",
  "resolved_models": [],
  "resolution_note": null,
  "evidence_refs": [
    {
      "kind": "supporting_evidence",
      "evidence_id": "feishu-case005-source-record"
    }
  ]
}
```

`board_key` and `board_id` remain the canonical physical identity. Device
identity describes model naming only and can never override the board.

## Identity States

`mapping_status` has four values:

- `exact_catalog_match`: every reported model is already a catalog-compatible
  model and `resolved_models` contains those exact values;
- `confirmed_alias`: independent source evidence confirms that one or more
  reported names map to the listed catalog models;
- `unresolved_alias`: the board is exact, but the relationship between
  reported names and catalog models is not proven;
- `conflict`: available evidence contradicts a proposed model mapping.

For `exact_catalog_match` and `confirmed_alias`, `resolved_models` must be a
non-empty subset of `catalog_models`. For `unresolved_alias` and `conflict`,
`resolved_models` must be empty.

`catalog_models` must exactly match the selected board's current catalog
compatibility set in canonical catalog order. It is context, not a claim that
the source-reported device uses every listed model name.

`reported_models` preserves one or more non-empty source strings. The builder
does not normalize case, trim model suffixes, infer aliases, or silently
replace them with catalog values.

## Evidence Rules

An unresolved or conflicting identity requires at least one evidence
reference. CASE005 will reference the privacy-reduced Feishu source snapshot,
which preserves record IDs and exact non-sensitive source wording.

`confirmed_alias` additionally requires a non-empty `resolution_note` and at
least one evidence reference supporting the resolution. Operator belief,
filename similarity, shared board shape, or a matching board revision alone
does not prove a sales-model alias.

`exact_catalog_match` may use an empty evidence list only when each reported
model exactly appears in `catalog_models`. Otherwise it is invalid.

Evidence references use the existing package-entry and supporting-evidence
contracts and must resolve inside the same revision.

## Revision Rules

V1 history remains valid. A case may begin at V2 or move from a V1 head to a
V2 revision while retaining the same board and all prior facts.

Identity progression is append-only:

- `unresolved_alias -> confirmed_alias`;
- `unresolved_alias -> conflict`;
- `conflict -> confirmed_alias` only with a correction record and new
  resolution evidence;
- `exact_catalog_match` and `confirmed_alias` are immutable after publication.

Reported models cannot be removed or rewritten. A later revision may append a
new reported model only when new evidence is added. Catalog models may change
only when the board catalog itself changes and the revision records the new
catalog set; this does not resolve an alias automatically.

Every transition preserves the prior manifest SHA-256. Invalid backward
transitions, silent model replacement, evidence removal, and identity changes
without new context fail closed.

## Builder Input

The owner CLI keeps its existing source-package and supporting-file arguments.
The case-record JSON accepts `device_identity` for V2 instead of
`device_models`.

The CLI derives the manifest version from the case-record identity shape:

- `device_models` only: V1 behavior, unchanged;
- `device_identity` only: V2 behavior;
- both or neither: validation failure.

This preserves existing automation while making the V2 choice explicit.

## Downstream Boundaries

All existing false boundaries remain fixed:

```json
{
  "visual_defect_confirmed": false,
  "golden_approved": false,
  "training_label_allowed": false,
  "repair_instruction_allowed": false,
  "field_accuracy_claim_allowed": false
}
```

V2 adds:

```json
{
  "model_identity_resolved": false
}
```

The value is derived, never supplied:

- `true` for `exact_catalog_match` and `confirmed_alias`;
- `false` for `unresolved_alias` and `conflict`.

An unresolved case may be searched by exact board identity and reviewed as a
repair-case source. It cannot enter model-specific aggregation, model-specific
SOP publication, model training, Golden approval, or repair-action generation.
No existing dataset or server route becomes eligible merely because V2 exists.

## CASE005 Publication

CASE005 will be published as a V2 revision with:

- repair case ID `case-005-bg6-f069`;
- board `bg6h-f069` / `BOARD-F069-MAIN-V1.2`;
- source package `f069-case005-after-source`, role `after_repair`;
- supporting evidence `CASE-005-BG6-feishu-source-record.txt`;
- reported model `TECNO/BG6`;
- catalog models `BG6H` and `BG6h`;
- mapping status `unresolved_alias`;
- reported symptom `不开机`;
- reported finding `EMMC坏` with claim status `reported`;
- reported action wording `已做检测`, without target or inferred action type;
- reported outcome `repair_completed`, with no invented verification;
- all visual, Golden, training, repair-instruction, and field-accuracy
  boundaries false.

The resulting completeness remains `symptom_linked`: the record contains
reported diagnosis/action/outcome wording, but no `documented` finding or
verified repair action.

## Validation

Tests must prove:

- all existing V1 fixtures and revision chains remain valid;
- V2 exact-match, confirmed-alias, unresolved-alias, and conflict manifests
  validate only under their stated invariants;
- catalog models are exact and ordered;
- unresolved identity requires evidence and cannot contain resolved models;
- confirmed aliases require evidence, a note, and catalog-compatible resolved
  models;
- V1-to-V2 revision is accepted without rewriting prior bytes;
- backward or unsupported identity transitions fail;
- source-reported strings cannot be normalized or replaced silently;
- V2 boundaries derive `model_identity_resolved` correctly;
- CASE005 stages idempotently, validates from disk, binds exact source and
  supporting-evidence hashes, and remains excluded from all governed training
  exits;
- strict UTF-8, JSON Schema, compilation, full Python/Node suites, controlled
  source audit, and repository diff checks pass.

## Non-Goals

- Proving that `TECNO/BG6` is `BG6H`.
- Adding `BG6` to the board catalog.
- Inferring a repair action from `EMMC坏` or `已做检测`.
- Confirming a visible EMMC defect from the two after-repair photos.
- Creating a Golden Sample, training label, QC conclusion, or production
  upload.
- Migrating historical V1 manifests merely to use the newer schema.
