# Visual QC Upgrade Preflight Design

## Status

Approved for implementation on 2026-07-23. This design adds a read-only
upgrade rehearsal and a fail-closed deployment gate. It does not authorize or
perform a production deployment.

## Purpose

Production remains at `f278061`, while Local HEAD adds acceptance-qualified
handoff provenance, Create/Get V2, Admin List V2, Admin Detail V3, and removal
of direct browser upload. The existing deployment script backs up SQLite and
rolls back on failure, but its preflight checks only host resources and service
presence. It does not prove that the current production database can migrate
to the candidate runtime without data loss or that the old runtime can read a
post-migration database during rollback.

The upgrade preflight closes that gap by rehearsing the candidate migration on
a consistent SQLite backup. The original database and managed image objects
remain read-only.

## Command Contract

`scripts/audit_visual_qc_upgrade.py` accepts:

- `--source-database`: a consistent SQLite snapshot to rehearse;
- `--source-data-root`: the Visual-QC object root used to validate referenced
  originals and artifacts;
- `--source-app-root`: the currently deployed application, including `VERSION`
  and its rollback `store.py`;
- `--target-version`: the exact candidate Git commit written to candidate
  `VERSION`;
- `--output`: a new JSON report path outside the source data root.

The source application's `VERSION` must be in the candidate's explicit
compatibility allowlist. The first allowlisted version is `f278061`.

CLI exit codes are:

- `0`: every preflight check passed;
- `1`: a complete report was generated and at least one compatibility,
  integrity, migration, object, API, training-gate, or rollback check failed;
- `2`: arguments are invalid, a controlled path is unsafe, the report cannot
  be published, or the preflight cannot complete.

## Read-Only And Snapshot Semantics

The tool opens the supplied source database with SQLite URI `mode=ro`, runs
`PRAGMA integrity_check`, and uses the SQLite backup API to create a temporary
working database. It never opens the source through `VisualQcStore`, never
changes source pragmas, and never writes beside the source database.

Before and after the run, tests prove byte-identical source database, WAL/SHM
companions, and referenced object files. The report binds:

- the SHA-256 of the consistent pre-migration backup;
- a deterministic logical digest of every user table and row;
- per-table row counts;
- every referenced original and artifact SHA-256;
- source version and target version.

Temporary migration and smoke-test files are created outside the source data
root and removed after report construction. The final report is atomically
published with no overwrite.

## Migration Contract

The candidate `VisualQcStore` migrates only the temporary database. Preflight
compares the before and after schemas and row projections:

- no source table or source column may disappear;
- values in every pre-existing column must remain byte-equivalent;
- row counts and shared-column logical digests must remain equal;
- only allowlisted additive columns may appear;
- for `f278061`, the only allowed addition is
  `cases.qualified_handoff_json`;
- the added provenance column must be nullable and every legacy row must remain
  `NULL`.

Both pre- and post-migration databases must pass `PRAGMA integrity_check`.

## Object Contract

Every `images.storage_path` and `artifacts.storage_path` row is checked against
the canonical content-addressed path derived from its stored SHA-256 and MIME
type. The canonical file must remain inside `source-data-root`, exist as a
regular non-reparse file, have the expected byte size, and match the expected
SHA-256. Missing, escaping, malformed, or changed objects fail the preflight.

The tool does not inspect or classify image content.

## Candidate Runtime Smoke

The candidate service starts in-process with zero workers and the migrated
temporary database. It must prove:

- Health schema `VISUAL-QC-SERVER-HEALTH-V2`;
- Admin List schema `VISUAL-QC-ADMIN-CASE-LIST-V2`;
- Admin Detail schema `VISUAL-QC-SERVER-CASE-V3` for every existing case;
- Dataset Audit schema `VISUAL-QC-DATASET-AUDIT-V1`;
- total case counts agree across the database, list, health, and dataset audit;
- every legacy physical case without qualified handoff provenance remains
  excluded with `qualified_handoff_provenance_required`;
- every non-physical proxy case remains excluded with
  `non_physical_evidence`.

No worker, upload, review, Golden Sample, defect decision, or training export is
created.

## Rollback Runtime Smoke

The currently deployed `scripts/visual_qc/server/store.py` is loaded from
`source-app-root` under an isolated module name and is pointed only at a second
copy of the migrated temporary database. It must initialize successfully,
return operational counts equal to the candidate runtime, and read every
existing case. This proves the deployed rollback store tolerates the additive
candidate schema without modifying production.

## Report Contract

`VISUAL-QC-UPGRADE-PREFLIGHT-V1` contains:

- `schema_version`, `status`, and `generated_at`;
- source and target version identities;
- source snapshot SHA-256 and logical digest;
- table and object counts;
- ordered checks with stable ids, statuses, error codes, and messages;
- migration additions and preservation digests;
- candidate API schema evidence;
- dataset-gate evidence;
- rollback smoke evidence.

The report contains no credentials and no absolute source paths. Check ordering
is deterministic. A JSON Schema in `knowledge-base/` validates every completed
report.

## Deployment Gate

After the standalone tool is verified, `deploy-visual-qc-pilot.ps1` invokes it
after the Visual-QC service is quiesced and after the consistent rollback
database snapshot exists, but before application or runtime links are switched.
The candidate tool reads the snapshot, current app, and persistent object root.

Deployment continues only when:

- the command exits `0`;
- the report status is `passed`;
- report source snapshot SHA-256 matches the rollback snapshot;
- report target version matches the candidate `VERSION`.

Any failure enters the existing rollback path and restarts the unchanged
production application. The successful report remains in the commit-versioned
rollback directory as deployment evidence.

## Verification Boundary

P0/P1 cover deterministic snapshots, migration preservation, object integrity,
candidate schemas, dataset gates, rollback compatibility, CLI codes, atomic
publication, and deployment-script enforcement. P2 covers Python compilation,
JSON Schema validation, PowerShell parsing/static contract tests, and full
Python/Node regressions.

No UI changes occur, so P3 is not required. P4 is limited to a local
production-like rehearsal built from the exact `f278061` store contract and a
synthetic production snapshot. No SSH, production database read, upload,
service restart, or deployment occurs without separate approval.
