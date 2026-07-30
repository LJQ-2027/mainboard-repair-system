from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import jsonschema

from scripts.visual_qc.repair_case_contract import (
    FIXED_FALSE_BOUNDARIES,
    REPAIR_CASE_SCHEMA_V1,
    REPAIR_CASE_SCHEMA_V2,
    REPAIR_CASE_SCHEMA_V3,
    REPAIR_CASE_SCHEMA_VERSION,
    REPAIR_CASE_SCHEMA_VERSIONS,
    derive_completeness,
    validate_repair_case_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT
    / "knowledge-base"
    / "visual-qc-repair-case-source-v1-schema.json"
)
V2_SCHEMA_PATH = (
    ROOT
    / "knowledge-base"
    / "visual-qc-repair-case-source-v2-schema.json"
)
V3_SCHEMA_PATH = (
    ROOT
    / "knowledge-base"
    / "visual-qc-repair-case-source-v3-schema.json"
)
CATALOG_MODELS = ["KM4", "KM4 Pro"]


def package_link():
    return {
        "package_id": "pkg-before",
        "source_package_manifest_sha256": "a" * 64,
        "capture_stage": "before_repair",
        "role": "before_repair",
        "entry_ids": ["session-main_page_1"],
    }


def unknown_outcome():
    return {
        "status": "unknown",
        "description": None,
        "verification_description": None,
        "evidence_refs": [],
    }


def supporting_evidence():
    digest = "c" * 64
    return {
        "evidence_id": "case-note",
        "original_filename": "case-note.txt",
        "object_path": f"objects/case-evidence/{digest[:2]}/{digest}.txt",
        "mime_type": "text/plain",
        "byte_size": 12,
        "sha256": digest,
        "description": "Same-revision case note.",
    }


def heic_supporting_evidence():
    digest = "d" * 64
    return {
        "evidence_id": "repair-photo",
        "original_filename": "repair.heic",
        "object_path": f"objects/case-evidence/{digest[:2]}/{digest}.heic",
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


def canonical_payload():
    return {
        "schema_version": REPAIR_CASE_SCHEMA_VERSION,
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
        "outcome": unknown_outcome(),
        "corrections": [],
        "completeness": "photos_only",
        "boundaries": copy.deepcopy(FIXED_FALSE_BOUNDARIES),
    }


def identity_evidence_reference():
    return {
        "kind": "package_entry",
        "package_id": "pkg-before",
        "entry_id": "session-main_page_1",
    }


def device_identity(status="exact_catalog_match"):
    if status == "exact_catalog_match":
        return {
            "reported_models": ["KM4"],
            "catalog_models": list(CATALOG_MODELS),
            "mapping_status": status,
            "resolved_models": ["KM4"],
            "resolution_note": None,
            "evidence_refs": [],
        }
    identity = {
        "reported_models": ["TECNO/KM4"],
        "catalog_models": list(CATALOG_MODELS),
        "mapping_status": status,
        "resolved_models": [],
        "resolution_note": None,
        "evidence_refs": [identity_evidence_reference()],
    }
    if status == "confirmed_alias":
        identity["resolved_models"] = ["KM4"]
        identity["resolution_note"] = "The source record confirms the alias."
    return identity


def canonical_v2_payload(status="exact_catalog_match"):
    payload = canonical_payload()
    payload["schema_version"] = REPAIR_CASE_SCHEMA_V2
    del payload["device_models"]
    payload["device_identity"] = device_identity(status)
    payload["boundaries"]["model_identity_resolved"] = status in {
        "exact_catalog_match",
        "confirmed_alias",
    }
    return payload


def canonical_v3_supporting_only_payload():
    payload = canonical_v2_payload("unresolved_alias")
    payload["schema_version"] = REPAIR_CASE_SCHEMA_V3
    payload["evidence_mode"] = "supporting_only"
    payload["package_links"] = []
    payload["supporting_evidence"] = [heic_supporting_evidence()]
    payload["supporting_evidence_contexts"] = [repair_photo_context()]
    payload["device_identity"]["evidence_refs"] = [
        {
            "kind": "supporting_evidence",
            "evidence_id": "repair-photo",
        }
    ]
    return payload


def evidence_reference():
    return {
        "kind": "package_entry",
        "package_id": "pkg-before",
        "entry_id": "session-main_page_1",
    }


def symptom():
    return {
        "symptom_id": "symptom-1",
        "text": "Phone does not power on.",
        "source_wording": "No power",
        "fault_code": None,
        "evidence_refs": [evidence_reference()],
    }


def finding(status="documented", finding_id="finding-1"):
    return {
        "finding_id": finding_id,
        "claim_status": status,
        "description": "The repair record identifies the PMU area.",
        "defect_category": "power_management",
        "designator": "U2001",
        "side_id": "main_page_2",
        "region": {"x": 0.2, "y": 0.3, "width": 0.1, "height": 0.2},
        "evidence_refs": [evidence_reference()],
    }


def action():
    return {
        "action_id": "action-1",
        "description": "Replaced the documented PMU.",
        "action_category": "component_replacement",
        "target_designator": "U2001",
        "side_id": "main_page_2",
        "region": None,
        "evidence_refs": [evidence_reference()],
    }


class VisualQcRepairCaseContractTests(unittest.TestCase):
    def test_public_version_constants_preserve_v1_compatibility(self):
        self.assertEqual(
            REPAIR_CASE_SCHEMA_VERSION,
            "VISUAL-QC-REPAIR-CASE-SOURCE-V1",
        )
        self.assertEqual(REPAIR_CASE_SCHEMA_V1, REPAIR_CASE_SCHEMA_VERSION)
        self.assertEqual(
            REPAIR_CASE_SCHEMA_V2,
            "VISUAL-QC-REPAIR-CASE-SOURCE-V2",
        )
        self.assertEqual(
            REPAIR_CASE_SCHEMA_V3,
            "VISUAL-QC-REPAIR-CASE-SOURCE-V3",
        )
        self.assertEqual(
            REPAIR_CASE_SCHEMA_VERSIONS,
            {
                REPAIR_CASE_SCHEMA_V1,
                REPAIR_CASE_SCHEMA_V2,
                REPAIR_CASE_SCHEMA_V3,
            },
        )

    def test_canonical_photo_only_payload_matches_python_and_schema(self):
        payload = canonical_payload()

        validated = validate_repair_case_manifest(payload)

        self.assertEqual(validated, payload)
        self.assertIsNot(validated, payload)
        self.assertEqual(derive_completeness(payload), "photos_only")
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(payload)

    def test_canonical_v2_payload_matches_python_and_schema(self):
        payload = canonical_v2_payload()

        validated = validate_repair_case_manifest(
            payload,
            catalog_models=CATALOG_MODELS,
        )

        self.assertEqual(validated, payload)
        self.assertIsNot(validated, payload)
        self.assertIsNot(validated["device_identity"], payload["device_identity"])
        schema = json.loads(V2_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(payload)

    def test_canonical_v3_supporting_only_matches_python_and_schema(self):
        payload = canonical_v3_supporting_only_payload()

        validated = validate_repair_case_manifest(
            payload,
            catalog_models=CATALOG_MODELS,
        )

        self.assertEqual(validated, payload)
        self.assertIsNot(validated, payload)
        schema = json.loads(V3_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(payload)

    def test_v3_mode_cardinality_rules_match_python_and_schema(self):
        schema = json.loads(V3_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)

        invalid_payloads = []

        with_package = canonical_v3_supporting_only_payload()
        with_package["package_links"] = [package_link()]
        invalid_payloads.append((with_package, True))

        without_evidence = canonical_v3_supporting_only_payload()
        without_evidence["supporting_evidence"] = []
        invalid_payloads.append((without_evidence, True))

        without_context = canonical_v3_supporting_only_payload()
        without_context["supporting_evidence_contexts"] = []
        invalid_payloads.append((without_context, True))

        duplicate_context = canonical_v3_supporting_only_payload()
        duplicate_context["supporting_evidence_contexts"].append(
            repair_photo_context()
        )
        invalid_payloads.append((duplicate_context, True))

        for payload, schema_rejects in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=CATALOG_MODELS,
                    )
                if schema_rejects:
                    with self.assertRaises(jsonschema.ValidationError):
                        validator.validate(payload)

        package_linked = canonical_v2_payload("unresolved_alias")
        package_linked["schema_version"] = REPAIR_CASE_SCHEMA_V3
        package_linked["evidence_mode"] = "package_linked"
        package_linked["supporting_evidence_contexts"] = []
        self.assertEqual(
            validate_repair_case_manifest(
                package_linked,
                catalog_models=CATALOG_MODELS,
            ),
            package_linked,
        )
        validator.validate(package_linked)

    def test_v3_package_linked_rejects_empty_package_links(self):
        payload = canonical_v2_payload("unresolved_alias")
        payload["schema_version"] = REPAIR_CASE_SCHEMA_V3
        payload["evidence_mode"] = "package_linked"
        payload["package_links"] = []
        payload["supporting_evidence_contexts"] = []

        with self.assertRaisesRegex(ValueError, "package_links"):
            validate_repair_case_manifest(
                payload,
                catalog_models=CATALOG_MODELS,
            )

        schema = json.loads(V3_SCHEMA_PATH.read_text(encoding="utf-8"))
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(payload)

    def test_v3_rejects_malformed_evidence_mode_types(self):
        schema = json.loads(V3_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        for malformed in (None, False, 1, ["supporting_only"], {"mode": "x"}):
            payload = canonical_v3_supporting_only_payload()
            payload["evidence_mode"] = malformed
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(ValueError, "evidence_mode"):
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=CATALOG_MODELS,
                    )
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(payload)

    def test_v3_schema_rejects_mime_and_object_path_extension_mismatches(self):
        schema = json.loads(V3_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        mismatches = []

        heic_with_jpg_path = canonical_v3_supporting_only_payload()
        heic_with_jpg_path["supporting_evidence"][0][
            "object_path"
        ] = heic_with_jpg_path["supporting_evidence"][0][
            "object_path"
        ].removesuffix(".heic") + ".jpg"
        mismatches.append(heic_with_jpg_path)

        jpeg_with_heic_path = canonical_v3_supporting_only_payload()
        evidence = jpeg_with_heic_path["supporting_evidence"][0]
        evidence["original_filename"] = "repair.jpg"
        evidence["mime_type"] = "image/jpeg"
        mismatches.append(jpeg_with_heic_path)

        for payload in mismatches:
            evidence = payload["supporting_evidence"][0]
            with self.subTest(
                mime_type=evidence["mime_type"],
                object_path=evidence["object_path"],
            ):
                with self.assertRaisesRegex(ValueError, "object_path"):
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=CATALOG_MODELS,
                    )
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(payload)

    def test_v3_rejects_context_and_mode_mutation_matrix(self):
        schema = json.loads(V3_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        mutations = []

        unknown_mode = canonical_v3_supporting_only_payload()
        unknown_mode["evidence_mode"] = "unknown"
        mutations.append((unknown_mode, True))

        unknown_context_field = canonical_v3_supporting_only_payload()
        unknown_context_field["supporting_evidence_contexts"][0][
            "unexpected"
        ] = True
        mutations.append((unknown_context_field, True))

        dangling_context = canonical_v3_supporting_only_payload()
        dangling_context["supporting_evidence_contexts"][0][
            "evidence_id"
        ] = "missing-photo"
        mutations.append((dangling_context, False))

        duplicate_context = canonical_v3_supporting_only_payload()
        second_context = repair_photo_context()
        second_context["source_capture_stage"] = "维修后复核"
        duplicate_context["supporting_evidence_contexts"].append(second_context)
        mutations.append((duplicate_context, False))

        whitespace_stage = canonical_v3_supporting_only_payload()
        whitespace_stage["supporting_evidence_contexts"][0][
            "source_capture_stage"
        ] = "   "
        mutations.append((whitespace_stage, True))

        non_image_role = canonical_v3_supporting_only_payload()
        non_image_role["supporting_evidence"] = [supporting_evidence()]
        non_image_role["supporting_evidence"][0]["evidence_id"] = "repair-photo"
        non_image_role["device_identity"]["evidence_refs"][0][
            "evidence_id"
        ] = "repair-photo"
        mutations.append((non_image_role, False))

        for payload, schema_rejects in mutations:
            with self.subTest(
                mode=payload["evidence_mode"],
                context=payload["supporting_evidence_contexts"],
            ):
                with self.assertRaises(ValueError):
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=CATALOG_MODELS,
                    )
                if schema_rejects:
                    with self.assertRaises(jsonschema.ValidationError):
                        validator.validate(payload)

    def test_v3_schema_rejects_path_style_original_filenames(self):
        schema = json.loads(V3_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)

        for filename in ("folder/repair.heic", r"folder\repair.heic"):
            payload = canonical_v3_supporting_only_payload()
            payload["supporting_evidence"][0]["original_filename"] = filename
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(ValueError, "original_filename"):
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=CATALOG_MODELS,
                    )
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(payload)

    def test_heic_supporting_evidence_remains_v3_only(self):
        for version, schema_path in (
            (REPAIR_CASE_SCHEMA_V1, SCHEMA_PATH),
            (REPAIR_CASE_SCHEMA_V2, V2_SCHEMA_PATH),
        ):
            payload = (
                canonical_payload()
                if version == REPAIR_CASE_SCHEMA_V1
                else canonical_v2_payload()
            )
            payload["supporting_evidence"] = [heic_supporting_evidence()]
            with self.subTest(version=version):
                with self.assertRaisesRegex(ValueError, "MIME type"):
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=(
                            None
                            if version == REPAIR_CASE_SCHEMA_V1
                            else CATALOG_MODELS
                        ),
                    )
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.Draft202012Validator(schema).validate(payload)

    def test_supporting_evidence_rejects_whitespace_only_original_filename(self):
        payload = canonical_v2_payload()
        payload["supporting_evidence"] = [supporting_evidence()]
        payload["supporting_evidence"][0]["original_filename"] = "   "

        with self.assertRaisesRegex(ValueError, "original_filename"):
            validate_repair_case_manifest(
                payload,
                catalog_models=CATALOG_MODELS,
            )

        schema = json.loads(V2_SCHEMA_PATH.read_text(encoding="utf-8"))
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(payload)

    def test_v2_accepts_all_four_identity_states_through_full_manifest(self):
        schema = json.loads(V2_SCHEMA_PATH.read_text(encoding="utf-8"))
        for status in (
            "exact_catalog_match",
            "confirmed_alias",
            "unresolved_alias",
            "conflict",
        ):
            payload = canonical_v2_payload(status)
            with self.subTest(status=status):
                self.assertEqual(
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=CATALOG_MODELS,
                    ),
                    payload,
                )
                jsonschema.Draft202012Validator(schema).validate(payload)

    def test_version_dispatch_rejects_unknown_and_identity_shape_conflicts(self):
        unknown = canonical_payload()
        unknown["schema_version"] = "VISUAL-QC-REPAIR-CASE-SOURCE-V99"
        with self.assertRaisesRegex(ValueError, "schema_version"):
            validate_repair_case_manifest(unknown)

        both = canonical_v2_payload()
        both["device_models"] = ["KM4"]
        with self.assertRaisesRegex(ValueError, "fields"):
            validate_repair_case_manifest(
                both,
                catalog_models=CATALOG_MODELS,
            )

        neither = canonical_v2_payload()
        del neither["device_identity"]
        with self.assertRaisesRegex(ValueError, "fields"):
            validate_repair_case_manifest(
                neither,
                catalog_models=CATALOG_MODELS,
            )

        extra = canonical_v2_payload()
        extra["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "fields"):
            validate_repair_case_manifest(
                extra,
                catalog_models=CATALOG_MODELS,
            )

    def test_v1_rejects_v2_identity_and_derived_boundary_fields(self):
        with_identity = canonical_payload()
        with_identity["device_identity"] = device_identity()
        with self.assertRaisesRegex(ValueError, "fields"):
            validate_repair_case_manifest(with_identity)

        with_boundary = canonical_payload()
        with_boundary["boundaries"]["model_identity_resolved"] = True
        with self.assertRaisesRegex(ValueError, "boundaries"):
            validate_repair_case_manifest(with_boundary)

    def test_v2_requires_canonical_catalog_in_exact_order(self):
        payload = canonical_v2_payload()
        with self.assertRaisesRegex(ValueError, "catalog_models"):
            validate_repair_case_manifest(payload)

        for catalog in (["KM4 Pro", "KM4"], ["KM4"]):
            with self.subTest(catalog=catalog):
                with self.assertRaisesRegex(ValueError, "catalog_models"):
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=catalog,
                    )

    def test_v2_identity_evidence_resolves_against_same_revision_targets(self):
        payload = canonical_v2_payload("unresolved_alias")
        validated = validate_repair_case_manifest(
            payload,
            catalog_models=CATALOG_MODELS,
        )
        self.assertEqual(
            validated["device_identity"]["evidence_refs"],
            [identity_evidence_reference()],
        )

        payload["device_identity"]["evidence_refs"][0]["entry_id"] = "missing"
        with self.assertRaisesRegex(ValueError, "evidence reference"):
            validate_repair_case_manifest(
                payload,
                catalog_models=CATALOG_MODELS,
            )

    def test_v2_rejects_invalid_state_dependent_identity_shapes(self):
        cases = []

        unresolved = canonical_v2_payload("unresolved_alias")
        unresolved["device_identity"]["evidence_refs"] = []
        cases.append((unresolved, "evidence"))

        for field, value, message in (
            ("resolved_models", [], "resolved_models"),
            ("resolution_note", None, "resolution note"),
            ("evidence_refs", [], "evidence"),
        ):
            confirmed = canonical_v2_payload("confirmed_alias")
            confirmed["device_identity"][field] = value
            cases.append((confirmed, message))

        exact = canonical_v2_payload()
        exact["device_identity"]["resolved_models"] = ["KM4 Pro"]
        cases.append((exact, "identical"))

        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=CATALOG_MODELS,
                    )

    def test_v2_rejects_caller_supplied_derived_boundary_mismatch(self):
        for status in (
            "exact_catalog_match",
            "confirmed_alias",
            "unresolved_alias",
            "conflict",
        ):
            payload = canonical_v2_payload(status)
            payload["boundaries"]["model_identity_resolved"] = not payload[
                "boundaries"
            ]["model_identity_resolved"]
            with self.subTest(status=status):
                with self.assertRaisesRegex(
                    ValueError,
                    "model_identity_resolved",
                ):
                    validate_repair_case_manifest(
                        payload,
                        catalog_models=CATALOG_MODELS,
                    )

    def test_malformed_enum_like_json_values_raise_value_error(self):
        for version in (REPAIR_CASE_SCHEMA_V1, REPAIR_CASE_SCHEMA_V2):
            for malformed in ([version], {"version": version}):
                payload = (
                    canonical_payload()
                    if version == REPAIR_CASE_SCHEMA_V1
                    else canonical_v2_payload()
                )
                payload["schema_version"] = malformed
                with self.subTest(field="schema_version", malformed=malformed):
                    with self.assertRaisesRegex(ValueError, "schema_version"):
                        validate_repair_case_manifest(
                            payload,
                            catalog_models=(
                                None
                                if version == REPAIR_CASE_SCHEMA_V1
                                else CATALOG_MODELS
                            ),
                        )

        for field, message in (
            ("capture_stage", "capture_stage"),
            ("role", "package role"),
            ("mime_type", "MIME type"),
            ("claim_status", "claim_status"),
            ("outcome_status", "outcome status"),
            ("completeness", "completeness"),
        ):
            for malformed in ([field], {"value": field}):
                payload = canonical_payload()
                if field in {"capture_stage", "role"}:
                    payload["package_links"][0][field] = malformed
                elif field == "mime_type":
                    payload["supporting_evidence"] = [supporting_evidence()]
                    payload["supporting_evidence"][0]["mime_type"] = malformed
                elif field == "claim_status":
                    payload["findings"] = [finding()]
                    payload["findings"][0]["claim_status"] = malformed
                elif field == "outcome_status":
                    payload["outcome"]["status"] = malformed
                else:
                    payload["completeness"] = malformed
                with self.subTest(field=field, malformed=malformed):
                    with self.assertRaisesRegex(ValueError, message):
                        validate_repair_case_manifest(payload)

    def test_boundary_values_require_actual_booleans_not_zero_or_one(self):
        for field in FIXED_FALSE_BOUNDARIES:
            for integer in (0, 1):
                payload = canonical_payload()
                payload["boundaries"][field] = integer
                with self.subTest(version="V1", field=field, value=integer):
                    with self.assertRaisesRegex(ValueError, "boundaries"):
                        validate_repair_case_manifest(payload)

        for status in ("exact_catalog_match", "unresolved_alias"):
            for field in (*FIXED_FALSE_BOUNDARIES, "model_identity_resolved"):
                for integer in (0, 1):
                    payload = canonical_v2_payload(status)
                    payload["boundaries"][field] = integer
                    with self.subTest(
                        version="V2",
                        status=status,
                        field=field,
                        value=integer,
                    ):
                        with self.assertRaisesRegex(ValueError, "boundar"):
                            validate_repair_case_manifest(
                                payload,
                                catalog_models=CATALOG_MODELS,
                            )

    def test_python_enforces_identity_semantics_beyond_raw_json_schema(self):
        exact_mismatch = canonical_v2_payload()
        exact_mismatch["device_identity"]["resolved_models"] = ["KM4 Pro"]
        with self.assertRaisesRegex(ValueError, "identical"):
            validate_repair_case_manifest(
                exact_mismatch,
                catalog_models=CATALOG_MODELS,
            )

        alias_outside_catalog = canonical_v2_payload("confirmed_alias")
        alias_outside_catalog["device_identity"]["resolved_models"] = [
            "UNKNOWN"
        ]
        with self.assertRaisesRegex(ValueError, "catalog"):
            validate_repair_case_manifest(
                alias_outside_catalog,
                catalog_models=CATALOG_MODELS,
            )

    def test_python_enforces_region_sums_beyond_raw_json_schema(self):
        for axis, start_field, size_field in (
            ("x", "x", "width"),
            ("y", "y", "height"),
        ):
            payload = canonical_payload()
            payload["reported_symptoms"] = [symptom()]
            invalid_finding = finding()
            invalid_finding["region"][start_field] = 0.95
            invalid_finding["region"][size_field] = 0.1
            payload["findings"] = [invalid_finding]
            payload["completeness"] = "diagnosis_linked"
            with self.subTest(axis=axis):
                with self.assertRaisesRegex(ValueError, "normalized region"):
                    validate_repair_case_manifest(payload)

    def test_normalized_regions_reject_nonfinite_and_oversized_numbers(self):
        invalid_numbers = (
            ("nan", float("nan")),
            ("positive_infinity", float("inf")),
            ("negative_infinity", float("-inf")),
            ("oversized_integer", 10**400),
        )
        for number_name, invalid_number in invalid_numbers:
            for field in ("x", "y", "width", "height"):
                payload = canonical_payload()
                payload["reported_symptoms"] = [symptom()]
                invalid_finding = finding()
                invalid_finding["region"][field] = invalid_number
                payload["findings"] = [invalid_finding]
                payload["completeness"] = "diagnosis_linked"
                with self.subTest(number=number_name, field=field):
                    with self.assertRaisesRegex(
                        ValueError,
                        "normalized region",
                    ):
                        validate_repair_case_manifest(payload)

    def test_completeness_is_derived_from_available_case_context(self):
        payload = canonical_payload()
        payload["reported_symptoms"] = [symptom()]
        payload["completeness"] = "symptom_linked"
        self.assertEqual(
            validate_repair_case_manifest(payload)["completeness"],
            "symptom_linked",
        )

        payload["findings"] = [finding("suspected")]
        with self.assertRaisesRegex(ValueError, "completeness"):
            payload["completeness"] = "diagnosis_linked"
            validate_repair_case_manifest(payload)

        payload["findings"] = [finding()]
        self.assertEqual(derive_completeness(payload), "diagnosis_linked")
        payload["completeness"] = "diagnosis_linked"
        validate_repair_case_manifest(payload)

        payload["repair_actions"] = [action()]
        payload["outcome"] = {
            "status": "repair_completed",
            "description": "The phone powered on after repair.",
            "verification_description": "Power-on test passed.",
            "evidence_refs": [evidence_reference()],
        }
        payload["completeness"] = "repair_outcome_linked"
        validate_repair_case_manifest(payload)

    def test_contract_rejects_extra_fields_false_boundary_and_dangling_reference(self):
        invalid = canonical_payload()
        invalid["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "fields"):
            validate_repair_case_manifest(invalid)

        invalid = canonical_payload()
        invalid["boundaries"]["training_label_allowed"] = True
        with self.assertRaisesRegex(ValueError, "boundaries"):
            validate_repair_case_manifest(invalid)

        invalid = canonical_payload()
        dangling = symptom()
        dangling["evidence_refs"][0]["entry_id"] = "missing-entry"
        invalid["reported_symptoms"] = [dangling]
        invalid["completeness"] = "symptom_linked"
        with self.assertRaisesRegex(ValueError, "evidence reference"):
            validate_repair_case_manifest(invalid)

    def test_contract_rejects_duplicate_ids_and_invalid_normalized_region(self):
        invalid = canonical_payload()
        invalid["findings"] = [finding(), finding(finding_id="finding-1")]
        with self.assertRaisesRegex(ValueError, "duplicate finding_id"):
            validate_repair_case_manifest(invalid)

        invalid = canonical_payload()
        bad_finding = finding()
        bad_finding["region"]["width"] = 0.9
        invalid["findings"] = [bad_finding]
        with self.assertRaisesRegex(ValueError, "normalized region"):
            validate_repair_case_manifest(invalid)

        invalid = canonical_payload()
        invalid["revision"] = True
        with self.assertRaisesRegex(ValueError, "revision"):
            validate_repair_case_manifest(invalid)

    def test_correction_resolves_historical_fact_and_current_replacement(self):
        payload = canonical_payload()
        payload["revision"] = 2
        payload["previous_manifest_sha256"] = "b" * 64
        payload["reported_symptoms"] = [symptom()]
        payload["findings"] = [finding(finding_id="finding-2")]
        payload["corrections"] = [
            {
                "correction_id": "correction-1",
                "corrects_fact_id": "finding-1",
                "description": "Later record identifies U2001 instead.",
                "replacement_fact_id": "finding-2",
                "evidence_refs": [evidence_reference()],
            }
        ]
        payload["completeness"] = "diagnosis_linked"

        validate_repair_case_manifest(
            payload,
            historical_fact_ids={"finding-1"},
        )

        with self.assertRaisesRegex(ValueError, "correction target"):
            validate_repair_case_manifest(payload, historical_fact_ids=set())

    def test_correction_id_cannot_collide_with_a_fact_id(self):
        payload = canonical_payload()
        payload["revision"] = 2
        payload["previous_manifest_sha256"] = "b" * 64
        payload["reported_symptoms"] = [symptom()]
        payload["findings"] = [finding(finding_id="finding-2")]
        payload["corrections"] = [
            {
                "correction_id": "finding-2",
                "corrects_fact_id": "finding-1",
                "description": "Later record supersedes the initial finding.",
                "replacement_fact_id": "finding-2",
                "evidence_refs": [evidence_reference()],
            }
        ]
        payload["completeness"] = "diagnosis_linked"

        with self.assertRaisesRegex(ValueError, "duplicate correction_id"):
            validate_repair_case_manifest(
                payload,
                historical_fact_ids={"finding-1"},
            )

    def test_schema_enforces_revision_chain_and_derived_completeness(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        revision_one_with_parent = canonical_payload()
        revision_one_with_parent["previous_manifest_sha256"] = "b" * 64
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(revision_one_with_parent, schema)

        later_without_parent = canonical_payload()
        later_without_parent["revision"] = 2
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(later_without_parent, schema)

        false_completeness = canonical_payload()
        false_completeness["completeness"] = "symptom_linked"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(false_completeness, schema)

    def test_v2_schema_rejects_revision_completeness_and_state_shapes(self):
        schema = json.loads(V2_SCHEMA_PATH.read_text(encoding="utf-8"))
        invalid_payloads = []

        revision_one_with_parent = canonical_v2_payload()
        revision_one_with_parent["previous_manifest_sha256"] = "b" * 64
        invalid_payloads.append(revision_one_with_parent)

        later_without_parent = canonical_v2_payload()
        later_without_parent["revision"] = 2
        invalid_payloads.append(later_without_parent)

        false_completeness = canonical_v2_payload()
        false_completeness["completeness"] = "symptom_linked"
        invalid_payloads.append(false_completeness)

        both_identity_fields = canonical_v2_payload()
        both_identity_fields["device_models"] = ["KM4"]
        invalid_payloads.append(both_identity_fields)

        neither_identity_field = canonical_v2_payload()
        del neither_identity_field["device_identity"]
        invalid_payloads.append(neither_identity_field)

        false_identity_boundary = canonical_v2_payload()
        false_identity_boundary["boundaries"]["model_identity_resolved"] = False
        invalid_payloads.append(false_identity_boundary)

        for status, field, value in (
            ("exact_catalog_match", "resolution_note", "Not allowed."),
            ("confirmed_alias", "resolution_note", None),
            ("confirmed_alias", "evidence_refs", []),
            ("unresolved_alias", "evidence_refs", []),
            ("unresolved_alias", "resolved_models", ["KM4"]),
            ("conflict", "resolution_note", "Tentative."),
        ):
            invalid = canonical_v2_payload(status)
            invalid["device_identity"][field] = value
            invalid_payloads.append(invalid)

        for payload in invalid_payloads:
            with self.subTest(
                revision=payload["revision"],
                status=payload.get("device_identity", {}).get(
                    "mapping_status",
                    "missing",
                ),
            ):
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.Draft202012Validator(schema).validate(payload)


if __name__ == "__main__":
    unittest.main()
