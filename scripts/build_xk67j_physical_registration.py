import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.visual_qc.reviewed_registration import build_review


def pair(landmark_id, label, board, image, selection_basis="reviewed_visible_landmark"):
    return {
        "landmark_id": landmark_id,
        "label": label,
        "selection_basis": selection_basis,
        "board": {"x": board[0], "y": board[1]},
        "image": {"x": image[0], "y": image[1]},
    }


def page_one_review():
    return build_review(
        solve_anchors=[
            pair("outline_upper_left", "Upper-left board outline", (0.09625, 0.083744), (0.105062, 0.156449), "reviewed_outline_correspondence"),
            pair("outline_upper_right", "Upper-right board outline", (0.931875, 0.10936), (0.902898, 0.161469), "reviewed_outline_correspondence"),
            pair("outline_lower_right", "Lower-right board outline", (0.9075, 0.976355), (0.89563, 0.871184), "reviewed_outline_correspondence"),
            pair("outline_lower_left", "Lower-left board outline", (0.06625, 0.971429), (0.050409, 0.868123), "reviewed_outline_correspondence"),
        ],
        independent_check_points=[
            pair("j6205_center", "J6205 connector center", (0.49, 0.36), (0.475, 0.35)),
            pair("hole2_center", "HOLE2 center", (0.47, 0.93), (0.465, 0.82)),
            pair("hole3_center", "HOLE3 center", (0.70, 0.49), (0.68, 0.46)),
            pair("u5007_region_center", "U5007 package region center", (0.735, 0.155), (0.70, 0.20)),
        ],
        selection_basis="reviewed_outline_correspondence",
        review_note=(
            "The rotated full-board image was aligned to the engineering outline and checked "
            "against two mechanical holes, J6205, and the U5007 package region."
        ),
    )


def page_two_review():
    return build_review(
        solve_anchors=[
            pair("j6201_contact_center", "J6201 contact-field center", (0.349, 0.366), (0.34, 0.42)),
            pair("u4002_package_center", "U4002 package center", (0.212, 0.681), (0.236, 0.687)),
            pair("j2810_connector_center", "J2810 connector center", (0.85, 0.876), (0.807, 0.852)),
            pair("outline_upper_right", "Upper-right board outline", (0.96875, 0.127985), (0.872373, 0.21805), "outline_assisted_estimate"),
        ],
        independent_check_points=[
            pair("j6402_connector_center", "J6402 connector center", (0.665, 0.875), (0.66, 0.845)),
            pair("u2001_package_center", "U2001 package center", (0.548, 0.538), (0.552, 0.589)),
            pair("wpl1001_center", "WPL1001 circular landmark center", (0.093, 0.414), (0.116, 0.477)),
        ],
        selection_basis="reviewed_component_and_outline_correspondence",
        review_note=(
            "The exposed full-board image was aligned from three visible package or connector "
            "centers plus the upper-right outline. Independent checks retain the photographed "
            "V1.0 versus engineering V1.0B population boundary."
        ),
    )


def build_manifest():
    page_two = page_two_review()
    page_one = page_one_review()
    images = [
        {
            "sha256": "1a3e4bdb3f5019656cd0910544e4f825b0eb94c3f85bf6668c956cd6a757687d",
            "side_id": "main_page_2",
            "source_dimensions": {"width": 4032, "height": 3024},
            "registration_transform": "none",
            "registration_dimensions": {"width": 4032, "height": 3024},
            "capture_geometry_id": "XK67J-KM4N-PAGE2-CAPTURE-01",
            "view_scope": "full_board_repair_case",
            "source_annotation_present": True,
            "source_annotation_role": "source_component_callout_not_system_label",
            "automatic_registration": {
                "status": "failed",
                "failure_code": "low_inlier_count",
                "attempts": [
                    {"detector": "orb", "matches": 45, "inliers": 10, "inlier_ratio": 0.222222, "failure_code": "low_inlier_ratio"},
                    {"detector": "akaze", "matches": 40, "inliers": 4, "inlier_ratio": 0.1, "failure_code": "low_inlier_count"},
                ],
            },
            "registration_status": "reviewed_manual_registration",
            "registration_review": copy.deepcopy(page_two),
        },
        {
            "sha256": "28a193f9bbd0750240fb20477f5ec0497de7f279868b408eab7c872dcd0273d6",
            "side_id": "main_page_2",
            "source_dimensions": {"width": 4032, "height": 3024},
            "registration_transform": "none",
            "registration_dimensions": {"width": 4032, "height": 3024},
            "capture_geometry_id": "XK67J-KM4N-PAGE2-CAPTURE-01",
            "view_scope": "full_board_repair_case",
            "source_annotation_present": True,
            "source_annotation_role": "source_component_callout_not_system_label",
            "automatic_registration": {
                "status": "failed",
                "failure_code": "low_inlier_count",
                "attempts": [
                    {"detector": "orb", "matches": 54, "inliers": 20, "inlier_ratio": 0.37037, "failure_code": "invalid_projected_shape"},
                    {"detector": "akaze", "matches": 45, "inliers": 3, "inlier_ratio": 0.066667, "failure_code": "low_inlier_count"},
                ],
            },
            "registration_status": "reviewed_manual_registration",
            "registration_review": copy.deepcopy(page_two),
        },
        {
            "sha256": "57a9b1d36326cd0a0b1cee3a0bc622290728cbb1b4775cfab5182b9b84138fa6",
            "side_id": "main_page_1",
            "source_dimensions": {"width": 3024, "height": 4032},
            "registration_transform": "rotate_90_counterclockwise",
            "registration_dimensions": {"width": 4032, "height": 3024},
            "capture_geometry_id": "XK67J-KM4N-PAGE1-CAPTURE-01-ROTATED-CCW",
            "view_scope": "full_board_repair_case",
            "source_annotation_present": False,
            "source_annotation_role": None,
            "automatic_registration": {
                "status": "failed",
                "failure_code": "low_inlier_count",
                "attempts": [
                    {"detector": "orb", "matches": 22, "inliers": 4, "inlier_ratio": 0.181818, "failure_code": "low_inlier_count"},
                    {"detector": "akaze", "matches": 30, "inliers": 5, "inlier_ratio": 0.166667, "failure_code": "low_inlier_count"},
                ],
            },
            "registration_status": "reviewed_manual_registration",
            "registration_review": page_one,
        },
    ]
    return {
        "schema_version": "XK67J-PHYSICAL-REGISTRATION-REVIEW-V1",
        "review_id": "XK67J-KM4N-REGISTRATION-REVIEW-20260731",
        "board_key": "xk67j-shared",
        "board_id": "BOARD-XK67J-MAIN-V1.0B",
        "physical_board_revision": "XK67J_MAIN V1.0",
        "engineering_board_revision": "XK67J_MAIN_PCB V1.0B",
        "status": "reviewed_board_coordinate_registration",
        "threshold_policy": "no_industrial_pass_threshold_declared",
        "field_accuracy_claim_allowed": False,
        "images": images,
        "downstream_admission": {
            "golden_sample": False,
            "defect_label": False,
            "training_data": False,
            "repair_causality": False,
        },
        "accuracy_boundary": (
            "Reviewed registration supports board-coordinate association for these exact image "
            "hashes. It does not establish V1.0/V1.0B population equality, industrial accuracy, "
            "a normal-board Golden Sample, a visible defect, training admission, or repair causality."
        ),
    }


def main():
    manifest = build_manifest()
    output = ROOT / "knowledge-base/xk67j-physical-registration-reviewed.json"
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"images": len(manifest["images"]), "status": manifest["status"]}))


if __name__ == "__main__":
    main()
