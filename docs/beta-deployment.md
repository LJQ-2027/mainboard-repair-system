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
