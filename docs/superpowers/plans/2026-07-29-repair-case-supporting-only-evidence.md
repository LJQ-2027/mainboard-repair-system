# Repair Case Supporting-Only Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a V3 repair-case evidence mode that preserves exact repair-in-progress HEIC photographs without creating Visual-QC source packages, then publish F069 CASE003 and CASE004 under that contract.

**Architecture:** Evolve the independent append-only repair-case contract to V3 while leaving V1/V2 bytes and semantics unchanged. V3 introduces an immutable `evidence_mode` and contextual supporting-evidence records; `supporting_only` permits no package links and requires contextual image evidence. The controlled library stores valid HEIC bytes directly, while all registration, server, Golden, QC, annotation, and training paths remain isolated.

**Tech Stack:** Python 3.11, `unittest`, JSON Schema Draft 2020-12, `pillow-heif`, existing content-addressed controlled library, existing owner-only repair-case CLI, PowerShell 7, Feishu Base CLI.

---

## File Map

- Create `knowledge-base/visual-qc-repair-case-source-v3-schema.json`: exact V3
  manifest contract and mode-dependent constraints.
- Modify `scripts/visual_qc/repair_case_contract.py`: V3 dispatch, evidence-mode,
  context, empty-package, and V3 HEIC validation.
- Modify `scripts/visual_qc/repair_case_library.py`: V3 case-record parsing,
  HEIC inspection, supporting-only build/validation, and revision compatibility.
- Modify `scripts/stage_visual_qc_repair_case.py`: optional source-package input
  and `evidence_mode` receipt.
- Modify `scripts/visual_qc/repair_evidence_link_library.py`: read V3 identity
  while retaining exact source-package authority checks.
- Modify `tests/test_visual_qc_repair_case_contract.py`: Python/Schema parity and
  malformed V3 contract cases.
- Modify `tests/test_visual_qc_repair_case_library.py`: HEIC storage,
  supporting-only publication, revision, security, and replay tests.
- Modify `tests/test_stage_visual_qc_repair_case_cli.py`: direct no-package V3
  invocation and failure contract.
- Modify `tests/test_visual_qc_repair_case_boundaries.py`: governed downstream
  exclusion for supporting-only evidence.
- Modify `tests/test_visual_qc_repair_evidence_link_library.py`: V3
  package-linked compatibility and supporting-only rejection.
- Modify `README.md`: owner-only V3 command and explicit non-Visual-QC boundary.
- Modify `docs/visual-qc-capture-intake-spec-2026-07-20.md`: distinguish
  source-package capture stages from supporting-only repair evidence.
- Update `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md` after
  real publication and verification.
- Update the Mainboard Repair Enablement Vault entry, overview, task index, and
  risks after real publication.

## Task 1: V3 Contract And JSON Schema

**Files:**
- Create: `knowledge-base/visual-qc-repair-case-source-v3-schema.json`
- Modify: `scripts/visual_qc/repair_case_contract.py`
- Modify: `tests/test_visual_qc_repair_case_contract.py`

- [ ] **Step 1: Add failing V3 contract fixtures and happy-path tests**

Add the V3 import and Schema path:

```python
from scripts.visual_qc.repair_case_contract import (
    REPAIR_CASE_SCHEMA_V3,
)

V3_SCHEMA_PATH = (
    ROOT
    / "knowledge-base"
    / "visual-qc-repair-case-source-v3-schema.json"
)
```

Add exact V3 helpers:

```python
def heic_supporting_evidence():
    digest = "d" * 64
    return {
        "evidence_id": "repair-photo",
        "original_filename": "repair.heic",
        "object_path": (
            f"objects/case-evidence/{digest[:2]}/{digest}.heic"
        ),
        "mime_type": "image/heic",
        "byte_size": 1024,
        "sha256": digest,
        "description": "Owner-supplied repair-in-progress photograph.",
    }


def repair_photo_context():
    return {
        "evidence_id": "repair-photo",
        "evidence_role": "repair_in_progress_photo",
        "source_capture_stage": "维修中",
        "source_board_area": "屏蔽罩内局部",
    }


def canonical_v3_supporting_only_payload():
    payload = canonical_v2_payload("unresolved_alias")
    payload["schema_version"] = REPAIR_CASE_SCHEMA_V3
    payload["evidence_mode"] = "supporting_only"
    payload["package_links"] = []
    payload["supporting_evidence"] = [heic_supporting_evidence()]
    payload["supporting_evidence_contexts"] = [repair_photo_context()]
    payload["device_identity"]["evidence_refs"] = [
        {"kind": "supporting_evidence", "evidence_id": "repair-photo"}
    ]
    return payload
```

Add tests proving:

```python
def test_canonical_v3_supporting_only_matches_python_and_schema(self):
    payload = canonical_v3_supporting_only_payload()
    validated = validate_repair_case_manifest(
        payload,
        catalog_models=CATALOG_MODELS,
    )
    self.assertEqual(validated, payload)
    schema = json.loads(V3_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(payload)


def test_v3_modes_enforce_package_and_context_cardinality(self):
    invalid_payloads = []

    package_in_supporting_only = canonical_v3_supporting_only_payload()
    package_in_supporting_only["package_links"] = [package_link()]
    invalid_payloads.append(package_in_supporting_only)

    missing_evidence = canonical_v3_supporting_only_payload()
    missing_evidence["supporting_evidence"] = []
    invalid_payloads.append(missing_evidence)

    missing_context = canonical_v3_supporting_only_payload()
    missing_context["supporting_evidence_contexts"] = []
    invalid_payloads.append(missing_context)

    duplicate_context = canonical_v3_supporting_only_payload()
    duplicate_context["supporting_evidence_contexts"].append(
        repair_photo_context()
    )
    invalid_payloads.append(duplicate_context)

    package_linked = canonical_v3_supporting_only_payload()
    package_linked["evidence_mode"] = "package_linked"
    package_linked["package_links"] = [package_link()]
    package_linked["supporting_evidence"] = []
    package_linked["supporting_evidence_contexts"] = []
    package_linked["device_identity"] = device_identity()
    self.assertEqual(
        validate_repair_case_manifest(
            package_linked,
            catalog_models=CATALOG_MODELS,
        ),
        package_linked,
    )

    for payload in invalid_payloads:
        with self.subTest(payload=payload):
            with self.assertRaises(ValueError):
                validate_repair_case_manifest(
                    payload,
                    catalog_models=CATALOG_MODELS,
                )
```

Add this mutation matrix and assert both Python and V3 Schema rejection where
the Schema can express the rule:

```python
def test_v3_rejects_invalid_mode_context_and_mime_shapes(self):
    def unknown_mode(payload):
        payload["evidence_mode"] = "repair_photo"

    def unknown_context_field(payload):
        payload["supporting_evidence_contexts"][0]["unexpected"] = True

    def dangling_context(payload):
        payload["supporting_evidence_contexts"][0]["evidence_id"] = "missing"

    def duplicate_context(payload):
        payload["supporting_evidence_contexts"].append(
            copy.deepcopy(payload["supporting_evidence_contexts"][0])
        )

    def empty_stage(payload):
        payload["supporting_evidence_contexts"][0][
            "source_capture_stage"
        ] = " "

    def non_image_photo(payload):
        payload["supporting_evidence"][0] = supporting_evidence()
        payload["supporting_evidence_contexts"][0]["evidence_id"] = "case-note"

    for mutate in (
        unknown_mode,
        unknown_context_field,
        dangling_context,
        duplicate_context,
        empty_stage,
        non_image_photo,
    ):
        payload = canonical_v3_supporting_only_payload()
        mutate(payload)
        with self.subTest(mutate=mutate.__name__):
            with self.assertRaises(ValueError):
                validate_repair_case_manifest(
                    payload,
                    catalog_models=CATALOG_MODELS,
                )


def test_heic_supporting_evidence_remains_v3_only(self):
    for payload, catalog in (
        (canonical_payload(), None),
        (canonical_v2_payload(), CATALOG_MODELS),
    ):
        payload["supporting_evidence"] = [heic_supporting_evidence()]
        with self.subTest(version=payload["schema_version"]):
            with self.assertRaisesRegex(ValueError, "MIME"):
                validate_repair_case_manifest(
                    payload,
                    catalog_models=catalog,
                )
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_repair_case_contract -v
```

Expected: import or Schema-path failure because V3 does not exist.

- [ ] **Step 3: Add V3 constants and exact validators**

Add these constants:

```python
REPAIR_CASE_SCHEMA_V3 = "VISUAL-QC-REPAIR-CASE-SOURCE-V3"
REPAIR_CASE_SCHEMA_VERSIONS = {
    REPAIR_CASE_SCHEMA_V1,
    REPAIR_CASE_SCHEMA_V2,
    REPAIR_CASE_SCHEMA_V3,
}
EVIDENCE_MODES = {"package_linked", "supporting_only"}
SUPPORTING_EVIDENCE_CONTEXT_FIELDS = {
    "evidence_id",
    "evidence_role",
    "source_capture_stage",
    "source_board_area",
}
SUPPORTING_EVIDENCE_ROLES = {"repair_in_progress_photo"}
MIME_EXTENSIONS_V3 = {**MIME_EXTENSIONS, "image/heic": ".heic"}
V3_MANIFEST_FIELDS = V2_MANIFEST_FIELDS | {
    "evidence_mode",
    "supporting_evidence_contexts",
}
```

Change package validation to accept a mode-specific empty list:

```python
def _validate_package_links(
    value,
    *,
    allow_empty: bool = False,
) -> tuple[set[tuple[str, str]], set[str]]:
    minimum = 0 if allow_empty else 1
    if (
        not isinstance(value, list)
        or len(value) < minimum
        or len(value) > 100
    ):
        label = "0 to 100" if allow_empty else "1 to 100"
        raise ValueError(f"package_links must contain {label} records.")
    # Keep the existing per-link loop unchanged.
```

Make supporting MIME validation version-aware:

```python
def _validate_supporting_evidence(
    value,
    *,
    allowed_mime_extensions: dict[str, str] = MIME_EXTENSIONS,
) -> tuple[set[str], dict[str, str]]:
    if not isinstance(value, list) or len(value) > MAX_SUPPORTING_FILES:
        raise ValueError("supporting_evidence exceeds its record limit.")
    evidence_ids: set[str] = set()
    evidence_mimes: dict[str, str] = {}
    for index, raw in enumerate(value):
        # Retain the existing exact-field, filename, size, hash and object checks.
        mime_type = evidence["mime_type"]
        if mime_type not in allowed_mime_extensions:
            raise ValueError("supporting evidence MIME type is invalid.")
        extension = allowed_mime_extensions[mime_type]
        evidence_mimes[evidence_id] = mime_type
    return evidence_ids, evidence_mimes
```

Add the context validator:

```python
def _validate_supporting_evidence_contexts(
    value,
    *,
    evidence_ids: set[str],
    evidence_mimes: dict[str, str],
    require_complete_coverage: bool,
) -> set[str]:
    if not isinstance(value, list) or len(value) > MAX_SUPPORTING_FILES:
        raise ValueError("supporting_evidence_contexts are invalid.")
    seen: set[str] = set()
    for index, raw in enumerate(value):
        context = _expect_object(
            raw,
            SUPPORTING_EVIDENCE_CONTEXT_FIELDS,
            f"supporting_evidence_contexts[{index}]",
        )
        evidence_id = _safe_id(context["evidence_id"], "evidence_id")
        _unique_id(evidence_id, seen, "supporting context evidence_id")
        if evidence_id not in evidence_ids:
            raise ValueError("supporting evidence context does not resolve.")
        if context["evidence_role"] not in SUPPORTING_EVIDENCE_ROLES:
            raise ValueError("supporting evidence role is invalid.")
        _required_text(
            context["source_capture_stage"],
            "source_capture_stage",
        )
        _required_text(context["source_board_area"], "source_board_area")
        if evidence_mimes[evidence_id] not in {
            "image/png",
            "image/jpeg",
            "image/heic",
        }:
            raise ValueError(
                "repair_in_progress_photo requires image evidence."
            )
    if require_complete_coverage and seen != evidence_ids:
        raise ValueError(
            "supporting_only contexts must cover every evidence record."
        )
    return seen
```

Dispatch exact V3 fields and mode rules inside
`validate_repair_case_manifest`:

```python
if schema_version == REPAIR_CASE_SCHEMA_V1:
    manifest_fields = V1_MANIFEST_FIELDS
elif schema_version == REPAIR_CASE_SCHEMA_V2:
    manifest_fields = V2_MANIFEST_FIELDS
else:
    manifest_fields = V3_MANIFEST_FIELDS

evidence_mode = (
    manifest["evidence_mode"]
    if schema_version == REPAIR_CASE_SCHEMA_V3
    else "package_linked"
)
if evidence_mode not in EVIDENCE_MODES:
    raise ValueError("evidence_mode is invalid.")
package_targets, _ = _validate_package_links(
    manifest["package_links"],
    allow_empty=evidence_mode == "supporting_only",
)
supporting_targets, supporting_mimes = _validate_supporting_evidence(
    manifest["supporting_evidence"],
    allowed_mime_extensions=(
        MIME_EXTENSIONS_V3
        if schema_version == REPAIR_CASE_SCHEMA_V3
        else MIME_EXTENSIONS
    ),
)
if schema_version == REPAIR_CASE_SCHEMA_V3:
    _validate_supporting_evidence_contexts(
        manifest["supporting_evidence_contexts"],
        evidence_ids=supporting_targets,
        evidence_mimes=supporting_mimes,
        require_complete_coverage=evidence_mode == "supporting_only",
    )
    if evidence_mode == "package_linked" and not manifest["package_links"]:
        raise ValueError("package_linked requires package links.")
    if evidence_mode == "supporting_only":
        if manifest["package_links"]:
            raise ValueError("supporting_only cannot contain package links.")
        if not manifest["supporting_evidence"]:
            raise ValueError("supporting_only requires supporting evidence.")
```

Use V2 identity and boundary validation for both V2 and V3.

- [ ] **Step 4: Create the V3 JSON Schema**

Create the file from the V2 Schema:

```powershell
Copy-Item `
  knowledge-base/visual-qc-repair-case-source-v2-schema.json `
  knowledge-base/visual-qc-repair-case-source-v3-schema.json
```

Apply these exact semantic changes:

```json
{
  "$id": "VISUAL-QC-REPAIR-CASE-SOURCE-V3",
  "title": "Visual QC Repair Case Source V3"
}
```

Add `evidence_mode` and `supporting_evidence_contexts` to `required`, set the
schema-version const to V3, remove `minItems` from `package_links`, and add:

```json
"evidence_mode": {
  "enum": ["package_linked", "supporting_only"]
},
"supporting_evidence_contexts": {
  "type": "array",
  "maxItems": 50,
  "items": {"$ref": "#/$defs/supportingEvidenceContext"}
}
```

Extend V3 supporting evidence only:

```json
"object_path": {
  "type": "string",
  "pattern": "^objects/case-evidence/[0-9a-f]{2}/[0-9a-f]{64}\\.(pdf|txt|csv|xls|xlsx|png|jpg|heic)$"
},
"mime_type": {
  "enum": [
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
    "image/heic"
  ]
}
```

Add the context definition:

```json
"supportingEvidenceContext": {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "evidence_id",
    "evidence_role",
    "source_capture_stage",
    "source_board_area"
  ],
  "properties": {
    "evidence_id": {"$ref": "#/$defs/safeId"},
    "evidence_role": {"const": "repair_in_progress_photo"},
    "source_capture_stage": {"$ref": "#/$defs/nonEmptyString"},
    "source_board_area": {"$ref": "#/$defs/nonEmptyString"}
  }
}
```

Add these exact `allOf` branches. Python remains authoritative for exact ID
coverage and MIME-to-role correlation that JSON Schema cannot express simply.

```json
{
  "if": {
    "properties": {"evidence_mode": {"const": "package_linked"}},
    "required": ["evidence_mode"]
  },
  "then": {
    "properties": {"package_links": {"minItems": 1}}
  }
},
{
  "if": {
    "properties": {"evidence_mode": {"const": "supporting_only"}},
    "required": ["evidence_mode"]
  },
  "then": {
    "properties": {
      "package_links": {"maxItems": 0},
      "supporting_evidence": {"minItems": 1},
      "supporting_evidence_contexts": {"minItems": 1}
    }
  }
}
```

- [ ] **Step 5: Run focused contract tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_visual_qc_repair_case_contract -v
```

Expected: all contract tests pass.

- [ ] **Step 6: Commit the contract**

```powershell
git add `
  knowledge-base/visual-qc-repair-case-source-v3-schema.json `
  scripts/visual_qc/repair_case_contract.py `
  tests/test_visual_qc_repair_case_contract.py
git commit -m "feat: add supporting-only repair case v3 contract"
```

## Task 2: HEIC Inspection And Supporting-Only Library Build

**Files:**
- Modify: `scripts/visual_qc/repair_case_library.py`
- Modify: `tests/test_visual_qc_repair_case_library.py`

- [ ] **Step 1: Add failing valid/invalid HEIC tests**

Import Pillow and the V3 constant:

```python
from PIL import Image
from pillow_heif import from_pillow

from scripts.visual_qc.repair_case_contract import REPAIR_CASE_SCHEMA_V3
```

Add a real HEIC writer:

```python
def write_heic(path: Path, *, width=180, height=120, value=120):
    image = Image.new("RGB", (width, height), (value, value, value))
    from_pillow(image).save(path, quality=90)
    return path
```

Add a V3 case-record helper:

```python
def v3_supporting_only_record(self, evidence_id="repair-photo"):
    ref = {"kind": "supporting_evidence", "evidence_id": evidence_id}
    return {
        "device_identity": self.unresolved_f069_identity(evidence_id),
        "evidence_mode": "supporting_only",
        "supporting_evidence_contexts": [
            {
                "evidence_id": evidence_id,
                "evidence_role": "repair_in_progress_photo",
                "source_capture_stage": "维修中",
                "source_board_area": "屏蔽罩内局部",
            }
        ],
        "supporting_evidence_descriptions": {
            evidence_id: "Owner-supplied repair-in-progress photograph"
        },
        "reported_symptoms": [
            {
                "symptom_id": "symptom-charge",
                "text": "无法充电",
                "source_wording": "无法充电",
                "fault_code": None,
                "evidence_refs": [ref],
            }
        ],
        "findings": [],
        "repair_actions": [],
        "outcome": {
            "status": "unknown",
            "description": None,
            "verification_description": None,
            "evidence_refs": [],
        },
        "corrections": [],
    }
```

Add tests:

```python
def test_v3_supporting_only_stores_exact_heic_without_package(self):
    photo = write_heic(self.root / "repair.heic")
    source_bytes = photo.read_bytes()
    created = self.stage_f069_case(
        repair_case_id="case-f069-supporting-only",
        package_assignments=[],
        case_record=self.v3_supporting_only_record(),
        supporting=[("repair-photo", photo)],
    )
    payload = json.loads(created["manifest_path"].read_text(encoding="utf-8"))
    evidence = payload["supporting_evidence"][0]
    self.assertEqual(created["schema_version"], REPAIR_CASE_SCHEMA_V3)
    self.assertEqual(created["evidence_mode"], "supporting_only")
    self.assertEqual(created["package_count"], 0)
    self.assertEqual(evidence["mime_type"], "image/heic")
    self.assertTrue(evidence["object_path"].endswith(".heic"))
    self.assertEqual(
        (self.library / evidence["object_path"]).read_bytes(),
        source_bytes,
    )


def test_v1_v2_and_invalid_heic_remain_rejected(self):
    photo = write_heic(self.root / "repair.heic")
    with self.assertRaisesRegex(IntakeValidationError, "unsupported"):
        inspect_supporting_evidence(
            [("repair-photo", photo)],
            {"repair-photo": "Photo"},
            schema_version=REPAIR_CASE_SCHEMA_V2,
        )

    invalid = self.root / "invalid.heic"
    invalid.write_bytes(b"not-a-heic")
    with self.assertRaisesRegex(IntakeValidationError, "HEIC"):
        inspect_supporting_evidence(
            [("repair-photo", invalid)],
            {"repair-photo": "Photo"},
            schema_version=REPAIR_CASE_SCHEMA_V3,
        )
```

Add named tests with these exact assertions:

```python
def test_supporting_only_requires_at_least_one_supporting_file(self):
    with self.assertRaisesRegex(IntakeValidationError, "requires"):
        self.stage_f069_case(
            package_assignments=[],
            case_record=self.v3_supporting_only_record(),
            supporting=[],
        )


def test_supporting_only_replay_is_idempotent_and_corruption_fails(self):
    photo = write_heic(self.root / "repair.heic")
    options = {
        "repair_case_id": "case-f069-v3-replay",
        "package_assignments": [],
        "case_record": self.v3_supporting_only_record(),
        "supporting": [("repair-photo", photo)],
    }
    created = self.stage_f069_case(**options)
    replayed = self.stage_f069_case(**options)
    self.assertEqual(replayed["state"], "existing")
    self.assertEqual(
        replayed["manifest_sha256"],
        created["manifest_sha256"],
    )
    payload = json.loads(created["manifest_path"].read_text(encoding="utf-8"))
    evidence_path = self.library / payload["supporting_evidence"][0][
        "object_path"
    ]
    evidence_path.write_bytes(b"corrupt")
    with self.assertRaisesRegex(IntakeValidationError, "integrity mismatch"):
        validate_repair_case_revision(
            manifest_path=created["manifest_path"],
            project_root=ROOT,
            library_root=self.library,
        )
```

Reuse the existing source-file mutation, hard-link, symlink, junction, reparse,
and atomic-publication harnesses with `package_assignments=[]` and the V3 record;
each must assert that no `.complete` revision and no new case-evidence object
remain after failure.

- [ ] **Step 2: Run the focused library tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_case_library -v
```

Expected: V3 case-record shape or HEIC MIME failure.

- [ ] **Step 3: Make supporting inspection schema-aware**

Import:

```python
from scripts.visual_qc.heic_derivative import (
    HEIC_MIME_TYPE,
    inspect_heic_source,
    is_heic_path,
)
```

Change the MIME detector signature and HEIC branch:

```python
def _detect_supporting_mime(
    path: Path,
    content: bytes,
    *,
    schema_version: str,
) -> str:
    extension = path.suffix.lower()
    if (
        schema_version == REPAIR_CASE_SCHEMA_V3
        and is_heic_path(path)
    ):
        evidence = inspect_heic_source(path)
        if (
            evidence["sha256"] != hashlib.sha256(content).hexdigest()
            or evidence["byte_size"] != len(content)
            or evidence["mime_type"] != HEIC_MIME_TYPE
        ):
            raise IntakeValidationError("HEIC supporting evidence changed")
        return HEIC_MIME_TYPE
    # Retain all existing V1/V2 MIME branches unchanged.
```

Change inspection to receive the schema version:

```python
def inspect_supporting_evidence(
    assignments: list[tuple[str, Path]],
    descriptions: dict[str, str],
    *,
    schema_version: str = REPAIR_CASE_SCHEMA_V1,
) -> list[dict]:
    # Existing validation remains.
    mime_type = _detect_supporting_mime(
        path,
        content,
        schema_version=schema_version,
    )
    extension = (
        MIME_EXTENSIONS_V3
        if schema_version == REPAIR_CASE_SCHEMA_V3
        else MIME_EXTENSIONS
    )[mime_type]
```

- [ ] **Step 4: Parse the exact V3 case-record shape**

Add:

```python
V3_CASE_RECORD_FIELDS = COMMON_CASE_RECORD_FIELDS | {
    "device_identity",
    "evidence_mode",
    "supporting_evidence_contexts",
}
```

Dispatch in `_validate_case_record`:

```python
elif fields == V3_CASE_RECORD_FIELDS:
    schema_version = REPAIR_CASE_SCHEMA_V3
```

In `_prepare_repair_case_revision`, derive package links by mode:

```python
evidence_mode = (
    record["evidence_mode"]
    if schema_version == REPAIR_CASE_SCHEMA_V3
    else "package_linked"
)
if evidence_mode == "supporting_only":
    if package_assignments:
        raise IntakeValidationError(
            "supporting_only cannot contain source packages"
        )
    links = []
else:
    links = resolve_package_links(
        project_root=project_root,
        library_root=library_root,
        assignments=package_assignments,
        board_key=board_key,
    )
if not links and not supporting_assignments:
    raise IntakeValidationError(
        "repair case requires source package or supporting evidence"
    )
```

Pass `schema_version` into supporting inspection and add V3 fields to the
manifest:

```python
inspected = inspect_supporting_evidence(
    supporting_assignments,
    record["supporting_evidence_descriptions"],
    schema_version=schema_version,
)

mode_fields = (
    {
        "evidence_mode": evidence_mode,
        "supporting_evidence_contexts": copy.deepcopy(
            record["supporting_evidence_contexts"]
        ),
    }
    if schema_version == REPAIR_CASE_SCHEMA_V3
    else {}
)
```

Include `**mode_fields` in the payload and `evidence_mode` in `_revision_result`.

- [ ] **Step 5: Run library and contract tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_case_contract `
  tests.test_visual_qc_repair_case_library -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit HEIC and supporting-only build**

```powershell
git add `
  scripts/visual_qc/repair_case_library.py `
  tests/test_visual_qc_repair_case_library.py
git commit -m "feat: preserve supporting-only repair HEIC evidence"
```

## Task 3: Revision Compatibility And Disk Validation

**Files:**
- Modify: `scripts/visual_qc/repair_case_library.py`
- Modify: `tests/test_visual_qc_repair_case_library.py`

- [ ] **Step 1: Add failing revision-chain tests**

Add these revision tests:

```python
def test_supporting_only_mode_is_immutable_across_v3_revisions(self):
    photo = write_heic(self.root / "repair.heic")
    first = self.stage_f069_case(
        repair_case_id="case-f069-v3-mode",
        package_assignments=[],
        case_record=self.v3_supporting_only_record(),
        supporting=[("repair-photo", photo)],
    )
    switched = self.v3_supporting_only_record()
    switched["evidence_mode"] = "package_linked"
    with self.assertRaisesRegex(IntakeValidationError, "evidence mode"):
        self.stage_f069_case(
            repair_case_id="case-f069-v3-mode",
            case_record=switched,
            previous_manifest_path=first["manifest_path"],
        )


def test_disk_validator_skips_package_resolution_for_supporting_only(self):
    photo = write_heic(self.root / "repair.heic")
    created = self.stage_f069_case(
        repair_case_id="case-f069-v3-disk",
        package_assignments=[],
        case_record=self.v3_supporting_only_record(),
        supporting=[("repair-photo", photo)],
    )
    validated = validate_repair_case_revision(
        manifest_path=created["manifest_path"],
        project_root=ROOT,
        library_root=self.library,
    )
    self.assertEqual(validated["package_links"], [])
    self.assertEqual(validated["evidence_mode"], "supporting_only")
```

Add explicit test methods named:

- `test_v1_v2_to_v3_require_package_linked`
- `test_v3_cannot_downgrade`
- `test_v3_contexts_are_append_only`
- `test_v3_cannot_rewrite_mode_heic_or_context_wording`
- `test_v3_new_context_requires_consistent_appended_evidence`
- `test_v3_disk_validation_rejects_changed_object_context_or_manifest`

Each test stages revision 1, snapshots its manifest/object SHA-256, attempts the
named invalid revision or mutation, asserts `IntakeValidationError`, asserts no
next `.complete` revision exists, and rechecks the original hashes.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_case_library -v
```

Expected: mode-transition or empty-link disk-validation failure.

- [ ] **Step 3: Implement V3 transition rules**

Extend `_validate_revision_transition`:

```python
previous_version = previous["schema_version"]
current_version = current["schema_version"]

if previous_version == REPAIR_CASE_SCHEMA_V3:
    if current_version != REPAIR_CASE_SCHEMA_V3:
        raise IntakeValidationError(
            "V3 repair case downgrade is not allowed"
        )
    if current["evidence_mode"] != previous["evidence_mode"]:
        raise IntakeValidationError(
            "repair case revision changes historical evidence mode"
        )
    _assert_prefix(
        previous["supporting_evidence_contexts"],
        current["supporting_evidence_contexts"],
        "supporting evidence contexts",
    )

if (
    previous_version in {REPAIR_CASE_SCHEMA_V1, REPAIR_CASE_SCHEMA_V2}
    and current_version == REPAIR_CASE_SCHEMA_V3
    and current["evidence_mode"] != "package_linked"
):
    raise IntakeValidationError(
        "historical repair case can enter V3 only as package_linked"
    )
```

Treat V2 and V3 identically for device-identity transition validation. For a
V1-to-V3 migration, apply the existing exact-catalog V1-to-V2 rule and require
`package_linked`.

In disk validation:

```python
expected_links = (
    []
    if (
        validated["schema_version"] == REPAIR_CASE_SCHEMA_V3
        and validated["evidence_mode"] == "supporting_only"
    )
    else resolve_package_links(...)
)
```

Keep stored object hash/size checks identical for HEIC and all historical
formats.

- [ ] **Step 4: Run the repair-case suite and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_case_contract `
  tests.test_visual_qc_repair_case_identity `
  tests.test_visual_qc_repair_case_library -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit revision compatibility**

```powershell
git add `
  scripts/visual_qc/repair_case_library.py `
  tests/test_visual_qc_repair_case_library.py
git commit -m "feat: enforce supporting-only repair revision history"
```

## Task 4: Owner CLI

**Files:**
- Modify: `scripts/stage_visual_qc_repair_case.py`
- Modify: `tests/test_stage_visual_qc_repair_case_cli.py`

- [ ] **Step 1: Add failing no-package V3 CLI tests**

Add a helper that removes the package arguments from the command:

```python
def supporting_only_command(self, photo):
    command = [
        sys.executable,
        str(self.script),
        "--library-root",
        str(self.library),
        "--repair-case-id",
        "case-f069-supporting-only-cli",
        "--board-key",
        "bg6h-f069",
        "--case-record",
        str(self.case_record),
        "--supporting-file",
        f"repair-photo={photo}",
    ]
    return command
```

Add tests proving a V3 HEIC call creates and replays with:

```python
self.assertEqual(payload["schema_version"], REPAIR_CASE_SCHEMA_V3)
self.assertEqual(payload["evidence_mode"], "supporting_only")
self.assertEqual(payload["package_count"], 0)
self.assertEqual(payload["supporting_evidence_count"], 1)
```

Add one table-driven CLI test with these command/record mutations:

- remove `--source-package` from the existing V1 command;
- use a V2 case record and no `--source-package`;
- set V3 `evidence_mode=package_linked` and omit the package;
- use V3 supporting-only and omit `--supporting-file`;
- append the existing `--source-package` to V3 supporting-only;
- set `supporting_evidence_contexts` to `{}`;
- replace the HEIC bytes with `b"not-a-heic"`.

For each case assert return code `2`, stdout status `validation_failed`, empty
stderr, no completed case revision, and no new case-evidence object.

- [ ] **Step 2: Run CLI tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_stage_visual_qc_repair_case_cli -v
```

Expected: argparse requires `--source-package`, or receipt fields are missing.

- [ ] **Step 3: Make the package argument optional and extend the receipt**

Change parser configuration:

```python
parser.add_argument(
    "--source-package",
    action="append",
    default=[],
    metavar="ROLE=PATH",
)
```

Add receipt fields:

```python
"evidence_mode": result["evidence_mode"],
"package_count": result["package_count"],
"supporting_evidence_count": result["supporting_evidence_count"],
```

Do not add inference flags, alternate upload paths, or a technician-facing
command.

- [ ] **Step 4: Run CLI and library tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_stage_visual_qc_repair_case_cli `
  tests.test_visual_qc_repair_case_library -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit the CLI**

```powershell
git add `
  scripts/stage_visual_qc_repair_case.py `
  tests/test_stage_visual_qc_repair_case_cli.py
git commit -m "feat: stage supporting-only repair cases"
```

## Task 5: Downstream Isolation And Repair-Evidence Compatibility

**Files:**
- Modify: `scripts/visual_qc/repair_evidence_link_library.py`
- Modify: `tests/test_visual_qc_repair_case_boundaries.py`
- Modify: `tests/test_visual_qc_repair_evidence_link_library.py`

- [ ] **Step 1: Add failing downstream boundary tests**

In the repair-case boundary test, stage a V3 supporting-only HEIC case and
assert:

```python
self.assertEqual(payload["package_links"], [])
self.assertEqual(payload["evidence_mode"], "supporting_only")
self.assertEqual(
    payload["boundaries"],
    {**FIXED_FALSE_BOUNDARIES, "model_identity_resolved": False},
)
self.assertEqual(service.store.operational_counts()["cases"]["total"], 0)
self.assertEqual(service.training_manifest()["cases"], [])
self.assertEqual(service.training_coco()["images"], [])
self.assertEqual(service.training_coco()["annotations"], [])
```

Inspect the generated dataset bundle and assert that the repair-case ID, HEIC
hash, evidence ID, `维修中`, `屏蔽罩内局部`, symptoms, and findings do not occur.

In repair-evidence-link tests:

```python
def test_v3_supporting_only_cannot_bind_physical_evidence(self):
    with self.assertRaisesRegex(
        RepairEvidenceLinkLibraryError,
        "source package is not linked",
    ):
        stage_repair_evidence_link_revision(
            repair_case_assignments=[
                ("case-ref", supporting_only_manifest)
            ],
            physical_evidence_paths=[physical_snapshot],
            binding_record=record,
            ...
        )
```

Also prove a V3 `package_linked` case can use the same link flow as V2.

- [ ] **Step 2: Run boundary and link tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_case_boundaries `
  tests.test_visual_qc_repair_evidence_link_library -v
```

Expected: V3 is unsupported by the repair-evidence identity reader.

- [ ] **Step 3: Accept V3 identity without weakening source-package checks**

Import `REPAIR_CASE_SCHEMA_V3` and change:

```python
def _model_identity_resolved(case: dict) -> bool:
    if case["schema_version"] == REPAIR_CASE_SCHEMA_V1:
        return True
    if case["schema_version"] not in {
        REPAIR_CASE_SCHEMA_V2,
        REPAIR_CASE_SCHEMA_V3,
    }:
        _error("repair case schema version is unsupported")
    value = case.get("boundaries", {}).get("model_identity_resolved")
    if type(value) is not bool:
        _error("repair case model identity boundary is invalid")
    return value
```

Do not change `_validate_physical_authority`. Its existing exact source-package
hash and entry checks must reject a V3 supporting-only case because
`package_links=[]`.

- [ ] **Step 4: Run focused and dataset tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_case_boundaries `
  tests.test_visual_qc_repair_evidence_link_contract `
  tests.test_visual_qc_repair_evidence_link_library `
  tests.test_visual_qc_dataset -v
```

Expected: all tests pass and no supporting-only evidence enters a governed
surface.

- [ ] **Step 5: Commit downstream isolation**

```powershell
git add `
  scripts/visual_qc/repair_evidence_link_library.py `
  tests/test_visual_qc_repair_case_boundaries.py `
  tests/test_visual_qc_repair_evidence_link_library.py
git commit -m "test: isolate supporting-only repair evidence"
```

## Task 6: Operator Documentation And Full Regression

**Files:**
- Modify: `README.md`
- Modify: `docs/visual-qc-capture-intake-spec-2026-07-20.md`

- [ ] **Step 1: Update the operator documentation**

Document this exact example:

```powershell
.\.venv\Scripts\python.exe scripts\stage_visual_qc_repair_case.py `
  --library-root G:\Programming\_Data\Visual-QC-Controlled-Source\library `
  --repair-case-id case-003-bg6-f069 `
  --board-key bg6h-f069 `
  --case-record <case-record-v3.json> `
  --supporting-file repair-in-progress-photo=<IMG_5604.HEIC>
```

State directly:

- absence of `--source-package` is valid only for V3 `supporting_only`;
- `source_capture_stage` is preserved source wording, not a Visual-QC stage;
- no derivative, registration, Golden, QC, annotation, training, API, or
  production record is created;
- package-linked V1/V2 behavior remains unchanged.

- [ ] **Step 2: Run all focused Python tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest `
  tests.test_visual_qc_repair_case_contract `
  tests.test_visual_qc_repair_case_identity `
  tests.test_visual_qc_repair_case_library `
  tests.test_stage_visual_qc_repair_case_cli `
  tests.test_visual_qc_repair_case_boundaries `
  tests.test_visual_qc_repair_evidence_link_contract `
  tests.test_visual_qc_repair_evidence_link_library -v
```

Expected: all focused tests pass.

- [ ] **Step 3: Run the full regression and static checks**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
node --test tests/*.test.mjs
.\.venv\Scripts\python.exe -m compileall -q scripts
git diff --check
```

Expected:

- Python suite passes with only existing documented platform skips;
- Node suite passes;
- compilation exits zero;
- `git diff --check` prints no errors.

Parse all repair-case Schemas and run strict UTF-8/U+FFFD checks on every
touched text file.

- [ ] **Step 4: Commit documentation and close code implementation**

```powershell
git add README.md docs/visual-qc-capture-intake-spec-2026-07-20.md
git commit -m "docs: document supporting-only repair evidence"
```

## Task 7: Publish Real CASE003 And CASE004

**Files:**
- Create outside Git: temporary CASE003/CASE004 V3 case-record JSON inputs.
- Create outside Git: temporary validation library.
- Publish outside Git:
  `G:/Programming/_Data/Visual-QC-Controlled-Source/library/cases/case-003-bg6-f069`
- Publish outside Git:
  `G:/Programming/_Data/Visual-QC-Controlled-Source/library/cases/case-004-bg6-f069`
- Modify: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`
- Modify Vault project entry, overview, task index, and risks.
- Update Feishu Base only after controlled publication succeeds.

- [ ] **Step 1: Verify the preserved source bytes**

Run:

```powershell
Get-FileHash `
  'G:\Programming\_Data\Visual-QC-Controlled-Source\incoming\feishu-Bf57b8-20260724\recvq19e1dBvWY\IMG_5604.HEIC' `
  -Algorithm SHA256
Get-FileHash `
  'G:\Programming\_Data\Visual-QC-Controlled-Source\incoming\feishu-Bf57b8-20260724\recvq19C6xXFUa\IMG_5602.HEIC' `
  -Algorithm SHA256
```

Expected:

```text
IMG_5604.HEIC  01078e943ceeba14567345919d185a56f3e254e6c8dc38135ded067f7e1fae30
IMG_5602.HEIC  0250e050c58b3d1faf9cbe9788c84bba3df42f91e922da73aa1490b1801b7df1
```

- [ ] **Step 2: Create privacy-reduced exact case records**

CASE003 record:

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
        "evidence_id": "repair-in-progress-photo"
      }
    ]
  },
  "evidence_mode": "supporting_only",
  "supporting_evidence_contexts": [
    {
      "evidence_id": "repair-in-progress-photo",
      "evidence_role": "repair_in_progress_photo",
      "source_capture_stage": "维修中",
      "source_board_area": "屏蔽罩内局部"
    }
  ],
  "supporting_evidence_descriptions": {
    "repair-in-progress-photo": "Milo-supplied CASE003 repair-in-progress photograph"
  },
  "reported_symptoms": [
    {
      "symptom_id": "unable-to-charge",
      "text": "无法充电",
      "source_wording": "无法充电",
      "fault_code": null,
      "evidence_refs": []
    }
  ],
  "findings": [
    {
      "finding_id": "power-bad",
      "claim_status": "documented",
      "description": "电源坏",
      "defect_category": null,
      "designator": null,
      "side_id": null,
      "region": null,
      "evidence_refs": []
    }
  ],
  "repair_actions": [],
  "outcome": {
    "status": "repair_completed",
    "description": "维修后已修复",
    "verification_description": null,
    "evidence_refs": []
  },
  "corrections": []
}
```

CASE004 record:

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
        "evidence_id": "repair-in-progress-photo"
      }
    ]
  },
  "evidence_mode": "supporting_only",
  "supporting_evidence_contexts": [
    {
      "evidence_id": "repair-in-progress-photo",
      "evidence_role": "repair_in_progress_photo",
      "source_capture_stage": "维修中",
      "source_board_area": "屏蔽罩内局部"
    }
  ],
  "supporting_evidence_descriptions": {
    "repair-in-progress-photo": "Milo-supplied CASE004 repair-in-progress photograph"
  },
  "reported_symptoms": [
    {
      "symptom_id": "unable-to-charge",
      "text": "无法充电",
      "source_wording": "无法充电",
      "fault_code": null,
      "evidence_refs": []
    }
  ],
  "findings": [
    {
      "finding_id": "charging-ic-burnt",
      "claim_status": "documented",
      "description": "充电IC烧坏",
      "defect_category": null,
      "designator": null,
      "side_id": null,
      "region": null,
      "evidence_refs": []
    }
  ],
  "repair_actions": [],
  "outcome": {
    "status": "repair_completed",
    "description": "维修后已修复",
    "verification_description": null,
    "evidence_refs": []
  },
  "corrections": []
}
```

Do not add a designator, region, defect category, action, verification method,
or visible-burn annotation.

- [ ] **Step 3: Rehearse both cases in a fresh temporary library**

Run the CLI twice without `--source-package`, using the two exact HEIC paths.
For each receipt, assert:

```text
status=ok
state=created
schema_version=VISUAL-QC-REPAIR-CASE-SOURCE-V3
evidence_mode=supporting_only
package_count=0
supporting_evidence_count=1
identity_status=unresolved_alias
completeness=diagnosis_linked
```

Run `validate_repair_case_revision` on both temporary manifests. Compare stored
object hashes and sizes against the source bytes. Re-run both commands and
require `state=existing` with identical manifest SHA-256.

- [ ] **Step 4: Publish to the controlled library**

Run the same two commands against:

```text
G:\Programming\_Data\Visual-QC-Controlled-Source\library
```

Reopen and validate both published manifests. Confirm:

- `.complete` exists;
- revision is 1;
- `package_links=[]`;
- source and stored HEIC bytes match exactly;
- contexts retain `维修中` and `屏蔽罩内局部`;
- five fixed downstream boundaries are false;
- `model_identity_resolved=false`;
- there is no source package, physical acceptance, handoff, server case,
  annotation, Golden, or training record.

- [ ] **Step 5: Re-run controlled audits and regression smoke**

Run the existing source-library audit and confirm existing source packages and
objects remain healthy. Validate CASE003/004 directly because source-library
audit intentionally does not treat repair-case supporting objects as source
packages.

Re-run the focused repair-case and boundary tests after publication.

- [ ] **Step 6: Update Feishu status and reread**

For case records `recvpVTDi1wknh`, `recvpVTDxYkfmG` and photo records
`recvq19e1dBvWY`, `recvq19C6xXFUa`, update only:

```text
Codex录入状态 = 已进入案例库
Codex录入说明 = exact V3 case/package-free supporting evidence receipt,
                original filename/hash,
                维修中 boundary,
                no Visual-QC/Golden/QC/training claim
```

Reread all four rows. Do not modify original model, board, stage, board-area,
symptom, finding, repair status, attachments, or Milo collection fields.

- [ ] **Step 7: Record durable project facts**

Update the enablement ledger and Vault with:

- implementation commits and test counts;
- CASE003/004 manifest hashes and exact object hashes;
- supporting-only mode and zero package links;
- preserved source stage/area;
- no visible-defect, registration, Golden, QC, training, repair-causality,
  repair-instruction, field-accuracy, or model-alias claim;
- production unchanged at `f278061`.

Run strict UTF-8/U+FFFD checks on every updated durable record.

- [ ] **Step 8: Final verification and closeout commit**

Run:

```powershell
git status --short --branch
git log -8 --oneline
```

Confirm implementation tracked files are clean except intentional generated
`output/` evidence. Commit the enablement ledger separately:

```powershell
git add PROJECT_LEDGER.md
git commit -m "docs: record CASE003 CASE004 supporting evidence"
```

Do not deploy or push. Production remains `f278061`, and current Milo network
status keeps GitHub push outside normal closeout.
