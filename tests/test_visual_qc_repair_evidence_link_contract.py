from __future__ import annotations

import copy
import hashlib
import importlib
import json
import math
from pathlib import Path
import tempfile
import unittest

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
PHYSICAL_SCHEMA_PATH = (
    ROOT
    / "knowledge-base"
    / "visual-qc-linkable-physical-evidence-v1-schema.json"
)
LINK_SCHEMA_PATH = (
    ROOT
    / "knowledge-base"
    / "visual-qc-repair-evidence-link-v1-schema.json"
)

try:
    contract = importlib.import_module(
        "scripts.visual_qc.repair_evidence_link_contract"
    )
except ModuleNotFoundError:
    contract = None


FIXED_FALSE_BOUNDARIES = {
    "visual_defect_confirmed": False,
    "qc_annotation_created": False,
    "golden_approved": False,
    "training_label_allowed": False,
    "repair_causality_confirmed": False,
    "repair_instruction_allowed": False,
    "field_accuracy_claim_allowed": False,
}
EXPECTED_MAX_POLYGON_POINTS = 256
EXPECTED_MAX_REPAIR_CASE_REFERENCES = 100
EXPECTED_MAX_PHYSICAL_EVIDENCE = 500
EXPECTED_MAX_BINDINGS = 5000
EXPECTED_MAX_COMPILED_SOURCES = 100
EXPECTED_MAX_EVIDENCE_DESCRIPTORS = 100
EXPECTED_MAX_EVIDENCE_BASES = 3
EXPECTED_MAX_CHECK_POINTS = 1000


def fixture_canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def fixture_sha256(value: object) -> str:
    return hashlib.sha256(fixture_canonical_bytes(value)).hexdigest()


def closed_hash(value: dict, field: str) -> dict:
    result = copy.deepcopy(value)
    result[field] = fixture_sha256(
        {key: item for key, item in result.items() if key != field}
    )
    return result


def normalized_point(x=0.2, y=0.3):
    return {"x": x, "y": y}


def registration_point(board_x, board_y, image_x, image_y):
    return {
        "board": normalized_point(board_x, board_y),
        "image": normalized_point(image_x, image_y),
    }


def projected_point(matrix, x, y):
    denominator = matrix[6] * x + matrix[7] * y + matrix[8]
    return (
        (matrix[0] * x + matrix[1] * y + matrix[2]) / denominator,
        (matrix[3] * x + matrix[4] * y + matrix[5]) / denominator,
    )


def registration_point_from_matrix(matrix, board_x, board_y):
    image_x, image_y = projected_point(matrix, board_x, board_y)
    return registration_point(
        board_x, board_y, image_x, image_y
    )


def qualified_handoff():
    return {
        "schema_version": "VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1",
        "handoff_schema_version": "VISUAL-QC-PHYSICAL-HANDOFF-V1",
        "source_package_manifest_sha256": "a" * 64,
        "archived_intake_manifest_sha256": "b" * 64,
        "acceptance_report_sha256": "c" * 64,
        "acceptance_action": "manual_registration_required",
        "registration_review_required": True,
        "field_accuracy_claim_allowed": False,
    }


def physical_snapshot(
    evidence_id="physical-page-2",
    *,
    side_id="main_page_2",
    board_key="reviewed-board-a",
    board_id="BOARD-REVIEWED-A-V1",
):
    handoff = qualified_handoff()
    snapshot = {
        "schema_version": "VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1",
        "physical_evidence_id": evidence_id,
        "server_case_id": "vqc-generic-reviewed-page-2",
        "intake": {
            "batch_id": "generic-reviewed-batch",
            "entry_id": "generic-reviewed-page-2",
        },
        "board_key": board_key,
        "board_id": board_id,
        "side_id": side_id,
        "capture_stage": "after_repair",
        "evidence_role": "physical_capture",
        "qualified_handoff": handoff,
        "qualified_handoff_sha256": fixture_sha256(handoff),
        "image_id": "image-generic-page-2",
        "image_sha256": "d" * 64,
        "job_id": "job-generic-page-2",
        "registration_review_id": "review-generic-page-2",
        "registration": {
            "method": "reviewed_manual_four_point",
            "board_to_image_matrix": [
                1.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                1.0,
            ],
            "solve_anchors": [
                registration_point(0.1, 0.1, 0.1, 0.1),
                registration_point(0.9, 0.1, 0.9, 0.1),
                registration_point(0.9, 0.9, 0.9, 0.9),
                registration_point(0.1, 0.9, 0.1, 0.9),
            ],
            "independent_check_points": [
                registration_point(0.25, 0.25, 0.250003, 0.250004),
                registration_point(0.75, 0.6, 0.750006, 0.600008),
            ],
            "error": {
                "count": 2,
                "rms": 7.90569415042095e-06,
                "maximum": 1e-05,
            },
        },
        "physical_evidence_snapshot_sha256": "",
    }
    return closed_hash(snapshot, "physical_evidence_snapshot_sha256")


def repair_case_reference(reference_id="generic-v2-r1"):
    return {
        "repair_case_reference_id": reference_id,
        "repair_case_id": "repair-case-generic",
        "revision": 1,
        "schema_version": "VISUAL-QC-REPAIR-CASE-SOURCE-V2",
        "manifest_sha256": "e" * 64,
        "board_key": "reviewed-board-a",
        "board_id": "BOARD-REVIEWED-A-V1",
    }


def board_snapshot():
    board = {
        "board_key": "reviewed-board-a",
        "board_id": "BOARD-REVIEWED-A-V1",
        "catalog_asset": {
            "path": "knowledge-base/model-board-assets.json",
            "sha256": "f" * 64,
            "entry_sha256": "1" * 64,
        },
        "compiled_sources": [
            {
                "kind": "compiled_board",
                "path": "knowledge-base/reviewed-board-a-compiled.json",
                "sha256": "2" * 64,
            }
        ],
        "board_snapshot_sha256": "",
    }
    return closed_hash(board, "board_snapshot_sha256")


def source_fact(kind="finding", fact_id="finding-emmc"):
    claim_status = "documented" if kind == "finding" else None
    if kind == "outcome":
        fact_id = "outcome"
    fact = {
        "kind": kind,
        "fact_id": fact_id,
        "display": {
            "text": "Generic reviewed source fact / 已审核来源事实",
            "claim_status": claim_status,
        },
        "fact_sha256": "",
    }
    return closed_hash(fact, "fact_sha256")


def engineering_snapshot(*, geometry_source_status="low"):
    location = {
        "kind": "normalized_point",
        "point": normalized_point(0.45, 0.55),
    }
    engineering = {
        "component_id": "BOARD-A-P2-R100",
        "designator": "R100",
        "technician_category": "resistor",
        "location": location,
        "evidence_descriptors": [
            "reviewed point-map designator R100",
            "reviewed compiled entity BOARD-A-P2-R100",
        ],
        "geometry_source_status": geometry_source_status,
        "semantic_identity_proven": True,
        "engineering_snapshot_sha256": "",
    }
    return closed_hash(engineering, "engineering_snapshot_sha256")


def target(kind="designator"):
    if kind == "whole_board":
        return {"kind": kind, "side_id": "main_page_2"}
    if kind == "board_region":
        return {
            "kind": kind,
            "side_id": "main_page_2",
            "region": {
                "kind": "normalized_rectangle",
                "x": 0.2,
                "y": 0.3,
                "width": 0.2,
                "height": 0.1,
            },
        }
    return {
        "kind": "designator",
        "side_id": "main_page_2",
        "engineering": engineering_snapshot(),
    }


def evidence_bases(*kinds):
    records = []
    for kind in kinds:
        record = {"kind": kind}
        if kind == "human_observation":
            record["observation_code"] = "target_visible"
        records.append(record)
    return records


def binding(
    binding_id="binding-finding-u4000",
    *,
    source_kind="finding",
    target_kind="designator",
    association_status="related",
    visibility_status="visible",
    supersedes_binding_id=None,
):
    bases = ["repair_case_fact"]
    if target_kind == "designator":
        bases.append("engineering_identity")
    if visibility_status != "not_assessed":
        bases.append("human_observation")
    result = {
        "binding_id": binding_id,
        "repair_case_reference_id": "generic-v2-r1",
        "source_fact": source_fact(source_kind),
        "target": target(target_kind),
        "physical_evidence_id": "physical-page-2",
        "association_status": association_status,
        "visibility_status": visibility_status,
        "evidence_bases": evidence_bases(*bases),
        "supersedes_binding_id": supersedes_binding_id,
        "boundaries": {
            **copy.deepcopy(FIXED_FALSE_BOUNDARIES),
            "model_identity_resolved": False,
        },
    }
    if visibility_status != "visible":
        for basis in result["evidence_bases"]:
            if basis["kind"] == "human_observation":
                basis["observation_code"] = {
                    "not_visible": "target_not_visible",
                    "occluded": "target_occluded",
                }[visibility_status]
    return result


def link_manifest(*, bindings=None, revision=1):
    return {
        "schema_version": "VISUAL-QC-REPAIR-EVIDENCE-LINK-V1",
        "link_set_id": "link-generic-reviewed-after",
        "revision": revision,
        "previous_manifest_sha256": None if revision == 1 else "3" * 64,
        "source_origin": "codex_operator",
        "repair_case_references": [repair_case_reference()],
        "board": board_snapshot(),
        "physical_evidence": [physical_snapshot()],
        "bindings": bindings if bindings is not None else [binding()],
        "boundaries": copy.deepcopy(FIXED_FALSE_BOUNDARIES),
    }


@unittest.skipIf(contract is None, "contract module has not been implemented")
class VisualQcRepairEvidenceLinkContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.physical_schema = json.loads(
            PHYSICAL_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        cls.link_schema = json.loads(
            LINK_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator.check_schema(cls.physical_schema)
        jsonschema.Draft202012Validator.check_schema(cls.link_schema)

    def assertContractError(self, code, callback):
        try:
            callback()
        except contract.RepairEvidenceLinkContractError as caught:
            self.assertEqual(caught.code, code)
            self.assertNotIn("\\", str(caught))
            return caught
        except Exception as caught:
            self.fail(
                "expected RepairEvidenceLinkContractError, got "
                f"{type(caught).__name__}"
            )
        self.fail("RepairEvidenceLinkContractError not raised")

    def assertBothReject(self, payload, validator, schema, code):
        self.assertContractError(code, lambda: validator(payload))
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(payload)

    def test_public_api_and_canonical_json_are_deterministic_utf8(self):
        self.assertTrue(
            issubclass(contract.RepairEvidenceLinkContractError, ValueError)
        )
        left = {"z": 1, "text": "主板", "nested": {"b": 2, "a": 1}}
        right = {"nested": {"a": 1, "b": 2}, "text": "主板", "z": 1}
        expected = (
            '{"nested":{"a":1,"b":2},"text":"主板","z":1}'.encode("utf-8")
        )
        self.assertEqual(contract.canonical_json_bytes(left), expected)
        self.assertEqual(contract.canonical_json_bytes(right), expected)
        self.assertEqual(
            contract.canonical_sha256(left),
            hashlib.sha256(expected).hexdigest(),
        )
        with self.assertRaises(ValueError):
            contract.canonical_json_bytes({"bad": math.nan})

    def test_canonical_json_rejects_lone_unicode_surrogates_with_typed_error(self):
        for value in (
            {"text": "\ud800"},
            {"text": "\udfff"},
            {"\ud800": "value"},
        ):
            with self.subTest(value=value):
                self.assertContractError(
                    "invalid_unicode_scalar",
                    lambda value=value: contract.canonical_json_bytes(value),
                )

    def test_strict_loader_rejects_duplicates_non_objects_and_bad_utf8(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "valid.json"
            valid.write_bytes(b'{"a":1,"nested":{"b":2}}')
            self.assertEqual(
                contract.load_json_object_strict(valid),
                {"a": 1, "nested": {"b": 2}},
            )

            duplicate = root / "duplicate.json"
            duplicate.write_bytes(b'{"a":1,"a":2}')
            error = self.assertContractError(
                "duplicate_json_key",
                lambda: contract.load_json_object_strict(duplicate),
            )
            self.assertIn("duplicate.json", str(error))
            self.assertNotIn(str(root), str(error))

            non_object = root / "array.json"
            non_object.write_bytes(b"[]")
            self.assertContractError(
                "json_root_not_object",
                lambda: contract.load_json_object_strict(non_object),
            )

            malformed = root / "bad.json"
            malformed.write_bytes(b'{"text":"\xff"}')
            self.assertContractError(
                "invalid_utf8_json",
                lambda: contract.load_json_object_strict(malformed),
            )

    def test_strict_loader_rejects_nonfinite_json_constants(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, constant in enumerate(("NaN", "Infinity", "-Infinity")):
                path = root / f"constant-{index}.json"
                path.write_bytes(f'{{"value":{constant}}}'.encode("ascii"))
                with self.subTest(constant=constant):
                    self.assertContractError(
                        "invalid_json_constant",
                        lambda path=path: contract.load_json_object_strict(path),
                    )

    def test_strict_loader_rejects_escaped_lone_unicode_surrogates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payloads = (
                b'{"value":"\\ud800"}',
                b'{"value":"\\udfff"}',
                b'{"\\ud800":"value"}',
            )
            for index, content in enumerate(payloads):
                path = root / f"surrogate-{index}.json"
                path.write_bytes(content)
                with self.subTest(content=content):
                    self.assertContractError(
                        "invalid_unicode_scalar",
                        lambda path=path: contract.load_json_object_strict(path),
                    )

    def test_valid_physical_snapshot_is_deep_copied_and_schema_valid(self):
        payload = physical_snapshot()
        validated = contract.validate_physical_evidence_snapshot(payload)
        self.assertEqual(validated, payload)
        self.assertIsNot(validated, payload)
        self.assertIsNot(validated["registration"], payload["registration"])
        jsonschema.Draft202012Validator(self.physical_schema).validate(payload)

        payload["registration"]["method"] = "changed"
        self.assertEqual(
            validated["registration"]["method"],
            "reviewed_manual_four_point",
        )

    def test_physical_snapshot_requires_exact_fields_and_canonical_hashes(self):
        extra = physical_snapshot()
        extra["absolute_path"] = "D:/private/image.jpg"
        self.assertBothReject(
            extra,
            contract.validate_physical_evidence_snapshot,
            self.physical_schema,
            "invalid_fields",
        )

        bad_handoff = physical_snapshot()
        bad_handoff["qualified_handoff_sha256"] = "0" * 64
        bad_handoff = closed_hash(
            bad_handoff, "physical_evidence_snapshot_sha256"
        )
        jsonschema.Draft202012Validator(self.physical_schema).validate(
            bad_handoff
        )
        self.assertContractError(
            "qualified_handoff_hash_mismatch",
            lambda: contract.validate_physical_evidence_snapshot(bad_handoff),
        )

        bad_snapshot = physical_snapshot()
        bad_snapshot["image_id"] = "changed-image"
        jsonschema.Draft202012Validator(self.physical_schema).validate(
            bad_snapshot
        )
        self.assertContractError(
            "physical_snapshot_hash_mismatch",
            lambda: contract.validate_physical_evidence_snapshot(bad_snapshot),
        )

    def test_physical_snapshot_enforces_ids_hashes_and_fixed_handoff(self):
        invalid_id = physical_snapshot()
        invalid_id["server_case_id"] = "../case"
        invalid_id = closed_hash(
            invalid_id, "physical_evidence_snapshot_sha256"
        )
        self.assertBothReject(
            invalid_id,
            contract.validate_physical_evidence_snapshot,
            self.physical_schema,
            "invalid_id",
        )

        uppercase_hash = physical_snapshot()
        uppercase_hash["image_sha256"] = "A" * 64
        uppercase_hash = closed_hash(
            uppercase_hash, "physical_evidence_snapshot_sha256"
        )
        self.assertBothReject(
            uppercase_hash,
            contract.validate_physical_evidence_snapshot,
            self.physical_schema,
            "invalid_sha256",
        )

        for field, value in (
            ("registration_review_required", False),
            ("field_accuracy_claim_allowed", True),
        ):
            invalid = physical_snapshot()
            invalid["qualified_handoff"][field] = value
            invalid["qualified_handoff_sha256"] = fixture_sha256(
                invalid["qualified_handoff"]
            )
            invalid = closed_hash(
                invalid, "physical_evidence_snapshot_sha256"
            )
            with self.subTest(field=field):
                self.assertBothReject(
                    invalid,
                    contract.validate_physical_evidence_snapshot,
                    self.physical_schema,
                    "invalid_qualified_handoff",
                )

    def test_v1_linkability_requires_reviewed_manual_four_point(self):
        registration_schema = self.physical_schema["$defs"]["registration"]
        self.assertEqual(
            registration_schema["properties"]["method"]["enum"],
            ["reviewed_manual_four_point"],
        )
        self.assertEqual(
            self.link_schema["$defs"]["registration"]["properties"][
                "method"
            ]["enum"],
            ["reviewed_manual_four_point"],
        )

        manual = physical_snapshot()
        self.assertEqual(
            contract.validate_physical_evidence_snapshot(manual),
            manual,
        )
        jsonschema.Draft202012Validator(self.physical_schema).validate(manual)

    def test_current_automatic_review_shapes_are_not_v1_linkable(self):
        current = physical_snapshot()
        current["registration"] = {
            "decision": "accept_automatic",
            "method": "automatic",
            "board_to_image_matrix": copy.deepcopy(
                current["registration"]["board_to_image_matrix"]
            ),
            "solve_anchors": [],
            "independent_check_points": [],
            "error": None,
        }
        current = closed_hash(
            current, "physical_evidence_snapshot_sha256"
        )
        self.assertBothReject(
            current,
            contract.validate_physical_evidence_snapshot,
            self.physical_schema,
            "invalid_fields",
        )

        prior_candidate = physical_snapshot()
        prior_candidate["registration"].update(
            method="reviewed_automatic_candidate",
            solve_anchors=[],
            independent_check_points=[],
            error={"count": None, "rms": None, "maximum": None},
        )
        prior_candidate = closed_hash(
            prior_candidate, "physical_evidence_snapshot_sha256"
        )
        self.assertBothReject(
            prior_candidate,
            contract.validate_physical_evidence_snapshot,
            self.physical_schema,
            "invalid_registration_method",
        )

    def test_registration_rejects_bad_cardinality_numbers_and_error_count(self):
        cases = []
        too_few_matrix = physical_snapshot()
        too_few_matrix["registration"]["board_to_image_matrix"].pop()
        cases.append((too_few_matrix, "invalid_registration"))

        too_few_anchors = physical_snapshot()
        too_few_anchors["registration"]["solve_anchors"].pop()
        cases.append((too_few_anchors, "invalid_registration"))

        no_checks = physical_snapshot()
        no_checks["registration"]["independent_check_points"] = []
        no_checks["registration"]["error"]["count"] = 0
        cases.append((no_checks, "invalid_registration"))

        bad_count = physical_snapshot()
        bad_count["registration"]["error"]["count"] = True
        cases.append((bad_count, "invalid_number"))

        mismatched_count = physical_snapshot()
        mismatched_count["registration"]["error"]["count"] = 1
        cases.append((mismatched_count, "invalid_registration"))

        for payload, code in cases:
            payload = closed_hash(
                payload, "physical_evidence_snapshot_sha256"
            )
            with self.subTest(code=code):
                self.assertContractError(
                    code,
                    lambda payload=payload: (
                        contract.validate_physical_evidence_snapshot(payload)
                    ),
                )

    def test_registration_rejects_nonfinite_boolean_and_out_of_range_coordinates(self):
        invalid_values = [
            ("matrix_nan", ("matrix", 0), math.nan),
            ("matrix_bool", ("matrix", 0), True),
            ("anchor_infinite", ("anchor", "x"), math.inf),
            ("anchor_bool", ("anchor", "x"), False),
            ("anchor_outside", ("anchor", "x"), 1.01),
            ("error_negative", ("error", "rms"), -0.1),
            ("error_nonfinite", ("error", "maximum"), math.inf),
        ]
        for name, location, value in invalid_values:
            payload = physical_snapshot()
            if location[0] == "matrix":
                payload["registration"]["board_to_image_matrix"][
                    location[1]
                ] = value
            elif location[0] == "anchor":
                payload["registration"]["solve_anchors"][0]["board"][
                    location[1]
                ] = value
            else:
                payload["registration"]["error"][location[1]] = value
            with self.subTest(name=name):
                self.assertContractError(
                    "invalid_number",
                    lambda payload=payload: (
                        contract.validate_physical_evidence_snapshot(payload)
                    ),
                )

    def test_registration_accepts_real_shaped_perspective_homography(self):
        payload = physical_snapshot()
        matrix = [
            0.8,
            0.05,
            0.05,
            0.02,
            0.8,
            0.05,
            0.05,
            0.02,
            1.0,
        ]
        payload["registration"]["board_to_image_matrix"] = matrix
        payload["registration"]["solve_anchors"] = [
            registration_point_from_matrix(matrix, x, y)
            for x, y in (
                (0.1, 0.1),
                (0.9, 0.1),
                (0.9, 0.9),
                (0.1, 0.9),
            )
        ]
        payload["registration"]["independent_check_points"] = [
            registration_point_from_matrix(matrix, 0.25, 0.25),
            registration_point_from_matrix(matrix, 0.75, 0.6),
        ]
        payload["registration"]["error"] = {
            "count": 2,
            "rms": 0.0,
            "maximum": 0.0,
        }
        payload = closed_hash(
            payload, "physical_evidence_snapshot_sha256"
        )

        contract.validate_physical_evidence_snapshot(payload)
        jsonschema.Draft202012Validator(self.physical_schema).validate(payload)

    def test_registration_accepts_scaled_equivalent_homographies_as_supplied(self):
        for scale in (1e-6, 1e6):
            payload = physical_snapshot()
            supplied = [
                scale,
                0.0,
                0.0,
                0.0,
                scale,
                0.0,
                0.0,
                0.0,
                scale,
            ]
            payload["registration"]["board_to_image_matrix"] = supplied
            payload = closed_hash(
                payload, "physical_evidence_snapshot_sha256"
            )

            with self.subTest(scale=scale):
                validated = contract.validate_physical_evidence_snapshot(
                    payload
                )
                self.assertEqual(
                    validated["registration"]["board_to_image_matrix"],
                    supplied,
                )
                self.assertEqual(
                    validated["physical_evidence_snapshot_sha256"],
                    fixture_sha256(
                        {
                            key: value
                            for key, value in payload.items()
                            if key != "physical_evidence_snapshot_sha256"
                        }
                    ),
                )

    def test_registration_projection_bounds_tolerate_only_roundoff(self):
        def boundary_payload(offset):
            payload = physical_snapshot()
            matrix = [
                1.0,
                0.0,
                offset,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                1.0,
            ]
            payload["registration"]["board_to_image_matrix"] = matrix
            payload["registration"]["solve_anchors"] = [
                registration_point(
                    x,
                    y,
                    min(1.0, max(0.0, x + offset)),
                    y,
                )
                for x, y in (
                    (0.0, 0.0),
                    (1.0, 0.0),
                    (1.0, 1.0),
                    (0.0, 1.0),
                )
            ]
            payload["registration"]["independent_check_points"] = [
                registration_point_from_matrix(matrix, 0.25, 0.25),
                registration_point_from_matrix(matrix, 0.75, 0.6),
            ]
            payload["registration"]["error"] = {
                "count": 2,
                "rms": 0.0,
                "maximum": 0.0,
            }
            return closed_hash(
                payload, "physical_evidence_snapshot_sha256"
            )

        for offset in (-1e-16, 5e-16):
            payload = boundary_payload(offset)
            with self.subTest(offset=offset):
                validated = contract.validate_physical_evidence_snapshot(
                    payload
                )
                self.assertEqual(validated, payload)

        material = boundary_payload(0.01)
        self.assertContractError(
            "invalid_registration_projection",
            lambda: contract.validate_physical_evidence_snapshot(material),
        )
    def test_registration_rejects_horizon_crossing_unsampled_board_location(self):
        payload = physical_snapshot()
        payload["registration"]["board_to_image_matrix"] = [
            1.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            1.0,
            0.0,
            -0.6,
        ]
        payload = closed_hash(
            payload, "physical_evidence_snapshot_sha256"
        )

        self.assertContractError(
            "invalid_homography_horizon",
            lambda: contract.validate_physical_evidence_snapshot(payload),
        )

    def test_registration_rejects_mismatched_solve_anchor_correspondence(self):
        payload = physical_snapshot()
        payload["registration"]["solve_anchors"][0]["image"] = (
            normalized_point(0.2, 0.2)
        )
        payload = closed_hash(
            payload, "physical_evidence_snapshot_sha256"
        )

        self.assertContractError(
            "registration_correspondence_mismatch",
            lambda: contract.validate_physical_evidence_snapshot(payload),
        )

    def test_registration_recomputes_check_error_summary(self):
        valid = physical_snapshot()
        contract.validate_physical_evidence_snapshot(valid)
        check_errors = [
            math.dist(
                (
                    point["board"]["x"],
                    point["board"]["y"],
                ),
                (
                    point["image"]["x"],
                    point["image"]["y"],
                ),
            )
            for point in valid["registration"]["independent_check_points"]
        ]
        self.assertAlmostEqual(
            valid["registration"]["error"]["rms"],
            math.sqrt(
                sum(error * error for error in check_errors)
                / len(check_errors)
            ),
            places=15,
        )
        self.assertAlmostEqual(
            valid["registration"]["error"]["maximum"],
            max(check_errors),
            places=15,
        )

        contradictory = physical_snapshot()
        contradictory["registration"]["independent_check_points"][0][
            "image"
        ] = normalized_point(0.4, 0.4)
        contradictory["registration"]["error"] = {
            "count": 2,
            "rms": 0.0,
            "maximum": 0.0,
        }
        contradictory = closed_hash(
            contradictory, "physical_evidence_snapshot_sha256"
        )
        self.assertContractError(
            "registration_error_mismatch",
            lambda: contract.validate_physical_evidence_snapshot(
                contradictory
            ),
        )

    def test_registration_rejects_singular_and_near_singular_homographies(self):
        matrices = (
            [0.0] * 9,
            [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1e-13],
        )
        for matrix in matrices:
            payload = physical_snapshot()
            payload["registration"]["board_to_image_matrix"] = matrix
            payload = closed_hash(
                payload, "physical_evidence_snapshot_sha256"
            )
            with self.subTest(matrix=matrix):
                self.assertContractError(
                    "invalid_homography",
                    lambda payload=payload: (
                        contract.validate_physical_evidence_snapshot(payload)
                    ),
                )

    def test_registration_rejects_duplicate_and_degenerate_anchor_quads(self):
        cases = []

        duplicate_board = physical_snapshot()
        duplicate_board["registration"]["solve_anchors"][1][
            "board"
        ] = copy.deepcopy(
            duplicate_board["registration"]["solve_anchors"][0]["board"]
        )
        cases.append(duplicate_board)

        collinear_board = physical_snapshot()
        for index, coordinate in enumerate((0.1, 0.4, 0.7)):
            collinear_board["registration"]["solve_anchors"][index][
                "board"
            ] = normalized_point(coordinate, coordinate)
        cases.append(collinear_board)

        collinear_image = physical_snapshot()
        for index, coordinate in enumerate((0.1, 0.4, 0.7)):
            collinear_image["registration"]["solve_anchors"][index][
                "image"
            ] = normalized_point(coordinate, 0.5)
        cases.append(collinear_image)

        near_collinear_board = physical_snapshot()
        near_collinear_board["registration"]["solve_anchors"][0][
            "board"
        ] = normalized_point(0.1, 0.1)
        near_collinear_board["registration"]["solve_anchors"][1][
            "board"
        ] = normalized_point(0.5, 0.50000000001)
        near_collinear_board["registration"]["solve_anchors"][2][
            "board"
        ] = normalized_point(0.9, 0.9)
        cases.append(near_collinear_board)

        for payload in cases:
            payload = closed_hash(
                payload, "physical_evidence_snapshot_sha256"
            )
            with self.subTest(anchors=payload["registration"]["solve_anchors"]):
                self.assertContractError(
                    "invalid_registration_anchors",
                    lambda payload=payload: (
                        contract.validate_physical_evidence_snapshot(payload)
                    ),
                )

    def test_registration_rejects_denominator_touching_board_domain(self):
        payload = physical_snapshot()
        payload["registration"]["board_to_image_matrix"] = [
            0.2,
            0.0,
            0.05,
            0.0,
            0.05,
            0.0,
            1.0,
            0.0,
            0.0,
        ]
        payload["registration"]["independent_check_points"][0][
            "board"
        ] = normalized_point(0.0, 0.5)
        payload = closed_hash(
            payload, "physical_evidence_snapshot_sha256"
        )

        self.assertContractError(
            "invalid_homography_horizon",
            lambda: contract.validate_physical_evidence_snapshot(payload),
        )

    def test_valid_link_manifest_is_deep_copied_and_schema_valid(self):
        payload = link_manifest()
        validated = contract.validate_repair_evidence_link_manifest(payload)
        self.assertEqual(validated, payload)
        self.assertIsNot(validated, payload)
        self.assertIsNot(validated["bindings"][0], payload["bindings"][0])
        jsonschema.Draft202012Validator(self.link_schema).validate(payload)

    def test_link_top_level_is_exact_and_revision_parent_is_consistent(self):
        for field in ("timestamp", "path", "model_identity_resolved", "extra"):
            invalid = link_manifest()
            invalid[field] = None
            with self.subTest(field=field):
                self.assertBothReject(
                    invalid,
                    contract.validate_repair_evidence_link_manifest,
                    self.link_schema,
                    "invalid_fields",
                )

        revision_one_parent = link_manifest()
        revision_one_parent["previous_manifest_sha256"] = "3" * 64
        self.assertBothReject(
            revision_one_parent,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_revision",
        )

        later_without_parent = link_manifest(revision=2)
        later_without_parent["previous_manifest_sha256"] = None
        self.assertBothReject(
            later_without_parent,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_revision",
        )

        boolean_revision = link_manifest()
        boolean_revision["revision"] = True
        self.assertBothReject(
            boolean_revision,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_revision",
        )

    def test_repair_case_references_structurally_accept_publisher_derived_v1_v2(self):
        for version in (
            "VISUAL-QC-REPAIR-CASE-SOURCE-V1",
            "VISUAL-QC-REPAIR-CASE-SOURCE-V2",
        ):
            payload = link_manifest()
            payload["repair_case_references"][0]["schema_version"] = version
            payload["bindings"][0]["boundaries"][
                "model_identity_resolved"
            ] = version == "VISUAL-QC-REPAIR-CASE-SOURCE-V1"
            with self.subTest(version=version):
                contract.validate_repair_evidence_link_manifest(payload)
                jsonschema.Draft202012Validator(self.link_schema).validate(
                    payload
                )

        duplicate = link_manifest()
        duplicate["repair_case_references"].append(
            copy.deepcopy(duplicate["repair_case_references"][0])
        )
        self.assertContractError(
            "duplicate_id",
            lambda: contract.validate_repair_evidence_link_manifest(duplicate),
        )

    def test_repair_case_references_reject_duplicate_case_revision_identity(self):
        payload = link_manifest()
        alias = copy.deepcopy(payload["repair_case_references"][0])
        alias["repair_case_reference_id"] = "generic-v2-r1-alias"
        alias["manifest_sha256"] = "9" * 64
        payload["repair_case_references"].append(alias)

        self.assertContractError(
            "duplicate_repair_case_revision",
            lambda: contract.validate_repair_evidence_link_manifest(payload),
        )

    def test_board_paths_are_windows_safe_normalized_repository_relative_posix(self):
        invalid_paths = (
            "/knowledge-base/board.json",
            "//server/share/board.json",
            "C:/knowledge-base/board.json",
            "knowledge-base/file.json:stream",
            "knowledge-base/file<name>.json",
            "knowledge-base/file>name.json",
            "knowledge-base/file\"name.json",
            "knowledge-base/file|name.json",
            "knowledge-base/file?name.json",
            "knowledge-base/file*name.json",
            "knowledge-base\\board.json",
            "\\\\server\\share\\board.json",
            "knowledge-base/../board.json",
            "knowledge-base/./board.json",
            "./knowledge-base/board.json",
            "knowledge-base//board.json",
            "knowledge-base/board.json.",
            "knowledge-base/board.json ",
            "knowledge-base./board.json",
            "knowledge-base /board.json",
            "knowledge-base/board\u0000.json",
            "knowledge-base/board\u001f.json",
            "knowledge-base/board\u007f.json",
            "knowledge-base/board\u0085.json",
            "CON",
            "knowledge-base/con.json",
            "knowledge-base/CON .txt",
            "knowledge-base/PRN.txt",
            "knowledge-base/AuX.bin",
            "knowledge-base/NUL",
            "knowledge-base/NuL .bin",
            "knowledge-base/com1.json",
            "knowledge-base/cOm1 .json",
            "knowledge-base/COM9",
            "knowledge-base/lpt1.txt",
            "knowledge-base/LPT9",
        )
        for path in invalid_paths:
            payload = link_manifest()
            payload["board"]["catalog_asset"]["path"] = path
            payload["board"] = closed_hash(
                payload["board"], "board_snapshot_sha256"
            )
            with self.subTest(path=path):
                self.assertBothReject(
                    payload,
                    contract.validate_repair_evidence_link_manifest,
                    self.link_schema,
                    "invalid_repository_path",
                )

    def test_board_snapshot_hash_and_compiled_sources_are_closed(self):
        bad_hash = link_manifest()
        bad_hash["board"]["board_id"] = "BOARD-CHANGED"
        self.assertContractError(
            "board_snapshot_hash_mismatch",
            lambda: contract.validate_repair_evidence_link_manifest(bad_hash),
        )

        empty_sources = link_manifest()
        empty_sources["board"]["compiled_sources"] = []
        empty_sources["board"] = closed_hash(
            empty_sources["board"], "board_snapshot_sha256"
        )
        self.assertBothReject(
            empty_sources,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_board_snapshot",
        )

        unknown = link_manifest()
        unknown["board"]["catalog_asset"]["label"] = "free text"
        unknown["board"] = closed_hash(
            unknown["board"], "board_snapshot_sha256"
        )
        self.assertBothReject(
            unknown,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_fields",
        )

    def test_all_four_source_fact_variants_accept_and_validate_fact_hash(self):
        for kind in (
            "reported_symptom",
            "finding",
            "repair_action",
            "outcome",
        ):
            payload = link_manifest(
                bindings=[
                    binding(
                        binding_id=f"binding-{kind}",
                        source_kind=kind,
                        target_kind="whole_board",
                    )
                ]
            )
            with self.subTest(kind=kind):
                contract.validate_repair_evidence_link_manifest(payload)
                jsonschema.Draft202012Validator(self.link_schema).validate(
                    payload
                )

        bad_hash = link_manifest()
        bad_hash["bindings"][0]["source_fact"]["display"]["text"] = "changed"
        self.assertContractError(
            "source_fact_hash_mismatch",
            lambda: contract.validate_repair_evidence_link_manifest(bad_hash),
        )

    def test_source_fact_variant_shapes_reject_invalid_ids_and_claim_status(self):
        invalid_cases = []
        outcome_id = link_manifest()
        outcome_id["bindings"][0]["source_fact"] = source_fact(
            "outcome", "ignored"
        )
        outcome_id["bindings"][0]["source_fact"]["fact_id"] = "outcome-1"
        outcome_id["bindings"][0]["source_fact"] = closed_hash(
            outcome_id["bindings"][0]["source_fact"], "fact_sha256"
        )
        invalid_cases.append(outcome_id)

        empty_finding_id = link_manifest()
        empty_finding_id["bindings"][0]["source_fact"]["fact_id"] = ""
        empty_finding_id["bindings"][0]["source_fact"] = closed_hash(
            empty_finding_id["bindings"][0]["source_fact"], "fact_sha256"
        )
        invalid_cases.append(empty_finding_id)

        symptom_claim = link_manifest()
        symptom_claim["bindings"][0]["source_fact"] = source_fact(
            "reported_symptom", "symptom-1"
        )
        symptom_claim["bindings"][0]["source_fact"]["display"][
            "claim_status"
        ] = "reported"
        symptom_claim["bindings"][0]["source_fact"] = closed_hash(
            symptom_claim["bindings"][0]["source_fact"], "fact_sha256"
        )
        invalid_cases.append(symptom_claim)

        action_claim = link_manifest()
        action_claim["bindings"][0]["source_fact"] = source_fact(
            "repair_action", "action-1"
        )
        action_claim["bindings"][0]["source_fact"]["display"][
            "claim_status"
        ] = "documented"
        action_claim["bindings"][0]["source_fact"] = closed_hash(
            action_claim["bindings"][0]["source_fact"], "fact_sha256"
        )
        invalid_cases.append(action_claim)

        finding_without_claim = link_manifest()
        finding_without_claim["bindings"][0]["source_fact"]["display"][
            "claim_status"
        ] = None
        finding_without_claim["bindings"][0]["source_fact"] = closed_hash(
            finding_without_claim["bindings"][0]["source_fact"], "fact_sha256"
        )
        invalid_cases.append(finding_without_claim)

        for invalid in invalid_cases:
            with self.subTest(
                fact=invalid["bindings"][0]["source_fact"]
            ):
                self.assertContractError(
                    "invalid_source_fact",
                    lambda invalid=invalid: (
                        contract.validate_repair_evidence_link_manifest(invalid)
                    ),
                )

    def test_manifest_source_text_rejects_lone_unicode_surrogate(self):
        payload = link_manifest()
        payload["bindings"][0]["source_fact"]["display"]["text"] = "\ud800"

        self.assertContractError(
            "invalid_unicode_scalar",
            lambda: contract.validate_repair_evidence_link_manifest(payload),
        )

    def test_target_variants_accept_rectangle_polygon_and_designator(self):
        polygon_target = {
            "kind": "board_region",
            "side_id": "main_page_2",
            "region": {
                "kind": "normalized_polygon",
                "points": [
                    normalized_point(0.2, 0.2),
                    normalized_point(0.6, 0.2),
                    normalized_point(0.4, 0.6),
                ],
            },
        }
        targets = [
            target("whole_board"),
            target("board_region"),
            polygon_target,
            target("designator"),
        ]
        for index, target_value in enumerate(targets):
            item = binding(
                binding_id=f"binding-target-{index}",
                target_kind="whole_board",
            )
            item["target"] = target_value
            if target_value["kind"] == "designator":
                item["evidence_bases"].insert(
                    1, {"kind": "engineering_identity"}
                )
            payload = link_manifest(bindings=[item])
            with self.subTest(target=target_value["kind"], index=index):
                contract.validate_repair_evidence_link_manifest(payload)
                jsonschema.Draft202012Validator(self.link_schema).validate(
                    payload
                )

    def test_rectangle_rejects_nonfinite_bool_out_of_range_and_zero_size(self):
        for field, value in (
            ("x", math.nan),
            ("y", True),
            ("x", -0.1),
            ("width", 0),
            ("height", -0.1),
            ("width", 0.9),
        ):
            payload = link_manifest(
                bindings=[
                    binding(
                        target_kind="board_region",
                        association_status="possibly_related",
                    )
                ]
            )
            payload["bindings"][0]["target"]["region"][field] = value
            with self.subTest(field=field, value=value):
                self.assertContractError(
                    "invalid_geometry",
                    lambda payload=payload: (
                        contract.validate_repair_evidence_link_manifest(payload)
                    ),
                )

    def test_polygon_rejects_too_few_degenerate_and_self_intersecting_points(self):
        invalid_points = (
            [
                normalized_point(0.1, 0.1),
                normalized_point(0.2, 0.2),
            ],
            [
                normalized_point(0.1, 0.1),
                normalized_point(0.2, 0.2),
                normalized_point(0.3, 0.3),
            ],
            [
                normalized_point(0.1, 0.1),
                normalized_point(0.8, 0.8),
                normalized_point(0.1, 0.8),
                normalized_point(0.8, 0.1),
            ],
            [
                normalized_point(0.1, 0.1),
                normalized_point(math.inf, 0.2),
                normalized_point(0.2, 0.8),
            ],
        )
        for points in invalid_points:
            item = binding(
                target_kind="board_region",
                association_status="possibly_related",
            )
            item["target"]["region"] = {
                "kind": "normalized_polygon",
                "points": points,
            }
            payload = link_manifest(bindings=[item])
            with self.subTest(points=points):
                self.assertContractError(
                    "invalid_geometry",
                    lambda payload=payload: (
                        contract.validate_repair_evidence_link_manifest(payload)
                    ),
                )

    def test_contract_rejects_oversized_collections_before_deep_validation(self):
        oversized = []

        references = link_manifest()
        references["repair_case_references"] = [
            {
                **repair_case_reference(f"generic-v2-r{index}"),
                "revision": index,
            }
            for index in range(
                1, EXPECTED_MAX_REPAIR_CASE_REFERENCES + 2
            )
        ]
        oversized.append(
            (
                "repair_case_references",
                references,
                contract.validate_repair_evidence_link_manifest,
            )
        )

        physical = link_manifest()
        physical["physical_evidence"] = [
            physical["physical_evidence"][0]
        ] * (EXPECTED_MAX_PHYSICAL_EVIDENCE + 1)
        oversized.append(
            (
                "physical_evidence",
                physical,
                contract.validate_repair_evidence_link_manifest,
            )
        )

        bindings = link_manifest()
        bindings["bindings"] = [
            bindings["bindings"][0]
        ] * (EXPECTED_MAX_BINDINGS + 1)
        oversized.append(
            (
                "bindings",
                bindings,
                contract.validate_repair_evidence_link_manifest,
            )
        )

        sources = link_manifest()
        sources["board"]["compiled_sources"] = [
            sources["board"]["compiled_sources"][0]
        ] * (EXPECTED_MAX_COMPILED_SOURCES + 1)
        sources["board"] = closed_hash(
            sources["board"], "board_snapshot_sha256"
        )
        oversized.append(
            (
                "compiled_sources",
                sources,
                contract.validate_repair_evidence_link_manifest,
            )
        )

        descriptors = link_manifest()
        engineering = descriptors["bindings"][0]["target"]["engineering"]
        engineering["evidence_descriptors"] = [
            f"descriptor-{index}"
            for index in range(EXPECTED_MAX_EVIDENCE_DESCRIPTORS + 1)
        ]
        descriptors["bindings"][0]["target"]["engineering"] = closed_hash(
            engineering, "engineering_snapshot_sha256"
        )
        oversized.append(
            (
                "evidence_descriptors",
                descriptors,
                contract.validate_repair_evidence_link_manifest,
            )
        )

        bases = link_manifest()
        bases["bindings"][0]["evidence_bases"] = [
            {"kind": "repair_case_fact"}
        ] * (EXPECTED_MAX_EVIDENCE_BASES + 1)
        oversized.append(
            (
                "evidence_bases",
                bases,
                contract.validate_repair_evidence_link_manifest,
            )
        )

        checks = physical_snapshot()
        checks["registration"]["independent_check_points"] = [
            checks["registration"]["independent_check_points"][0]
        ] * (EXPECTED_MAX_CHECK_POINTS + 1)
        checks["registration"]["error"]["count"] = (
            EXPECTED_MAX_CHECK_POINTS + 1
        )
        checks = closed_hash(checks, "physical_evidence_snapshot_sha256")
        oversized.append(
            (
                "independent_check_points",
                checks,
                contract.validate_physical_evidence_snapshot,
            )
        )

        polygon = link_manifest(
            bindings=[
                binding(
                    target_kind="board_region",
                    association_status="possibly_related",
                )
            ]
        )
        polygon["bindings"][0]["target"]["region"] = {
            "kind": "normalized_polygon",
            "points": [
                normalized_point(
                    0.5 + 0.4 * math.cos(2 * math.pi * index / 257),
                    0.5 + 0.4 * math.sin(2 * math.pi * index / 257),
                )
                for index in range(EXPECTED_MAX_POLYGON_POINTS + 1)
            ],
        }
        oversized.append(
            (
                "polygon points",
                polygon,
                contract.validate_repair_evidence_link_manifest,
            )
        )

        for label, payload, validator in oversized:
            with self.subTest(label=label):
                self.assertContractError(
                    "limit_exceeded",
                    lambda payload=payload, validator=validator: validator(
                        payload
                    ),
                )

    def test_schema_collection_limits_match_runtime_constants(self):
        defs = self.link_schema["$defs"]
        self.assertEqual(
            self.link_schema["properties"]["repair_case_references"].get(
                "maxItems"
            ),
            EXPECTED_MAX_REPAIR_CASE_REFERENCES,
        )
        self.assertEqual(
            self.link_schema["properties"]["physical_evidence"].get(
                "maxItems"
            ),
            EXPECTED_MAX_PHYSICAL_EVIDENCE,
        )
        self.assertEqual(
            self.link_schema["properties"]["bindings"].get("maxItems"),
            EXPECTED_MAX_BINDINGS,
        )
        self.assertEqual(
            defs["board"]["properties"]["compiled_sources"].get("maxItems"),
            EXPECTED_MAX_COMPILED_SOURCES,
        )
        self.assertEqual(
            defs["engineering"]["properties"]["evidence_descriptors"].get(
                "maxItems"
            ),
            EXPECTED_MAX_EVIDENCE_DESCRIPTORS,
        )
        self.assertEqual(
            defs["binding"]["properties"]["evidence_bases"].get("maxItems"),
            EXPECTED_MAX_EVIDENCE_BASES,
        )
        self.assertEqual(
            defs["normalizedPolygon"]["properties"]["points"].get("maxItems"),
            EXPECTED_MAX_POLYGON_POINTS,
        )
        self.assertEqual(
            defs["registration"]["properties"][
                "independent_check_points"
            ].get("maxItems"),
            EXPECTED_MAX_CHECK_POINTS,
        )
        self.assertEqual(
            self.physical_schema["$defs"]["registration"]["properties"][
                "independent_check_points"
            ].get("maxItems"),
            EXPECTED_MAX_CHECK_POINTS,
        )
        for name, expected in (
            ("MAX_POLYGON_POINTS", EXPECTED_MAX_POLYGON_POINTS),
            (
                "MAX_REPAIR_CASE_REFERENCES",
                EXPECTED_MAX_REPAIR_CASE_REFERENCES,
            ),
            ("MAX_PHYSICAL_EVIDENCE", EXPECTED_MAX_PHYSICAL_EVIDENCE),
            ("MAX_BINDINGS", EXPECTED_MAX_BINDINGS),
            ("MAX_COMPILED_SOURCES", EXPECTED_MAX_COMPILED_SOURCES),
            (
                "MAX_EVIDENCE_DESCRIPTORS",
                EXPECTED_MAX_EVIDENCE_DESCRIPTORS,
            ),
            ("MAX_EVIDENCE_BASES", EXPECTED_MAX_EVIDENCE_BASES),
            ("MAX_CHECK_POINTS", EXPECTED_MAX_CHECK_POINTS),
        ):
            with self.subTest(constant=name):
                self.assertEqual(getattr(contract, name, None), expected)

    def test_designator_engineering_snapshot_hash_and_low_geometry_rule(self):
        bad_hash = link_manifest()
        bad_hash["bindings"][0]["target"]["engineering"]["designator"] = "U9999"
        self.assertContractError(
            "engineering_snapshot_hash_mismatch",
            lambda: contract.validate_repair_evidence_link_manifest(bad_hash),
        )

        low_footprint = link_manifest()
        engineering = low_footprint["bindings"][0]["target"]["engineering"]
        engineering["location"] = {
            "kind": "normalized_footprint",
            "rectangle": {
                "x": 0.4,
                "y": 0.5,
                "width": 0.1,
                "height": 0.1,
            },
        }
        low_footprint["bindings"][0]["target"]["engineering"] = closed_hash(
            engineering, "engineering_snapshot_sha256"
        )
        self.assertContractError(
            "invalid_engineering_geometry",
            lambda: contract.validate_repair_evidence_link_manifest(
                low_footprint
            ),
        )

        high_footprint = copy.deepcopy(low_footprint)
        high_engineering = high_footprint["bindings"][0]["target"][
            "engineering"
        ]
        high_engineering["geometry_source_status"] = "high"
        high_footprint["bindings"][0]["target"]["engineering"] = closed_hash(
            high_engineering, "engineering_snapshot_sha256"
        )
        contract.validate_repair_evidence_link_manifest(high_footprint)

    def test_related_designator_structurally_requires_publisher_derived_semantic_proof(self):
        no_semantic_proof = link_manifest()
        engineering = no_semantic_proof["bindings"][0]["target"]["engineering"]
        engineering["semantic_identity_proven"] = False
        no_semantic_proof["bindings"][0]["target"][
            "engineering"
        ] = closed_hash(engineering, "engineering_snapshot_sha256")
        self.assertContractError(
            "related_designator_not_proven",
            lambda: contract.validate_repair_evidence_link_manifest(
                no_semantic_proof
            ),
        )

        conservative = copy.deepcopy(no_semantic_proof)
        conservative["bindings"][0][
            "association_status"
        ] = "possibly_related"
        contract.validate_repair_evidence_link_manifest(conservative)
        jsonschema.Draft202012Validator(self.link_schema).validate(
            conservative
        )

        for missing_kind in ("repair_case_fact", "engineering_identity"):
            payload = link_manifest()
            payload["bindings"][0]["evidence_bases"] = [
                basis
                for basis in payload["bindings"][0]["evidence_bases"]
                if basis["kind"] != missing_kind
            ]
            with self.subTest(missing_kind=missing_kind):
                self.assertContractError(
                    "related_designator_not_proven",
                    lambda payload=payload: (
                        contract.validate_repair_evidence_link_manifest(payload)
                    ),
                )

        whole_board = link_manifest(
            bindings=[
                binding(
                    target_kind="whole_board",
                    association_status="related",
                )
            ]
        )
        contract.validate_repair_evidence_link_manifest(whole_board)

    def test_related_designator_rejects_empty_engineering_evidence_descriptors(self):
        payload = link_manifest()
        engineering = payload["bindings"][0]["target"]["engineering"]
        engineering["evidence_descriptors"] = []
        payload["bindings"][0]["target"]["engineering"] = closed_hash(
            engineering, "engineering_snapshot_sha256"
        )

        self.assertBothReject(
            payload,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_engineering_evidence",
        )

    def test_evidence_bases_are_structured_unique_and_visibility_consistent(self):
        free_text = link_manifest()
        free_text["bindings"][0]["evidence_bases"][0]["note"] = "looks bad"
        self.assertBothReject(
            free_text,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_fields",
        )

        wrong_observation = link_manifest()
        wrong_observation["bindings"][0]["visibility_status"] = "occluded"
        self.assertContractError(
            "observation_visibility_mismatch",
            lambda: contract.validate_repair_evidence_link_manifest(
                wrong_observation
            ),
        )

        not_assessed_observation = link_manifest()
        not_assessed_observation["bindings"][0][
            "visibility_status"
        ] = "not_assessed"
        self.assertContractError(
            "observation_visibility_mismatch",
            lambda: contract.validate_repair_evidence_link_manifest(
                not_assessed_observation
            ),
        )

        duplicate = link_manifest()
        duplicate["bindings"][0]["evidence_bases"] = duplicate["bindings"][0][
            "evidence_bases"
        ][:2]
        duplicate["bindings"][0]["evidence_bases"].append(
            {"kind": "repair_case_fact"}
        )
        self.assertContractError(
            "duplicate_evidence_basis",
            lambda: contract.validate_repair_evidence_link_manifest(duplicate),
        )

    def test_binding_reference_cardinality_and_resolution(self):
        missing_reference = link_manifest()
        missing_reference["bindings"][0][
            "repair_case_reference_id"
        ] = "missing"
        self.assertContractError(
            "unresolved_reference",
            lambda: contract.validate_repair_evidence_link_manifest(
                missing_reference
            ),
        )

        missing_evidence = link_manifest()
        missing_evidence["bindings"][0]["physical_evidence_id"] = "missing"
        self.assertContractError(
            "unresolved_reference",
            lambda: contract.validate_repair_evidence_link_manifest(
                missing_evidence
            ),
        )

        zero_evidence = link_manifest()
        del zero_evidence["bindings"][0]["physical_evidence_id"]
        self.assertBothReject(
            zero_evidence,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_fields",
        )

        multiple_evidence = link_manifest()
        multiple_evidence["bindings"][0]["physical_evidence_id"] = [
            "physical-page-2",
            "physical-page-1",
        ]
        self.assertBothReject(
            multiple_evidence,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_id",
        )

    def test_board_and_side_identity_must_agree_everywhere(self):
        mutations = [
            ("reference-board", lambda p: p["repair_case_references"][0].update(board_id="OTHER")),
            ("physical-board", lambda p: p["physical_evidence"][0].update(board_key="other")),
            ("target-side", lambda p: p["bindings"][0]["target"].update(side_id="main_page_1")),
        ]
        for name, mutate in mutations:
            payload = link_manifest()
            mutate(payload)
            if name == "physical-board":
                payload["physical_evidence"][0] = closed_hash(
                    payload["physical_evidence"][0],
                    "physical_evidence_snapshot_sha256",
                )
            with self.subTest(name=name):
                self.assertContractError(
                    "identity_mismatch",
                    lambda payload=payload: (
                        contract.validate_repair_evidence_link_manifest(payload)
                    ),
                )

    def test_duplicate_ids_are_rejected_for_all_identity_collections(self):
        duplicate_physical = link_manifest()
        duplicate_physical["physical_evidence"].append(
            copy.deepcopy(duplicate_physical["physical_evidence"][0])
        )
        self.assertContractError(
            "duplicate_id",
            lambda: contract.validate_repair_evidence_link_manifest(
                duplicate_physical
            ),
        )

        duplicate_binding = link_manifest()
        duplicate_binding["bindings"].append(
            copy.deepcopy(duplicate_binding["bindings"][0])
        )
        self.assertContractError(
            "duplicate_id",
            lambda: contract.validate_repair_evidence_link_manifest(
                duplicate_binding
            ),
        )

    def test_fixed_boundaries_reject_true_non_boolean_and_missing_values(self):
        for scope in ("manifest", "binding"):
            for field in FIXED_FALSE_BOUNDARIES:
                for value in (True, 0):
                    payload = link_manifest()
                    boundaries = (
                        payload["boundaries"]
                        if scope == "manifest"
                        else payload["bindings"][0]["boundaries"]
                    )
                    boundaries[field] = value
                    with self.subTest(
                        scope=scope, field=field, value=value
                    ):
                        self.assertContractError(
                            "invalid_boundaries",
                            lambda payload=payload: (
                                contract.validate_repair_evidence_link_manifest(
                                    payload
                                )
                            ),
                        )

        missing = link_manifest()
        del missing["boundaries"]["golden_approved"]
        self.assertBothReject(
            missing,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_boundaries",
        )

    def test_generic_v1_binding_structurally_accepts_publisher_derived_model_identity_true(self):
        resolved = link_manifest()
        reference = resolved["repair_case_references"][0]
        reference["repair_case_reference_id"] = "generic-v1-r1"
        reference["schema_version"] = "VISUAL-QC-REPAIR-CASE-SOURCE-V1"
        resolved["bindings"][0][
            "repair_case_reference_id"
        ] = "generic-v1-r1"
        resolved["bindings"][0]["boundaries"][
            "model_identity_resolved"
        ] = True
        contract.validate_repair_evidence_link_manifest(resolved)
        jsonschema.Draft202012Validator(self.link_schema).validate(resolved)

        invalid = link_manifest()
        invalid["bindings"][0]["boundaries"][
            "model_identity_resolved"
        ] = 1
        self.assertBothReject(
            invalid,
            contract.validate_repair_evidence_link_manifest,
            self.link_schema,
            "invalid_boundaries",
        )

    def test_pure_validator_revision_boundary_is_explicit(self):
        later = link_manifest(revision=7)
        newer_reference = repair_case_reference("generic-v2-r2")
        newer_reference["revision"] = 2
        newer_reference["manifest_sha256"] = "8" * 64
        later["repair_case_references"].append(newer_reference)

        # Task 1 validates shape and the self-contained graph. It has no prior
        # manifest with which to prove +1, the actual parent hash, or append-only
        # preservation; Task 3 performs those on-disk checks.
        contract.validate_repair_evidence_link_manifest(later)
        jsonschema.Draft202012Validator(self.link_schema).validate(later)

        different_case = copy.deepcopy(later)
        different_case["repair_case_references"][1][
            "repair_case_id"
        ] = "another-repair-case"
        self.assertContractError(
            "identity_mismatch",
            lambda: contract.validate_repair_evidence_link_manifest(
                different_case
            ),
        )

    def test_schema_portability_boundary_defers_cross_field_geometry_to_runtime(self):
        rectangle = link_manifest(
            bindings=[
                binding(
                    target_kind="board_region",
                    association_status="possibly_related",
                )
            ]
        )
        rectangle["bindings"][0]["target"]["region"].update(
            x=0.9,
            width=0.2,
        )
        jsonschema.Draft202012Validator(self.link_schema).validate(rectangle)
        self.assertContractError(
            "invalid_geometry",
            lambda: contract.validate_repair_evidence_link_manifest(rectangle),
        )

        polygon = link_manifest(
            bindings=[
                binding(
                    target_kind="board_region",
                    association_status="possibly_related",
                )
            ]
        )
        polygon["bindings"][0]["target"]["region"] = {
            "kind": "normalized_polygon",
            "points": [
                normalized_point(0.1, 0.1),
                normalized_point(0.8, 0.8),
                normalized_point(0.1, 0.8),
                normalized_point(0.8, 0.1),
            ],
        }
        jsonschema.Draft202012Validator(self.link_schema).validate(polygon)
        self.assertContractError(
            "invalid_geometry",
            lambda: contract.validate_repair_evidence_link_manifest(polygon),
        )

    def test_schema_comments_document_portable_structure_boundary(self):
        for schema in (self.physical_schema, self.link_schema):
            comment = schema.get("$comment", "")
            with self.subTest(schema=schema["$id"]):
                self.assertIn("portable structure", comment)
                self.assertIn("strict loader", comment)
                self.assertIn("canonical hashes", comment)
                self.assertIn("horizon", comment)
                self.assertIn("correspondence", comment)
                self.assertIn("reviewed_manual_four_point only", comment)

    def test_schema_integer_semantics_do_not_weaken_strict_python_revision(self):
        payload = link_manifest()
        payload["revision"] = 1.0

        # Draft 2020-12 considers mathematically integral 1.0 an integer.
        jsonschema.Draft202012Validator(self.link_schema).validate(payload)
        self.assertContractError(
            "invalid_revision",
            lambda: contract.validate_repair_evidence_link_manifest(payload),
        )

    def test_embedded_physical_schema_stays_synchronized_with_standalone_schema(self):
        standalone_shape = {
            key: self.physical_schema[key]
            for key in (
                "type",
                "additionalProperties",
                "required",
                "properties",
            )
        }
        self.assertEqual(
            self.link_schema["$defs"]["physicalEvidence"],
            standalone_shape,
        )
        for definition in (
            "intake",
            "qualifiedHandoff",
            "normalizedPoint",
            "registrationPoint",
            "registrationError",
            "registration",
        ):
            with self.subTest(definition=definition):
                self.assertEqual(
                    self.link_schema["$defs"][definition],
                    self.physical_schema["$defs"][definition],
                )

    def test_revision_one_cannot_supersede_and_later_revision_can_chain(self):
        revision_one = link_manifest()
        revision_one["bindings"][0]["supersedes_binding_id"] = "older"
        self.assertContractError(
            "invalid_supersession",
            lambda: contract.validate_repair_evidence_link_manifest(
                revision_one
            ),
        )

        first = binding(binding_id="binding-1")
        second = binding(
            binding_id="binding-2",
            association_status="not_related",
            supersedes_binding_id="binding-1",
        )
        third = binding(
            binding_id="binding-3",
            association_status="possibly_related",
            supersedes_binding_id="binding-2",
        )
        later = link_manifest(bindings=[first, second, third], revision=3)
        contract.validate_repair_evidence_link_manifest(later)

    def test_long_valid_supersession_chain_is_accepted(self):
        chain_length = 1000
        bindings = []
        for index in range(chain_length):
            binding_id = f"binding-chain-{index}"
            bindings.append(
                binding(
                    binding_id=binding_id,
                    association_status="possibly_related",
                    supersedes_binding_id=(
                        None
                        if index == 0
                        else f"binding-chain-{index - 1}"
                    ),
                )
            )
        payload = link_manifest(bindings=bindings, revision=2)

        validated = contract.validate_repair_evidence_link_manifest(payload)

        self.assertEqual(len(validated["bindings"]), chain_length)
        self.assertEqual(
            validated["bindings"][-1]["supersedes_binding_id"],
            f"binding-chain-{chain_length - 2}",
        )

    def test_supersession_rejects_missing_target_cycle_and_duplicate_replacement(self):
        missing = link_manifest(
            bindings=[
                binding(
                    binding_id="binding-2",
                    supersedes_binding_id="missing",
                )
            ],
            revision=2,
        )
        self.assertContractError(
            "invalid_supersession",
            lambda: contract.validate_repair_evidence_link_manifest(missing),
        )

        first = binding(
            binding_id="binding-1",
            supersedes_binding_id="binding-2",
        )
        second = binding(
            binding_id="binding-2",
            supersedes_binding_id="binding-1",
        )
        cycle = link_manifest(bindings=[first, second], revision=2)
        self.assertContractError(
            "supersession_cycle",
            lambda: contract.validate_repair_evidence_link_manifest(cycle),
        )

        forward_reference = link_manifest(
            bindings=[
                binding(
                    binding_id="binding-2",
                    supersedes_binding_id="binding-1",
                ),
                binding(binding_id="binding-1"),
            ],
            revision=2,
        )
        self.assertContractError(
            "invalid_supersession",
            lambda: contract.validate_repair_evidence_link_manifest(
                forward_reference
            ),
        )

        root = binding(binding_id="binding-1")
        replacement_a = binding(
            binding_id="binding-2",
            supersedes_binding_id="binding-1",
        )
        replacement_b = binding(
            binding_id="binding-3",
            supersedes_binding_id="binding-1",
        )
        duplicate = link_manifest(
            bindings=[root, replacement_a, replacement_b],
            revision=2,
        )
        self.assertContractError(
            "duplicate_replacement",
            lambda: contract.validate_repair_evidence_link_manifest(duplicate),
        )


class VisualQcRepairEvidenceLinkRedTests(unittest.TestCase):
    def test_contract_module_exists(self):
        self.assertIsNotNone(
            contract,
            "scripts.visual_qc.repair_evidence_link_contract is missing",
        )

    def test_schema_files_exist(self):
        self.assertTrue(
            PHYSICAL_SCHEMA_PATH.is_file(),
            "physical evidence schema is missing",
        )
        self.assertTrue(LINK_SCHEMA_PATH.is_file(), "link schema is missing")


if __name__ == "__main__":
    unittest.main()
