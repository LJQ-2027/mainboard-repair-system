# Visual-QC Repair Evidence Link V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish immutable links from repair-case facts to exact engineering targets and registered physical photos, project them read-only into the local Visual-QC server, and expose source-safe navigation in the internal workbench.

**Architecture:** The repository-external controlled library remains authoritative. Pure Python contracts validate deterministic physical-evidence snapshots and append-only link manifests; an owner CLI publishes and synchronizes them. The local FastAPI/SQLite server stores an immutable projection and derives active/stale/unavailable state at read time, while the browser consumes only data-administrator routes and never turns a link into an annotation or QC conclusion.

**Tech Stack:** Python 3.11, `jsonschema` Draft 2020-12, `unittest`, FastAPI, SQLite, browser ES modules, Canvas 2D, Node test runner, existing controlled-library and Visual-QC patterns.

---

## Scope And File Map

### Contract And Controlled Library

- Create `knowledge-base/visual-qc-linkable-physical-evidence-v1-schema.json`:
  deterministic reduced server-evidence export contract.
- Create `knowledge-base/visual-qc-repair-evidence-link-v1-schema.json`:
  exact append-only link manifest contract.
- Create `scripts/visual_qc/repair_evidence_link_contract.py`:
  pure shape, hash, boundary, reference, and revision validation.
- Create `scripts/visual_qc/repair_evidence_engineering.py`:
  canonical board-asset and engineering-target snapshots.
- Create `scripts/visual_qc/repair_evidence_export.py`:
  convert one admin case detail into linkable physical evidence.
- Create `scripts/visual_qc/repair_evidence_link_library.py`:
  build, validate, publish, reopen, and replay link revisions.
- Create `scripts/export_visual_qc_linkable_evidence.py`:
  owner CLI for read-only local-server export.
- Create `scripts/stage_visual_qc_repair_evidence_link.py`:
  owner CLI for controlled link publication.

### Local Server Projection

- Create `knowledge-base/visual-qc-repair-evidence-link-list-v1-schema.json`:
  redacted admin list response.
- Create `knowledge-base/visual-qc-repair-evidence-link-detail-v1-schema.json`:
  canonical admin detail plus derived health.
- Modify `scripts/visual_qc/server/store.py`:
  additive link-revision and referenced-case tables, import, list, and retention
  exclusion.
- Modify `scripts/visual_qc/server/service.py`:
  projection import, read-time health validation, and admin responses.
- Modify `scripts/visual_qc/server/api.py`:
  data-administrator-only import/list/detail routes.
- Create `scripts/sync_visual_qc_repair_evidence_link.py`:
  owner-only idempotent server projection.

### Internal Workbench

- Modify `assets/visual-qc-workbench/index.html`:
  compact repair-evidence panel.
- Modify `assets/visual-qc-workbench/styles.css`:
  neutral evidence states and responsive layout.
- Modify `assets/visual-qc-workbench/visual-qc-server-client.js`:
  list/detail retrieval and response validation.
- Create `assets/visual-qc-workbench/repair-evidence-links.js`:
  pure presentation, current-binding, and location-state helpers.
- Modify `assets/visual-qc-workbench/app.js`:
  load, render, cross-case restore, and canvas centering.

### Tests And Runtime

- Create `tests/test_visual_qc_repair_evidence_link_contract.py`.
- Create `tests/test_visual_qc_repair_evidence_export.py`.
- Create `tests/test_export_visual_qc_linkable_evidence_cli.py`.
- Create `tests/test_visual_qc_repair_evidence_link_library.py`.
- Create `tests/test_stage_visual_qc_repair_evidence_link_cli.py`.
- Create `tests/test_visual_qc_repair_evidence_link_server.py`.
- Create `tests/test_sync_visual_qc_repair_evidence_link_cli.py`.
- Create `tests/test_visual_qc_repair_evidence_link_boundaries.py`.
- Create `tests/visual-qc-repair-evidence-links.test.mjs`.
- Modify `tests/test_visual_qc_maintenance.py`.
- Modify `tests/test_visual_qc_deployment.py`.
- Modify `tests/test_visual_qc_documentation.py`.
- Modify `deploy/visual-qc-runtime-files.txt`.
- Modify `README.md`.
- Modify `docs/visual-qc-capture-intake-spec-2026-07-20.md`.
- Modify `docs/visual-qc-server-api-2026-07-20.md`.
- Modify `docs/visual-qc-workbench-2026-07-17.md`.
- Modify `docs/visual-qc-f069-first-physical-acceptance-2026-07-24.md`.

### Repository-External Real Evidence

- Export under
  `G:/Programming/_Data/Visual-QC-Controlled-Source/incoming/repair-evidence-links/case005/`.
- Publish under
  `G:/Programming/_Data/Visual-QC-Controlled-Source/library/repair-evidence-links/link-case005-f069-after/revisions/0001/`.
- Import only into
  `G:/Programming/_Data/Visual-QC-Controlled-Source/local-server/visual-qc.sqlite3`.

Production `f278061` is not targeted.

### Task 1: Pure Link And Physical-Evidence Contracts

**Files:**
- Create: `tests/test_visual_qc_repair_evidence_link_contract.py`
- Create: `scripts/visual_qc/repair_evidence_link_contract.py`
- Create: `knowledge-base/visual-qc-linkable-physical-evidence-v1-schema.json`
- Create: `knowledge-base/visual-qc-repair-evidence-link-v1-schema.json`

- [ ] **Step 1: Write failing canonical contract tests**

Create helpers with exact V1 shapes:

```python
def physical_snapshot():
    qualified_handoff = {
        "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
        "handoff_schema_version": "VISUAL-QC-PHYSICAL-HANDOFF-V1",
        "source_package_manifest_sha256": "a" * 64,
        "archived_intake_manifest_sha256": "b" * 64,
        "acceptance_report_sha256": "c" * 64,
        "acceptance_action": "manual_registration_required",
        "registration_review_required": True,
        "field_accuracy_claim_allowed": False,
    }
    snapshot = {
        "schema_version": "VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1",
        "physical_evidence_id": "case005-main-page-2",
        "server_case_id": "vqc_page_2",
        "intake": {
            "batch_id": "f069-case005-after-batch",
            "entry_id": "feishu-case005-board-01-after-main-page-2",
        },
        "board_key": "bg6h-f069",
        "board_id": "BOARD-F069-MAIN-V1.2",
        "side_id": "main_page_2",
        "capture_stage": "after_repair",
        "evidence_role": "physical_capture",
        "qualified_handoff": qualified_handoff,
        "qualified_handoff_sha256": canonical_sha256(qualified_handoff),
        "image_id": "img_page_2",
        "image_sha256": "d" * 64,
        "job_id": "job_page_2",
        "registration_review_id": "regrev_page_2",
        "registration": {
            "method": "reviewed_manual_four_point",
            "board_to_image_matrix": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
            "anchors": [
                {"board": [0.1, 0.1], "image": [0.1, 0.1]},
                {"board": [0.9, 0.1], "image": [0.9, 0.1]},
                {"board": [0.9, 0.9], "image": [0.9, 0.9]},
                {"board": [0.1, 0.9], "image": [0.1, 0.9]},
            ],
            "check_points": [
                {"board": [0.5, 0.5], "image": [0.5, 0.5], "error": 0.001}
            ],
            "error": {"count": 1, "rms": 0.001, "maximum": 0.001},
        },
    }
    snapshot["physical_evidence_snapshot_sha256"] = canonical_sha256(snapshot)
    return snapshot


def fixed_boundaries():
    return {
        "visual_defect_confirmed": False,
        "qc_annotation_created": False,
        "golden_approved": False,
        "training_label_allowed": False,
        "repair_causality_confirmed": False,
        "repair_instruction_allowed": False,
        "field_accuracy_claim_allowed": False,
    }


def board_snapshot():
    snapshot = {
        "board_key": "bg6h-f069",
        "board_id": "BOARD-F069-MAIN-V1.2",
        "catalog_asset": {
            "path": "knowledge-base/repair-workbench-boards.json",
            "sha256": "f" * 64,
            "entry_sha256": "1" * 64,
        },
        "compiled_sources": [
            {
                "kind": "cross_source_dataset",
                "path": "knowledge-base/f069-cross-source-registration.json",
                "sha256": "2" * 64,
            },
            {
                "kind": "side_manifest",
                "path": "knowledge-base/f069-board-sides.json",
                "sha256": "3" * 64,
            },
        ],
    }
    snapshot["board_snapshot_sha256"] = canonical_sha256(snapshot)
    return snapshot


def binding():
    fact_snapshot = {
        "kind": "reported_symptom",
        "fact_id": "case005-symptom-no-power",
        "display": {
            "text": "不开机",
            "claim_status": None,
        },
    }
    return {
        "binding_id": "case005-no-power-page-2",
        "repair_case_reference_id": "case005-r1",
        "source_fact": {
            **fact_snapshot,
            "fact_sha256": canonical_sha256(fact_snapshot),
        },
        "target": {
            "kind": "whole_board",
            "side_id": "main_page_2",
        },
        "physical_evidence_id": "case005-main-page-2",
        "association_status": "related",
        "visibility_status": "not_assessed",
        "evidence_bases": [{"kind": "repair_case_fact"}],
        "supersedes_binding_id": None,
        "boundaries": {
            **fixed_boundaries(),
            "model_identity_resolved": False,
        },
    }
```

The canonical link manifest must use:

```python
{
    "schema_version": "VISUAL-QC-REPAIR-EVIDENCE-LINK-V1",
    "link_set_id": "link-case005-f069-after",
    "revision": 1,
    "previous_manifest_sha256": None,
    "source_origin": "codex_operator",
    "repair_case_references": [
        {
            "repair_case_reference_id": "case005-r1",
            "repair_case_id": "case-005-bg6-f069",
            "revision": 1,
            "schema_version": "VISUAL-QC-REPAIR-CASE-SOURCE-V2",
            "manifest_sha256": "e" * 64,
            "board_key": "bg6h-f069",
            "board_id": "BOARD-F069-MAIN-V1.2",
        }
    ],
    "board": board_snapshot(),
    "physical_evidence": [physical_snapshot()],
    "bindings": [binding()],
    "boundaries": fixed_boundaries(),
}
```

Add a strict loader before the validators:

```python
def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RepairEvidenceLinkContractError(
                "duplicate_json_key",
                f"Duplicate JSON key: {key}",
            )
        result[key] = value
    return result


def load_json_object_strict(path: Path) -> dict:
    text = path.read_bytes().decode("utf-8")
    value = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise RepairEvidenceLinkContractError(
            "json_object_required",
            "The JSON document must contain one object.",
        )
    return value
```

Require this loader for physical snapshots, binding records, link manifests,
and every on-disk replay/revalidation path. Tests must reject:

- duplicate JSON keys and unknown fields;
- incorrect canonical hashes;
- non-finite matrix/geometry numbers;
- top-level `model_identity_resolved`;
- a binding without its own `repair_case_reference_id`;
- zero or multiple physical-evidence references;
- cross-side evidence;
- free-text operator or human-observation fields;
- a `related` designator binding without semantic identity evidence;
- any true fixed boundary;
- invalid supersede cycles and duplicate active replacements.

Add one valid and one invalid fixture for every source-fact selector:
`reported_symptom`, `finding`, `repair_action`, and `outcome`. The outcome
fixture must use the reserved fact ID `outcome`; any other outcome fact ID
fails closed. Claim status is copied only when the selected source object
contains it.

- [ ] **Step 2: Run the contract tests and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_evidence_link_contract -v
```

Expected: import failure because `repair_evidence_link_contract` does not
exist.

- [ ] **Step 3: Implement canonical hashing and exact validators**

Create public functions `canonical_json_bytes(value: object) -> bytes`,
`canonical_sha256(value: object) -> str`,
`load_json_object_strict(path: Path) -> dict`,
`validate_physical_evidence_snapshot(value: dict) -> dict`,
`validate_repair_evidence_link_manifest(value: dict) -> dict`.

`canonical_json_bytes` must call `json.dumps` with `ensure_ascii=False`,
`sort_keys=True`, `separators=(",", ":")`, and `allow_nan=False`, then encode
UTF-8. `canonical_sha256` hashes those exact bytes. The validators first run
Draft 2020-12 schema validation, then perform every cross-reference,
association, supersession, hash, and fixed-boundary check that can be proven
from the self-contained link document, and return a deep copy. The pure
validator checks that every binding has one boolean
`model_identity_resolved`; it does not try to derive that value from the
repair-case reference summary because the approved reference contract does not
copy the repair-case identity boundary.

Use an exact safe-ID regex, deep-copy successful results, reject Python
booleans where integers are required, validate normalized geometry through the
existing registration conventions, and calculate the physical snapshot hash
from every field except `physical_evidence_snapshot_sha256`.

The top-level boundary fields are exactly:

```python
FIXED_LINK_BOUNDARIES = {
    "visual_defect_confirmed": False,
    "qc_annotation_created": False,
    "golden_approved": False,
    "training_label_allowed": False,
    "repair_causality_confirmed": False,
    "repair_instruction_allowed": False,
    "field_accuracy_claim_allowed": False,
}
```

Bindings contain the same fields plus derived
`model_identity_resolved`.

- [ ] **Step 4: Add exact Draft 2020-12 schemas**

The physical schema must close the complete qualified-handoff and physical
snapshot objects. The link schema must encode:

- exact top-level fields;
- non-empty unique reference/evidence/binding IDs;
- one `physical_evidence_id` string per binding;
- association enum `related`, `possibly_related`, `not_related`, or
  `insufficient_evidence`;
- visibility enum `not_assessed`, `visible`, `not_visible`, or `occluded`;
- structured evidence bases only;
- nullable `supersedes_binding_id`;
- seven top-level fixed-false boundaries;
- per-binding derived identity boolean.

Target schemas must close all three variants: `whole_board`, `board_region`
with a normalized rectangle or polygon, and `designator` with the reviewed
engineering snapshot. Do not reference mutable external schema files; copy the
small qualified-handoff definition.

- [ ] **Step 5: Verify Python and JSON Schema parity**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_evidence_link_contract -v
```

Expected: all canonical and invalid parity cases pass.

- [ ] **Step 6: Commit**

```powershell
git add `
  knowledge-base/visual-qc-linkable-physical-evidence-v1-schema.json `
  knowledge-base/visual-qc-repair-evidence-link-v1-schema.json `
  scripts/visual_qc/repair_evidence_link_contract.py `
  tests/test_visual_qc_repair_evidence_link_contract.py
git commit -m "feat: define repair evidence link contract"
```

### Task 2: Read-Only Physical Evidence Export

**Files:**
- Create: `tests/test_visual_qc_repair_evidence_export.py`
- Create: `tests/test_export_visual_qc_linkable_evidence_cli.py`
- Create: `scripts/visual_qc/repair_evidence_export.py`
- Create: `scripts/export_visual_qc_linkable_evidence.py`

- [ ] **Step 1: Write failing normalization tests**

Build one V3 admin-case fixture containing qualified handoff, image, succeeded
job, and reviewed manual registration. Assert:

```python
snapshot = build_linkable_physical_evidence(
    server_case,
    physical_evidence_id="case005-main-page-2",
)
self.assertEqual(
    snapshot["schema_version"],
    "VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1",
)
self.assertEqual(snapshot["side_id"], "main_page_2")
self.assertEqual(
    snapshot["registration_review_id"],
    server_case["server_registration_review"]["review_id"],
)
self.assertEqual(
    snapshot["physical_evidence_snapshot_sha256"],
    canonical_sha256(
        {
            key: value
            for key, value in snapshot.items()
            if key != "physical_evidence_snapshot_sha256"
        }
    ),
)
```

Reject proxy evidence, missing qualified handoff, unreviewed registration,
case/job/review mismatch, missing intake IDs, and non-V3 responses. A valid V3
detail may contain unrelated `server_qc_review`, Golden, or candidate fields;
the exporter must ignore them and must not copy them into the reduced physical
snapshot.

- [ ] **Step 2: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_evidence_export -v
```

Expected: import failure.

- [ ] **Step 3: Implement the pure exporter**

Create `build_linkable_physical_evidence(server_case: dict, *,
physical_evidence_id: str) -> dict`. It must reject any response other than
`VISUAL-QC-SERVER-CASE-V3`, copy only the exact V1 fields, canonical-hash the
complete qualified-handoff object, calculate the complete physical snapshot
hash, call `validate_physical_evidence_snapshot`, and return the validated
copy.

The function must copy only the fields named by the V1 design, canonicalize the
complete qualified-handoff object, and call
`validate_physical_evidence_snapshot` before returning.

- [ ] **Step 4: Write failing owner-CLI tests**

Patch the HTTP reader with a deterministic V3 fixture. Assert the command:

```powershell
.\.venv\Scripts\python.exe scripts\export_visual_qc_linkable_evidence.py `
  --api-base http://127.0.0.1:3020/api/v1/visual-qc `
  --credential-file C:\secure\visual-qc-credential.json `
  --case-id vqc_page_2 `
  --physical-evidence-id case005-main-page-2 `
  --output C:\evidence\case005-main-page-2.json `
  --allow-http-localhost
```

prints compact JSON with `status=ok`, writes strict UTF-8 atomically, refuses
overwrite, sends both actor headers, rejects non-local HTTP, and never performs
a POST. Add the real localhost mode to the same test task: `--actor-id
milo-visual-data-operator` without a credential file is accepted only with
`--allow-http-localhost` and a loopback host; the same credentialless mode is
rejected for non-loopback and HTTPS remote hosts.

- [ ] **Step 5: Implement the CLI and verify**

Use the same credential JSON shape and localhost policy as the existing
handoff/import tools. Keep HTTP code in the CLI module and evidence
normalization in `repair_evidence_export.py`.

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_evidence_export `
  tests.test_export_visual_qc_linkable_evidence_cli -v
```

Expected: all tests pass and stderr is empty on success.

- [ ] **Step 6: Commit**

```powershell
git add `
  scripts/visual_qc/repair_evidence_export.py `
  scripts/export_visual_qc_linkable_evidence.py `
  tests/test_visual_qc_repair_evidence_export.py `
  tests/test_export_visual_qc_linkable_evidence_cli.py
git commit -m "feat: export linkable physical evidence"
```

### Task 3: Engineering Resolver And Append-Only Link Library

**Files:**
- Create: `tests/test_visual_qc_repair_evidence_link_library.py`
- Create: `scripts/visual_qc/repair_evidence_engineering.py`
- Create: `scripts/visual_qc/repair_evidence_link_library.py`

- [ ] **Step 1: Write failing engineering snapshot tests**

Resolve `bg6h-f069` and U4000. Assert:

```python
snapshot = resolve_engineering_target(
    project_root=ROOT,
    board_key="bg6h-f069",
    target={"kind": "designator", "side_id": "main_page_2", "designator": "U4000"},
)
self.assertEqual(snapshot["component_id"], "F069-MAIN-U4000")
self.assertEqual(snapshot["designator"], "U4000")
self.assertEqual(snapshot["side_id"], "main_page_2")
self.assertEqual(snapshot["geometry_source_status"], "low")
self.assertFalse(snapshot["semantic_identity_proven"])
```

The board snapshot hash must bind canonical catalog entry bytes, the side
manifest, and the cross-source dataset. Reject unknown board/side/designator,
cross-side target, path escape, changed bytes, missing files, duplicate entity,
and a low-confidence size treated as measured footprint. Add rectangle and
polygon `board_region` fixtures; accept finite normalized coordinates on the
declared side and reject out-of-range, degenerate, self-intersecting, or
opposite-side geometry.

- [ ] **Step 2: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_evidence_link_library.VisualQcRepairEvidenceEngineeringTests -v
```

Expected: import failure.

- [ ] **Step 3: Implement deterministic engineering resolution**

Expose `resolve_board_asset_snapshot(project_root: Path, board_key: str) ->
dict` and `resolve_engineering_target(*, project_root: Path, board_key: str,
target: dict) -> dict`. The board resolver opens the catalog entry, verifies
every referenced byte/hash, and returns the canonical asset snapshot. The
target resolver supports `whole_board`, normalized rectangle/polygon
`board_region`, and exact reviewed `designator` selectors. It binds the
current component ID/side/geometry-source status for designators and rejects
missing, duplicate, cross-side, path-escaping, changed, non-finite,
out-of-range, degenerate, or self-intersecting assets/geometry.

For designators, preserve reviewed entity identity and the current geometry
source status. Derive `semantic_identity_proven` only from explicit evidence
descriptors or an exact source-fact designator match; never from the display
name alone.

- [ ] **Step 4: Write failing library publication tests**

Use a repository-external temporary library with:

- one V2 repair case;
- one valid source package;
- one valid physical snapshot;
- a `possibly_related` U4000 binding.

Assert first publication, exact replay, no-clobber conflict, `.complete`,
manifest hash, full disk revalidation, and append-only revision 2. Add invalid
tests for:

- repair-case hash/revision mismatch;
- fact snapshot or correction drift;
- `related` U4000 without semantic proof;
- physical source package not linked by the repair case;
- cross-board or cross-side binding;
- multiple active replacements;
- source-fact and binding supersede derivation;
- historical mutation, fork, gap, hard link, symlink, junction, and reparse
  paths.

Add a process-level publication race: two workers publish identical revision-1
bytes concurrently and both finish with the same manifest hash, one `created`
and one `existing`. Repeat with conflicting bytes and assert exactly one
revision is complete while the loser reports conflict and leaves no temporary
or partial revision.

- [ ] **Step 5: Implement the link library**

Create these exact public APIs:

- `build_repair_evidence_link_revision(*, project_root: Path, library_root:
  Path, link_set_id: str, repair_case_manifest_path: Path,
  physical_evidence_paths: list[Path], binding_record: dict,
  previous_manifest_path: Path | None = None) -> dict`;
- `publish_repair_evidence_link_revision(*, project_root: Path, library_root:
  Path, link_set_id: str, repair_case_manifest_path: Path,
  physical_evidence_paths: list[Path], binding_record_path: Path,
  previous_manifest_path: Path | None = None) -> dict`;
- `validate_repair_evidence_link_revision_on_disk(manifest_path: Path, *,
  project_root: Path, library_root: Path) -> dict`.

The builder accepts project/library roots,
link-set ID, repair-case manifest, physical-evidence paths, binding record, and
optional previous manifest. It reopens and validates every input, derives all
snapshots and hashes, and returns a complete V1 manifest. Publication uses the
existing lock, temporary-directory, fsync, atomic-rename, and `.complete`
primitives. On-disk validation reopens every authoritative dependency and
rejects any byte, chain, or path drift.

For every binding, the builder resolves `repair_case_reference_id` to the
validated repair-case manifest and derives `model_identity_resolved` from that
exact revision: V1 derives `true`; V2 copies its existing immutable derived
boundary. On-disk validation repeats that comparison. The repair-case
reference summary itself remains limited to the fields approved by the
specification and must not gain a duplicate identity field.

Reuse repair-case validation, current source-package validation, and the
existing safe publication primitives. The input binding record contains only
selectors and statuses; the builder derives repair-case fact snapshots,
engineering snapshots, physical snapshots, boundaries, and all hashes.

- [ ] **Step 6: Run and verify**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_evidence_link_contract `
  tests.test_visual_qc_repair_evidence_link_library -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add `
  scripts/visual_qc/repair_evidence_engineering.py `
  scripts/visual_qc/repair_evidence_link_library.py `
  tests/test_visual_qc_repair_evidence_link_library.py
git commit -m "feat: publish repair evidence links"
```

### Task 4: Owner Publication CLI And Downstream Isolation

**Files:**
- Create: `tests/test_stage_visual_qc_repair_evidence_link_cli.py`
- Create: `tests/test_visual_qc_repair_evidence_link_boundaries.py`
- Create: `scripts/stage_visual_qc_repair_evidence_link.py`

- [ ] **Step 1: Write failing CLI tests**

Invoke the command directly with:

```powershell
.\.venv\Scripts\python.exe scripts\stage_visual_qc_repair_evidence_link.py `
  --library-root "$testRoot\library" `
  --link-set-id link-case005-f069-after `
  --repair-case-manifest "$testRoot\library\cases\case-005-bg6-f069\revisions\0001\repair-case.json" `
  --physical-evidence "$testRoot\incoming\case005-main-page-1.json" `
  --physical-evidence "$testRoot\incoming\case005-main-page-2.json" `
  --binding-record "$testRoot\incoming\case005-bindings.json"
```

Set `$testRoot` to the test method's temporary directory. Assert typed success
contains the fixed IDs/counts below and use
`self.assertRegex(result["manifest_sha256"], r"^[0-9a-f]{64}$")` for the
manifest hash:

```python
{
    "status": "ok",
    "state": "created",
    "link_set_id": "link-case005-f069-after",
    "revision": 1,
    "binding_count": 3,
    "physical_evidence_count": 2,
}
```

Exact replay returns `state=existing`; duplicate JSON keys, inference flags,
both output and error text, unsafe IDs, and incomplete arguments fail before
creating the link root.

- [ ] **Step 2: Write failing boundary tests**

Publish a real-shaped link in a temporary library, then assert its IDs, hash,
fact text, and manifest bytes are absent from:

- annotation arrays;
- final QC reviews;
- Golden rows;
- training manifest;
- COCO;
- dataset bundle;
- model-specific repair output;
- repair-case manifest history.

- [ ] **Step 3: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_stage_visual_qc_repair_evidence_link_cli `
  tests.test_visual_qc_repair_evidence_link_boundaries -v
```

Expected: CLI module missing.

- [ ] **Step 4: Implement the CLI**

Use strict duplicate-key JSON loading and compact typed output. The CLI may
select explicit facts and targets but must expose no model-normalization,
defect-confirmation, annotation, QC, Golden, training, or repair-action flag.

- [ ] **Step 5: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_stage_visual_qc_repair_evidence_link_cli `
  tests.test_visual_qc_repair_evidence_link_boundaries -v

git add `
  scripts/stage_visual_qc_repair_evidence_link.py `
  tests/test_stage_visual_qc_repair_evidence_link_cli.py `
  tests/test_visual_qc_repair_evidence_link_boundaries.py
git commit -m "feat: stage repair evidence links"
```

### Task 5: Local Server Projection, Health State, And Retention

**Files:**
- Create: `tests/test_visual_qc_repair_evidence_link_server.py`
- Create: `knowledge-base/visual-qc-repair-evidence-link-list-v1-schema.json`
- Create: `knowledge-base/visual-qc-repair-evidence-link-detail-v1-schema.json`
- Modify: `scripts/visual_qc/server/store.py`
- Modify: `scripts/visual_qc/server/service.py`
- Modify: `scripts/visual_qc/server/api.py`
- Modify: `tests/test_visual_qc_maintenance.py`

- [ ] **Step 1: Write failing migration and store tests**

Assert a new database creates:

```sql
CREATE TABLE repair_evidence_link_revisions (
  link_set_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  repair_case_id TEXT NOT NULL,
  board_key TEXT NOT NULL,
  board_id TEXT NOT NULL,
  manifest_json TEXT NOT NULL,
  import_actor_id TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  PRIMARY KEY (link_set_id, revision),
  UNIQUE (manifest_sha256)
);

CREATE TABLE repair_evidence_link_cases (
  link_set_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  server_case_id TEXT NOT NULL,
  physical_evidence_snapshot_sha256 TEXT NOT NULL,
  PRIMARY KEY (link_set_id, revision, server_case_id),
  FOREIGN KEY (link_set_id, revision)
    REFERENCES repair_evidence_link_revisions(link_set_id, revision),
  FOREIGN KEY (server_case_id) REFERENCES cases(case_id)
);
```

Migration must be additive and old databases remain readable. Store tests must
prove exact idempotency, conflict rejection, transaction rollback, latest
revision listing, and linked-case retention exclusion.

- [ ] **Step 2: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_evidence_link_server.VisualQcRepairEvidenceLinkStoreTests -v
```

Expected: missing tables/methods.

- [ ] **Step 3: Implement additive storage**

Add these exact store APIs:

- `import_repair_evidence_link_revision(self, *, manifest: dict,
  manifest_sha256: str, actor_id: str, imported_at: str) -> dict`;
- `list_repair_evidence_link_revisions(self, *, server_case_id: str | None =
  None, repair_case_id: str | None = None) -> list[dict]`;
- `get_repair_evidence_link_revision(self, link_set_id: str, revision: int) ->
  dict | None`.

Import inserts canonical JSON and all referenced server cases in one
transaction; exact manifest replay returns the existing row and the same
`(link_set_id, revision)` with different bytes is a conflict. List uses stable
newest-revision ordering and optional exact server-case or repair-case filters.
Detail returns the stored immutable JSON or `None`.

Modify retention selection to exclude every referenced server case and report
`repair_evidence_link_present` in maintenance audit output.

- [ ] **Step 4: Write failing service/API tests**

Test exact routes:

```text
POST /api/v1/visual-qc/admin/repair-evidence-links
GET  /api/v1/visual-qc/admin/repair-evidence-links?server_case_id={server_case_id}
GET  /api/v1/visual-qc/admin/repair-evidence-links?repair_case_id={repair_case_id}
GET  /api/v1/visual-qc/admin/repair-evidence-links/{link_set_id}/revisions/{revision}
```

Assertions:

- `reviewer` role required for every route;
- technician receives `403`;
- import revalidates schema, manifest hash, server case, image, intake,
  qualified handoff, job, registration review, and board asset;
- import accepts only derived `active`;
- list is redacted and schema-valid;
- detail is canonical and schema-valid;
- read-time changes derive every stated `stale`/`unavailable` reason without
  mutating stored JSON;
- no link field appears in technician case detail;
- no link changes annotation, QC, Golden, or training counts.

- [ ] **Step 5: Implement service/API and response schemas**

Add Pydantic request:

```python
class RepairEvidenceLinkImportRequest(BaseModel):
    manifest: dict
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
```

The service must canonical-hash the request, validate the manifest, compare
every pinned field to current state, and derive:

```python
{
    "state": "active" | "stale" | "unavailable",
    "reasons": ["server_case_missing"],
}
```

The exact stale reasons are `server_case_identity_mismatch`,
`image_identity_mismatch`, `qualified_handoff_mismatch`,
`registration_job_mismatch`, `registration_review_mismatch`, and
`board_asset_mismatch`. The exact unavailable reasons are
`server_case_missing`, `image_missing`, `registration_job_missing`,
`registration_review_missing`, and `board_asset_missing`. Tests must exercise
each reason independently and prove list/detail revalidation does not mutate
the stored canonical JSON.

List responses contain no source text or canonical manifest. Detail returns
canonical content only through the admin route.

- [ ] **Step 6: Run server and maintenance tests**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_evidence_link_server `
  tests.test_visual_qc_maintenance `
  tests.test_visual_qc_admin_cases `
  tests.test_visual_qc_training_manifest -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```powershell
git add `
  knowledge-base/visual-qc-repair-evidence-link-list-v1-schema.json `
  knowledge-base/visual-qc-repair-evidence-link-detail-v1-schema.json `
  scripts/visual_qc/server/api.py `
  scripts/visual_qc/server/service.py `
  scripts/visual_qc/server/store.py `
  tests/test_visual_qc_repair_evidence_link_server.py `
  tests/test_visual_qc_maintenance.py
git commit -m "feat: project repair evidence links"
```

### Task 6: Idempotent Owner Synchronization

**Files:**
- Create: `tests/test_sync_visual_qc_repair_evidence_link_cli.py`
- Create: `scripts/sync_visual_qc_repair_evidence_link.py`

- [ ] **Step 1: Write failing synchronization tests**

Patch the HTTP transport and assert:

```powershell
.\.venv\Scripts\python.exe scripts\sync_visual_qc_repair_evidence_link.py `
  "$testRoot\library\repair-evidence-links\link-case005-f069-after\revisions\0001\repair-evidence-link.json" `
  --library-root "$testRoot\library" `
  --api-base http://127.0.0.1:3020/api/v1/visual-qc `
  --credential-file C:\secure\visual-qc-credential.json `
  --allow-http-localhost
```

The command must:

- validate the completed on-disk revision before network access;
- send canonical manifest and exact SHA-256 once;
- use data-administrator actor headers;
- return created or existing;
- reject non-local HTTP, credential leakage, malformed response, stale server
  evidence, and changed manifest bytes;
- never modify the controlled link revision.

The tests must also cover the exact local integration path: `--actor-id
milo-visual-data-operator` without a credential file succeeds only for a
loopback host with `--allow-http-localhost`; credentialless remote requests
fail before network access.

- [ ] **Step 2: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_sync_visual_qc_repair_evidence_link_cli -v
```

Expected: script missing.

- [ ] **Step 3: Implement and verify**

Use standard-library HTTP and the same credential/path safety rules as the
existing handoff tools. Print only IDs, revision, hash, and projection state.

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_sync_visual_qc_repair_evidence_link_cli `
  tests.test_visual_qc_repair_evidence_link_server -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```powershell
git add `
  scripts/sync_visual_qc_repair_evidence_link.py `
  tests/test_sync_visual_qc_repair_evidence_link_cli.py
git commit -m "feat: sync repair evidence links"
```

### Task 7: Read-Only Workbench Evidence Navigation

**Files:**
- Create: `tests/visual-qc-repair-evidence-links.test.mjs`
- Create: `assets/visual-qc-workbench/repair-evidence-links.js`
- Modify: `assets/visual-qc-workbench/index.html`
- Modify: `assets/visual-qc-workbench/styles.css`
- Modify: `assets/visual-qc-workbench/visual-qc-server-client.js`
- Modify: `assets/visual-qc-workbench/app.js`

- [ ] **Step 1: Write failing pure presentation tests**

Test:

```javascript
const view = repairEvidenceBindingView(binding, detail);
assert.equal(view.associationLabel, '候选工程关联');
assert.equal(view.conclusionLabel, '未形成视觉缺陷结论');
assert.equal(view.canLocate, true);
assert.equal(view.markerMode, 'conservative_point');
```

Also prove:

- `related` uses `工程资料关联`;
- stale/unavailable disables locate;
- `source_fact_superseded` and `binding_superseded` have separate labels and
  replacement IDs;
- low geometry never yields a package-sized region;
- neutral evidence presentation never returns the confirmed-anomaly coral
  token;
- selecting a binding does not mutate annotations, QC result, Golden state, or
  registration.

- [ ] **Step 2: Run Node test and verify RED**

```powershell
node --test tests/visual-qc-repair-evidence-links.test.mjs
```

Expected: module missing.

- [ ] **Step 3: Implement pure link presentation**

Export `repairEvidenceBindingView(binding, detail)`,
`activeRepairEvidenceBindings(detail)`, and
`repairEvidenceLocation(binding, detail)`. The first maps only fixed enum
values to fixed Chinese labels and neutral visual tokens. The second excludes
bindings whose source fact or binding is superseded. The third returns either
an exact board-side selector, a conservative normalized point for low
geometry, or `null`; it never manufactures package dimensions.

Return data only; do not access DOM or app state.

- [ ] **Step 4: Write failing server-client tests**

Extend `tests/visual-qc-server-client.test.mjs` or the new module to assert:

- data-administrator headers on list/detail;
- no technician fallback;
- strict V1 schema/version checks;
- redacted list cannot be used as canonical detail;
- target case ID and side are preserved.

- [ ] **Step 5: Implement client functions**

Add `listRepairEvidenceLinks(apiBase, actorId, actorRole, filters)` and
`getRepairEvidenceLinkDetail(apiBase, actorId, actorRole, linkSetId,
revision)`. Both reject any role except `reviewer` before transport, send the
gateway actor headers, require the exact V1 response schema version, and
return parsed immutable data. The list function accepts only
`serverCaseId`/`repairCaseId`; the detail function percent-encodes both path
segments.

- [ ] **Step 6: Add the compact evidence panel**

Place `维修案例证据` after registration review and before comparison/annotation.
It needs:

- loading, empty, active, stale, unavailable, and error states;
- repair case/revision;
- source fact;
- association and visibility badges;
- separate correction/replacement history notice;
- one `定位` icon/text action.

Do not add browser editing controls.

- [ ] **Step 7: Wire location without QC mutation**

When a binding references another server case, reuse the existing admin-case
restore path. After the correct case loads:

- switch to its source side;
- center both canvases on the board coordinate;
- render a compact neutral marker for low geometry;
- keep annotations and QC state unchanged;
- disable location if detail health is not active or board-asset identity
  differs.

- [ ] **Step 8: Run Node suites**

```powershell
node --test `
  tests/visual-qc-repair-evidence-links.test.mjs `
  tests/visual-qc-server-client.test.mjs `
  tests/visual-qc-canvas.test.mjs `
  tests/visual-qc-state.test.mjs
```

Expected: all pass.

- [ ] **Step 9: Run headed browser QA**

Use the Chrome skill first. If the extension path is unavailable after the
documented health check, use Playwright fallback.

Verify desktop `1600x1000` and mobile `390x844`:

- panel loading, empty, active, stale, unavailable, and transport/schema error
  states;
- CASE005 page-1 whole-board binding;
- cross-case navigation to page-2 U4000 candidate;
- conservative marker and complete Chinese status text;
- no coral anomaly styling;
- no annotation/QC mutation;
- keyboard focus, touch activation, exact screen-reader labels for panel,
  badges and `定位`, no overlap, no horizontal overflow, no console errors,
  and nonblank canvases.

- [ ] **Step 10: Commit**

```powershell
git add `
  assets/visual-qc-workbench/index.html `
  assets/visual-qc-workbench/styles.css `
  assets/visual-qc-workbench/visual-qc-server-client.js `
  assets/visual-qc-workbench/repair-evidence-links.js `
  assets/visual-qc-workbench/app.js `
  tests/visual-qc-repair-evidence-links.test.mjs `
  tests/visual-qc-server-client.test.mjs
git commit -m "feat: navigate repair evidence links"
```

### Task 8: Publish And Project The First Real CASE005 Link Set

**Files outside Git:**
- Create:
  `G:/Programming/_Data/Visual-QC-Controlled-Source/incoming/repair-evidence-links/case005/case005-main-page-1.json`
- Create:
  `G:/Programming/_Data/Visual-QC-Controlled-Source/incoming/repair-evidence-links/case005/case005-main-page-2.json`
- Create:
  `G:/Programming/_Data/Visual-QC-Controlled-Source/incoming/repair-evidence-links/case005/case005-bindings.json`
- Publish:
  `G:/Programming/_Data/Visual-QC-Controlled-Source/library/repair-evidence-links/link-case005-f069-after/revisions/0001/repair-evidence-link.json`

- [ ] **Step 1: Export both exact physical snapshots**

Use the existing local integration server and exact case IDs:

```powershell
.\.venv\Scripts\python.exe scripts\export_visual_qc_linkable_evidence.py `
  --api-base http://127.0.0.1:3020/api/v1/visual-qc `
  --actor-id milo-visual-data-operator `
  --case-id vqc_0d436505e8794c06999ffa9dddd2d538 `
  --physical-evidence-id case005-main-page-1 `
  --output G:\Programming\_Data\Visual-QC-Controlled-Source\incoming\repair-evidence-links\case005\case005-main-page-1.json `
  --allow-http-localhost

.\.venv\Scripts\python.exe scripts\export_visual_qc_linkable_evidence.py `
  --api-base http://127.0.0.1:3020/api/v1/visual-qc `
  --actor-id milo-visual-data-operator `
  --case-id vqc_05982f6198c142f9810665f7ea80c45c `
  --physical-evidence-id case005-main-page-2 `
  --output G:\Programming\_Data\Visual-QC-Controlled-Source\incoming\repair-evidence-links\case005\case005-main-page-2.json `
  --allow-http-localhost
```

The exact server rows are actor-owned by `milo-visual-data-operator`; actor
scope must remain unchanged. The local integration API authorizes through
explicit gateway-compatible actor headers and does not require a committed
Basic Auth secret. The export CLI supports this credentialless actor mode only
when `--allow-http-localhost` is set and the host is loopback. Remote or
production use still requires the existing external credential mechanism.

- [ ] **Step 2: Reinspect visibility and create the exact binding-record input**

Before writing JSON, re-hash and open the exact working derivatives:

- page 1 SHA-256
  `82525e32efd2cd7b456927b79a5d037eeb41d1651f905571bfa63e5be53cb386`;
- page 2 SHA-256
  `a9cf3c187cbd82b8304c49ef2848f2a9058955b0be69f470527b4e4074831b76`.

The plan-author inspection on 2026-07-27 confirmed the complete board outline
is in frame on both images, so the two whole-board bindings use
`visibility_status=visible` and the fixed `target_visible` observation code.
The inspection did not establish a defect and did not establish whether U4000
itself is optically visible beneath installed structures, so the U4000 binding
remains `not_assessed` and has no human-observation basis. If either image hash
or this structured visibility observation cannot be reproduced at execution
time, stop before publishing revision 1.

After that prerequisite, create the three-binding input:

```json
{
  "physical_evidence_ids": [
    "case005-main-page-1",
    "case005-main-page-2"
  ],
  "bindings": [
    {
      "binding_id": "case005-no-power-page-1",
      "repair_case_reference_id": "case005-r1",
      "source_fact": {
        "kind": "reported_symptom",
        "fact_id": "case005-symptom-no-power"
      },
      "physical_evidence_id": "case005-main-page-1",
      "target": {
        "kind": "whole_board",
        "side_id": "main_page_1"
      },
      "association_status": "related",
      "visibility_status": "visible",
      "evidence_bases": [
        {"kind": "repair_case_fact"},
        {"kind": "human_observation", "observation_code": "target_visible"}
      ],
      "supersedes_binding_id": null
    },
    {
      "binding_id": "case005-no-power-page-2",
      "repair_case_reference_id": "case005-r1",
      "source_fact": {
        "kind": "reported_symptom",
        "fact_id": "case005-symptom-no-power"
      },
      "physical_evidence_id": "case005-main-page-2",
      "target": {
        "kind": "whole_board",
        "side_id": "main_page_2"
      },
      "association_status": "related",
      "visibility_status": "visible",
      "evidence_bases": [
        {"kind": "repair_case_fact"},
        {"kind": "human_observation", "observation_code": "target_visible"}
      ],
      "supersedes_binding_id": null
    },
    {
      "binding_id": "case005-emmc-u4000-page-2",
      "repair_case_reference_id": "case005-r1",
      "source_fact": {
        "kind": "finding",
        "fact_id": "case005-reported-emmc-fault"
      },
      "physical_evidence_id": "case005-main-page-2",
      "target": {
        "kind": "designator",
        "side_id": "main_page_2",
        "designator": "U4000"
      },
      "association_status": "possibly_related",
      "visibility_status": "not_assessed",
      "evidence_bases": [
        {"kind": "repair_case_fact"},
        {"kind": "engineering_identity"}
      ],
      "supersedes_binding_id": null
    }
  ]
}
```

The binding record contains no narrative observation and no defect inference.

- [ ] **Step 3: Publish revision 1 and replay**

```powershell
.\.venv\Scripts\python.exe scripts\stage_visual_qc_repair_evidence_link.py `
  --library-root G:\Programming\_Data\Visual-QC-Controlled-Source\library `
  --link-set-id link-case005-f069-after `
  --repair-case-manifest G:\Programming\_Data\Visual-QC-Controlled-Source\library\cases\case-005-bg6-f069\revisions\0001\repair-case.json `
  --physical-evidence G:\Programming\_Data\Visual-QC-Controlled-Source\incoming\repair-evidence-links\case005\case005-main-page-1.json `
  --physical-evidence G:\Programming\_Data\Visual-QC-Controlled-Source\incoming\repair-evidence-links\case005\case005-main-page-2.json `
  --binding-record G:\Programming\_Data\Visual-QC-Controlled-Source\incoming\repair-evidence-links\case005\case005-bindings.json
```

First run must return `created`; exact replay must return `existing` with the
same SHA-256 and no modified evidence bytes.

- [ ] **Step 4: Synchronize to the isolated local server**

```powershell
.\.venv\Scripts\python.exe scripts\sync_visual_qc_repair_evidence_link.py `
  G:\Programming\_Data\Visual-QC-Controlled-Source\library\repair-evidence-links\link-case005-f069-after\revisions\0001\repair-evidence-link.json `
  --library-root G:\Programming\_Data\Visual-QC-Controlled-Source\library `
  --api-base http://127.0.0.1:3020/api/v1/visual-qc `
  --actor-id milo-visual-data-operator `
  --allow-http-localhost
```

Replay must return existing. Re-read list/detail, validate response schemas,
and confirm projection state `active`.

- [ ] **Step 5: Verify real workbench behavior**

Open the local workbench, restore page 1, select the no-power binding, then
navigate to the U4000 candidate. Confirm:

- page 2 case is restored;
- U4000 uses a compact neutral point;
- status reads `来源报告 · 候选工程关联 · 未形成视觉缺陷结论`;
- registration remains the same reviewed record;
- annotations remain empty;
- QC remains `needs_review`;
- no Golden/training counts change.

### Task 9: Runtime Boundary, Documentation, And Full Verification

**Files:**
- Modify: `deploy/visual-qc-runtime-files.txt`
- Modify: `tests/test_visual_qc_deployment.py`
- Modify: `tests/test_visual_qc_documentation.py`
- Modify: `README.md`
- Modify: `docs/visual-qc-capture-intake-spec-2026-07-20.md`
- Modify: `docs/visual-qc-server-api-2026-07-20.md`
- Modify: `docs/visual-qc-workbench-2026-07-17.md`
- Modify: `docs/visual-qc-f069-first-physical-acceptance-2026-07-24.md`

- [ ] **Step 1: Write failing runtime/documentation assertions**

Require every new runtime module, script, schema, and workbench asset in the
bounded runtime manifest. Require canonical docs to state:

- controlled library authority and read-only server projection;
- CASE005 U4000 remains `possibly_related`;
- one photo per binding;
- no annotation/QC/Golden/training/causality authority;
- admin-only detail and no technician route;
- production remains unchanged.

- [ ] **Step 2: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_deployment `
  tests.test_visual_qc_documentation -v
```

Expected: missing runtime paths and wording.

- [ ] **Step 3: Update runtime and canonical documentation**

Preserve historical dated statements. Document the new owner sequence:

```text
repair case revision
-> export linkable physical evidence
-> stage repair evidence link revision
-> validate/replay
-> sync read-only projection
-> inspect in internal workbench
```

Do not describe local implementation as production deployment.

- [ ] **Step 4: Run focused Python verification**

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_evidence_link_contract `
  tests.test_visual_qc_repair_evidence_export `
  tests.test_export_visual_qc_linkable_evidence_cli `
  tests.test_visual_qc_repair_evidence_link_library `
  tests.test_stage_visual_qc_repair_evidence_link_cli `
  tests.test_visual_qc_repair_evidence_link_server `
  tests.test_sync_visual_qc_repair_evidence_link_cli `
  tests.test_visual_qc_repair_evidence_link_boundaries `
  tests.test_visual_qc_maintenance `
  tests.test_visual_qc_deployment `
  tests.test_visual_qc_documentation -v
```

Expected: all pass.

- [ ] **Step 5: Run full Python and Node suites**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --test (Get-ChildItem tests -Filter *.test.mjs | ForEach-Object FullName)
```

Expected: all pass.

- [ ] **Step 6: Run compile, schema, encoding, and source audits**

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  scripts/visual_qc/repair_evidence_link_contract.py `
  scripts/visual_qc/repair_evidence_engineering.py `
  scripts/visual_qc/repair_evidence_export.py `
  scripts/visual_qc/repair_evidence_link_library.py `
  scripts/export_visual_qc_linkable_evidence.py `
  scripts/stage_visual_qc_repair_evidence_link.py `
  scripts/sync_visual_qc_repair_evidence_link.py

.\.venv\Scripts\python.exe scripts\audit_visual_qc_source_library.py `
  --library-root G:\Programming\_Data\Visual-QC-Controlled-Source\library

git diff --check
```

Parse all four new schemas with Draft 2020-12:

```powershell
@'
import json
from pathlib import Path
from jsonschema.validators import Draft202012Validator

paths = [
    Path("knowledge-base/visual-qc-linkable-physical-evidence-v1-schema.json"),
    Path("knowledge-base/visual-qc-repair-evidence-link-v1-schema.json"),
    Path("knowledge-base/visual-qc-repair-evidence-link-list-v1-schema.json"),
    Path("knowledge-base/visual-qc-repair-evidence-link-detail-v1-schema.json"),
]
for path in paths:
    Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
print("SCHEMAS_OK=4")
'@ | .\.venv\Scripts\python.exe -
```

Strictly decode every touched text file and reject U+FFFD:

```powershell
$textExtensions = @('.py', '.json', '.md', '.js', '.mjs', '.html', '.css', '.txt')
$touched = git diff --name-only 07376d6..HEAD
foreach ($relative in $touched) {
  if ($textExtensions -notcontains [IO.Path]::GetExtension($relative)) { continue }
  $bytes = [IO.File]::ReadAllBytes((Join-Path $PWD $relative))
  $text = [Text.UTF8Encoding]::new($false, $true).GetString($bytes)
  if ($text.Contains([char]0xFFFD)) { throw "U+FFFD found in $relative" }
}
Write-Output "UTF8_OK=$($touched.Count)"
```

Validate the real link on disk. This call reopens and re-hashes its exact
repair-case revision, source package, physical snapshots, board assets, and
prior-chain dependencies:

```powershell
@'
from pathlib import Path
from scripts.visual_qc.repair_evidence_link_library import (
    validate_repair_evidence_link_revision_on_disk,
)

result = validate_repair_evidence_link_revision_on_disk(
    Path(
        "G:/Programming/_Data/Visual-QC-Controlled-Source/library/"
        "repair-evidence-links/link-case005-f069-after/revisions/0001/"
        "repair-evidence-link.json"
    ),
    project_root=Path(".").resolve(),
    library_root=Path(
        "G:/Programming/_Data/Visual-QC-Controlled-Source/library"
    ),
)
print(result["link_set_id"], result["revision"])
'@ | .\.venv\Scripts\python.exe -
```

Check the two existing immutable authorities against their already recorded
SHA-256 values, then calculate and report the exact published link-file hash:

```powershell
$casePath = 'G:\Programming\_Data\Visual-QC-Controlled-Source\library\cases\case-005-bg6-f069\revisions\0001\repair-case.json'
$packagePath = 'G:\Programming\_Data\Visual-QC-Controlled-Source\library\packages\f069-case005-after-source\source-package.json'
$linkPath = 'G:\Programming\_Data\Visual-QC-Controlled-Source\library\repair-evidence-links\link-case005-f069-after\revisions\0001\repair-evidence-link.json'
if ((Get-FileHash $casePath -Algorithm SHA256).Hash.ToLower() -ne '85c8c64cb97cf1ea1e567e4d1f7fc62ec00ebf02719939c74a5e0faf46298177') { throw 'CASE005 repair-case hash drift' }
if ((Get-FileHash $packagePath -Algorithm SHA256).Hash.ToLower() -ne '68557dd996d21bf441af3d227e0239aab6e9aaee1b71503e59f9c1d802b3a6a0') { throw 'CASE005 source-package hash drift' }
$linkHash = (Get-FileHash $linkPath -Algorithm SHA256).Hash.ToLower()
if ($linkHash -notmatch '^[0-9a-f]{64}$') { throw 'Invalid link hash' }
Write-Output "CASE005_HASHES_OK=$linkHash"
```

Expected: four schemas valid, all touched text is strict UTF-8 without U+FFFD,
the real link validates as revision 1, both historical hashes remain exact,
the link hash is recorded in closeout evidence, and the controlled source
audit reports `healthy`.

- [ ] **Step 7: Final independent code and evidence review**

Review:

- all implementation commits against the written spec;
- real CASE005 link bytes and replay;
- local projection state;
- dataset/Golden/QC isolation;
- browser desktop/mobile evidence;
- production unchanged.

Fix every Critical, Important, and applicable Minor finding before closeout.

- [ ] **Step 8: Commit documentation and closeout**

```powershell
git add `
  deploy/visual-qc-runtime-files.txt `
  tests/test_visual_qc_deployment.py `
  tests/test_visual_qc_documentation.py `
  README.md `
  docs/visual-qc-capture-intake-spec-2026-07-20.md `
  docs/visual-qc-server-api-2026-07-20.md `
  docs/visual-qc-workbench-2026-07-17.md `
  docs/visual-qc-f069-first-physical-acceptance-2026-07-24.md
git commit -m "docs: record first repair evidence link"
```

- [ ] **Step 9: Sync durable project facts**

Update and commit
`G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`, update the Vault
project Overview, and update only CASE005's existing Feishu
`Codex录入说明`. Preserve Milo's original collection fields and retain the
explicit `possibly_related`, no-visual-defect, no-Golden, no-training,
no-causality, and production-unchanged boundaries.

- [ ] **Step 10: Confirm clean repositories**

```powershell
git -C G:\Programming\mainboard-repair-system status --porcelain
git -C G:\Programming\mainboard-repair-enablement status --porcelain
```

Expected: both commands print nothing. Do not attempt GitHub push while Milo's
current status marks it unavailable unless Milo separately requests a network
troubleshooting run.
