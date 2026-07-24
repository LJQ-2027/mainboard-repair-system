from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import jsonschema

from scripts.visual_qc.repair_case_contract import (
    FIXED_FALSE_BOUNDARIES,
    REPAIR_CASE_SCHEMA_VERSION,
    derive_completeness,
    validate_repair_case_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT
    / "knowledge-base"
    / "visual-qc-repair-case-source-v1-schema.json"
)


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
    def test_canonical_photo_only_payload_matches_python_and_schema(self):
        payload = canonical_payload()

        validated = validate_repair_case_manifest(payload)

        self.assertEqual(validated, payload)
        self.assertIsNot(validated, payload)
        self.assertEqual(derive_completeness(payload), "photos_only")
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(payload)

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


if __name__ == "__main__":
    unittest.main()
