# Visual-QC Deployment Manifest Design

## Purpose

Bind every Visual-QC deployment rehearsal and runtime switch to both:

1. the exact 40-character Git commit selected locally; and
2. the exact runtime archive bytes received by the controlled server.

The existing upgrade preflight proves database and runtime compatibility, but
its seven-character target version does not prove which archive was uploaded.
This design closes that identity gap without introducing a signing
infrastructure or changing the production deployment in this development
phase.

## Decision

Use a deterministic, versioned deployment manifest:

```json
{
  "schema_version": "VISUAL-QC-DEPLOYMENT-MANIFEST-V1",
  "commit_sha": "40 lowercase hexadecimal characters",
  "archive_sha256": "64 lowercase hexadecimal characters",
  "archive_bytes": 123456,
  "runtime_manifest_sha256": "64 lowercase hexadecimal characters",
  "runtime_path_count": 12
}
```

The manifest contains no timestamp, local path, username, hostname, or
credential. Given the same commit, runtime path list, and archive bytes, its
content is deterministic.

## Local Packaging

`scripts/deploy-visual-qc-pilot.ps1` must:

1. require a clean Git worktree;
2. resolve `HEAD` to the full 40-character lowercase commit;
3. validate the bounded runtime path list;
4. build `app.tar.gz` with `git archive`;
5. compute the archive SHA-256 and exact byte count;
6. compute the raw SHA-256 of
   `deploy/visual-qc-runtime-files.txt`;
7. write `deployment-manifest.json` as UTF-8 without BOM;
8. upload the archive and manifest as immutable deployment inputs.

The short commit may still be used in human-readable temporary directory
names. It cannot be used as the identity in `VERSION`, the upgrade report, or
manifest verification.

## Server Verification

Before extraction, the remote deployment script must parse the uploaded
manifest with the server's preflight-verified system Python 3 standard library
and require:

- the exact V1 schema version;
- exactly the six reviewed keys and no extras;
- a full 40-character lowercase commit;
- valid lowercase SHA-256 values;
- positive archive byte size and runtime path count;
- commit equality with the full commit embedded by the local deployment
  script;
- archive byte-size equality;
- archive SHA-256 equality.

Only after those checks pass may the server extract the archive. Immediately
after extraction it must verify:

- the extracted runtime manifest hash equals
  `runtime_manifest_sha256`;
- the normalized non-comment path count equals `runtime_path_count`;
- every normalized runtime path exists inside the extracted application root;
- `VERSION` is written with the full commit.

The existing deployment lock, staged-input cleanup, rollback, and no-production
deployment boundary remain unchanged.

## Upgrade Preflight Binding

`VISUAL-QC-UPGRADE-PREFLIGHT-V1` gains immutable target evidence:

```json
{
  "target": {
    "version": "full 40-character commit",
    "archive_sha256": "uploaded archive SHA-256",
    "archive_bytes": 123456,
    "runtime_manifest_sha256": "runtime manifest SHA-256"
  }
}
```

The standalone CLI requires these values explicitly. The deployment script
passes values read from the already verified deployment manifest. The
post-report verifier requires all four values to equal the deployment
manifest before any application or virtualenv switch.

The preflight does not claim to cryptographically sign the archive. It proves
that one locally produced manifest, one remotely received archive, one
extracted runtime, and one migration rehearsal share the same identity.

## Failure Behavior

- Missing, malformed, duplicated, or extra manifest fields: fail before
  extraction.
- Archive hash or size mismatch: fail before extraction.
- Extracted runtime manifest hash, path count, or path mismatch: fail before
  database rehearsal.
- Upgrade report target mismatch: fail before application or virtualenv
  switch.
- A failure before the candidate QC runtime can open the live database must
  not restore or replace that untouched database.

No fallback to a short commit, absent manifest, or unverified archive is
allowed.

## Tests

### Deployment Contract

- full commit is used for deployment identity;
- local manifest contains the exact archive evidence;
- archive and manifest are both uploaded;
- remote verification occurs before `tar -xzf`;
- extracted runtime boundary verification occurs before upgrade rehearsal;
- upgrade report checks all target evidence before app switching;
- malformed or mismatched evidence fails closed;
- preflight failure retains the existing no-database-overwrite guarantee.

### Upgrade Contract

- the CLI rejects short target commits;
- target archive and runtime-manifest hashes require 64 lowercase hex;
- archive byte size must be positive;
- report Schema requires the complete target evidence;
- exact `f278061` rollback rehearsal remains readable and source-immutable.

### Regression

- focused deployment/preflight tests;
- full Python and Node suites;
- PowerShell parser, Python compilation, JSON parsing, `git diff --check`,
  and strict UTF-8/U+FFFD checks;
- a local exact-version rehearsal bound to a real generated runtime archive.

P3 browser QA is not required because this change has no visible UI. No
production connection or deployment is part of implementation acceptance.

## Deferred Work

Digital signing, CI provenance attestations, corporate key management, and
reproducible gzip byte-for-byte builds are deferred until the deployment
channel moves into managed CI/CD. The V1 manifest is intentionally compatible
with adding a signature envelope later without weakening the current checks.
