from __future__ import annotations

import copy
import importlib
import unittest


try:
    exporter = importlib.import_module(
        "scripts.visual_qc.repair_evidence_export"
    )
except ModuleNotFoundError:
    exporter = None


def handoff():
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


def point(board_x, board_y, image_x, image_y):
    return {
        "board": {"x": board_x, "y": board_y},
        "image": {"x": image_x, "y": image_y},
    }


def server_case():
    return {
        "schema_version": "VISUAL-QC-SERVER-CASE-V3",
        "case_id": "vqc-case-005-page-2",
        "board_key": "bg6h-f069",
        "board_id": "BOARD-F069-MAIN-V1.2",
        "side_id": "main_page_2",
        "capture_stage": "after_repair",
        "evidence_role": "physical_capture",
        "intake": {
            "batch_id": "f069-case005-after-source",
            "entry_id": "case005-main-page-2",
        },
        "qualified_handoff": handoff(),
        "capture_session": {"session_id": "private-session"},
        "created_at": "2026-07-24T00:00:00Z",
        "image": {
            "image_id": "image-case005-page-2",
            "sha256": "d" * 64,
            "side_id": "main_page_2",
            "board_id": "BOARD-F069-MAIN-V1.2",
            "original_filename": "private-name.jpg",
        },
        "job": {
            "job_id": "job-case005-page-2",
            "case_id": "vqc-case-005-page-2",
            "status": "succeeded",
            "result": {"private": "ignored"},
        },
        "server_registration_review": {
            "review_id": "review-case005-page-2",
            "case_id": "vqc-case-005-page-2",
            "job_id": "job-case005-page-2",
            "status": "reviewed",
            "decision": "accept_manual",
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
            "anchors": [
                point(0.1, 0.1, 0.1, 0.1),
                point(0.9, 0.1, 0.9, 0.1),
                point(0.9, 0.9, 0.9, 0.9),
                point(0.1, 0.9, 0.1, 0.9),
            ],
            "check_points": [
                point(0.25, 0.25, 0.250003, 0.250004),
                point(0.75, 0.6, 0.750006, 0.600008),
            ],
            "error": {
                "count": 2,
                "rms": 7.90569415042095e-06,
                "maximum": 1e-05,
            },
            "reviewer_id": "private-reviewer",
            "notes": "private notes",
            "created_at": "2026-07-24T00:01:00Z",
        },
        "server_qc_review": {
            "qc_result": "visible_anomaly",
            "reviewer_id": "private-reviewer",
        },
        "golden_sample": {"state": "candidate"},
        "audit": [{"actor": "private-reviewer"}],
    }


class RepairEvidenceExportAvailabilityTests(unittest.TestCase):
    def test_export_module_exists(self):
        self.assertIsNotNone(exporter)


@unittest.skipUnless(exporter is not None, "export module not implemented")
class RepairEvidenceExportTests(unittest.TestCase):
    def assertExportError(self, expected_code, payload):
        with self.assertRaises(exporter.RepairEvidenceExportError) as caught:
            exporter.build_linkable_physical_evidence(
                payload,
                physical_evidence_id="physical-case005-page-2",
            )
        self.assertEqual(caught.exception.code, expected_code)
        self.assertNotIn("private", caught.exception.message.lower())
        self.assertNotIn("\\", caught.exception.message)
        self.assertNotIn("/", caught.exception.message)

    def test_builds_exact_validated_reduced_snapshot(self):
        payload = server_case()
        result = exporter.build_linkable_physical_evidence(
            payload,
            physical_evidence_id="physical-case005-page-2",
        )

        self.assertEqual(
            set(result),
            {
                "schema_version",
                "physical_evidence_id",
                "server_case_id",
                "intake",
                "board_key",
                "board_id",
                "side_id",
                "capture_stage",
                "evidence_role",
                "qualified_handoff",
                "qualified_handoff_sha256",
                "image_id",
                "image_sha256",
                "job_id",
                "registration_review_id",
                "registration",
                "physical_evidence_snapshot_sha256",
            },
        )
        self.assertEqual(
            result["schema_version"],
            "VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1",
        )
        self.assertEqual(result["qualified_handoff"], payload["qualified_handoff"])
        self.assertIsNot(result["qualified_handoff"], payload["qualified_handoff"])
        self.assertEqual(
            result["registration"],
            {
                "method": "reviewed_manual_four_point",
                "board_to_image_matrix": payload[
                    "server_registration_review"
                ]["board_to_image_matrix"],
                "solve_anchors": payload["server_registration_review"]["anchors"],
                "independent_check_points": payload[
                    "server_registration_review"
                ]["check_points"],
                "error": payload["server_registration_review"]["error"],
            },
        )
        rendered = repr(result)
        for forbidden in (
            "private-reviewer",
            "private notes",
            "server_qc_review",
            "golden_sample",
            "audit",
            "original_filename",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_normalizes_server_coordinate_pairs_without_changing_values(self):
        payload = server_case()
        payload["server_registration_review"]["anchors"] = [
            {"board": [0.1, 0.1], "image": [0.1, 0.1]},
            {"board": [0.9, 0.1], "image": [0.9, 0.1]},
            {"board": [0.9, 0.9], "image": [0.9, 0.9]},
            {"board": [0.1, 0.9], "image": [0.1, 0.9]},
        ]
        payload["server_registration_review"]["check_points"] = [
            {"board": [0.25, 0.25], "image": [0.250003, 0.250004]},
            {"board": [0.75, 0.6], "image": [0.750006, 0.600008]},
        ]

        result = exporter.build_linkable_physical_evidence(
            payload,
            physical_evidence_id="physical-case005-page-2",
        )

        self.assertEqual(
            result["registration"]["solve_anchors"][0],
            point(0.1, 0.1, 0.1, 0.1),
        )
        self.assertEqual(
            result["registration"]["independent_check_points"][1],
            point(0.75, 0.6, 0.750006, 0.600008),
        )

    def test_unrelated_v3_fields_and_qc_presence_do_not_change_output(self):
        left = server_case()
        right = server_case()
        right.pop("server_qc_review")
        right.pop("golden_sample")
        right.pop("audit")
        right["new_valid_v3_field"] = {"future": True}

        self.assertEqual(
            exporter.build_linkable_physical_evidence(
                left, physical_evidence_id="physical-case005-page-2"
            ),
            exporter.build_linkable_physical_evidence(
                right, physical_evidence_id="physical-case005-page-2"
            ),
        )

    def test_rejects_nonphysical_and_incomplete_provenance(self):
        for role in ("synthetic_proxy", "service_manual_proxy"):
            payload = server_case()
            payload["evidence_role"] = role
            with self.subTest(role=role):
                self.assertExportError("invalid_evidence_role", payload)

        for value in (None, {}, {"schema_version": "wrong"}):
            payload = server_case()
            payload["qualified_handoff"] = value
            with self.subTest(value=value):
                self.assertExportError("invalid_qualified_handoff", payload)

    def test_rejects_unreviewed_automatic_and_incomplete_jobs(self):
        mutations = (
            ("missing_registration_review", lambda value: value.pop(
                "server_registration_review"
            )),
            ("invalid_registration_review", lambda value: value[
                "server_registration_review"
            ].update(status="pending")),
            ("invalid_registration_review", lambda value: value[
                "server_registration_review"
            ].update(decision="accept_automatic")),
            ("invalid_registration_review", lambda value: value[
                "server_registration_review"
            ].update(method="orb_homography")),
            ("job_not_succeeded", lambda value: value["job"].update(
                status="failed"
            )),
            ("job_not_succeeded", lambda value: value["job"].update(
                status="processing"
            )),
        )
        for code, mutate in mutations:
            payload = server_case()
            mutate(payload)
            with self.subTest(code=code, payload=payload):
                self.assertExportError(code, payload)

    def test_rejects_missing_intake_ids_and_identity_mismatches(self):
        mutations = (
            ("invalid_intake", lambda value: value["intake"].update(batch_id=None)),
            ("invalid_intake", lambda value: value["intake"].update(entry_id="")),
            ("identity_mismatch", lambda value: value["job"].update(case_id="other")),
            ("identity_mismatch", lambda value: value[
                "server_registration_review"
            ].update(case_id="other")),
            ("identity_mismatch", lambda value: value[
                "server_registration_review"
            ].update(job_id="other")),
            ("invalid_image", lambda value: value["image"].pop("sha256")),
            ("identity_mismatch", lambda value: value["image"].update(
                side_id="main_page_1"
            )),
            ("identity_mismatch", lambda value: value["image"].update(
                board_id="OTHER-BOARD"
            )),
        )
        for code, mutate in mutations:
            payload = server_case()
            mutate(payload)
            with self.subTest(code=code):
                self.assertExportError(code, payload)

    def test_rejects_malformed_v3_and_registration_shapes(self):
        mutations = (
            ("invalid_schema_version", lambda value: value.update(
                schema_version="VISUAL-QC-SERVER-CASE-V2"
            )),
            ("invalid_case", lambda value: value.update(case_id="../case")),
            ("invalid_image", lambda value: value.update(image=[])),
            ("invalid_job", lambda value: value.update(job=[])),
            ("invalid_registration_review", lambda value: value[
                "server_registration_review"
            ].update(board_to_image_matrix=[1.0] * 8)),
            ("invalid_registration_review", lambda value: value[
                "server_registration_review"
            ].update(anchors=[])),
            ("invalid_registration_review", lambda value: value[
                "server_registration_review"
            ].update(check_points=[])),
            ("invalid_registration_review", lambda value: value[
                "server_registration_review"
            ].update(error=None)),
        )
        for code, mutate in mutations:
            payload = server_case()
            mutate(payload)
            with self.subTest(code=code):
                self.assertExportError(code, payload)

    def test_returns_deep_copy_and_deterministic_hashes(self):
        payload = server_case()
        first = exporter.build_linkable_physical_evidence(
            payload, physical_evidence_id="physical-case005-page-2"
        )
        second = exporter.build_linkable_physical_evidence(
            copy.deepcopy(payload),
            physical_evidence_id="physical-case005-page-2",
        )
        self.assertEqual(first, second)
        payload["qualified_handoff"]["acceptance_action"] = "changed"
        self.assertEqual(
            first["qualified_handoff"]["acceptance_action"],
            "manual_registration_required",
        )


if __name__ == "__main__":
    unittest.main()
