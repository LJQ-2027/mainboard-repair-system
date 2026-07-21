# Motherboard Repair Beta Deployment

This project is deployed as an isolated beta service on the same server used by CSAT.

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
reviewed runtime allowlist. It includes the technician UI, five-board assets,
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

- Deployed on: 2026-07-21
- Deployed commit: `1f07b4a`
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
- Latest P4 evidence: desktop and 390px workbench paths render with no fresh
  console errors or horizontal overflow; technician/reviewer roles pass through
  the HTTPS gateway; forged actor headers are overwritten; PM2 restart retains
  the persisted proxy case and completed registration job.
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

The beta server remains the target technician entry for the visual-QC pilot. Physical-board photos are authorized for upload to this controlled server. The approved architecture adds a same-origin QC API, persisted image-processing jobs, controlled image storage, one or two CPU OpenCV workers, Golden Sample review, and candidate confirmation/rejection.

The server was inspected read-only on 2026-07-20: 4 x86_64 vCPU, 7.3 GB RAM, 4 GB swap, 19 GB free disk, Python 3.10, Node.js 20, no GPU, no installed OpenCV, and no active PostgreSQL or Redis. This supports a bounded CPU pilot, not deep-model training or unrestricted long-term image retention.

The bounded visual-QC pilot is now deployed with the approved same-origin
architecture. Upload, async processing, manual fallback, role assertion,
loopback binding, restart recovery, storage health, and proxy-path smoke checks
have passed. Physical bare-board photos, reviewed Golden Samples, and
real-defect acceptance remain the field-readiness gate. Canonical design:
`docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`.

### 2026-07-20 P4 Preflight

Read-only inspection initially confirmed that `/mb-repair-beta/` had no
authentication or verified user-header injection. The 2026-07-20 deployment
closed that gate and installed the isolated Python 3.10 visual-QC runtime.

The bounded pilot deployment therefore adds:

- per-user Nginx Basic Auth around the complete beta route;
- `$remote_user` as the gateway-owned `X-Actor-Id`;
- a server-owned reviewer map that fails closed to `technician`;
- removal of client `Authorization` before proxying;
- a loopback-only static/AI process on `127.0.0.1:3010`;
- a loopback-only QC process on `127.0.0.1:3020`;
- a commit-versioned QC runtime behind the stable
  `/opt/motherboard-repair-beta/venv-visual-qc` symlink;
- persistent data outside the replaceable app directory;
- Nginx, PM2, internal health, authenticated technician/reviewer identity,
  forged-header rejection, and unauthenticated-401 checks;
- consistent SQLite backup plus automatic application, runtime, database, and
  gateway rollback on deployment failure.

Run the read-only gate first:

```powershell
.\scripts\deploy-visual-qc-pilot.ps1 `
  -KeyPath "C:\Users\Mercurluto\OneDrive\AI\90_Meta\Sensitive\Milo.pem" `
  -PreflightOnly
```

Actual deployment additionally requires a local htpasswd file, reviewer-map
file, and matching technician/reviewer credentials for the authenticated smoke
test:

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
