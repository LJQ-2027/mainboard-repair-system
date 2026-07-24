# Visual-QC Repair Case Device Identity V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve real repair cases whose exact physical board is known while their source-reported sales-model alias remains unresolved.

**Architecture:** Add a focused device-identity validator and a V2 repair-case schema while keeping V1 manifests and builders readable and unchanged. The existing repair-case library will select V1 or V2 from the case-record identity shape, enforce append-only identity transitions, and continue using the same source-package, supporting-evidence, hashing, publication, and downstream exclusion paths.

**Tech Stack:** Python 3.11, `jsonschema` Draft 2020-12, `unittest`, existing content-addressed controlled library, existing Visual-QC CLI and board catalog.

---

## File Map

- Create `scripts/visual_qc/repair_case_identity.py`: V2 identity validation,
  derived resolution boundary, and revision-transition rules.
- Create `knowledge-base/visual-qc-repair-case-source-v2-schema.json`: exact
  machine-readable V2 contract.
- Modify `scripts/visual_qc/repair_case_contract.py`: dispatch V1/V2 manifest
  validation and reuse all non-identity fact validation.
- Modify `scripts/visual_qc/repair_case_library.py`: accept one identity input
  shape, build V1 or V2, and validate V1-to-V2 revision chains.
- Modify `scripts/stage_visual_qc_repair_case.py`: include schema version and
  identity state in successful operator output.
- Create `tests/test_visual_qc_repair_case_identity.py`: isolated V2 identity
  state and transition tests.
- Modify `tests/test_visual_qc_repair_case_contract.py`: Python/Schema parity
  for complete V2 manifests.
- Modify `tests/test_visual_qc_repair_case_library.py`: V2 publication,
  idempotency, catalog checks, and V1-to-V2 revision tests.
- Modify `tests/test_stage_visual_qc_repair_case_cli.py`: direct V2 CLI and
  ambiguous-input failures.
- Modify `tests/test_visual_qc_repair_case_boundaries.py`: unresolved identities
  remain absent from all governed dataset exits.
- Modify operator and architecture documentation only after behavior is green.

### Task 1: Isolated Device-Identity Contract

**Files:**
- Create: `tests/test_visual_qc_repair_case_identity.py`
- Create: `scripts/visual_qc/repair_case_identity.py`

- [ ] **Step 1: Write failing validation tests**

Add helpers and tests that express all four identity states:

```python
from scripts.visual_qc.repair_case_identity import (
    derive_model_identity_resolved,
    validate_device_identity,
    validate_identity_transition,
)


def unresolved_identity():
    return {
        "reported_models": ["TECNO/BG6"],
        "catalog_models": ["BG6H", "BG6h"],
        "mapping_status": "unresolved_alias",
        "resolved_models": [],
        "resolution_note": None,
        "evidence_refs": [
            {
                "kind": "supporting_evidence",
                "evidence_id": "feishu-case005-source-record",
            }
        ],
    }


def test_unresolved_alias_is_valid_but_not_resolved():
    identity = unresolved_identity()
    assert validate_device_identity(
        identity,
        catalog_models=["BG6H", "BG6h"],
        validate_evidence_refs=lambda refs: None,
    ) == identity
    assert derive_model_identity_resolved(identity) is False


def test_unresolved_alias_rejects_resolved_models_or_missing_evidence():
    identity = unresolved_identity()
    identity["resolved_models"] = ["BG6H"]
    with pytest.raises(ValueError, match="resolved_models"):
        validate_device_identity(
            identity,
            catalog_models=["BG6H", "BG6h"],
            validate_evidence_refs=lambda refs: None,
        )

    identity = unresolved_identity()
    identity["evidence_refs"] = []
    with pytest.raises(ValueError, match="evidence"):
        validate_device_identity(
            identity,
            catalog_models=["BG6H", "BG6h"],
            validate_evidence_refs=lambda refs: None,
        )
```

Also test exact-match string equality, confirmed-alias note/evidence requirements,
conflict semantics, duplicate values, exact catalog order, unknown fields, and
the allowed/forbidden transitions from the design.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_visual_qc_repair_case_identity.py -q
```

Expected: collection fails because `repair_case_identity` does not exist.

- [ ] **Step 3: Implement the minimal identity module**

Define these public constants and functions:

```python
from __future__ import annotations

import copy
from collections.abc import Callable


IDENTITY_FIELDS = {
    "reported_models",
    "catalog_models",
    "mapping_status",
    "resolved_models",
    "resolution_note",
    "evidence_refs",
}
IDENTITY_STATUSES = {
    "exact_catalog_match",
    "confirmed_alias",
    "unresolved_alias",
    "conflict",
}
RESOLVED_IDENTITY_STATUSES = {"exact_catalog_match", "confirmed_alias"}


def _string_list(value, label: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{label} is invalid.")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} is invalid.")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicates.")
    return list(value)


def validate_device_identity(
    value: dict,
    *,
    catalog_models: list[str],
    validate_evidence_refs: Callable[[list[dict]], None],
) -> dict:
    if not isinstance(value, dict) or set(value) != IDENTITY_FIELDS:
        raise ValueError("device_identity fields are invalid.")
    identity = copy.deepcopy(value)
    reported = _string_list(
        identity["reported_models"], "reported_models", allow_empty=False
    )
    catalog = _string_list(
        identity["catalog_models"], "catalog_models", allow_empty=False
    )
    expected_catalog = _string_list(
        catalog_models, "catalog_models", allow_empty=False
    )
    if catalog != expected_catalog:
        raise ValueError("catalog_models do not match board catalog order.")
    status = identity["mapping_status"]
    if status not in IDENTITY_STATUSES:
        raise ValueError("mapping_status is invalid.")
    resolved = _string_list(
        identity["resolved_models"], "resolved_models", allow_empty=True
    )
    if any(model not in catalog for model in resolved):
        raise ValueError("resolved_models must be catalog compatible.")
    note = identity["resolution_note"]
    if note is not None and (
        not isinstance(note, str) or not note.strip()
    ):
        raise ValueError("resolution_note is invalid.")
    refs = identity["evidence_refs"]
    validate_evidence_refs(refs)

    if status == "exact_catalog_match":
        if reported != resolved or any(model not in catalog for model in reported):
            raise ValueError("exact_catalog_match requires exact reported models.")
        if note is not None:
            raise ValueError("exact_catalog_match cannot have a resolution note.")
    elif status == "confirmed_alias":
        if not resolved:
            raise ValueError("confirmed_alias requires resolved_models.")
        if note is None:
            raise ValueError("confirmed_alias requires a resolution note.")
        if not refs:
            raise ValueError("confirmed_alias requires evidence.")
    else:
        if resolved:
            raise ValueError(f"{status} cannot contain resolved_models.")
        if note is not None:
            raise ValueError(f"{status} cannot contain a resolution note.")
        if not refs:
            raise ValueError(f"{status} requires evidence.")
    return identity


def derive_model_identity_resolved(value: dict) -> bool:
    return value["mapping_status"] in RESOLVED_IDENTITY_STATUSES


def validate_identity_transition(
    previous: dict,
    current: dict,
    *,
    has_new_correction: bool,
) -> None:
    previous_status = previous["mapping_status"]
    current_status = current["mapping_status"]
    if previous["reported_models"] != current["reported_models"][
        : len(previous["reported_models"])
    ]:
        raise ValueError("device identity removes or rewrites reported models.")
    previous_refs = previous["evidence_refs"]
    if previous_refs != current["evidence_refs"][: len(previous_refs)]:
        raise ValueError("device identity removes or rewrites evidence.")
    if previous_status in RESOLVED_IDENTITY_STATUSES:
        if current != previous:
            raise ValueError("resolved device identity is immutable.")
        return
    allowed = {
        "unresolved_alias": {
            "unresolved_alias",
            "confirmed_alias",
            "conflict",
        },
        "conflict": {"conflict", "confirmed_alias"},
    }
    if current_status not in allowed[previous_status]:
        raise ValueError("device identity transition is not allowed.")
    if (
        previous_status == "conflict"
        and current_status == "confirmed_alias"
        and not has_new_correction
    ):
        raise ValueError(
            "conflict resolution requires a new correction record."
        )
    changed_names = (
        previous["reported_models"] != current["reported_models"]
        or previous["catalog_models"] != current["catalog_models"]
    )
    if changed_names and len(current["evidence_refs"]) == len(previous_refs):
        raise ValueError("device identity name changes require new evidence.")
```

The validator must deep-copy its result, preserve exact source strings, require
the canonical catalog list in exact order, and implement the state invariants
from the design. Transition validation must reject backwards movement and
mutation of a resolved identity.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the Task 1 command again. Expected: all identity tests pass.

- [ ] **Step 5: Commit**

```powershell
git add scripts/visual_qc/repair_case_identity.py tests/test_visual_qc_repair_case_identity.py
git commit -m "feat: validate repair case device identity"
```

### Task 2: V2 JSON Schema and Python Contract Dispatch

**Files:**
- Create: `knowledge-base/visual-qc-repair-case-source-v2-schema.json`
- Modify: `tests/test_visual_qc_repair_case_contract.py`
- Modify: `scripts/visual_qc/repair_case_contract.py`

- [ ] **Step 1: Add a failing canonical V2 parity test**

Add:

```python
V2_SCHEMA_PATH = (
    ROOT / "knowledge-base" / "visual-qc-repair-case-source-v2-schema.json"
)


def canonical_v2_payload():
    payload = canonical_payload()
    payload["schema_version"] = "VISUAL-QC-REPAIR-CASE-SOURCE-V2"
    del payload["device_models"]
    payload["device_identity"] = {
        "reported_models": ["TECNO/BG6"],
        "catalog_models": ["BG6H", "BG6h"],
        "mapping_status": "unresolved_alias",
        "resolved_models": [],
        "resolution_note": None,
        "evidence_refs": [evidence_reference()],
    }
    payload["boundaries"]["model_identity_resolved"] = False
    return payload


def test_canonical_v2_payload_matches_python_and_schema():
    payload = canonical_v2_payload()
    validated = validate_repair_case_manifest(
        payload,
        catalog_models=["BG6H", "BG6h"],
    )
    assert validated == payload
    schema = json.loads(V2_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)
```

Add invalid parity cases for both/neither identity fields, supplied incorrect
resolution boundary, unresolved-without-evidence, and confirmed alias without
note.

- [ ] **Step 2: Run the contract tests and verify RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_visual_qc_repair_case_contract.py -q
```

Expected: V2 schema missing and V1-only Python validator rejects V2.

- [ ] **Step 3: Add the exact V2 Schema**

Copy reusable V1 definitions without `$ref`-ing a mutable external document.
The V2 top level must require `device_identity`, forbid `device_models`, and
require `model_identity_resolved` inside boundaries. Encode the four state
conditions with `allOf` branches so Schema and Python reject the same shapes.

- [ ] **Step 4: Dispatch V1 and V2 in Python**

Add:

```python
REPAIR_CASE_SCHEMA_V1 = "VISUAL-QC-REPAIR-CASE-SOURCE-V1"
REPAIR_CASE_SCHEMA_V2 = "VISUAL-QC-REPAIR-CASE-SOURCE-V2"
REPAIR_CASE_SCHEMA_VERSION = REPAIR_CASE_SCHEMA_V1
REPAIR_CASE_SCHEMA_VERSIONS = {
    REPAIR_CASE_SCHEMA_V1,
    REPAIR_CASE_SCHEMA_V2,
}
```

Update `validate_repair_case_manifest` to select the exact top-level fields by
version. Reuse existing package, supporting evidence, fact, correction,
completeness, and boundary validation. For V2, invoke
`validate_device_identity`, derive `model_identity_resolved`, and reject a
supplied value that differs.

- [ ] **Step 5: Verify V1 and V2 GREEN**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_visual_qc_repair_case_contract.py tests/test_visual_qc_repair_case_identity.py -q
```

Expected: all tests pass, including unchanged V1 Schema parity.

- [ ] **Step 6: Commit**

```powershell
git add knowledge-base/visual-qc-repair-case-source-v2-schema.json scripts/visual_qc/repair_case_contract.py tests/test_visual_qc_repair_case_contract.py
git commit -m "feat: add repair case source v2 contract"
```

### Task 3: Dual-Version Library Builder

**Files:**
- Modify: `tests/test_visual_qc_repair_case_library.py`
- Modify: `scripts/visual_qc/repair_case_library.py`

- [ ] **Step 1: Add failing V2 publication tests**

Add a `v2_case_record()` helper using `device_identity`. Test:

```python
def test_unresolved_v2_revision_publishes_and_replays_idempotently(self):
    evidence = self.root / "case-source.txt"
    evidence.write_text("Reported model: TECNO/BG6", encoding="utf-8")
    record = self.v2_case_record(
        supporting_evidence_descriptions={
            "case-source": "Privacy-reduced source record"
        }
    )
    options = {
        "board_key": "bg6h-f069",
        "repair_case_id": "case-bg6-0001",
        "package_assignments": [
            ("after_repair", self.f069_after_path)
        ],
        "case_record": record,
        "supporting_assignments": [("case-source", evidence)],
    }
    created = self.stage_case(**options)
    replayed = self.stage_case(**options)
    self.assertEqual(created["schema_version"], "VISUAL-QC-REPAIR-CASE-SOURCE-V2")
    self.assertEqual(created["identity_status"], "unresolved_alias")
    self.assertEqual(replayed["state"], "existing")
```

Add tests for ambiguous case records containing both identity shapes, catalog
model order mismatch, V1-to-V2 revision with unchanged prior bytes, allowed
unresolved-to-confirmed transition, and rejected backward transition.

- [ ] **Step 2: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_visual_qc_repair_case_library.py -q
```

Expected: the case-record field validator rejects `device_identity`.

- [ ] **Step 3: Implement minimal dual-version building**

Replace the single exact case-record field set with:

```python
COMMON_CASE_RECORD_FIELDS = {
    "supporting_evidence_descriptions",
    "reported_symptoms",
    "findings",
    "repair_actions",
    "outcome",
    "corrections",
}
V1_CASE_RECORD_FIELDS = COMMON_CASE_RECORD_FIELDS | {"device_models"}
V2_CASE_RECORD_FIELDS = COMMON_CASE_RECORD_FIELDS | {"device_identity"}
```

Return the selected schema version from `_validate_case_record`. V1 retains its
catalog-subset check. V2 injects the exact catalog model list into
`validate_repair_case_manifest`, derives the boundary, and calls
`validate_identity_transition` when a prior V2 identity exists.

When a V1 head moves to V2, carry the V1 models into a synthetic prior
`exact_catalog_match` identity only for transition validation; do not rewrite
the V1 manifest.

Extend `_revision_result` with:

```python
"schema_version": payload["schema_version"],
"identity_status": (
    payload["device_identity"]["mapping_status"]
    if payload["schema_version"] == REPAIR_CASE_SCHEMA_V2
    else "exact_catalog_match"
),
```

- [ ] **Step 4: Run focused library and contract tests**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_visual_qc_repair_case_library.py tests/test_visual_qc_repair_case_contract.py tests/test_visual_qc_repair_case_identity.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add scripts/visual_qc/repair_case_library.py tests/test_visual_qc_repair_case_library.py
git commit -m "feat: publish versioned repair case identities"
```

### Task 4: CLI and Boundary Enforcement

**Files:**
- Modify: `tests/test_stage_visual_qc_repair_case_cli.py`
- Modify: `tests/test_visual_qc_repair_case_boundaries.py`
- Modify: `scripts/stage_visual_qc_repair_case.py`

- [ ] **Step 1: Add failing CLI and downstream tests**

Add a CLI case record containing only `device_identity` and source evidence.
Assert successful output includes:

```python
self.assertEqual(payload["schema_version"], "VISUAL-QC-REPAIR-CASE-SOURCE-V2")
self.assertEqual(payload["identity_status"], "unresolved_alias")
```

Add one test showing both `device_models` and `device_identity` fail before a
case directory is created.

Extend the boundary test to publish an unresolved V2 case and assert its
manifest ID and hash are absent from training manifest, COCO, bundle, server
case tables, Golden tables, and model-specific repair outputs.

- [ ] **Step 2: Run and verify RED**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_stage_visual_qc_repair_case_cli.py tests/test_visual_qc_repair_case_boundaries.py -q
```

Expected: CLI omits V2 identity output and/or input shape is rejected.

- [ ] **Step 3: Emit identity-safe CLI output**

Add only the two derived result fields:

```python
"schema_version": result["schema_version"],
"identity_status": result["identity_status"],
```

Do not add inference flags or CLI model-normalization options.

- [ ] **Step 4: Run and verify GREEN**

Run the Task 4 command again. Expected: all pass and stderr remains empty.

- [ ] **Step 5: Commit**

```powershell
git add scripts/stage_visual_qc_repair_case.py tests/test_stage_visual_qc_repair_case_cli.py tests/test_visual_qc_repair_case_boundaries.py
git commit -m "feat: expose unresolved repair case identity"
```

### Task 5: CASE005 Real Publication

**Files:**
- Create outside Git:
  `G:/Programming/_Data/Visual-QC-Controlled-Source/incoming/feishu-Bf57b8-20260724/recvq19VUYj1AX/CASE-005-BG6-repair-case-record.json`
- Read:
  `G:/Programming/_Data/Visual-QC-Controlled-Source/library/packages/f069-case005-after-source/source-package.json`
- Publish outside Git:
  `G:/Programming/_Data/Visual-QC-Controlled-Source/library/cases/case-005-bg6-f069/revisions/0001/repair-case.json`

- [ ] **Step 1: Create the exact case-record input**

Use:

```json
{
  "device_identity": {
    "reported_models": ["TECNO/BG6"],
    "catalog_models": ["BG6H", "BG6h"],
    "mapping_status": "unresolved_alias",
    "resolved_models": [],
    "resolution_note": null,
    "evidence_refs": [
      {
        "kind": "supporting_evidence",
        "evidence_id": "feishu-case005-source-record"
      }
    ]
  },
  "supporting_evidence_descriptions": {
    "feishu-case005-source-record": "Privacy-reduced Feishu CASE005 source-field snapshot"
  },
  "reported_symptoms": [
    {
      "symptom_id": "case005-symptom-no-power",
      "text": "不开机",
      "source_wording": "不开机",
      "fault_code": null,
      "evidence_refs": [
        {
          "kind": "supporting_evidence",
          "evidence_id": "feishu-case005-source-record"
        }
      ]
    }
  ],
  "findings": [
    {
      "finding_id": "case005-reported-emmc-fault",
      "claim_status": "reported",
      "description": "EMMC坏",
      "defect_category": null,
      "designator": null,
      "side_id": null,
      "region": null,
      "evidence_refs": [
        {
          "kind": "supporting_evidence",
          "evidence_id": "feishu-case005-source-record"
        }
      ]
    }
  ],
  "repair_actions": [
    {
      "action_id": "case005-reported-test-action",
      "description": "已做检测",
      "action_category": null,
      "target_designator": null,
      "side_id": null,
      "region": null,
      "evidence_refs": [
        {
          "kind": "supporting_evidence",
          "evidence_id": "feishu-case005-source-record"
        }
      ]
    }
  ],
  "outcome": {
    "status": "repair_completed",
    "description": "维修后已修复",
    "verification_description": null,
    "evidence_refs": [
      {
        "kind": "supporting_evidence",
        "evidence_id": "feishu-case005-source-record"
      }
    ]
  },
  "corrections": []
}
```

- [ ] **Step 2: Run a non-publishing build validation**

Call `build_repair_case_revision` from the project virtual environment and
assert:

- schema V2;
- `unresolved_alias`;
- exact F069 board ID;
- `symptom_linked`;
- `model_identity_resolved=false`;
- every source and supporting reference resolves.

- [ ] **Step 3: Publish through the owner CLI**

```powershell
.\.venv\Scripts\python.exe scripts/stage_visual_qc_repair_case.py `
  --library-root G:\Programming\_Data\Visual-QC-Controlled-Source\library `
  --repair-case-id case-005-bg6-f069 `
  --board-key bg6h-f069 `
  --case-record G:\Programming\_Data\Visual-QC-Controlled-Source\incoming\feishu-Bf57b8-20260724\recvq19VUYj1AX\CASE-005-BG6-repair-case-record.json `
  --source-package after_repair=G:\Programming\_Data\Visual-QC-Controlled-Source\library\packages\f069-case005-after-source\source-package.json `
  --supporting-file feishu-case005-source-record=G:\Programming\_Data\Visual-QC-Controlled-Source\incoming\feishu-Bf57b8-20260724\recvq19VUYj1AX\CASE-005-BG6-feishu-source-record.txt
```

Expected: status `ok`, state `created`, revision `1`, completeness
`symptom_linked`, identity `unresolved_alias`.

- [ ] **Step 4: Replay and audit**

Run the same command again and expect `state=existing` with the same manifest
SHA-256. Validate the stored revision, rerun the controlled source audit, and
confirm no governed dataset count changes.

### Task 6: Documentation and Full Verification

**Files:**
- Modify: `docs/visual-qc-f069-first-physical-acceptance-2026-07-24.md`
- Modify: `docs/visual-qc-capture-intake-spec-2026-07-20.md`
- Modify: `docs/superpowers/specs/2026-07-24-visual-qc-repair-case-source-design.md`
- Modify: `README.md`

- [ ] **Step 1: Add documentation assertions if an existing fact-source test covers these files**

Use `rg` to identify the current documentation consistency tests. Extend them
to require:

- V1 remains readable and immutable;
- V2 supports unresolved aliases only with exact board identity and evidence;
- CASE005 is an unresolved repair-case source, not a visual diagnosis;
- production remains unchanged.

- [ ] **Step 2: Run the documentation tests and verify RED**

Run the exact identified test modules. Expected: missing V2 wording fails.

- [ ] **Step 3: Update canonical documentation**

Document the V2 identity object, the monotonic resolution rule, CASE005
manifest/hash, and all unchanged downstream boundaries. Remove only current
wording that incorrectly states unresolved sales-model aliases block
board-identified repair-case intake; preserve historical dated statements.

- [ ] **Step 4: Run focused and full verification**

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/test_visual_qc_repair_case_identity.py `
  tests/test_visual_qc_repair_case_contract.py `
  tests/test_visual_qc_repair_case_library.py `
  tests/test_stage_visual_qc_repair_case_cli.py `
  tests/test_visual_qc_repair_case_boundaries.py -q

.\.venv\Scripts\python.exe -m pytest tests -q
node --test (Get-ChildItem tests -Filter *.test.mjs | ForEach-Object FullName)
```

Also run:

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  scripts/visual_qc/repair_case_identity.py `
  scripts/visual_qc/repair_case_contract.py `
  scripts/visual_qc/repair_case_library.py `
  scripts/stage_visual_qc_repair_case.py

git diff --check
```

Parse both JSON Schemas, strict-decode all touched text as UTF-8 with invalid
byte rejection, scan for U+FFFD, and verify both repositories are clean after
commits.

- [ ] **Step 5: Commit documentation and closeout evidence**

```powershell
git add README.md docs/ knowledge-base/ scripts/ tests/
git commit -m "docs: record first unresolved repair case identity"
```

- [ ] **Step 6: Sync durable project facts**

Update and commit
`G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`, update the Vault
project Overview, and write back CASE005's repair-case manifest identity and
unresolved sales-model status to Feishu without changing Milo's original
collection fields.
