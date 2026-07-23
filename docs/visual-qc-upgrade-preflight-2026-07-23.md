# Visual-QC Upgrade Preflight

## Purpose

`scripts/audit_visual_qc_upgrade.py` proves that one consistent Visual-QC
SQLite snapshot and its managed objects can move from the currently deployed
runtime to a candidate runtime without changing legacy data or breaking
rollback.

The command is an internal deployment-safety tool. It does not upload photos,
change a review, create a Golden Sample, export training data, restart a
service, or deploy the candidate.

## Required Inputs

- a consistent SQLite backup with no `-wal` or `-shm` companion;
- the persistent Visual-QC data root containing canonical managed objects;
- the currently deployed app root containing `VERSION` and its original
  `scripts/visual_qc/server/store.py`;
- the exact candidate Git commit;
- a new report path outside the source data root.

The first reviewed source version is production `f278061`. A different source
version is rejected until its exact migration and rollback contract is added
and tested.

Do not point the command at a database that is still being written. The
deployment script stops only the Visual-QC process and uses SQLite backup
before invoking the preflight.

## Standalone Command

```powershell
.\.venv\Scripts\python.exe scripts\audit_visual_qc_upgrade.py `
  --source-database D:\visual-qc-upgrade\visual-qc.sqlite3 `
  --source-data-root D:\visual-qc-data `
  --source-app-root D:\visual-qc-current-app `
  --target-version 908a872 `
  --output D:\visual-qc-upgrade\upgrade-preflight.json
```

Exit codes:

- `0`: the complete report is `passed`;
- `1`: the report was published but one or more gates failed;
- `2`: the input, path, runtime, or report publication was invalid.

Reports are no-overwrite and atomically published. The command refuses output
inside the source data root or through a symlink/Windows reparse parent.

## Ten Gates

`VISUAL-QC-UPGRADE-PREFLIGHT-V1` records these ordered checks:

1. source version is explicitly supported;
2. source SQLite integrity passes;
3. every referenced original and artifact matches its canonical path, size,
   and SHA-256;
4. migrated SQLite integrity passes;
5. migration is limited to the reviewed additive schema;
6. every legacy shared-column value is unchanged;
7. Health V2, Admin List V2, Admin Detail V3, and Dataset Audit V1 are readable
   from the candidate runtime;
8. proxy evidence and legacy physical evidence without qualified handoff
   remain excluded from training;
9. the old deployed store can initialize and read every case from a second
   candidate-migrated copy;
10. the supplied database and managed objects remain byte-identical throughout
    the run.

For `f278061`, the only accepted schema change is nullable
`cases.qualified_handoff_json`; every legacy row must keep `NULL` in that
column.

## Deployment Enforcement

An actual `scripts/deploy-visual-qc-pilot.ps1` run now performs the same
rehearsal after it has:

1. staged the candidate app and isolated virtualenv;
2. stopped `motherboard-repair-visual-qc`;
3. created the consistent rollback SQLite snapshot.

It does this before moving the old app directory or switching
`venv-visual-qc`. Deployment continues only when:

- report status is `passed`;
- `source.snapshot_sha256` equals the exact rollback database SHA-256;
- `target.version` equals the candidate commit.

The report remains at
`rollback/<deploy-id>/upgrade-preflight.json`. Any failure enters the existing
database, app, virtualenv, gateway, and service rollback path.

`-PreflightOnly` remains a host-level read-only check and does not stage the
candidate or rehearse a migration.

## 2026-07-23 Local Evidence

The implementation was rehearsed locally against the exact
`f278061:scripts/visual_qc/server/store.py`, a production-shape proxy case, and
canonical original/artifact objects. All ten checks passed, the old store read
the candidate-migrated case, and source bytes remained unchanged.

The local evidence report is under
`.local/upgrade-preflight-rehearsal/f278061-to-local-head.json` and is not a
production report. No SSH, server read, upload, restart, or deployment was
performed. Production remains `f278061`.
