import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = "XK67J_L6735-KM5_MAIN_SCH_V1.0B.pdf"
MODELS = ["KM4n", "KM4k", "KM5", "KM5n", "KM5s"]
MODEL_EVIDENCE = {
    "KM4n": "photo_verified_shared_platform",
    "KM4k": "owner_confirmed_alias",
    "KM5": "engineering_source",
    "KM5n": "owner_confirmed_alias",
    "KM5s": "owner_confirmed_alias",
}


def _read_json(root, path):
    return json.loads((root / path).read_text(encoding="utf-8"))


def _component_index(*datasets):
    return {
        component["designator"]: (dataset["side_id"], component)
        for dataset in datasets
        for component in dataset["components"]
    }


def _schematic_link(schematic, designator):
    pages = sorted({item["page"] for item in schematic["components"][designator]})
    return [
        {
            "source": SCHEMATIC,
            "page": ", ".join(str(page) for page in pages),
            "facts": [f"Exact schematic designator {designator}"],
        }
    ]


def _entity(components, schematic, designator, *, name, category, module, shape="square"):
    side_id, component = components[designator]
    return {
        "component_id": f"XK67J-MAIN-{designator}",
        "designator": designator,
        "name": name,
        "category": category,
        "module": module,
        "side_id": side_id,
        "proxy_visibility": "point_map_only",
        "geometry": {
            "center": component["center"],
            "size": {"x": 0.025, "y": 0.025},
            "rotation": 0,
            "source_status": "location_only",
        },
        "schematic_links": _schematic_link(schematic, designator),
        "repair_links": [],
        "visual_profile": {
            "shape": shape,
            "height": 0.02 if shape == "rectangle" else 0.035,
            "engineering_dimension": False,
        },
    }


def build_dataset(root=ROOT):
    page_one = _read_json(root, "knowledge-base/xk67j-board-compiled-page-1.json")
    page_two = _read_json(root, "knowledge-base/xk67j-board-compiled-page-2.json")
    schematic = _read_json(root, "knowledge-base/xk67j-schematic-compiled.json")
    components = _component_index(page_one, page_two)
    entities = [
        _entity(
            components,
            schematic,
            "U1001",
            name="Main processor",
            category="bga_ic",
            module="Processor",
        ),
        _entity(
            components,
            schematic,
            "U2001",
            name="MT6358W/A power management IC",
            category="bga_ic",
            module="Power management",
        ),
        _entity(
            components,
            schematic,
            "U3001",
            name="MT6177M RF transceiver",
            category="bga_ic",
            module="RF transceiver",
        ),
        _entity(
            components,
            schematic,
            "U3101",
            name="RR88643-31M RF power amplifier",
            category="ic",
            module="RF power amplifier",
        ),
        _entity(
            components,
            schematic,
            "U4001",
            name="LPDDR4 memory",
            category="bga_ic",
            module="Memory",
        ),
        _entity(
            components,
            schematic,
            "U4002",
            name="eMMC storage",
            category="bga_ic",
            module="Storage",
        ),
        _entity(
            components,
            schematic,
            "U5007",
            name="MT6631N wireless connectivity IC",
            category="ic",
            module="Wireless connectivity",
        ),
        _entity(
            components,
            schematic,
            "X2101",
            name="OZ26000004 crystal",
            category="crystal",
            module="System clock",
        ),
        _entity(
            components,
            schematic,
            "J2810",
            name="Battery connector",
            category="connector",
            module="Battery interconnect",
            shape="rectangle",
        ),
        _entity(
            components,
            schematic,
            "J6102",
            name="LCM and touch interconnect",
            category="connector",
            module="Display interconnect",
            shape="rectangle",
        ),
        _entity(
            components,
            schematic,
            "J6402",
            name="USB sub-board interconnect",
            category="connector",
            module="USB interconnect",
            shape="rectangle",
        ),
        _entity(
            components,
            schematic,
            "J6501",
            name="SIM connector",
            category="connector",
            module="SIM interconnect",
            shape="rectangle",
        ),
    ]
    return {
        "dataset_id": "XK67J-MAIN-XREG-20260731",
        "board_id": page_two["board_id"],
        "model": "KM5",
        "compatible_models": MODELS,
        "model_evidence": MODEL_EVIDENCE,
        "board_version": "XK67J_MAIN_PCB_V1.0B",
        "physical_board_revision": "XK67J_MAIN V1.0",
        "side_id": "main_page_2",
        "coordinate_system": "normalized_board_plane",
        "status": "source_compiled_reference_only",
        "board_outline": page_two["board_outline"],
        "registration": {
            "reference_mode": "point_map_only",
            "point_map_image": "assets/board-atlas/xk67j/main-point-map-page-2.png",
            "point_map_source": "XK67J_MAIN_PCB_V1.0B Placement page 2",
            "point_map_note": "XK67J V1.0B 第2面点位图；KM4n V1.0 实拍已保存，但尚未进入审核配准。",
            "method": "normalized_point_map_registration",
            "confidence": "source_compiled",
        },
        "physical_evidence": {
            "status": "preserved_pending_reviewed_registration",
            "board_revision": "XK67J_MAIN V1.0",
            "source_scope": "owner_authorized_feishu_case_library",
            "unique_image_sha256": [
                "1a3e4bdb3f5019656cd0910544e4f825b0eb94c3f85bf6668c956cd6a757687d",
                "28a193f9bbd0750240fb20477f5ec0497de7f279868b408eab7c872dcd0273d6",
                "57a9b1d36326cd0a0b1cee3a0bc622290728cbb1b4775cfab5182b9b84138fa6",
            ],
            "images": [
                {
                    "sha256": "1a3e4bdb3f5019656cd0910544e4f825b0eb94c3f85bf6668c956cd6a757687d",
                    "side_id": "main_page_2",
                    "view_scope": "full_board_repair_case",
                    "source_annotation_present": True,
                    "registration_status": "manual_registration_required",
                    "automatic_failure_code": "low_inlier_count",
                    "automatic_attempts": [
                        {
                            "detector": "orb",
                            "matches": 45,
                            "inliers": 10,
                            "inlier_ratio": 0.222222,
                            "failure_code": "low_inlier_ratio",
                        },
                        {
                            "detector": "akaze",
                            "matches": 40,
                            "inliers": 4,
                            "inlier_ratio": 0.1,
                            "failure_code": "low_inlier_count",
                        },
                    ],
                },
                {
                    "sha256": "57a9b1d36326cd0a0b1cee3a0bc622290728cbb1b4775cfab5182b9b84138fa6",
                    "side_id": "main_page_1",
                    "view_scope": "full_board_repair_case",
                    "source_annotation_present": False,
                    "registration_status": "manual_registration_required",
                    "automatic_failure_code": "low_inlier_count",
                    "automatic_attempts": [
                        {
                            "detector": "orb",
                            "matches": 22,
                            "inliers": 4,
                            "inlier_ratio": 0.181818,
                            "failure_code": "low_inlier_count",
                        },
                        {
                            "detector": "akaze",
                            "matches": 30,
                            "inliers": 5,
                            "inlier_ratio": 0.166667,
                            "failure_code": "low_inlier_count",
                        },
                    ],
                },
                {
                    "sha256": "28a193f9bbd0750240fb20477f5ec0497de7f279868b408eab7c872dcd0273d6",
                    "side_id": "main_page_2",
                    "view_scope": "full_board_repair_case",
                    "source_annotation_present": True,
                    "registration_status": "manual_registration_required",
                    "automatic_failure_code": "low_inlier_count",
                    "automatic_attempts": [
                        {
                            "detector": "orb",
                            "matches": 54,
                            "inliers": 20,
                            "inlier_ratio": 0.37037,
                            "failure_code": "invalid_projected_shape",
                        },
                        {
                            "detector": "akaze",
                            "matches": 45,
                            "inliers": 3,
                            "inlier_ratio": 0.066667,
                            "failure_code": "low_inlier_count",
                        },
                    ],
                },
            ],
            "accuracy_boundary": "Preserved repair-case photos are not yet reviewed registrations, Golden Samples, defect labels, or training rows.",
        },
        "repair_coverage": {
            "status": "source_unavailable",
            "title": "暂无可执行维修流程",
            "note": "当前 XK67J 资料仅支持点位、器件类别和原理图索引；未提供经审核的机型维修步骤，系统不会生成维修动作。",
        },
        "repair_flows": [],
        "entities": entities,
    }


def main():
    payload = build_dataset(ROOT)
    output = ROOT / "knowledge-base/xk67j-cross-source-registration.json"
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"entities": len(payload["entities"]), "repair_flows": 0}))


if __name__ == "__main__":
    main()
