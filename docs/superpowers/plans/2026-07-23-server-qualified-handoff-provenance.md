# Server Qualified-Handoff Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind every newly admitted physical Visual-QC server case to the exact locally qualified source package, archived intake manifest, and acceptance report without uploading those evidence bodies.

**Architecture:** A focused server provenance module strictly normalizes the compact versioned assertion. The API, service, SQLite store, handoff importer, admin workbench, and training gate carry the same immutable object; legacy rows remain readable as null but cannot establish training eligibility.

**Tech Stack:** Python 3, FastAPI multipart forms, SQLite, unittest/TestClient, JavaScript ES modules, Node test runner, IndexedDB workbench contracts.

---

## File Map

- Create `scripts/visual_qc/server/provenance.py`: strict qualified-handoff normalization and canonical serialization.
- Create `knowledge-base/visual-qc-qualified-handoff-provenance-v1-schema.json`: portable closed JSON contract.
- Modify `scripts/visual_qc/server/api.py`: accept the compact multipart JSON field.
- Modify `scripts/visual_qc/server/service.py`: enforce evidence-role admission, fingerprint provenance, expose versioned responses, and gate training.
- Modify `scripts/visual_qc/server/store.py`: compatibility migration, persistence, queries, and audit payload.
- Modify `scripts/import_visual_qc_batch.py`: carry prequalified per-entry provenance and refuse to synthesize it.
- Modify `scripts/visual_qc/physical_handoff.py`: derive exact per-entry server provenance from validated handoff evidence.
- Modify `assets/visual-qc-workbench/visual-qc-server-client.js`: restore the V3 admin contract and preserve provenance as trace metadata.
- Modify `tests/test_visual_qc_server.py`: API, validation, migration, persistence, idempotency, and audit coverage.
- Modify `tests/test_visual_qc_admin_cases.py`: admin list/detail contract coverage.
- Modify `tests/test_visual_qc_physical_handoff.py`: producer and resumable transport binding coverage.
- Modify `tests/test_visual_qc_training_manifest.py`: legacy/null provenance training exclusion.
- Modify `tests/visual-qc-server-client.test.mjs`: browser-client restoration contract coverage.
- Modify project facts only after verification: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`, the Mainboard Repair Enablement Vault project records, and the current daily architecture check.

### Task 1: Define And Prove The Closed Provenance Contract

**Files:**
- Create: `scripts/visual_qc/server/provenance.py`
- Create: `knowledge-base/visual-qc-qualified-handoff-provenance-v1-schema.json`
- Modify: `tests/test_visual_qc_server.py`

- [ ] **Step 1: Add failing normalizer and JSON Schema tests**

Add a reusable test fixture and tests that exercise real normalization:

```python
def qualified_handoff(action="automatic_candidate_review_required", **overrides):
    payload = {
        "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
        "handoff_schema_version": "VISUAL-QC-PHYSICAL-HANDOFF-V1",
        "source_package_manifest_sha256": "a" * 64,
        "archived_intake_manifest_sha256": "b" * 64,
        "acceptance_report_sha256": "c" * 64,
        "acceptance_action": action,
        "registration_review_required": True,
        "field_accuracy_claim_allowed": False,
    }
    payload.update(overrides)
    return payload


def test_qualified_handoff_contract_is_closed_and_schema_valid(self):
    normalized = normalize_qualified_handoff(
        json.dumps(qualified_handoff(), separators=(",", ":"))
    )
    self.assertEqual(normalized, qualified_handoff())
    schema = json.loads(
        (ROOT / "knowledge-base"
         / "visual-qc-qualified-handoff-provenance-v1-schema.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.validate(normalized, schema)


def test_qualified_handoff_rejects_unknown_fields_and_semantic_drift(self):
    invalid = qualified_handoff(extra="pollution")
    with self.assertRaises(QualifiedHandoffError):
        normalize_qualified_handoff(json.dumps(invalid))
    for key, value in (
        ("registration_review_required", False),
        ("field_accuracy_claim_allowed", True),
        ("source_package_manifest_sha256", "A" * 64),
        ("acceptance_action", "reviewed"),
    ):
        invalid = qualified_handoff(**{key: value})
        with self.assertRaises(QualifiedHandoffError):
            normalize_qualified_handoff(json.dumps(invalid))
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_visual_qc_server.VisualQcServerTests.test_qualified_handoff_contract_is_closed_and_schema_valid tests.test_visual_qc_server.VisualQcServerTests.test_qualified_handoff_rejects_unknown_fields_and_semantic_drift -v
```

Expected: import failure because `scripts.visual_qc.server.provenance` and the JSON Schema do not exist.

- [ ] **Step 3: Implement strict normalization**

Create `provenance.py` with one public normalizer and one canonical serializer:

```python
from __future__ import annotations

import json
import re

SCHEMA_VERSION = "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1"
HANDOFF_SCHEMA_VERSION = "VISUAL-QC-PHYSICAL-HANDOFF-V1"
ALLOWED_ACTIONS = {
    "automatic_candidate_review_required",
    "manual_registration_required",
}
FIELDS = {
    "schema_version",
    "handoff_schema_version",
    "source_package_manifest_sha256",
    "archived_intake_manifest_sha256",
    "acceptance_report_sha256",
    "acceptance_action",
    "registration_review_required",
    "field_accuracy_claim_allowed",
}
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class QualifiedHandoffError(ValueError):
    pass


def normalize_qualified_handoff(raw: str | dict) -> dict:
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as exc:
        raise QualifiedHandoffError("Qualified handoff JSON is invalid.") from exc
    if not isinstance(payload, dict) or set(payload) != FIELDS:
        raise QualifiedHandoffError("Qualified handoff fields are invalid.")
    if (
        payload["schema_version"] != SCHEMA_VERSION
        or payload["handoff_schema_version"] != HANDOFF_SCHEMA_VERSION
        or payload["acceptance_action"] not in ALLOWED_ACTIONS
        or payload["registration_review_required"] is not True
        or payload["field_accuracy_claim_allowed"] is not False
        or any(
            not isinstance(payload[field], str)
            or not LOWER_SHA256.fullmatch(payload[field])
            for field in (
                "source_package_manifest_sha256",
                "archived_intake_manifest_sha256",
                "acceptance_report_sha256",
            )
        )
    ):
        raise QualifiedHandoffError("Qualified handoff values are invalid.")
    return {field: payload[field] for field in sorted(FIELDS)}


def serialize_qualified_handoff(payload: dict | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(
        normalize_qualified_handoff(payload),
        sort_keys=True,
        separators=(",", ":"),
    )
```

Create a Draft 2020-12 JSON Schema with `additionalProperties: false`, exact constants for both semantic booleans and schema versions, the two-action enum, and lowercase `^[0-9a-f]{64}$` patterns for all three hashes.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command.

Expected: both tests pass.

- [ ] **Step 5: Commit the contract**

```powershell
git add scripts/visual_qc/server/provenance.py knowledge-base/visual-qc-qualified-handoff-provenance-v1-schema.json tests/test_visual_qc_server.py
git commit -m "feat: define qualified handoff provenance"
```

### Task 2: Enforce Admission And Persist Immutable Provenance

**Files:**
- Modify: `scripts/visual_qc/server/api.py`
- Modify: `scripts/visual_qc/server/service.py`
- Modify: `scripts/visual_qc/server/store.py`
- Modify: `tests/test_visual_qc_server.py`
- Modify: `tests/test_visual_qc_admin_cases.py`

- [ ] **Step 1: Add failing API admission tests**

Extend the upload helper so valid physical requests include intake identity and:

```python
"qualified_handoff": json.dumps(qualified_handoff(), separators=(",", ":")),
```

Add explicit rejection tests:

```python
def test_new_physical_case_requires_intake_and_qualified_handoff(self):
    missing = self.upload(self.image_bytes, qualified_handoff=None)
    self.assertEqual(missing.status_code, 422)
    self.assertEqual(
        missing.json()["detail"]["code"],
        "physical_handoff_provenance_required",
    )


def test_nonphysical_case_rejects_qualified_handoff(self):
    response = self.upload(
        self.image_bytes,
        evidence_role="service_manual_proxy",
        qualified_handoff=json.dumps(qualified_handoff()),
    )
    self.assertEqual(response.status_code, 422)
    self.assertEqual(
        response.json()["detail"]["code"],
        "qualified_handoff_not_allowed",
    )
```

Add a round-trip test asserting:

- create/get schema is `VISUAL-QC-SERVER-CASE-V2`;
- `qualified_handoff` equals the normalized fixture;
- the stored JSON is canonical;
- `case_created.payload_json` contains the same object;
- no fixture path, report body, or overlay field appears.

- [ ] **Step 2: Add failing migration and idempotency tests**

Extend the legacy SQLite fixture without `qualified_handoff_json`, initialize `VisualQcStore`, and assert the migrated row remains null. Add a request that reuses the same idempotency key with one changed acceptance-report hash and assert `409 idempotency_conflict`.

- [ ] **Step 3: Run the focused server tests and verify RED**

Run:

```powershell
python -m unittest tests.test_visual_qc_server -v
```

Expected: valid uploads fail because the API ignores provenance, response remains V1, and the database lacks the new column.

- [ ] **Step 4: Wire API and service admission**

In `api.py`, add:

```python
qualified_handoff: str | None = Form(None, max_length=4096),
```

and pass it to `service.create_case`.

In `service.py`, normalize after intake identity:

```python
normalized_handoff = self._normalized_qualified_handoff(
    evidence_role=evidence_role,
    raw=qualified_handoff,
    intake_batch_id=intake_batch_id,
    intake_entry_id=intake_entry_id,
)
```

The helper must:

```python
if evidence_role == "physical_capture":
    if intake_batch_id is None or raw is None:
        raise VisualQcServiceError(
            "physical_handoff_provenance_required",
            "Physical capture requires controlled intake and qualified handoff provenance.",
        )
    try:
        return normalize_qualified_handoff(raw)
    except QualifiedHandoffError as exc:
        raise VisualQcServiceError(
            "invalid_qualified_handoff", str(exc)
        ) from exc
if raw is not None and raw.strip():
    raise VisualQcServiceError(
        "qualified_handoff_not_allowed",
        "Qualified handoff provenance is allowed only for physical capture.",
    )
return None
```

Add `qualified_handoff` to the sorted request-fingerprint payload and canonical `qualified_handoff_json` to the case record. Return `qualified_handoff` and advance the standard case response to V2.

- [ ] **Step 5: Persist, migrate, query, and audit**

Add `qualified_handoff_json TEXT` to new databases and a nullable compatibility migration:

```python
if "qualified_handoff_json" not in case_columns:
    connection.execute(
        "ALTER TABLE cases ADD COLUMN qualified_handoff_json TEXT"
    )
```

Include the column in case insert/select/list/dataset queries. Decode it only through a helper that returns `None` or calls `normalize_qualified_handoff`; corrupt stored JSON must fail closed rather than be silently ignored. Add the decoded object to `case_created`.

- [ ] **Step 6: Version admin list/detail responses**

Return `VISUAL-QC-ADMIN-CASE-LIST-V2` with `qualified_handoff` on each row. Return `VISUAL-QC-SERVER-CASE-V3` from admin detail. Update admin tests to assert both the version and exact provenance object.

- [ ] **Step 7: Run server and admin tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_visual_qc_server tests.test_visual_qc_admin_cases -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit server persistence**

```powershell
git add scripts/visual_qc/server/api.py scripts/visual_qc/server/service.py scripts/visual_qc/server/store.py tests/test_visual_qc_server.py tests/test_visual_qc_admin_cases.py
git commit -m "feat: persist qualified physical provenance"
```

### Task 3: Bind The Controlled Physical Handoff To Multipart Upload

**Files:**
- Modify: `scripts/import_visual_qc_batch.py`
- Modify: `scripts/visual_qc/physical_handoff.py`
- Modify: `tests/test_visual_qc_physical_handoff.py`
- Modify: `tests/test_visual_qc_intake.py`

- [ ] **Step 1: Add failing handoff-producer tests**

Upgrade `FakeTransport.upload` to record a deep copy of `entry["qualified_handoff"]`. Assert the candidate and manual fixtures produce:

```python
{
    "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
    "handoff_schema_version": "VISUAL-QC-PHYSICAL-HANDOFF-V1",
    "source_package_manifest_sha256": evidence["package"]["manifest_sha256"],
    "archived_intake_manifest_sha256": evidence["archived_intake"]["manifest_sha256"],
    "acceptance_report_sha256": evidence["acceptance"]["sha256"],
    "acceptance_action": evidence["entries"][0]["acceptance_action"],
    "registration_review_required": True,
    "field_accuracy_claim_allowed": False,
}
```

Add a resume test proving the same entry produces byte-identical canonical JSON after an interrupted upload.

- [ ] **Step 2: Add failing real multipart tests**

Patch `_request_json`, invoke `VisualQcIntakeTransport.upload`, parse the generated multipart body, and assert the `qualified_handoff` form field exists once and equals canonical compact JSON. Add a negative test where the entry lacks provenance and assert `physical_handoff_provenance_required` before `_request_json` is called.

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_visual_qc_physical_handoff tests.test_visual_qc_intake -v
```

Expected: fake uploads lack the new object and multipart contains no qualified-handoff field.

- [ ] **Step 4: Build provenance only from validated evidence**

Add:

```python
def _qualified_handoff_by_entry(evidence: dict) -> dict[str, dict]:
    common = {
        "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
        "handoff_schema_version": HANDOFF_SCHEMA_VERSION,
        "source_package_manifest_sha256": evidence["package"]["manifest_sha256"],
        "archived_intake_manifest_sha256": evidence["archived_intake"]["manifest_sha256"],
        "acceptance_report_sha256": evidence["acceptance"]["sha256"],
        "registration_review_required": True,
        "field_accuracy_claim_allowed": False,
    }
    return {
        entry["entry_id"]: normalize_qualified_handoff({
            **common,
            "acceptance_action": entry["acceptance_action"],
        })
        for entry in evidence["entries"]
    }
```

Pass this mapping to both preflight and transfer calls through `_run_bound_intake`.

- [ ] **Step 5: Carry but never synthesize provenance**

Add `qualified_handoff_by_entry: dict[str, dict] | None = None` to `run_intake`. When provided, require its keys to equal the validated entry ids and attach deep-copied normalized values to entries. When omitted, do not create values.

In `VisualQcIntakeTransport.upload`, require `entry["qualified_handoff"]`, normalize it, and add:

```python
"qualified_handoff": serialize_qualified_handoff(
    entry["qualified_handoff"]
),
```

to multipart fields. This keeps the generic dry-run validator usable while making generic physical upload fail locally without the qualified producer.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run the Step 3 command.

Expected: all tests pass.

- [ ] **Step 7: Commit controlled transport binding**

```powershell
git add scripts/import_visual_qc_batch.py scripts/visual_qc/physical_handoff.py tests/test_visual_qc_physical_handoff.py tests/test_visual_qc_intake.py
git commit -m "feat: bind handoff provenance to upload"
```

### Task 4: Restore Provenance In The Internal Workbench

**Files:**
- Modify: `assets/visual-qc-workbench/visual-qc-server-client.js`
- Modify: `tests/visual-qc-server-client.test.mjs`

- [ ] **Step 1: Add failing V3 restoration tests**

Change the admin fixture to `VISUAL-QC-SERVER-CASE-V3` and include a valid `qualified_handoff`. Assert:

```javascript
assert.deepEqual(
  restored.visualCase.server_sync.qualified_handoff,
  serverCase.qualified_handoff,
);
assert.equal(restored.visualCase.registration.status, 'draft');
assert.equal(restored.visualCase.qc_result.status, 'needs_review');
```

Add a regression test that a V2 admin payload is rejected with `unsupported_server_schema`, proving version changes are explicit.

- [ ] **Step 2: Run the focused Node test and verify RED**

Run:

```powershell
node --test tests/visual-qc-server-client.test.mjs
```

Expected: the V3 fixture is rejected and provenance is absent from restored sync metadata.

- [ ] **Step 3: Implement V3 restoration**

Require `VISUAL-QC-SERVER-CASE-V3` in `restoreAdminServerCase`. After applying the server job:

```javascript
restored.intake = clone(
  serverCase.intake || { batch_id: null, entry_id: null },
);
restored.server_sync.qualified_handoff = clone(
  serverCase.qualified_handoff,
);
```

Do not map `acceptance_action` to registration status, QC result, Golden status, annotations, or repair advice.

- [ ] **Step 4: Run the focused Node test and verify GREEN**

Run the Step 2 command.

Expected: all tests pass.

- [ ] **Step 5: Commit the client contract**

```powershell
git add assets/visual-qc-workbench/visual-qc-server-client.js tests/visual-qc-server-client.test.mjs
git commit -m "feat: restore server handoff provenance"
```

### Task 5: Enforce Provenance In Dataset Eligibility

**Files:**
- Modify: `scripts/visual_qc/server/service.py`
- Modify: `scripts/visual_qc/server/store.py`
- Modify: `tests/test_visual_qc_training_manifest.py`
- Modify: `knowledge-base/visual-qc-dataset-audit-v1-schema.json`

- [ ] **Step 1: Add failing training-gate tests**

Create a valid reviewed physical case, then set `qualified_handoff_json = NULL` directly to represent a legacy row. Assert dataset audit reports:

```python
self.assertEqual(case["status"], "excluded")
self.assertEqual(
    case["blocking_reason"],
    "qualified_handoff_provenance_required",
)
```

Assert the case is absent from training manifest, COCO, and bundle outputs. Keep the existing nonphysical and registration-review reasons unchanged.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_visual_qc_training_manifest -v
```

Expected: the null-provenance legacy row remains eligible.

- [ ] **Step 3: Add the provenance gate before review gates**

Include `cases.qualified_handoff_json` in `list_dataset_audit_cases`. In `training_audit`, order reasons:

```python
if record["evidence_role"] != "physical_capture":
    reason = "non_physical_evidence"
elif record["qualified_handoff"] is None:
    reason = "qualified_handoff_provenance_required"
elif record["job_status"] != "succeeded":
    reason = "processing_incomplete"
elif registration_review is None:
    reason = "registration_review_required"
elif qc_review is None:
    reason = "final_qc_review_required"
else:
    status = "eligible"
```

Use the same gate in training-manifest selection, not only the explanatory audit endpoint. Extend the audit schema reason enum with `qualified_handoff_provenance_required`.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command.

Expected: all tests pass and the legacy row is excluded from every training artifact.

- [ ] **Step 5: Commit the dataset gate**

```powershell
git add scripts/visual_qc/server/service.py scripts/visual_qc/server/store.py tests/test_visual_qc_training_manifest.py knowledge-base/visual-qc-dataset-audit-v1-schema.json
git commit -m "feat: gate training on handoff provenance"
```

### Task 6: Full Regression, Browser QA, And Project Facts

**Files:**
- Modify after evidence is collected: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`
- Modify after evidence is collected: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Overview.md`
- Modify after evidence is collected: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Task Index.md`
- Modify after evidence is collected: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Decisions.md`
- Modify after evidence is collected: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Risks.md`
- Modify after evidence is collected: `C:/Users/Mercurluto/OneDrive/AI/90_Meta/System Checks/2026-07-23 Daily Architecture Check.md`
- Modify: `docs/superpowers/plans/2026-07-23-server-qualified-handoff-provenance.md`

- [ ] **Step 1: Run all Python tests**

Run:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: zero failures and zero errors.

- [ ] **Step 2: Run all Node tests**

Run:

```powershell
node --test tests/*.test.mjs
```

Expected: zero failures.

- [ ] **Step 3: Run static and contract checks**

Run:

```powershell
python -m compileall scripts visual_qc_server.py
python -c "import json, pathlib; [json.loads(p.read_text(encoding='utf-8')) for p in pathlib.Path('knowledge-base').glob('*schema.json')]"
python -c "from pathlib import Path; bad=[str(p) for p in Path('.').rglob('*') if p.is_file() and p.suffix in {'.py','.js','.mjs','.json','.md'} and '\ufffd' in p.read_text(encoding='utf-8', errors='ignore')]; assert not bad, bad"
git diff --check
```

Expected: all commands exit `0`.

- [ ] **Step 4: Run a local end-to-end two-side handoff**

Using temporary directories and the existing synthetic KM4 fixture:

1. Stage a controlled two-side package.
2. Publish physical registration acceptance.
3. Start a local Visual-QC API with a temporary SQLite database.
4. Run the physical handoff against localhost with `--wait`.
5. Fetch both admin case details.
6. Assert each server case contains the exact per-side action and the same three evidence hashes.
7. Assert no report or overlay body exists under server storage.
8. Assert the local source package, acceptance report, and overlays remain byte-identical.

Expected: both cases reach server job success while registration review remains required.

- [ ] **Step 5: Perform P3 browser restoration QA**

Start the existing local workbench server, open the admin case list, and verify:

- list requests accept `VISUAL-QC-ADMIN-CASE-LIST-V2`;
- opening a case accepts `VISUAL-QC-SERVER-CASE-V3`;
- image, pan/zoom, registration candidate/manual fallback, and review controls still work;
- provenance restoration does not visually mark registration or QC as approved;
- desktop and 390px layouts remain readable with no overlap or contrast regression.

Capture screenshots and record the route, viewport, and interaction evidence in the project ledger.

- [ ] **Step 6: Review the diff against every design requirement**

Explicitly verify:

- server stores only compact hashes/action/constants;
- new physical admission cannot omit intake or provenance;
- proxy evidence cannot claim physical provenance;
- idempotent retries cannot drift;
- old rows stay readable but are not training eligible;
- response schema identifiers changed wherever payload shape changed;
- workbench preserves provenance without changing review facts;
- no production deployment, real-photo upload, or field-accuracy claim occurred.

- [ ] **Step 7: Update project facts**

Record implementation commits, test counts, P3 evidence, production gap, and the unchanged real KM4/F151 photo gate in the coordination ledger, Vault `Overview.md`, `Task Index.md`, `Decisions.md`, `Risks.md`, and the daily architecture check. Mark all completed plan checkboxes only from command evidence.

- [ ] **Step 8: Commit closeout records**

```powershell
git add docs/superpowers/plans/2026-07-23-server-qualified-handoff-provenance.md
git commit -m "docs: close server handoff provenance plan"
git -C G:/Programming/mainboard-repair-enablement add PROJECT_LEDGER.md
git -C G:/Programming/mainboard-repair-enablement commit -m "docs: record server handoff provenance"
```

Vault files are durable coordination facts rather than files in either Git repository; verify their UTF-8 bodies after `apply_patch` writes.
