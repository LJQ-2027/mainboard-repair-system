# Motherboard Repair Beta Deployment

This project is deployed as an isolated beta service on the same server used by CSAT.

## Isolation Rules

- Remote directory: `/opt/motherboard-repair-beta`
- Public beta port: `3010`
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

- Deployed on: 2026-07-01
- Deployed commit: `47b4bd3`
- Internal service: `http://127.0.0.1:3010`
- External beta URL: `https://cccsat.top/mb-repair-beta/`
- Health URL: `https://cccsat.top/mb-repair-beta/health`
- PM2 process: `motherboard-repair-beta`
- Nginx config touched: `/etc/nginx/sites-available/sikayetvar`
- Nginx config backup: `/etc/nginx/sites-available/sikayetvar.before-mb-repair-20260622_095918`
- Current AI status: service is reachable, but `.env` still has no valid `ANTHROPIC_API_KEY`, so AI features are not enabled yet.
- Latest smoke check: complete; readiness dashboard, interactive SOP, and repair case template render through the external beta URL.

## Approved Visual-QC Evolution

The beta server remains the target technician entry for the visual-QC pilot. Physical-board photos are authorized for upload to this controlled server. The approved architecture adds a same-origin QC API, persisted image-processing jobs, controlled image storage, one or two CPU OpenCV workers, Golden Sample review, and candidate confirmation/rejection.

The server was inspected read-only on 2026-07-20: 4 x86_64 vCPU, 7.3 GB RAM, 4 GB swap, 19 GB free disk, Python 3.10, Node.js 20, no GPU, no installed OpenCV, and no active PostgreSQL or Redis. This supports a bounded CPU pilot, not deep-model training or unrestricted long-term image retention.

The current deployed commit `47b4bd3` predates the recent 2.5D and visual-QC work. A future deployment must use the new server architecture and pass upload, restart recovery, storage-limit, and proxy-path smoke tests before field use. Canonical design: `docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`.

### 2026-07-20 P4 Preflight

Read-only inspection confirmed that the current `/mb-repair-beta/` route has no authentication directive or verified user-header injection. It remains unsuitable for internal point maps, physical-board uploads, Golden review, or visual evidence. The server also has no FastAPI, Uvicorn, NumPy, OpenCV, or multipart runtime installed yet.

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
