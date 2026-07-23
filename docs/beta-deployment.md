# Motherboard Repair Beta Deployment

This project is deployed as an isolated beta service on the same server used by CSAT.

## Current Operating Model

Milo is the only source of real visual photos. Codex is the data administrator for batch intake, registration correction, visible-defect annotation, Golden Sample management, and governed export. Overseas technicians do not upload visual photos and do not enter the internal visual data workbench. The gateway role string `reviewer` remains only as a wire-compatible identifier for data-administrator permissions.

## Isolation Rules

- Remote directory: `/opt/motherboard-repair-beta`
- Loopback static/AI service port: `3010`
- Loopback visual-QC API port: `3020`
- PM2 process name: `motherboard-repair-beta`
- Env file: `/opt/motherboard-repair-beta/app/.env`
- Do not reuse the CSAT directory, port, PM2 process, database, upload directory, or env file.

## Deploy

```powershell
.\scripts\deploy-beta.ps1 `
  -KeyPath "C:\Users\Mercurluto\OneDrive\AI\90_Meta\Sensitive\Milo.pem"
```

The script packages the current Git `HEAD`, uploads it to the server, preserves the remote `.env`, replaces only `/opt/motherboard-repair-beta/app`, restarts PM2, and checks:

- `http://127.0.0.1:3010/health`
- `http://127.0.0.1:3010/`
- PM2 process status

The visual-QC pilot deploy uses `deploy/visual-qc-runtime-files.txt` as a
reviewed runtime allowlist. It includes the internal visual data workbench, five-board assets,
knowledge data, API/worker code, and maintenance validators while excluding raw
source archives, tests, reports, output, and documentation. The 2026-07-21
archive smoke reduced the package from about 197 MB to 52.4 MB with 305 tracked
entries and all required runtime files present. The first production deployment
through this allowlist completed in about 194 seconds versus about 808 seconds
for the preceding full-repository deployment, while preserving the existing
case database and serving the workbench, KM4 atlas, and training manifest.

## Runtime

The Python service serves both:

- Frontend page: `/`
- AI API: `/api/chat`
- Health check: `/health`

The frontend defaults to the current origin when opened through HTTP/HTTPS, so beta users do not need to configure `localhost`.

## First-Time Server Setup

After the first deploy, configure:

```bash
cd /opt/motherboard-repair-beta/app
vim .env
pm2 restart motherboard-repair-beta --update-env
```

Required variable:

```bash
ANTHROPIC_API_KEY=...
```

`PORT`, `STATIC_ROOT`, and `INDEX_FILE` are supplied by the deploy script / PM2 environment.

## Current Deployment

- Deployed on: 2026-07-22
- Deployed commit: `f278061`
- Internal service: `http://127.0.0.1:3010`
- Internal visual-QC API: `http://127.0.0.1:3020`
- External beta URL: `https://cccsat.top/mb-repair-beta/`
- Health URL: `https://cccsat.top/mb-repair-beta/health`
- Visual-QC workbench:
  `https://cccsat.top/mb-repair-beta/assets/visual-qc-workbench/`
- PM2 processes: `motherboard-repair-beta` and
  `motherboard-repair-visual-qc`
- Access control: per-user Nginx Basic Auth with gateway-owned actor headers
- Nginx config touched: `/etc/nginx/sites-available/sikayetvar`
- Nginx config backup: `/etc/nginx/sites-available/sikayetvar.before-mb-repair-20260622_095918`
- Current AI status: service is reachable, but `.env` still has no valid `ANTHROPIC_API_KEY`, so AI features are not enabled yet.
- 2026-07-22 owner-managed intake increment: Milo is the sole source of real
  visual photos and Codex operates the data-administrator path. Production now
  enforces data-administrator-only multipart intake before parsing, accepts
  validated batch/entry provenance, exposes the actor-scoped admin case
  catalog/detail/original routes, and restores a server case into the existing
  canvas workflow. The internal workbench hides every intake, Golden, catalog,
  local export, and dataset control from the restricted role; the API returned
  `403 data_admin_role_required` for a restricted multipart request.
- Production P4 at `f278061` reports one worker, one preserved succeeded proxy
  case, zero Golden Samples, and normal storage pressure. The legacy KM4 manual
  proxy was transactionally reassigned from the historical restricted actor to
  the current data administrator after a SQLite backup at
  `/opt/motherboard-repair-beta/data/visual-qc/visual-qc.sqlite3.before-owner-admin-actor-migration-20260722_104119`.
  Its evidence remains `service_manual_proxy`, registration remains
  `manual_registration_required`, and both intake provenance fields remain
  null. Dataset audit remains `0` eligible, `1` excluded, with
  `non_physical_evidence: 1`; repeated dataset ZIPs remain byte-identical.
- Production headed-Chrome QA at 1440x1000 and 390x844 restored the proxy
  original from the server catalog, rendered both canvases, and reported no
  horizontal overflow or console warnings/errors. The restricted production
  identity displayed the read-only surface with all visual-data controls
  hidden. Screenshots are retained locally under
  `output/playwright/owner-managed-intake/` and are not deployment inputs.
- Latest P4 evidence: desktop and 390px workbench paths render with no fresh
  console errors or horizontal overflow; restricted/data-administrator wire roles pass through
  the HTTPS gateway; forged actor headers are overwritten; PM2 restart retains
  the persisted proxy case and completed registration job.

The increment records below are historical deployment evidence. Their `technician` and `reviewer` labels describe the gateway wire roles tested at that time, not the current photo ownership or staffing model.
- 2026-07-20 capture-intake increment: the authenticated production route
  exposes the compact physical-capture panel and actor-scoped capture-session
  API. Same-board front/back pairing, the three capture confirmations,
  transaction-level session identity protection, and Golden/training gates are
  deployed. An authenticated no-write smoke returned the expected technician
  identity and typed `capture_session_not_found` response from the new API.
- 2026-07-21 final-QC increment: physical cases can persist append-only final
  human QC review versions. The reviewer-only training manifest and eligible
  original-image routes are deployed. Independent P4 checks returned page 200,
  technician `403 reviewer_role_required`, reviewer
  `VISUAL-QC-TRAINING-MANIFEST-V1` with zero eligible cases, and typed
  `404 training_image_not_found` for an unknown image. The empty manifest is
  expected because the only stored case is proxy evidence.
- 2026-07-21 governed COCO increment: the reviewer-only
  `VISUAL-QC-COCO-V1` route deterministically derives images and confirmed
  human annotations from the eligible training manifest. The reviewer
  workbench displays server-owned case, annotation, and category totals and
  downloads both JSON contracts; technicians do not see this panel and the
  API independently returns `403 reviewer_role_required`. Production P4 at
  `508cddb` returned an empty but schema-valid dataset with nine fixed
  categories and byte-identical repeated responses. Headed Chrome QA passed
  desktop and 390 px layouts, both downloads, no horizontal overflow, and
  zero console warnings or errors.
- 2026-07-21 dataset-readiness increment: reviewer-only
  `VISUAL-QC-DATASET-AUDIT-V1` reports one ordered primary gate reason per
  server case without exposing actor identity. Production contains one known
  KM4 manual proxy and now reports `0` eligible, `1` excluded, and
  `non_physical_evidence: 1`; technicians receive 403 and do not see the
  workbench audit fields. The legacy P4 case had been stored with the obsolete
  physical role despite its empty checklist; it was corrected transactionally
  in both case and capture-session rows after a SQLite backup at
  `/opt/motherboard-repair-beta/data/visual-qc/visual-qc.sqlite3.before-proxy-role-fix-20260721_134220`.
  Commit `7b46333` adds a default-collapsed reviewer drill-down listing the
  excluded board, side, case suffix, and primary blocker. Production Chrome
  verified keyboard focus, expanded desktop and 390 px states, zero overflow,
  intact download controls, and zero console warnings/errors.
- 2026-07-21 complete-dataset increment: reviewer-only
  `GET /datasets/bundle` returns a deterministic ZIP containing the governed
  manifest, COCO annotations, `VISUAL-QC-DATASET-BUNDLE-V1` index, and every
  eligible original under a stable case-derived path. Each original is checked
  against its stored SHA-256 before packaging; the response removes its
  temporary server file afterward. Production at `1f07b4a` returned technician
  403 and reviewer 200, with byte-identical repeated ZIPs. The current empty
  eligible set correctly produced three JSON entries, zero images/annotations,
  and nine COCO categories. Headed Chrome verified the download, keyboard focus,
  1440 px and 390 px two-column controls, no overflow, and zero console warnings
  or errors.
- Proxy evidence: one KM4 reviewed manual image was accepted as a proxy case,
  scored `usable`, and correctly fell back to manual four-point registration
  after ORB/AKAZE evidence failed the inlier gate. It is not physical-board
  accuracy evidence.

## Approved Visual-QC Evolution

The beta server remains the controlled host for the internal visual data workbench. Milo is the only physical-photo source, and Codex is the only data operator. New physical cases may enter only through the acceptance-qualified handoff CLI after local source audit and physical acceptance; the browser restores existing server cases and does not upload new physical captures. The approved architecture provides a same-origin QC API, persisted image-processing jobs, controlled image storage, one or two CPU OpenCV workers, Golden Sample management, and candidate confirmation/rejection.

The server was inspected read-only on 2026-07-20: 4 x86_64 vCPU, 7.3 GB RAM, 4 GB swap, 19 GB free disk, Python 3.10, Node.js 20, no GPU, no installed OpenCV, and no active PostgreSQL or Redis. This supports a bounded CPU pilot, not deep-model training or unrestricted long-term image retention.

The bounded visual-QC pilot is deployed with the approved same-origin
architecture at production revision `f278061`. Its original controlled upload,
async processing, manual fallback, role assertion,
loopback binding, restart recovery, storage health, and proxy-path smoke checks
have passed. The later acceptance-qualified handoff and server-provenance
hardening are complete locally but are not yet deployed. Physical bare-board photos, reviewed Golden Samples, and
real-defect acceptance remain the field-readiness gate. Canonical design:
`docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`.

### 2026-07-20 P4 Preflight

Read-only inspection initially confirmed that `/mb-repair-beta/` had no
authentication or verified user-header injection. The 2026-07-20 deployment
closed that gate and installed the isolated Python 3.10 visual-QC runtime.

The bounded pilot deployment therefore adds:

- per-user Nginx Basic Auth around the complete beta route;
- `$remote_user` as the gateway-owned `X-Actor-Id`;
- a server-owned data-administrator map that emits the compatibility role `reviewer` and otherwise fails closed to `technician`;
- removal of client `Authorization` before proxying;
- a loopback-only static/AI process on `127.0.0.1:3010`;
- a loopback-only QC process on `127.0.0.1:3020`;
- a commit-versioned QC runtime behind the stable
  `/opt/motherboard-repair-beta/venv-visual-qc` symlink;
- persistent data outside the replaceable app directory;
- Nginx, PM2, internal health, authenticated restricted/data-administrator wire identities,
  forged-header rejection, and unauthenticated-401 checks;
- consistent SQLite backup plus automatic application, runtime, database, and
  gateway rollback on deployment failure.
- a candidate-owned `VISUAL-QC-UPGRADE-PREFLIGHT-V1` rehearsal after the
  Visual-QC process is stopped and the rollback SQLite snapshot is complete,
  but before the application directory or virtualenv link is switched;
- exact binding between the rollback database SHA-256, the rehearsal report,
  the full candidate Git commit, the uploaded runtime archive SHA-256 and byte
  size, and the runtime path-manifest SHA-256. Migration, object-integrity,
  Local HEAD API, dataset-gate, full SQLite schema, and old-runtime rollback
  checks must all pass.
- `VISUAL-QC-DEPLOYMENT-MANIFEST-V1` is built locally without timestamps or
  workstation identity, uploaded beside `app.tar.gz`, and validated with
  system Python before extraction. The extracted runtime manifest and every
  declared runtime path are revalidated before the QC writer is stopped.

Run the read-only gate first:

```powershell
.\scripts\deploy-visual-qc-pilot.ps1 `
  -KeyPath "C:\Users\Mercurluto\OneDrive\AI\90_Meta\Sensitive\Milo.pem" `
  -PreflightOnly
```

`-PreflightOnly` checks host capacity, required commands, PM2, and Nginx
without uploading or changing server files. It does not rehearse the candidate
database migration because no candidate archive has been staged.

Every actual deployment performs the deeper rehearsal automatically. The
script first builds the bounded runtime archive and deterministic deployment
manifest from a clean full Git commit. The server verifies the uploaded
archive hash and byte size before extraction, then verifies the extracted
runtime manifest hash, normalized path count, and every declared path. Only
then does it stop `motherboard-repair-visual-qc`, create a consistent SQLite
backup, and run the candidate
`scripts/audit_visual_qc_upgrade.py` against that backup, the persistent object
root, and the still-active old application contract. The resulting
`deployment-manifest.json` and `upgrade-preflight.json` stay in the
commit-versioned rollback directory.
The app directory and `venv-visual-qc` link are switched only after the report
is `passed`, its `source.snapshot_sha256` matches the rollback database, and
its target object matches the complete deployment manifest. A rehearsal
failure restarts the unchanged old service without replacing the untouched live database.
Database restoration is enabled only after the candidate QC process may have
opened the live database.

The V1 deployment manifest is a byte-integrity and version-binding contract,
not a digital signature. Signing and CI provenance attestations remain
deferred until the deployment channel moves into managed CI/CD.

The rehearsal requires an existing Visual-QC database and a deployed
`VERSION` file whose commit is in the candidate's reviewed source-version
allowlist. It deliberately rejects a live database carrying `-wal` or `-shm`;
the deployment-owned SQLite backup is the accepted consistent input.

Actual deployment additionally requires a local htpasswd file, data-administrator map,
and matching restricted/data-administrator credentials for the authenticated smoke test.
The PowerShell parameter names remain `TechnicianCredential` and
`ReviewerCredential` for deployment-script compatibility:

```powershell
$technician = Get-Credential -UserName "pilot-technician"
$reviewer = Get-Credential -UserName "pilot-reviewer"
.\scripts\deploy-visual-qc-pilot.ps1 `
  -KeyPath "C:\Users\Mercurluto\OneDrive\AI\90_Meta\Sensitive\Milo.pem" `
  -HtpasswdPath "C:\secure\mb-repair.htpasswd" `
  -ReviewerMapPath "C:\secure\mb-repair-reviewers.map" `
  -TechnicianCredential $technician `
  -ReviewerCredential $reviewer
```

Passwords and account lists remain outside Git. Uploaded authentication inputs
are mode `0600` and removed from the staging directory after success or
rollback. The script refuses a dirty worktree and deploys only committed
`HEAD`.

Basic Auth is the controlled-pilot identity provider, not the final global identity architecture. A later corporate SSO/OIDC gateway may replace it while preserving the same verified `X-Actor-Id` and `X-Actor-Role` API contract.
