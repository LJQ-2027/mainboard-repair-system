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
            pair("outline_upper_left", "Upper-left board outline", (0.055, 0.20), (0.01, 0.14), "reviewed_outline_correspondence"),
            pair("outline_upper_right", "Upper-right board outline", (0.954, 0.20), (0.925, 0.13), "reviewed_outline_correspondence"),
            pair("outline_lower_right", "Lower-right board outline", (0.955, 0.952), (0.95, 0.91), "reviewed_outline_correspondence"),
            pair("outline_lower_left", "Lower-left board outline", (0.045, 0.795), (0.005, 0.82), "reviewed_outline_correspondence"),
        ],
        independent_check_points=[
            pair("j6210_center", "J6210 connector center", (0.501326, 0.436234), (0.468, 0.385)),
            pair("upper_shield_hole", "Upper shield mechanical hole", (0.697, 0.287), (0.691, 0.21)),
            pair("sim_cage_upper_left", "SIM cage upper-left corner", (0.065, 0.535), (0.02, 0.51)),
        ],
        selection_basis="reviewed_outline_and_visible_mechanical_correspondence",
        review_note=(
            "The EXIF-normalized photograph was rotated counterclockwise and aligned to the "
            "Placement page-1 outline. J6210 and two independent visible mechanical landmarks "
            "were used only to check board-coordinate association."
        ),
    )


def page_two_review():
    return build_review(
        solve_anchors=[
            pair("outline_upper_left", "Upper-left board outline", (0.05, 0.23), (0.055, 0.16), "reviewed_outline_correspondence"),
            pair("outline_upper_right", "Upper-right board outline", (0.95, 0.235), (0.965, 0.17), "reviewed_outline_correspondence"),
            pair("outline_lower_right", "Lower-right board outline", (0.96, 0.94), (0.96, 0.94), "reviewed_outline_correspondence"),
            pair("outline_lower_left", "Lower-left board outline", (0.05, 0.93), (0.06, 0.91), "reviewed_outline_correspondence"),
        ],
        independent_check_points=[
            pair("j6204_center", "J6204 connector center", (0.369571, 0.460008), (0.386, 0.436)),
            pair("j6101_center", "J6101 connector center", (0.390593, 0.906658), (0.356, 0.908)),
            pair("j6401_center", "J6401 connector center", (0.597696, 0.906658), (0.605, 0.91)),
            pair("j2801_center", "J2801 connector center", (0.716225, 0.906658), (0.718, 0.91)),
        ],
        selection_basis="reviewed_outline_and_visible_connector_correspondence",
        review_note=(
            "The full-board photograph was aligned to the Placement page-2 outline and checked "
            "against four visible connectors. Shielded package identities were not used as "
            "registration evidence."
        ),
    )


def build_manifest():
    return {
        "schema_version": "H897-PHYSICAL-REGISTRATION-REVIEW-V1",
        "review_id": "H897-KJ6-REGISTRATION-REVIEW-20260802",
        "board_key": "kj6-h897",
        "board_id": "BOARD-H897-MAIN-V1.2",
        "physical_board_revision": "H897 V1.2",
        "engineering_board_revision": "H897_MAIN_PCB_V1.2",
        "status": "reviewed_board_coordinate_registration",
        "threshold_policy": "no_industrial_pass_threshold_declared",
        "field_accuracy_claim_allowed": False,
        "images": [
            {
                "sha256": "5b8ffe55f4a2c285e4d85fcddc9acdbb459e8d1ed3760a0370a807617e476f48",
                "side_id": "main_page_1",
                "source_dimensions": {"width": 3024, "height": 4032},
                "registration_transform": "rotate_90_counterclockwise",
                "registration_dimensions": {"width": 4032, "height": 3024},
                "capture_geometry_id": "H897-KJ6-PAGE1-CAPTURE-01-ROTATED-CCW",
                "view_scope": "full_board_repair_case",
                "source_annotation_present": False,
                "source_annotation_role": None,
                "automatic_registration": {
                    "status": "not_used",
                    "reason": "reviewed_manual_registration_selected_for_first_exact_hash_pair",
                },
                "registration_status": "reviewed_manual_registration",
                "registration_review": page_one_review(),
            },
            {
                "sha256": "a862ecee11e683562ccfdc9a7743d813accfd37235e0267665bf32b44d9fe491",
                "side_id": "main_page_2",
                "source_dimensions": {"width": 4032, "height": 3024},
                "registration_transform": "none",
                "registration_dimensions": {"width": 4032, "height": 3024},
                "capture_geometry_id": "H897-KJ6-PAGE2-CAPTURE-01",
                "view_scope": "full_board_repair_case",
                "source_annotation_present": False,
                "source_annotation_role": None,
                "automatic_registration": {
                    "status": "not_used",
                    "reason": "reviewed_manual_registration_selected_for_first_exact_hash_pair",
                },
                "registration_status": "reviewed_manual_registration",
                "registration_review": page_two_review(),
            },
        ],
        "downstream_admission": {
            "golden_sample": False,
            "defect_label": False,
            "training_data": False,
            "repair_causality": False,
        },
        "accuracy_boundary": (
            "Reviewed registration supports board-coordinate navigation for these exact image "
            "hashes. It does not establish industrial measurement accuracy, a normal-board "
            "Golden Sample, a defect label, training admission, or repair causality."
        ),
    }


def main():
    manifest = build_manifest()
    output = ROOT / "knowledge-base/h897-physical-registration-reviewed.json"
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"images": len(manifest["images"]), "status": manifest["status"]}))


if __name__ == "__main__":
    main()
