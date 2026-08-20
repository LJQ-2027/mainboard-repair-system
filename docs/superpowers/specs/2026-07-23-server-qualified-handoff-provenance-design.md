# Server Qualified-Handoff Provenance Design

## Purpose

Persist the minimum trustworthy provenance needed to prove why a physical image was admitted to the controlled Visual-QC server. The server stores immutable hashes and admission semantics only. The complete local acceptance report, registration overlays, controlled-library paths, and source-package contents remain outside the server.

This increment connects `VISUAL-QC-PHYSICAL-HANDOFF-V1` to the server case record without changing the meaning of any downstream review:

- admission means the local physical-evidence gate allowed transfer;
- registration remains unreviewed until the existing server review is completed;
- Golden Sample approval remains a separate server action;
- defect and repair conclusions remain absent until their existing review steps complete;
- `field_accuracy_claim_allowed` remains `false`.

## Chosen Approach

Add one compact multipart JSON field named `qualified_handoff` to physical case creation. Its normalized contract is `VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1`:

```json
{
  "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
  "handoff_schema_version": "VISUAL-QC-PHYSICAL-HANDOFF-V1",
  "source_package_manifest_sha256": "<lowercase sha256>",
  "archived_intake_manifest_sha256": "<lowercase sha256>",
  "acceptance_report_sha256": "<lowercase sha256>",
  "acceptance_action": "automatic_candidate_review_required",
  "registration_review_required": true,
  "field_accuracy_claim_allowed": false
}
```

`acceptance_action` also permits `manual_registration_required`. Additional properties are rejected. The server does not receive the referenced documents or overlays and does not claim to re-run their local validation. It records the exact normalized assertion submitted by the already validated handoff command.

Alternatives rejected:

- Uploading the full report and overlays would duplicate controlled local evidence, increase storage and privacy exposure, and create a second apparent source of truth.
- Storing only an opaque handoff id would not bind the server case to the exact source package, archived intake, and acceptance report.
- Leaving provenance only in local receipts would make server review, audit, and dataset export unable to prove why physical bytes entered the system.

## Admission Rules

All newly created `physical_capture` cases must provide:

- `intake_batch_id` and `intake_entry_id`;
- valid `qualified_handoff` provenance;
- the existing image SHA-256 and capture identity.

The API rejects a physical upload when either the intake identity or qualified provenance is absent. `proxy_reference` and other nonphysical evidence roles must omit `qualified_handoff`; they cannot inherit physical-evidence status by supplying hashes.

The dedicated physical handoff command is the only supported producer in this increment. It builds one provenance object per entry from the already validated in-memory evidence and passes it through the existing resumable intake transport. The generic importer may carry the optional object but may not synthesize or weaken it.

Existing database rows are not backfilled and remain readable with `qualified_handoff: null`. This is historical compatibility, not permission for a new unqualified physical upload. Existing local or browser code that attempts direct physical upload will receive a typed admission error and must use the controlled handoff path.

## Persistence And Idempotency

Add a nullable `qualified_handoff_json` column to `cases` through the existing startup compatibility migration. New writes serialize the normalized object with sorted keys and compact separators. Legacy rows remain null.

The normalized provenance object enters the case request fingerprint. Reusing an idempotency key with a changed package hash, intake hash, report hash, action, schema version, or semantic boundary returns the existing idempotency conflict instead of silently changing provenance.

The `(actor_id, intake_batch_id, intake_entry_id)` uniqueness rule remains authoritative for source-entry deduplication. A repeated entry can resolve to its existing case only when the existing request fingerprint, including qualified provenance, is identical.

The `case_created` audit event stores the same compact object alongside intake identity. It stores no credentials, paths, source pixels, reports, or overlays.

## Response Contracts

Avoid mutating an existing versioned payload under the same schema identifier:

- standard create/get case responses advance from `VISUAL-QC-SERVER-CASE-V1` to `VISUAL-QC-SERVER-CASE-V2`;
- admin case detail advances from `VISUAL-QC-SERVER-CASE-V2` to `VISUAL-QC-SERVER-CASE-V3`;
- admin case list advances from `VISUAL-QC-ADMIN-CASE-LIST-V1` to `VISUAL-QC-ADMIN-CASE-LIST-V2`.

Each case representation includes `qualified_handoff`, either the normalized object or `null`. The server workbench accepts the new admin detail version and restores the same object into local server-sync metadata for traceability. It does not display or interpret admission as review approval.

Training manifest and audit logic read the persisted provenance directly. New physical cases without non-null qualified provenance are ineligible by construction; legacy physical rows remain excluded until a separate explicit migration policy exists. Dataset output may include the compact provenance for traceability but must not turn its hashes or actions into defect labels.

## Failure Semantics

Malformed JSON, unknown fields, invalid lowercase SHA-256 values, unsupported schema versions, invalid actions, or false semantic constants return a typed `invalid_qualified_handoff` error before image storage.

Missing physical provenance returns `physical_handoff_provenance_required`. Provenance supplied for nonphysical evidence returns `qualified_handoff_not_allowed`. Partial intake identity continues to return `incomplete_intake_provenance`.

The local handoff fails before network transfer if it cannot construct the exact per-entry provenance. A server rejection is written to the existing intake and physical-handoff receipts as a transfer error; it never changes local acceptance evidence.

## Security And Fact Boundaries

Hashes establish identity bindings, not the truth of image content. The server trusts the authenticated data-admin route and the validated local producer for admission, while retaining server-side registration and QC review gates.

No server endpoint is added for downloading an acceptance report or overlay because those bodies are never uploaded. No technician upload control is introduced. The existing controlled-server authentication, HTTPS requirement, actor identity, retention, and audit boundaries remain in force.

Production data already stored at the deployed revision is untouched. Deployment requires a separate migration and compatibility decision after local tests pass; this design does not authorize a production deploy or upload real evidence.

## Verification

TDD coverage will prove:

- strict normalization for both allowed actions and every malformed/extra-field case;
- rejection of unqualified physical uploads and qualified nonphysical uploads;
- compatibility migration with null provenance on legacy rows;
- request-fingerprint conflicts for every provenance drift;
- exact round-trip through create/get, admin list/detail, and audit payloads;
- resumable physical handoff transport sends per-entry hashes and action from validated evidence;
- retries reconstruct identical multipart provenance and reconcile the same server case;
- training audit excludes legacy or otherwise unqualified physical cases;
- no report body, overlay bytes, absolute path, or credential appears in the database or API response.

Regression includes the complete Python and Node suites, Python compilation, JSON parsing, UTF-8/U+FFFD checks, and `git diff --check`. API and workbench contract changes require local browser restoration/interaction checks. Production P4 remains a declared gap until deployment is separately approved, and physical accuracy remains gated on real KM4/F151 bare-board photos.
