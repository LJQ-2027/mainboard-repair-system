# Visual-QC Repair Case Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an append-only local evidence layer that links immutable physical-photo packages to supplied repair-case facts without creating visual defect, Golden, training, repair, or accuracy claims.

**Architecture:** A pure contract module validates exact V1 structures, evidence references, corrections, boundaries, and deterministic completeness. A separate controlled-library module resolves validated source packages, preserves opaque supporting files, and publishes a no-clobber revision chain with the existing path, lock, fsync, and content-addressed storage patterns. A thin CLI accepts operator-authored JSON and explicit package/file assignments; no server or browser contract changes in V1.

**Tech Stack:** Python 3 standard library, existing OpenCV-backed source-package validation, JSON Schema Draft 2020-12, `unittest`, repository-external controlled library.

---

### Task 1: Define The Pure Repair-Case Contract

**Files:**
- Create: `scripts/visual_qc/repair_case_contract.py`
- Create: `knowledge-base/visual-qc-repair-case-source-v1-schema.json`
- Create: `tests/test_visual_qc_repair_case_contract.py`

- [x] **Step 1: Write failing exact-shape and completeness tests**

Create a canonical payload fixture with exact fields:

```python
def canonical_payload():
    return {
        "schema_version": "VISUAL-QC-REPAIR-CASE-SOURCE-V1",
        "repair_case_id": "case-km4-0001",
        "revision": 1,
        "previous_manifest_sha256": None,
        "source_origin": "milo_supplied",
        "board_key": "km4-f151",
        "board_id": "BOARD-KM4-F151-MAIN-V1.2",
        "device_models": ["KM4"],
        "package_links": [package_link()],
        "supporting_evidence": [],
        "reported_symptoms": [],
        "findings": [],
        "repair_actions": [],
        "outcome": {
            "status": "unknown",
            "description": None,
            "verification_description": None,
            "evidence_refs": [],
        },
        "corrections": [],
        "completeness": "photos_only",
        "boundaries": FIXED_FALSE_BOUNDARIES,
    }
```

Require exact key sets, lowercase SHA-256, safe IDs, one-or-more compatible
device models, exact nested fields, unique IDs, and these derived states:

```python
photos_only
symptom_linked
diagnosis_linked
repair_outcome_linked
```

Validate the canonical payload with both the Python contract and the Draft
2020-12 Schema.

- [x] **Step 2: Run the contract tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_repair_case_contract -v
```

Expected: import failure because `repair_case_contract.py` does not exist.

- [x] **Step 3: Implement constants and exact validators**

Implement:

```python
REPAIR_CASE_SCHEMA_VERSION = "VISUAL-QC-REPAIR-CASE-SOURCE-V1"
CASE_ROLES = {
    "before_repair",
    "after_repair",
    "golden_reference",
    "supplemental",
}
CLAIM_STATUSES = {"reported", "suspected", "documented"}
OUTCOME_STATUSES = {
    "unknown",
    "repair_completed",
    "not_repaired",
    "non_repairable",
    "needs_followup",
}
FIXED_FALSE_BOUNDARIES = {
    "visual_defect_confirmed": False,
    "golden_approved": False,
    "training_label_allowed": False,
    "repair_instruction_allowed": False,
    "field_accuracy_claim_allowed": False,
}

```

Expose `derive_completeness(payload: dict) -> str` and
`validate_repair_case_manifest(payload: dict) -> dict`. Return a defensive
normalized copy from the validator.

The validator must reject booleans where integers are required, extra fields,
duplicate IDs, empty supplied text, invalid regions outside normalized
coordinates, an outcome description on an unsupported shape, and any boundary
value other than the fixed false object.

- [x] **Step 4: Implement evidence-reference and correction validation**

Accept only:

```python
{"kind": "package_entry", "package_id": "pkg-before", "entry_id": "session-main-page-1"}
{"kind": "supporting_evidence", "evidence_id": "repair-sheet-1"}
```

Require every reference to resolve in the current manifest. Require correction
targets and replacement IDs to resolve across a supplied historical fact index,
and reject correction-to-correction targets or two active corrections for one
fact.

- [x] **Step 5: Add the JSON Schema**

Mirror the exact Python contract with `additionalProperties: false` at every
object level. Require fixed false boundaries and conditional completeness:
Schema validates shape; Python remains authoritative for cross-reference and
revision-history checks.

- [x] **Step 6: Verify GREEN and commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_repair_case_contract -v
```

Expected: all Task 1 tests pass.

Commit:

```powershell
git add scripts/visual_qc/repair_case_contract.py knowledge-base/visual-qc-repair-case-source-v1-schema.json tests/test_visual_qc_repair_case_contract.py
git commit -m "feat: define visual qc repair case contract"
```

### Task 2: Resolve Immutable Packages And Supporting Evidence

**Files:**
- Create: `scripts/visual_qc/repair_case_library.py`
- Create: `tests/test_visual_qc_repair_case_library.py`
- Reuse: `scripts/visual_qc/source_library.py`

- [x] **Step 1: Write failing source-package link tests**

Stage real test source packages through `stage_source_package`, then require:

```python
links = resolve_package_links(
    project_root=ROOT,
    library_root=library,
    assignments=[
        ("before_repair", before_package_path),
        ("after_repair", after_package_path),
    ],
    board_key="km4-f151",
)
```

Each link must contain the exact source-package manifest SHA-256, package ID,
capture stage, role, and ordered entry IDs. Reject:

- board mismatch;
- role/stage mismatch except `supplemental`;
- duplicate package;
- revoked/changed source package;
- symlink, junction, reparse, or escaping package path.

- [x] **Step 2: Run package-link tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_repair_case_library.VisualQcRepairCaseLibraryTests.test_package_links -v
```

Expected: import or missing-function failure.

- [x] **Step 3: Implement package resolution**

Implement `resolve_package_links(*, project_root: Path, library_root: Path,
assignments: list[tuple[str, Path]], board_key: str) -> list[dict]`.

Call `validate_source_package` for every assignment. Use this role/stage map:

```python
{
    "before_repair": "before_repair",
    "after_repair": "after_repair",
    "golden_reference": "golden_reference",
}
```

`supplemental` accepts any existing capture stage but cannot alter it.

- [x] **Step 4: Write failing supporting-evidence tests**

Cover PDF, UTF-8 TXT, CSV, XLS, XLSX, PNG, and JPEG detection; exact SHA-256,
byte count, original filename, description, and canonical path:

```text
objects/case-evidence/<sha-prefix>/<sha256>.<extension>
```

Reject empty files, executable/archive/unknown formats, invalid UTF-8 text,
files over 100 MiB, more than 50 assignments, duplicate IDs, source changes
during hashing/copy, hard-linked inputs, and unsafe paths.

- [x] **Step 5: Implement stable evidence inspection and storage**

Implement `inspect_supporting_evidence(assignments: list[tuple[str, Path]],
descriptions: dict[str, str]) -> list[dict]` and
`store_supporting_evidence(*, library_root: Path, inspected: list[dict]) ->
None`.

Read/hash through stable regular-file descriptors. Store with exclusive
creation and byte-for-byte post-copy verification. Reuse identical canonical
objects; reject conflicting bytes and never overwrite.

- [x] **Step 6: Verify GREEN and commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_repair_case_library -v
```

Expected: all Task 2 tests pass.

Commit:

```powershell
git add scripts/visual_qc/repair_case_library.py tests/test_visual_qc_repair_case_library.py
git commit -m "feat: resolve repair case evidence"
```

### Task 3: Publish And Validate The Append-Only Revision Chain

**Files:**
- Modify: `scripts/visual_qc/repair_case_library.py`
- Modify: `tests/test_visual_qc_repair_case_library.py`

- [ ] **Step 1: Write failing revision-publication tests**

Require:

```python
result = stage_repair_case_revision(
    project_root=ROOT,
    library_root=library,
    repair_case_id="case-km4-0001",
    board_key="km4-f151",
    package_assignments=[("before_repair", package_path)],
    case_record=case_record,
    supporting_assignments=[],
    previous_manifest_path=None,
)
```

The first revision must publish:

```text
cases/case-km4-0001/revisions/0001/repair-case.json
cases/case-km4-0001/revisions/0001/.complete
```

The result must report `created`, revision `1`, manifest SHA-256, completeness,
package count, and supporting-evidence count.

- [ ] **Step 2: Run publication tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_repair_case_library.VisualQcRepairCaseLibraryTests.test_first_revision_publication -v
```

Expected: missing-function failure.

- [ ] **Step 3: Implement manifest construction and atomic publication**

Implement these public APIs:

```text
build_repair_case_revision(
  project_root, library_root, repair_case_id, board_key,
  package_assignments, case_record, supporting_assignments,
  previous_manifest_path
) -> dict
stage_repair_case_revision(**options) -> dict
validate_repair_case_revision(
  manifest_path, project_root, library_root
) -> dict
```

Reuse the source-library controlled-path and durability behavior through
publicly named helpers extracted without changing source-package behavior.
Publish into a temporary sibling directory, fsync files/directories, rename
once, then create and fsync `.complete`.

- [ ] **Step 4: Write and implement revision-chain tests**

Cover:

- exact idempotent replay returns `existing`;
- conflicting replay fails;
- revision increments by one;
- previous manifest SHA-256 binding;
- contiguous history with no fork or gap;
- board/case/source-origin invariance;
- prior packages, evidence metadata, facts, and actions remain unchanged;
- correction references a historical fact and one replacement;
- modified historical manifest or object invalidates the chain;
- concurrent publishers yield one created revision and one exact replay;
- failed publication leaves no complete revision.

- [ ] **Step 5: Add executable path-boundary tests**

Create Windows junctions or POSIX symlinks for:

- library root;
- case root;
- revisions root;
- prior manifest;
- supporting source;
- canonical evidence object.

Also cover special files where supported and hard-link count rejection. Every
unsafe case must fail before modifying a completed revision.

- [ ] **Step 6: Verify GREEN and commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_repair_case_library -v
```

Expected: all Task 3 tests pass.

Commit:

```powershell
git add scripts/visual_qc/source_library.py scripts/visual_qc/repair_case_library.py tests/test_visual_qc_repair_case_library.py
git commit -m "feat: publish repair case revisions"
```

### Task 4: Add The Operator CLI

**Files:**
- Create: `scripts/stage_visual_qc_repair_case.py`
- Create: `tests/test_stage_visual_qc_repair_case_cli.py`
- Modify: `deploy/visual-qc-runtime-files.txt`

- [ ] **Step 1: Write failing CLI tests**

The CLI must accept:

```text
--library-root PATH
--repair-case-id ID
--board-key KEY
--case-record PATH
--source-package ROLE=PATH
--supporting-file EVIDENCE_ID=PATH
--previous-manifest PATH
```

`--source-package` is repeatable and required. Supporting files and previous
manifest are optional. Require typed compact JSON with exit codes:

- `0`: `created` or exact `existing`;
- `2`: validation failure;
- `1`: unexpected failure.

Assert no image/model/side inference and no network call.

- [ ] **Step 2: Run CLI tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_stage_visual_qc_repair_case_cli -v
```

Expected: script missing.

- [ ] **Step 3: Implement the CLI**

Use a parser that converts argparse errors to `IntakeValidationError`. Load the
case-record JSON as strict UTF-8 and reject duplicate JSON keys recursively.
Parse assignments only on the first `=` and require safe IDs.

Call only `stage_repair_case_revision`; print:

```json
{
  "status": "ok",
  "state": "created",
  "repair_case_id": "case-km4-0001",
  "revision": 1,
  "completeness": "photos_only",
  "manifest_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "manifest_path": "C:/controlled-library/cases/case-km4-0001/revisions/0001/repair-case.json"
}
```

- [ ] **Step 4: Add the CLI and both new modules to the runtime allowlist**

Add:

```text
scripts/stage_visual_qc_repair_case.py
```

`scripts/visual_qc` is already included as a directory. Confirm the exact
deployment archive rehearsal still includes the new CLI and unchanged runtime
manifest identity semantics.

- [ ] **Step 5: Verify GREEN and commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_stage_visual_qc_repair_case_cli tests.test_visual_qc_deployment -v
```

Expected: all Task 4 tests pass.

Commit:

```powershell
git add scripts/stage_visual_qc_repair_case.py tests/test_stage_visual_qc_repair_case_cli.py deploy/visual-qc-runtime-files.txt
git commit -m "feat: stage visual qc repair cases"
```

### Task 5: Prove Non-Contamination And Close The Local Feature

**Files:**
- Modify: `README.md`
- Modify: `docs/visual-qc-capture-intake-spec-2026-07-20.md`
- Modify: `docs/superpowers/plans/2026-07-24-visual-qc-repair-case-source.md`
- Create: `tests/test_visual_qc_repair_case_boundaries.py`

- [ ] **Step 1: Write boundary and end-to-end tests**

Build:

1. a photo-only before-repair case;
2. a two-package before/after case;
3. a revision that adds documented finding, action, and outcome;
4. a correction revision.

Assert that no case manifest or case object appears in:

- visual annotation records;
- Golden state;
- QC result;
- COCO export;
- training manifest;
- governed bundle;
- server database or API payloads.

Assert every boundary stays false at every revision.

- [ ] **Step 2: Document the owner-only case flow**

Document:

```text
stage source package(s)
-> audit source library
-> stage repair case revision
-> validate append-only case chain
-> later run physical acceptance on selected photo package
```

State explicitly that completeness is context availability, not accuracy or
training eligibility. Milo supplies material; Codex performs IDs, package
roles, structured transcription, and missing-field reporting.

- [ ] **Step 3: Run focused and full verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_repair_case_contract tests.test_visual_qc_repair_case_library tests.test_stage_visual_qc_repair_case_cli tests.test_visual_qc_repair_case_boundaries -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
$files = rg --files tests | Where-Object { $_ -match '\.test\.mjs$' }; node --test $files
.\.venv\Scripts\python.exe -m compileall -q scripts tests
```

Also parse all modified JSON and PowerShell, run `git diff --check`, and scan
modified durable files as strict UTF-8 without U+FFFD.

- [ ] **Step 4: Run a repository-external integration rehearsal**

Use temporary generated images and a text supporting record to execute:

```text
two source packages
-> source-library audit
-> case revision 1
-> case revision 2
-> full chain validation
```

Require original/source/supporting object hashes unchanged, deterministic exact
replay, and no server/network action. Mark this synthetic rehearsal as plumbing
evidence only.

- [ ] **Step 5: Request independent review**

Review exact contract shape, reference resolution, source-package hash binding,
supporting-file safety, revision immutability, concurrency, no-clobber
publication, downstream non-contamination, tests, and documentation. Fix every
Critical or Important issue and rerun affected gates.

- [ ] **Step 6: Commit closeout and update durable facts**

Commit implementation closeout:

```powershell
git add README.md docs/visual-qc-capture-intake-spec-2026-07-20.md docs/superpowers/plans/2026-07-24-visual-qc-repair-case-source.md tests/test_visual_qc_repair_case_boundaries.py
git commit -m "docs: close visual qc repair case source plan"
```

Then update the coordination ledger, Vault Agent Entry, Overview, Task Index,
Decisions, Risks, and the daily architecture check with:

- final implementation commit;
- focused/full test counts;
- independent review result;
- synthetic-only evidence boundary;
- production still `f278061`;
- real-case staging waiting for Milo's exact first case package.
