# Owner-Managed Visual QC Intake Implementation Plan

> **HISTORICAL COMPLETED PLAN:** Do not execute this plan as the current intake procedure. Its direct generic-import transport, Admin List V1, and Detail V2 restoration steps were superseded by `2026-07-23-physical-acceptance-qualified-handoff.md` and `2026-07-23-server-qualified-handoff-provenance.md`. The current physical path is `stage -> source audit -> physical acceptance -> qualified handoff -> server review`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-data-administrator, resumable photo-intake path that binds Milo-supplied images to known board metadata, prevents technician uploads, and lets Codex reopen imported server cases in the existing visual data workbench.

**Architecture:** A local Python manifest/receipt layer validates complete batches and uploads entries sequentially through the existing FastAPI case endpoint. The server adds additive intake provenance, data-admin authorization, an actor-scoped paginated case catalog, and governed original download; the browser reuses the existing registration and annotation canvas by reconstructing a V2 draft from server case evidence.

**Tech Stack:** Python 3.10+, FastAPI, SQLite, OpenCV, standard-library HTTPS/multipart client, vanilla JavaScript, IndexedDB, Canvas 2D, Node test runner, Python unittest, JSON Schema.

---

### Task 1: Versioned Intake Manifest And Receipt Contracts

**Files:**
- Create: `knowledge-base/visual-qc-intake-batch-v1-schema.json`
- Create: `knowledge-base/visual-qc-intake-receipt-v1-schema.json`
- Create: `knowledge-base/visual-qc-intake-batch.example.json`
- Create: `scripts/visual_qc/intake.py`
- Create: `tests/test_visual_qc_intake.py`

- [x] **Step 1: Write failing schema and validation tests**

Add tests that build temporary JPEG files and assert the public validator returns normalized entries only when board, side, stage, session, setup, checklist, signature, dimensions, and optional hash agree:

```python
from scripts.visual_qc.intake import IntakeValidationError, validate_intake_batch

def test_valid_batch_binds_known_board_side_and_computed_hash(self):
    result = validate_intake_batch(self.manifest_path, ROOT)
    self.assertEqual(result["schema_version"], "VISUAL-QC-INTAKE-BATCH-V1")
    self.assertEqual(result["entries"][0]["board_key"], "km4-f151")
    self.assertEqual(result["entries"][0]["side_id"], "main_page_2")
    self.assertEqual(result["entries"][0]["mime_type"], "image/jpeg")
    self.assertEqual(result["entries"][0]["sha256"], hashlib.sha256(self.image).hexdigest())

def test_duplicate_session_side_fails_before_upload(self):
    self.write_manifest(entries=[self.entry("front-a"), self.entry("front-b")])
    with self.assertRaisesRegex(IntakeValidationError, "duplicate capture session side"):
        validate_intake_batch(self.manifest_path, ROOT)
```

Also cover unsafe identifiers, duplicate entry ids, duplicate resolved paths, unknown boards/sides, mixed session identity, incomplete checklist, MIME/signature mismatch, undecodable image, dimension limits, and expected-hash mismatch. Validate a generated receipt against the committed receipt schema.

- [x] **Step 2: Run the targeted tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_intake -v
```

Expected: import failure because `scripts.visual_qc.intake` does not exist.

- [x] **Step 3: Add the exact JSON contracts**

Define `VISUAL-QC-INTAKE-BATCH-V1` with bounded safe identifiers and this entry shape:

```json
{
  "entry_id": "km4-board-01-side-2",
  "file_path": "C:/controlled-source/km4-board-01-side-2.jpg",
  "board_key": "km4-f151",
  "side_id": "main_page_2",
  "capture_stage": "golden_reference",
  "capture_session_id": "km4-board-01",
  "capture_setup_id": "standard-bench",
  "capture_checklist": {
    "board_and_side_confirmed": true,
    "focus_and_lens_confirmed": true,
    "lighting_and_occlusion_confirmed": true
  },
  "expected_sha256": null
}
```

Define the receipt with stable `batch_id`, one row per `entry_id`, computed evidence, idempotency key, nullable server ids, terminal state, and nullable typed error. Commit an example that uses placeholder paths and hashes only; never commit a real photo path or credential.

- [x] **Step 4: Implement the focused validator and receipt helpers**

Expose these interfaces from `scripts/visual_qc/intake.py`:

```python
class IntakeValidationError(ValueError):
    pass

def validate_intake_batch(manifest_path: Path, project_root: Path) -> dict:
    """Return normalized entries with Path, MIME, dimensions, byte size, and SHA-256."""

def intake_idempotency_key(batch_id: str, entry_id: str, sha256: str) -> str:
    digest = hashlib.sha256(f"{batch_id}:{entry_id}:{sha256}".encode("utf-8")).hexdigest()
    return f"intake:{digest[:48]}"

def create_intake_receipt(validated_batch: dict) -> dict:
    """Create stable validated rows without credentials or authorization data."""

def merge_receipt(previous: dict | None, validated_batch: dict) -> dict:
    """Preserve server ids only when entry id and SHA-256 still match."""

def write_json_atomic(path: Path, payload: dict) -> None:
    """Write UTF-8/LF JSON through a same-directory temporary file and os.replace."""
```

Use `BoardCatalog`, `detect_image_mime_type`, and `cv2.imdecode`; do not duplicate board-side truth or infer metadata from image content.

- [x] **Step 5: Run tests and contract validation**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_intake -v
Get-Content knowledge-base/visual-qc-intake-batch-v1-schema.json -Raw -Encoding utf8 | ConvertFrom-Json | Out-Null
Get-Content knowledge-base/visual-qc-intake-receipt-v1-schema.json -Raw -Encoding utf8 | ConvertFrom-Json | Out-Null
```

Expected: all intake tests pass and both schemas parse.

- [x] **Step 6: Commit Task 1**

```powershell
git add knowledge-base/visual-qc-intake-batch-v1-schema.json knowledge-base/visual-qc-intake-receipt-v1-schema.json knowledge-base/visual-qc-intake-batch.example.json scripts/visual_qc/intake.py tests/test_visual_qc_intake.py
git commit -m "feat: validate owner-managed visual QC intake"
```

### Task 2: Data-Administrator Upload Gate And Intake Provenance

**Files:**
- Modify: `scripts/visual_qc/server/api.py`
- Modify: `scripts/visual_qc/server/service.py`
- Modify: `scripts/visual_qc/server/store.py`
- Modify: `tests/test_visual_qc_server.py`
- Modify: `tests/test_visual_qc_deployment.py`

- [x] **Step 1: Write failing authorization and migration tests**

Add an API test that patches the service method and proves a technician request is rejected before `create_case` is invoked:

```python
def test_technician_cannot_upload_visual_qc_case(self):
    service = self.app.state.visual_qc_service
    with mock.patch.object(service, "create_case") as create_case:
        response = self.client.post(
            "/api/v1/visual-qc/cases",
            files={"file": ("board.jpg", self.image_bytes, "image/jpeg")},
            data=self.valid_upload_fields(),
            headers={"X-Actor-Id": "technician-001", "X-Actor-Role": "technician"},
        )
    self.assertEqual(response.status_code, 403)
    self.assertEqual(response.json()["detail"]["code"], "data_admin_role_required")
    create_case.assert_not_called()
```

Update successful upload tests to send `X-Actor-Role: reviewer`. Add a legacy SQLite fixture without intake columns, open `VisualQcStore`, and assert existing rows survive with null provenance. Add a creation test asserting `intake_batch_id` and `intake_entry_id` round-trip.

- [x] **Step 2: Run targeted server tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_server -v
```

Expected: technician upload still reaches the endpoint and intake fields are absent.

- [x] **Step 3: Enforce authorization before multipart parsing**

Add a narrow HTTP middleware before route handling:

```python
@app.middleware("http")
async def protect_visual_intake(request, call_next):
    if request.method == "POST" and request.url.path.endswith("/api/v1/visual-qc/cases"):
        if request.headers.get("X-Actor-Role") != "reviewer":
            return JSONResponse(
                status_code=403,
                content={"detail": {
                    "code": "data_admin_role_required",
                    "message": "Visual data intake requires the data administrator role.",
                }},
            )
    return await call_next(request)
```

Keep a route-level role assertion for defense in depth. The production gateway remains responsible for replacing client-supplied actor headers.

- [x] **Step 4: Add additive intake provenance migration**

Add nullable columns to the create-table declaration and migration:

```sql
ALTER TABLE cases ADD COLUMN intake_batch_id TEXT;
ALTER TABLE cases ADD COLUMN intake_entry_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS cases_actor_intake_entry
ON cases(actor_id, intake_batch_id, intake_entry_id)
WHERE intake_batch_id IS NOT NULL AND intake_entry_id IS NOT NULL;
```

Accept both fields as optional bounded form values, validate that they are either both absent or both present, include them in the request fingerprint, case insert, public server-case response, and `case_created` audit payload. Historical browser-created admin cases remain valid with null provenance.

- [x] **Step 5: Run targeted authorization, migration, and deployment tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_server tests.test_visual_qc_deployment -v
```

Expected: technician upload is 403, data-admin upload is accepted, old databases migrate without data loss, and deployment contracts remain green.

- [x] **Step 6: Commit Task 2**

```powershell
git add scripts/visual_qc/server/api.py scripts/visual_qc/server/service.py scripts/visual_qc/server/store.py tests/test_visual_qc_server.py tests/test_visual_qc_deployment.py
git commit -m "feat: restrict visual intake to data administrators"
```

### Task 3: Actor-Scoped Server Case Catalog And Original Recovery

**Files:**
- Modify: `scripts/visual_qc/server/api.py`
- Modify: `scripts/visual_qc/server/service.py`
- Modify: `scripts/visual_qc/server/store.py`
- Create: `knowledge-base/visual-qc-admin-case-list-v1-schema.json`
- Create: `tests/test_visual_qc_admin_cases.py`

- [x] **Step 1: Write failing catalog, detail, and original tests**

Create cases in queued, failed, manual-required, candidate-ready, registration-reviewed, and final-QC states. Assert data-admin-only access, actor isolation, newest-first stable ordering, bounded pagination, fixed filters, and typed errors:

```python
def test_admin_catalog_is_actor_scoped_filtered_and_stably_paginated(self):
    response = self.client.get(
        "/api/v1/visual-qc/admin/cases?page=1&page_size=2&state=ready_for_human_qc",
        headers=self.admin_headers,
    )
    self.assertEqual(response.status_code, 200)
    payload = response.json()
    self.assertEqual(payload["schema_version"], "VISUAL-QC-ADMIN-CASE-LIST-V1")
    self.assertLessEqual(len(payload["cases"]), 2)
    self.assertTrue(all(item["state"] == "ready_for_human_qc" for item in payload["cases"]))
    self.assertNotIn("actor_id", json.dumps(payload))
```

Assert `GET /admin/cases/{case_id}` includes the latest registration review and latest final QC review, while `GET /admin/cases/{case_id}/image` returns byte-identical original content only to its owner. Technician and different-admin access return 403 or privacy-preserving 404 as specified.

- [x] **Step 2: Run the new test module and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_admin_cases -v
```

Expected: all three admin routes return 404 because they do not exist.

- [x] **Step 3: Implement catalog storage query and state derivation**

Add:

```python
ADMIN_CASE_STATES = {
    "processing", "processing_failed", "manual_registration_required",
    "registration_review_required", "ready_for_human_qc", "completed",
}

def list_admin_cases(
    self, actor_id: str, *, board_key: str | None, side_id: str | None,
    capture_stage: str | None, state: str | None, limit: int, offset: int,
) -> tuple[list[dict], int]:
    """Return only actor-owned cases with latest job/review joins."""
```

Derive one state in `VisualQcService` from persisted job result, registration review, and final QC review. Sort `created_at DESC, case_id DESC`; validate page size `1..100` and fixed filter enums.

- [x] **Step 4: Implement governed detail and original routes**

Add reviewer/data-admin-only routes:

```text
GET /api/v1/visual-qc/admin/cases
GET /api/v1/visual-qc/admin/cases/{case_id}
GET /api/v1/visual-qc/admin/cases/{case_id}/image
```

The detail route emits `VISUAL-QC-SERVER-CASE-V2` with intake provenance and `server_registration_review`. The original route resolves through a service method that confirms ownership, managed storage, file existence, and current SHA-256 before returning `FileResponse` with the original MIME and filename.

- [x] **Step 5: Run catalog tests and the complete server suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_admin_cases -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_visual_qc_*.py"
```

Expected: catalog module and all visual-QC server tests pass.

- [x] **Step 6: Commit Task 3**

```powershell
git add scripts/visual_qc/server/api.py scripts/visual_qc/server/service.py scripts/visual_qc/server/store.py knowledge-base/visual-qc-admin-case-list-v1-schema.json tests/test_visual_qc_admin_cases.py
git commit -m "feat: list owner-managed visual QC cases"
```

### Task 4: Resumable Batch Import CLI

**Files:**
- Modify: `scripts/visual_qc/intake.py`
- Create: `scripts/import_visual_qc_batch.py`
- Modify: `tests/test_visual_qc_intake.py`
- Modify: `deploy/visual-qc-runtime-files.txt`
- Modify: `tests/test_visual_qc_deployment.py`

- [x] **Step 1: Write failing dry-run, upload, resume, and secret-safety tests**

Use an injected fake transport rather than a network mock:

```python
def test_dry_run_writes_validated_receipt_without_transport_calls(self):
    transport = FakeTransport()
    result = run_intake(self.manifest_path, self.receipt_path, transport, dry_run=True)
    self.assertEqual(transport.requests, [])
    self.assertEqual(result["entries"][0]["state"], "validated")

def test_resume_uploads_only_rows_without_matching_server_ids(self):
    first = run_intake(self.manifest_path, self.receipt_path, self.transport)
    resumed = run_intake(self.manifest_path, self.receipt_path, self.transport)
    self.assertEqual(len(self.transport.uploads), len(first["entries"]))
    self.assertEqual(first, resumed)
```

Also assert sequential stop-on-error, explicit continue-on-error, job polling state updates, no password/header in receipts or stdout, changed SHA invalidates prior server ids, and the runtime manifest includes both import modules.

- [x] **Step 2: Run intake and deployment tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_intake tests.test_visual_qc_deployment -v
```

Expected: `run_intake` and CLI module are missing.

- [x] **Step 3: Implement transport and resumable orchestration**

Expose:

```python
class VisualQcIntakeTransport:
    def upload(self, entry: dict, *, idempotency_key: str) -> dict: ...
    def get_job(self, job_id: str) -> dict: ...

def run_intake(
    manifest_path: Path,
    receipt_path: Path,
    transport: VisualQcIntakeTransport,
    *, dry_run: bool = False,
    wait_for_jobs: bool = False,
    continue_on_error: bool = False,
) -> dict: ...
```

Use `urllib.request` and standard-library multipart construction to avoid a new runtime dependency. Read credentials from an explicitly supplied JSON file or environment variables, send Basic Auth only over HTTPS unless `--allow-http-localhost` is explicitly set, and never print credentials.

- [x] **Step 4: Implement the CLI surface**

Support:

```text
python -m scripts.import_visual_qc_batch MANIFEST
  --receipt PATH
  --dry-run
  --api-base URL
  --credential-file PATH
  --actor-id ID
  --wait
  --continue-on-error
  --allow-http-localhost
```

Default receipt path is `<manifest-name>.receipt.json`. Exit 0 only when every requested entry reaches its expected state; validation failures exit 2 and transfer/runtime failures exit 1. Output one bounded summary with counts and receipt path.

- [x] **Step 5: Run tests and a local dry-run against the committed example copy**

Create temporary image paths in the test fixture; do not modify the committed example with real files.

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_intake tests.test_visual_qc_deployment -v
.\.venv\Scripts\python.exe -m scripts.import_visual_qc_batch --help
```

Expected: all tests pass and help documents every bounded option.

- [x] **Step 6: Commit Task 4**

```powershell
git add scripts/visual_qc/intake.py scripts/import_visual_qc_batch.py tests/test_visual_qc_intake.py deploy/visual-qc-runtime-files.txt tests/test_visual_qc_deployment.py
git commit -m "feat: import visual QC batches resumably"
```

### Task 5: Browser Server-Case Reconstruction

**Files:**
- Modify: `assets/visual-qc-workbench/visual-qc-server-client.js`
- Modify: `tests/visual-qc-server-client.test.mjs`

- [x] **Step 1: Write failing client and reconstruction tests**

Add tests for role headers, filters, binary original response, and complete V2 restoration:

```javascript
test('server case restoration preserves reviewed registration and final QC evidence', () => {
  const restored = restoreAdminServerCase(serverCase(), imageBlob());
  assert.equal(restored.schema_version, 'VISUAL-QC-CASE-V2');
  assert.equal(restored.server_sync.server_case_id, 'vqc_server_case');
  assert.equal(restored.registration.status, 'reviewed');
  assert.deepEqual(restored.registration.matrix, [1, 0, 0, 0, 1, 0, 0, 0, 1]);
  assert.equal(restored.server_qc_review.version, 2);
  assert.equal(restored.qc_result.status, 'confirmed_anomaly');
});
```

Assert unsupported server schema, image hash mismatch, dimension mismatch, missing job result, and stale QC/registration linkage throw typed client errors instead of opening a misleading draft.

- [x] **Step 2: Run the client test and verify RED**

Run:

```powershell
node --test tests/visual-qc-server-client.test.mjs
```

Expected: missing admin API and restoration exports.

- [x] **Step 3: Implement admin API client functions**

Add:

```javascript
export function listVisualQcAdminCases(apiBase, actorId, actorRole, filters = {}) {}
export function getVisualQcAdminCase(apiBase, actorId, actorRole, caseId) {}
export function getVisualQcAdminCaseImage(apiBase, actorId, actorRole, caseId) {}
export async function restoreAdminServerCase(serverCase, imageBlob) {}
```

Use the existing JSON/blob error shape. Reconstruct through `createVisualQcCase`, `applyServerJobResult`, reviewed registration evidence, and `applyFinalQcReview`; verify SHA-256 and decoded dimensions before returning the case plus image blob.

- [x] **Step 4: Run client and state suites**

```powershell
node --test tests/visual-qc-server-client.test.mjs tests/visual-qc-state.test.mjs tests/visual-qc-core.test.mjs
```

Expected: all selected Node tests pass.

- [x] **Step 5: Commit Task 5**

```powershell
git add assets/visual-qc-workbench/visual-qc-server-client.js tests/visual-qc-server-client.test.mjs
git commit -m "feat: restore server visual QC cases"
```

### Task 6: Data Administrator Catalog In The Existing Workbench

**Files:**
- Modify: `assets/visual-qc-workbench/index.html`
- Modify: `assets/visual-qc-workbench/styles.css`
- Modify: `assets/visual-qc-workbench/app.js`
- Modify: `tests/visual-qc-capture-ui.test.mjs`
- Create: `tests/visual-qc-admin-catalog-ui.test.mjs`

- [x] **Step 1: Write failing UI contract tests**

Assert the workbench uses the approved terminology and exposes a single compact catalog dialog:

```javascript
test('data administrator workbench exposes one server case catalog', () => {
  assert.match(html, /主板视觉数据工作台/);
  assert.match(html, /id="serverCasesButton"/);
  assert.match(html, /id="serverCasesDialog"/);
  assert.match(html, /id="serverCaseStateFilter"/);
  assert.match(html, /id="serverCasesList"/);
  assert.doesNotMatch(html, /审核员工具/);
});
```

Add pure state tests for fixed state labels, filter serialization, bounded pagination, and an explicit technician access state that hides image intake, proxy loading, server synchronization, Golden, server catalog, and dataset export controls.

- [x] **Step 2: Run UI tests and verify RED**

Run:

```powershell
node --test tests/visual-qc-capture-ui.test.mjs tests/visual-qc-admin-catalog-ui.test.mjs
```

Expected: new ids and terminology are absent.

- [x] **Step 3: Add the un-nested catalog dialog and role presentation**

Use one dialog with a compact toolbar, unframed rows, pagination controls, loading/empty/error states, and an `打开` command. Keep cards out of cards. Map backend role `reviewer` to the visible label `数据管理员`; do not rename the wire role in this increment.

For technicians:

```javascript
const dataAdmin = VISUAL_QC_ACTOR_ROLE === 'reviewer';
elements.chooseImageButton.hidden = !dataAdmin;
elements.proxyButton.hidden = !dataAdmin || !state.dataset.registration?.proxy_image;
elements.serverCasesButton.hidden = !dataAdmin;
elements.trainingDatasetSection.hidden = !dataAdmin;
```

Also reject file input and drop actions when `dataAdmin` is false so hidden controls are not the only boundary.

- [x] **Step 4: Connect catalog loading and case restoration**

On `打开`:

1. fetch the V2 server detail and original in parallel;
2. verify and reconstruct through `restoreAdminServerCase`;
3. load the declared board and side without resetting the restored case;
4. save the restored case/image to IndexedDB;
5. render the existing quality, registration, annotation, Golden, and dataset surfaces;
6. close the dialog only after the first valid image frame renders.

Keep catalog filters and page in memory when returning. Opening a failed or missing original leaves the dialog open with a row-level typed error.

- [x] **Step 5: Run focused and full Node suites**

```powershell
node --test tests/visual-qc-capture-ui.test.mjs tests/visual-qc-admin-catalog-ui.test.mjs tests/visual-qc-server-client.test.mjs
node --test tests/*.test.mjs
```

Expected: focused tests and the complete Node suite pass.

- [x] **Step 6: Commit Task 6**

```powershell
git add assets/visual-qc-workbench/index.html assets/visual-qc-workbench/styles.css assets/visual-qc-workbench/app.js tests/visual-qc-capture-ui.test.mjs tests/visual-qc-admin-catalog-ui.test.mjs
git commit -m "feat: browse owner-managed visual QC cases"
```

### Task 7: Canonical Documentation, Full Verification, And Controlled Deployment

**Files:**
- Modify: `README.md`
- Modify: `docs/visual-qc-server-api-2026-07-20.md`
- Modify: `docs/visual-qc-capture-intake-spec-2026-07-20.md`
- Modify: `docs/visual-qc-workbench-2026-07-17.md`
- Modify: `docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md`
- Modify: `docs/beta-deployment.md`
- Modify: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`
- Modify: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Overview.md`
- Modify: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Task Index.md`
- Modify: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Risks.md`
- Modify: `C:/Users/Mercurluto/OneDrive/AI/90_Meta/System Checks/2026-07-21 Daily Architecture Check.md`

- [x] **Step 1: Replace stale current-architecture wording**

Current summaries must state:

```text
Milo is the only source of real visual photos. Codex operates the data-administrator intake and evidence-building path. Overseas technicians do not upload photos or enter the internal visual data workbench. The backend `reviewer` role is retained temporarily as the compatibility identifier for data-administrator capability; it is not a second-person approval layer.
```

Keep historical records intact but mark superseded technician-upload assumptions as historical. Document manifest/receipt commands and the first-real-batch acceptance procedure.

- [x] **Step 2: Run P0-P2 complete verification**

```powershell
node --test tests/*.test.mjs
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe -m py_compile scripts/import_visual_qc_batch.py scripts/visual_qc/intake.py scripts/visual_qc/server/api.py scripts/visual_qc/server/service.py scripts/visual_qc/server/store.py
git diff --check
```

Parse every changed JSON file with strict UTF-8, scan all changed code/docs plus Vault/ledger for U+FFFD, and run the existing dataset and deployment contract checks included in the suites.

- [x] **Step 3: Perform local P3 visual and interaction QA**

Use the Chrome extension path when available; otherwise document the installed headed-Chrome Playwright fallback. Check desktop 1440x1000 and mobile 390x844:

- data-admin catalog loading, empty/populated/error states;
- board/side/state filters and pagination;
- open imported case, image render, reviewed/manual registration state, and return;
- technician hidden controls and rejected direct upload;
- button default, hover, active, focus-visible, loading, and disabled states;
- text/background readability, overflow, overlap, blank canvas, failed requests, and console errors.

Save ignored screenshots under `output/playwright/owner-managed-intake/`.

- [x] **Step 4: Commit implementation documentation**

```powershell
git add README.md docs/visual-qc-server-api-2026-07-20.md docs/visual-qc-capture-intake-spec-2026-07-20.md docs/visual-qc-workbench-2026-07-17.md docs/superpowers/specs/2026-07-20-visual-qc-server-architecture-design.md docs/beta-deployment.md
git commit -m "docs: adopt owner-managed visual QC intake"
```

- [x] **Step 5: Deploy with the existing controlled script and run P4**

Run the committed `scripts/deploy-visual-qc-pilot.ps1` with credentials loaded from the external sensitive directory. Verify:

- production `VERSION` equals the feature commit deployed;
- PM2, Nginx, internal health, and authenticated route are healthy;
- technician multipart upload returns `403 data_admin_role_required`;
- data-admin empty/current catalog returns the preserved proxy case only;
- existing dataset audit remains `0` eligible, `1` excluded, `non_physical_evidence: 1`;
- repeated training ZIP remains deterministic;
- the legacy case has null intake provenance and no migration loss;
- no fake physical case is uploaded.

- [x] **Step 6: Run production P3 and write fact sources**

Repeat the desktop/mobile browser matrix against the authenticated production route. Update deployment facts, coordination ledger, Vault overview/task/risk cards, and the daily architecture check with actual commit ids and evidence. Commit the coordination ledger separately.

- [x] **Step 7: Perform Project Closeout Check**

Confirm clean implementation and coordination worktrees, local commit history, no GitHub push attempt under the recorded mainland-network constraint, synchronized Vault/ledger facts, P0-P4 evidence, encoding health, and the remaining real-photo acceptance gate.

The next physical step after this plan is not another software proxy: Milo supplies the first known bare-board front/back set, and Codex runs the committed dry-run/import/processing/registration/Golden/dataset procedure end to end.
