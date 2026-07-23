# Physical Acceptance-Qualified Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed, resumable command that imports only the exact controlled physical-photo package represented by a valid local registration-acceptance run.

**Architecture:** A new `physical_handoff` module validates package, acceptance JSON/overlays, and archived intake as one correlated evidence set, then delegates transfer to the existing resumable importer. It publishes a separate hash-bound handoff receipt while preserving the server workbench as the only registration approval surface. The real multipart transport is hardened to upload the same bytes it verifies.

**Tech Stack:** Python 3, OpenCV, JSON/JSON Schema, existing visual-QC source-library/intake/server modules, `unittest`, filesystem locks/fsync, HTTPS multipart transport.

---

### Task 1: Define And Validate The Handoff Contract

**Files:**
- Create: `scripts/visual_qc/physical_handoff.py`
- Create: `knowledge-base/visual-qc-physical-handoff-v1-schema.json`
- Create: `tests/test_visual_qc_physical_handoff.py`

- [x] **Step 1: Write failing package/report correlation tests**

Create temporary controlled packages with `stage_source_package`, publish acceptance evidence with `publish_physical_registration_run`, and assert the intended API:

```python
evidence = validate_physical_handoff_evidence(
    package_path=package_path,
    acceptance_report_path=acceptance_dir / "physical-registration-run.json",
    project_root=ROOT,
    library_root=library_root,
)
self.assertEqual(evidence["package"]["manifest_sha256"], report["source_package"]["manifest_sha256"])
self.assertEqual(evidence["acceptance"]["sha256"], sha256_file(acceptance_report_path))
self.assertEqual([row["entry_id"] for row in evidence["entries"]], expected_entry_ids)
```

Add independent failures for changed package identity, board/capture identity, missing/extra/duplicate entries, changed image metadata, retake, processing issue, missing overlay, corrupt overlay bytes, overlay path escape, and a changed proxy inventory.

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_visual_qc_physical_handoff -v
```

Expected: import failure because `scripts.visual_qc.physical_handoff` does not exist.

- [x] **Step 3: Implement exact-byte report and artifact validation**

Define `HANDOFF_SCHEMA_VERSION = "VISUAL-QC-PHYSICAL-HANDOFF-V1"`, a typed `PhysicalHandoffError(code, message)`, `validate_physical_handoff_evidence(*, package_path, acceptance_report_path, project_root, library_root) -> dict`, and `validate_physical_handoff_receipt(receipt) -> None`.

Read acceptance bytes once, hash and parse the same bytes, call `validate_physical_registration_report`, correlate every package/report/intake field, validate PNG signatures/dimensions/hash from the declared relative artifacts, and reject `image_retake_required` or `processing_issue`. Return normalized evidence with the derived archived intake path; never return absolute paths in serializable receipt fields.

The JSON Schema must fix `field_accuracy_claim_allowed` to `false`, `registration_review_required` to `true`, enumerate statuses/actions/states, reject additional properties, and require exact lowercase SHA-256 values.

- [x] **Step 4: Run focused tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_visual_qc_physical_handoff -v
python -c "import json; json.load(open('knowledge-base/visual-qc-physical-handoff-v1-schema.json', encoding='utf-8'))"
```

Expected: package/report/artifact tests pass and the schema parses.

### Task 2: Build Durable Resumable Handoff Receipts

**Files:**
- Modify: `scripts/visual_qc/physical_handoff.py`
- Modify: `tests/test_visual_qc_physical_handoff.py`

- [x] **Step 1: Write failing dry-run, transfer, resume, and conflict tests**

Exercise this API with a fake transport:

```python
receipt = run_physical_handoff(
    package_path=package_path,
    acceptance_report_path=acceptance_report_path,
    project_root=ROOT,
    library_root=library_root,
    handoff_root=handoff_root,
    transport=transport,
    dry_run=True,
)
self.assertEqual(receipt["schema_version"], "VISUAL-QC-PHYSICAL-HANDOFF-V1")
self.assertEqual(receipt["status"], "validated")
self.assertEqual(receipt["acceptance"]["sha256"], acceptance_sha256)
self.assertTrue(all(row["registration_review_required"] for row in receipt["entries"]))
```

Add tests for candidate/manual mixed admission, no credential/path leakage, successful completion with `--wait`, non-terminal `processing`, `partial_failure`, all-entry `failed`, stop/continue behavior, idempotent resume, process interruption reconstruction from the nested intake receipt, report/package hash conflict, handoff-root containment, existing reparse directories, same-target threads/processes, source immutability, and durable write failure.

- [x] **Step 2: Run focused tests and verify RED**

Run the new test class and confirm failure because `run_physical_handoff` is missing.

- [x] **Step 3: Implement the handoff runner and receipt projection**

Implement `run_physical_handoff(*, package_path, acceptance_report_path, project_root, library_root, handoff_root, transport, dry_run=False, wait_for_jobs=False, continue_on_error=False, poll_interval_seconds=1, maximum_job_polls=300) -> dict`.

Use one per-target thread/process lock. Prepare a durable handoff directory outside project/library roots, persist the nested intake receipt at `intake-receipt.json`, call existing `run_intake`, project the result into `physical-handoff.json`, validate the projected receipt before atomic write, and fsync the parent. On resume, require matching package manifest/report/batch/entry hashes before retaining server ids. Never delete or rewrite source/acceptance files.

Derive status deterministically from transfer states: dry-run `validated`; any non-terminal without failures `processing`; all completed `transferred`; failures plus any reached server `partial_failure`; otherwise `failed`.

- [x] **Step 4: Run focused tests and verify GREEN**

Run all handoff tests twice, including process-lock and resume cases. Expected: identical evidence fields and no duplicate fake uploads.

### Task 3: Close The Multipart Read Race

**Files:**
- Modify: `scripts/import_visual_qc_batch.py`
- Modify: `tests/test_visual_qc_intake.py`

- [x] **Step 1: Write failing same-byte transport tests**

Add a request interception test that mutates the source after manifest validation but before multipart construction and expects no HTTP request:

```python
with self.assertRaisesRegex(VisualQcIntakeTransportError, "changed after validation"):
    transport.upload(validated_entry, idempotency_key="intake:test")
self.assertEqual(opened_requests, [])
```

Add a positive assertion that multipart file bytes equal the exact content whose length and SHA-256 match the validated entry.

- [x] **Step 2: Run the two transport tests and verify RED**

Expected: the changed file is currently read and sent without a transport integrity error.

- [x] **Step 3: Verify and reuse one byte string in multipart construction**

In `VisualQcIntakeTransport._multipart_body`, read once and enforce:

```python
content = Path(entry["file_path"]).read_bytes()
if len(content) != entry["byte_size"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
    raise VisualQcIntakeTransportError(
        "source_changed_after_validation",
        "Visual-QC source changed after validation; upload was not attempted.",
    )
```

Append that same `content` object to multipart chunks. Do not re-open the path and do not include paths or digest values in the public error.

- [x] **Step 4: Run intake and handoff suites and verify GREEN**

Run:

```powershell
python -m unittest tests.test_visual_qc_intake tests.test_visual_qc_physical_handoff -v
```

Expected: all tests pass with no request on changed bytes.

### Task 4: Add The Operator CLI And Documentation

**Files:**
- Create: `scripts/handoff_visual_qc_physical_package.py`
- Modify: `tests/test_visual_qc_physical_handoff.py`
- Modify: `README.md`
- Modify: `knowledge-base/README.md`

- [x] **Step 1: Write failing subprocess tests**

Cover `--help`, successful dry-run JSON, blocked-retake exit `2`, invalid package/report exit `2`, transfer failure exit `1`, no absolute path or credential in stdout/stderr, and stable status/count fields.

- [x] **Step 2: Run CLI tests and verify RED**

Expected: failure because `scripts/handoff_visual_qc_physical_package.py` does not exist.

- [x] **Step 3: Implement CLI composition**

Parse package, acceptance report, library root, handoff root, `--dry-run`, `--api-base`, `--credential-file`, `--actor-id`, `--wait`, `--continue-on-error`, and `--allow-http-localhost`. Reuse `_load_credentials` and `VisualQcIntakeTransport`; emit only stable machine-readable JSON. Map `PhysicalHandoffError`/validation/safety failures to exit `2`, transfer statuses to exit `0`/`1`, and unexpected failures to a path-redacted exit `1` response.

- [x] **Step 4: Document the canonical owner workflow**

Document exactly:

```text
stage -> source audit -> physical acceptance -> acceptance-qualified handoff dry-run -> controlled transfer -> server registration review
```

State that only Milo supplies real photos, Codex is the operator, technicians never upload, manual/candidate admission is not approval, and retake/processing failures block transfer.

- [x] **Step 5: Run CLI tests and verify GREEN**

Expected: all subprocess contracts and direct `--help` pass.

### Task 5: Full Verification, Review, And Durable Project State

**Files:**
- Modify: `PROJECT_LEDGER.md` in `G:/Programming/mainboard-repair-enablement`
- Modify when facts change: Vault `Overview.md`, `Task Index.md`, `Risks.md`, and `2026-07-23 Daily Architecture Check.md`

- [x] Run all relevant source-library, audit, acceptance, handoff, and intake tests.
- [x] Run the complete Python suite and require zero failures.
- [x] Run the complete Node suite and require zero failures.
- [x] Run Python compilation, JSON/Schema parsing, UTF-8/U+FFFD checks, and `git diff --check`.
- [x] Run a temporary two-side stage -> audit -> acceptance -> handoff dry-run -> fake resumable transfer, compare source/acceptance snapshots before and after, and inspect receipt identity/status.
- [x] Request independent code review; resolve each blocking finding through a new failing test followed by the minimal fix and rerun relevant/full suites.
- [ ] Commit implementation locally, update and commit coordination/Vault facts, run Project Closeout Check, and do not push or deploy under the current runtime constraint.
