import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_h897_physical_registration import build_manifest as build_physical_registration
SCHEMATIC = "H897_MAIN_SCH_V1.2_202307171706.pdf"


def _case(
    case_id,
    record_id,
    symptoms,
    finding,
    photo_sha256,
    *,
    navigation_scope="board_only",
    candidate_component_ids=None,
    candidate_basis="source_case_has_no_exact_reviewed_designator",
):
    return {
        "case_id": case_id,
        "source_record_id": record_id,
        "symptoms": symptoms,
        "reported_finding": finding,
        "photo_sha256": photo_sha256,
        "navigation_scope": navigation_scope,
        "candidate_component_ids": candidate_component_ids or [],
        "candidate_basis": candidate_basis,
        "source_annotation_role": "source_case_context_not_system_diagnosis",
        "repair_causality_claim_allowed": False,
        "defect_label_allowed": False,
        "boundary": (
            "此来源案例仅用于板级或模块候选导航；资料未提供经审核的电气标准、"
            "可执行维修动作、通用因果或视觉缺陷标签。"
        ),
    }


def _case_navigation():
    cases = [
        _case(
            "CASE-008-KJ6", "recvq1622otvtN", ["摄像头异常"], "Three rows resistors bad",
            ["6915613106c8d912c87a5815e833774bc13ea2c8bdd21855352631eb8a673e77", "fa1055e69a47806cda43ec7ec09d6ef961adf02f2f7e98910b43d0cffacf56ea"],
            navigation_scope="component_group_candidate",
            candidate_component_ids=["H897-MAIN-J6202", "H897-MAIN-J6204", "H897-MAIN-J6210"],
            candidate_basis="symptom_to_schematic_camera_interconnect_group_only",
        ),
        _case("CASE-009-KJ6", "recvq162ggDrBn", ["不开机"], "Charging connector bad", ["827681e4835e0f79a5b6a6d680ec38a614080b4eb8ed4aa469db6efeb33e3cd4", "6915613106c8d912c87a5815e833774bc13ea2c8bdd21855352631eb8a673e77"]),
        _case("CASE-0010-KJ6", "recvq1SdKg9cNB", ["音频异常"], "Power bad", ["827681e4835e0f79a5b6a6d680ec38a614080b4eb8ed4aa469db6efeb33e3cd4", "5fe76e7d39b5a992ca16d4b4f8327f2bd01fef3a9ffad7fa70c85032c70de788"]),
        _case(
            "CASE-0011-KJ6", "recvq1SdYD7L0P", ["不开机"], "CPU bad",
            ["10a4cf0297ea162de4bf31121a3321fe8c78e8312fd63676234add19a54b2be1", "0bf4e68ba445f7907bd9e4716991faafc18e2bed7e3094a906401466da9c0ff8"],
            navigation_scope="component_candidate",
            candidate_component_ids=["H897-MAIN-U1001"],
            candidate_basis="source_CPU_term_to_exact_schematic_main_processor_designator",
        ),
        _case("CASE-0012", "recvqj9TvqHUlX", ["不开机"], "EMMC坏", ["b5d638f44fc3f78e496ad09ff65be63d1c7d21269037f8ffeb906601b01fbb4b", "5b8ffe55f4a2c285e4d85fcddc9acdbb459e8d1ed3760a0370a807617e476f48"]),
        _case("CASE-0013", "recvqj9TK9CfTh", ["无法充电"], "充电IC坏", ["e938724504f5d34d7513d68f24df041a77f2b5f1e4777670c6fed3e32e0ec2cb", "5b8ffe55f4a2c285e4d85fcddc9acdbb459e8d1ed3760a0370a807617e476f48"]),
        _case("CASE-0014", "recvqj9UBS16Dp", ["连接器损坏", "不开机"], "电池排扣坏", ["1fb4ccb4bdad50e0470312158cf0f4347fc23457fdec168a823e6de1093d109b", "e6f86bf8890651ca07bfb6d1c468aab04345ba6376b3f605a4d45c059178d666", "5b8ffe55f4a2c285e4d85fcddc9acdbb459e8d1ed3760a0370a807617e476f48"]),
        _case("CASE-0015", "recvqj9UQZgp7W", ["不开机", "连接器损坏"], "电池排扣坏", ["1fb4ccb4bdad50e0470312158cf0f4347fc23457fdec168a823e6de1093d109b", "e6f86bf8890651ca07bfb6d1c468aab04345ba6376b3f605a4d45c059178d666", "5b8ffe55f4a2c285e4d85fcddc9acdbb459e8d1ed3760a0370a807617e476f48"]),
        _case("CASE-0016", "recvqj9V73k84B", ["不开机", "连接器损坏"], "电池排扣坏", ["1fb4ccb4bdad50e0470312158cf0f4347fc23457fdec168a823e6de1093d109b", "e6f86bf8890651ca07bfb6d1c468aab04345ba6376b3f605a4d45c059178d666", "5b8ffe55f4a2c285e4d85fcddc9acdbb459e8d1ed3760a0370a807617e476f48"]),
        _case(
            "CASE-0017", "recvqj9Vnpz9Fa", ["重启 / 卡 logo"], "DDR坏",
            ["0eab68987cfce1aec8bdeb53969d87d8e9fbc861645886000520e3f049f29f36", "a862ecee11e683562ccfdc9a7743d813accfd37235e0267665bf32b44d9fe491"],
            navigation_scope="component_group_candidate",
            candidate_component_ids=["H897-MAIN-U4101", "H897-MAIN-U4102"],
            candidate_basis="source_DDR_term_to_exact_schematic_LPDDR4_designator_group",
        ),
        _case("CASE-0018", "recvqj9VDPYIx5", ["音频异常"], "电源坏", ["e938724504f5d34d7513d68f24df041a77f2b5f1e4777670c6fed3e32e0ec2cb", "5b8ffe55f4a2c285e4d85fcddc9acdbb459e8d1ed3760a0370a807617e476f48"]),
        _case(
            "CASE-0019", "recvqj9VWYmIf3", ["摄像头异常"], "后摄像头排扣坏",
            ["37eecca8dc343a2913c66728e1e741973ba1bcf0340b22215219b9929c32fd87", "5b8ffe55f4a2c285e4d85fcddc9acdbb459e8d1ed3760a0370a807617e476f48"],
            navigation_scope="component_group_candidate",
            candidate_component_ids=["H897-MAIN-J6202", "H897-MAIN-J6204"],
            candidate_basis="source_rear_camera_connector_term_to_schematic_camera_connector_group_only",
        ),
        _case("CASE-0020", "recvqjaM96kkqn", ["无显示"], "显示IC坏", ["5fe76e7d39b5a992ca16d4b4f8327f2bd01fef3a9ffad7fa70c85032c70de788", "827681e4835e0f79a5b6a6d680ec38a614080b4eb8ed4aa469db6efeb33e3cd4"]),
    ]
    unique_hashes = {digest for case in cases for digest in case["photo_sha256"]}
    gaps = [
        ("probe_location", "探针或检查位置", "Cannot reproduce the reported check."),
        ("tool_and_mode", "工具与档位", "Cannot reproduce measurement conditions."),
        ("measured_value", "测量值", "No auditable electrical result."),
        ("reference_or_tolerance", "参考值或容差", "No source-backed pass/fail judgment."),
        ("branch_logic", "结果分支", "Cannot create an executable diagnostic path."),
        ("repair_action_detail", "维修动作细节", "Cannot prescribe a reviewed action."),
        ("post_repair_recheck", "维修后复检", "Cannot verify outcome beyond the reported case state."),
    ]
    return {
        "schema_version": "H897-CASE-NAVIGATION-V1",
        "source": "Feishu Base Bf57b8mpsatj7isYrmxcQwNXnQe / 案例登记与照片清单",
        "source_table_id": "tblSbfji4q1ifubV",
        "photo_table_id": "tblrB8Q4YrMPuJk9",
        "case_count": len(cases),
        "unique_photo_count": len(unique_hashes),
        "cases": cases,
        "missing_fields": [
            {"field_id": field_id, "label": label, "missing_case_count": len(cases), "impact": impact}
            for field_id, label, impact in gaps
        ],
        "duplicate_policy": "same_sha256_is_one_physical_image_stream_across_cases",
        "boundary": (
            "案例导航仅展示来源记录的故障现象和谨慎限定的模块候选；"
            "不据此生成缺陷标签、电气阈值、维修动作或因果结论。"
        ),
    }


def _read_json(root, path):
    return json.loads((root / path).read_text(encoding="utf-8"))


def _component_index(*datasets):
    return {
        component["designator"]: (dataset["side_id"], component)
        for dataset in datasets
        for component in dataset["components"]
    }


def _schematic_link(schematic, designator, facts):
    pages = sorted({item["page"] for item in schematic["components"][designator]})
    return [
        {
            "source": SCHEMATIC,
            "page": ", ".join(str(page) for page in pages),
            "facts": [f"Exact schematic designator {designator}", *facts],
        }
    ]


def _entity(
    components,
    schematic,
    designator,
    *,
    name,
    category,
    module,
    facts,
    shape="square",
):
    side_id, component = components[designator]
    return {
        "component_id": f"H897-MAIN-{designator}",
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
        "schematic_links": _schematic_link(schematic, designator, facts),
        "repair_links": [],
        "visual_profile": {
            "shape": shape,
            "height": 0.02 if shape == "rectangle" else 0.035,
            "engineering_dimension": False,
        },
    }


def build_dataset(root=ROOT):
    page_one = _read_json(root, "knowledge-base/h897-board-compiled-page-1.json")
    page_two = _read_json(root, "knowledge-base/h897-board-compiled-page-2.json")
    schematic = _read_json(root, "knowledge-base/h897-schematic-compiled.json")
    photo_navigation = _read_json(root, "knowledge-base/h897-photo-navigation.json")
    components = _component_index(page_one, page_two)

    specs = [
        ("U1001", "MT6789 main processor", "bga_ic", "Main processor", ["MT6789 source page family"]),
        ("U2001", "MT6366MW/A power management IC", "bga_ic", "Power management", ["MT6366MW/A"]),
        ("X2101", "OZ26030001 crystal", "crystal", "System clock", ["OZ26030001", "XTAL1"]),
        ("U3001", "MT6186MV/AXD RF transceiver", "bga_ic", "RF transceiver", ["MT6186MV/AXD"]),
        ("U3101", "L/M/H RF power amplifier", "ic", "RF power amplifier", ["L/M/H PA"]),
        ("U3201", "RF receive-path device U3201", "ic", "RF receive path", ["RF_MT6186M_RF_PRX"]),
        ("U4101", "LPDDR4 memory package U4101", "bga_ic", "Memory", ["MEM_DSC_LPDDR4x", "LPDDR4_200B"]),
        ("U4102", "LPDDR4 memory package U4102", "bga_ic", "Memory", ["MEM_DSC_LPDDR4x", "LPDDR4_200B"]),
        ("U5003", "MT6631 connectivity IC", "ic", "Wireless connectivity", ["CONNECTIVITY_MT6631"]),
        ("U6000", "FS1559SN audio amplifier", "ic", "Audio amplifier", ["FS1559SN", "Audio PA"]),
        ("J6101", "LCM and touch connector", "connector", "Display interconnect", ["PERI_LCM_CTP_FP"]),
        ("J6202", "Camera connector J6202", "connector", "Camera interconnect", ["PERI_CAMERA_I"]),
        ("J6204", "Camera connector J6204", "connector", "Camera interconnect", ["PERI_CAMERA_I"]),
        ("J6210", "Front camera connector", "connector", "Camera interconnect", ["PERI_CAMERA_III", "FRONT MAIN CAMERA"]),
        ("U6601", "PN557 NFC controller", "ic", "NFC", ["PN557", "PERI_NFC"]),
    ]
    entities = [
        _entity(
            components,
            schematic,
            designator,
            name=name,
            category=category,
            module=module,
            facts=facts,
            shape="rectangle" if category == "connector" else "square",
        )
        for designator, name, category, module, facts in specs
    ]
    physical = build_physical_registration()
    case_navigation = _case_navigation()

    return {
        "dataset_id": "H897-MAIN-XREG-20260802",
        "board_id": page_one["board_id"],
        "model": "KJ6",
        "compatible_models": ["KJ6"],
        "model_evidence": {"KJ6": "engineering_source"},
        "board_version": "H897_MAIN_PCB_V1.2",
        "side_id": "main_page_1",
        "coordinate_system": "normalized_board_plane",
        "status": "source_compiled_with_reviewed_physical_navigation",
        "board_outline": page_one["board_outline"],
        "registration": {
            "reference_mode": "reviewed_physical_photo_navigation",
            "point_map_image": "assets/board-atlas/h897/main-point-map-page-1.png",
            "point_map_source": "H897_MAIN_PCB_V1.2 Placement page 1",
            "point_map_note": "H897 V1.2 双面 Placement 已编译；两张精确哈希实拍已完成板级坐标审核配准。",
            "method": "normalized_point_map_registration",
            "confidence": "source_compiled",
            "photo_navigation": photo_navigation,
        },
        "physical_evidence": {
            "status": physical["status"],
            "board_revision": physical["physical_board_revision"],
            "engineering_board_revision": physical["engineering_board_revision"],
            "source_scope": "owner_authorized_feishu_case_library",
            "threshold_policy": physical["threshold_policy"],
            "unique_image_sha256": [item["sha256"] for item in physical["images"]],
            "images": physical["images"],
            "downstream_admission": physical["downstream_admission"],
            "accuracy_boundary": physical["accuracy_boundary"],
        },
        "repair_coverage": {
            "status": "source_available_pending_review",
            "title": "案例可导航，检测步骤资料不足",
            "note": "当前可查询 15 个来源关联器件及 13 条案例；案例仅支持板级或模块候选导航，不能生成维修动作。",
            "source": "Feishu Base Bf57b8mpsatj7isYrmxcQwNXnQe KJ6/H897 cases and owner-supplied H897 V1.2 engineering sources",
        },
        "repair_flows": [],
        "case_navigation": case_navigation,
        "entities": entities,
        "boundaries": {
            "visual_defect_confirmed": False,
            "golden_approved": False,
            "training_label_allowed": False,
            "repair_causality_confirmed": False,
            "repair_instruction_allowed": False,
            "field_accuracy_claim_allowed": False,
        },
    }


def main():
    payload = build_dataset(ROOT)
    output = ROOT / "knowledge-base/h897-cross-source-registration.json"
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"entities": len(payload["entities"]), "repair_flows": 0}))


if __name__ == "__main__":
    main()
