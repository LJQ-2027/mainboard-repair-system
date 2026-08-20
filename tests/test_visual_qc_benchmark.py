import unittest
from pathlib import Path

from scripts.visual_qc.benchmark import (
    build_proxy_benchmark,
    run_synthetic_benchmark,
)


ROOT = Path(__file__).resolve().parents[1]


class VisualQcBenchmarkTests(unittest.TestCase):
    def test_synthetic_benchmark_covers_each_requested_board_side(self):
        report = run_synthetic_benchmark(
            ROOT,
            board_keys=["km4-f151"],
            seeds=[41],
        )

        self.assertEqual(report["schema_version"], "VISUAL-QC-REGISTRATION-BENCHMARK-V1")
        self.assertEqual(report["evidence_role"], "synthetic_proxy")
        self.assertFalse(report["field_accuracy_claim_allowed"])
        self.assertEqual(report["summary"]["case_count"], 2)
        self.assertEqual(report["summary"]["candidate_count"], 2)
        self.assertEqual(
            {case["side_id"] for case in report["cases"]},
            {"main_page_1", "main_page_2"},
        )
        self.assertTrue(all(case["mean_corner_error"] < 0.03 for case in report["cases"]))

    def test_proxy_benchmark_accounts_for_all_21_reviewed_manual_images(self):
        report = build_proxy_benchmark(ROOT)

        self.assertEqual(report["evidence_role"], "service_manual_proxy")
        self.assertFalse(report["field_accuracy_claim_allowed"])
        self.assertEqual(report["summary"]["case_count"], 21)
        self.assertEqual(
            report["summary"]["case_count"],
            sum(report["summary"]["status_counts"].values()),
        )
        self.assertTrue(all(case["evidence_role"] == "service_manual_proxy" for case in report["cases"]))
        self.assertTrue(
            any(case["status"] == "not_comparable" for case in report["cases"]),
            report["summary"],
        )
        self.assertFalse(any(case.get("counts_as_field_qc_evidence") for case in report["cases"]))


if __name__ == "__main__":
    unittest.main()
