import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_xk67j_physical_registration import build_manifest as build_physical_registration
SCHEMATIC = "XK67J_L6735-KM5_MAIN_SCH_V1.0B.pdf"
MODELS = ["KM4n", "KM4k", "KM5", "KM5n", "KM5s"]
MODEL_EVIDENCE = {
    "KM4n": "photo_verified_shared_platform",
    "KM4k": "owner_confirmed_alias",
    "KM5": "engineering_source",
    "KM5n": "owner_confirmed_alias",
    "KM5s": "owner_confirmed_alias",
}
NO_DISPLAY_PHOTO_SHA256 = "28a193f9bbd0750240fb20477f5ec0497de7f279868b408eab7c872dcd0273d6"


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


def _no_display_case_evidence():
    return {
        "evidence_id": "XK67J-KM4N-NO-DISPLAY-CASES-20260731",
        "source": "Feishu Base Bf57b8mpsatj7isYrmxcQwNXnQe",
        "source_table_id": "tblSbfji4q1ifubV",
        "fault": "No display",
        "source_symptom": "无显示",
        "source_finding": "显示IC坏",
        "cases": [
            {
                "case_id": "CASE-0022",
                "source_record_id": "recvqMNGR4Fra2",
                "board": "XK67J/1.0",
                "model": "TECNO/KM4n",
                "board_state": "维修后已修复",
            },
            {
                "case_id": "CASE-0025",
                "source_record_id": "recvqMNS2NdKDB",
                "board": "XK67J/1.0",
                "model": "TECNO/KM4n",
                "board_state": "维修后已修复",
            },
        ],
        "source_photo_record_id": "recvqMSU2K5nvW",
        "source_photo_sha256": NO_DISPLAY_PHOTO_SHA256,
        "source_annotation_role": "source_component_callout_not_system_diagnosis",
        "reviewed_target_component_id": "XK67J-MAIN-U2411",
        "reviewed_target_method": "annotation_center_inverse_projection",
        "repair_causality_claim_allowed": False,
        "boundary": (
            "The cases support prioritised U2411 navigation only. They do not provide "
            "an electrical test standard, pass/fail threshold, repair action, or universal causality."
        ),
    }


def _no_display_flow(evidence):
    return {
        "flow_id": "xk67j-no-display-u2411-location-check",
        "entry_label": "无显示",
        "entry_order": 1,
        "entry_type": "known_fault",
        "title": "XK67J 无显示 · U2411 定位核对",
        "fault": "No display",
        "entry_component_id": "XK67J-MAIN-U2411",
        "entry_step_id": "u2411_location_check",
        "source": {
            "source": "CASE-0022 / CASE-0025 + XK67J_L6735-KM5_MAIN_SCH_V1.0B.pdf",
            "page": "case records / SCH 9",
        },
        "source_status": "reviewed_partial",
        "source_photo_sha256": evidence["source_photo_sha256"],
        "source_case_ids": [case["case_id"] for case in evidence["cases"]],
        "boundary_note": "现有资料支持 U2411 定位与案例关联，不含 XK67J 电气检测标准或维修动作。",
        "steps": [
            {
                "step_id": "u2411_location_check",
                "label": "U2411 位置核对",
                "prompt": "实物板与图中 U2411（显示偏压 IC）位置是否一致？",
                "target_component_id": "XK67J-MAIN-U2411",
                "choices": [
                    {
                        "value": "location_match",
                        "label": "位置一致",
                        "outcome": {
                            "kind": "boundary",
                            "label": "已完成 U2411 定位；继续检测需补充 XK67J 审核版电气测试标准。",
                            "target_component_id": "XK67J-MAIN-U2411",
                        },
                    },
                    {
                        "value": "location_unconfirmed",
                        "label": "无法确认",
                        "outcome": {
                            "kind": "boundary",
                            "label": "停止排查；请先复核主板型号、版本与板面。",
                            "target_component_id": "XK67J-MAIN-U2411",
                        },
                    },
                ],
            }
        ],
    }


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
    photo_navigation = _read_json(root, "knowledge-base/xk67j-photo-navigation.json")
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
            "U2411",
            name="OCP2130WPAD-G LCM bias IC",
            category="ic",
            module="Display bias",
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
    no_display_evidence = _no_display_case_evidence()
    u2411 = next(entity for entity in entities if entity["designator"] == "U2411")
    u2411["schematic_links"][0]["facts"] = [
        "Exact schematic designator U2411",
        "Part marking OCP2130WPAD-G",
        "LCM BIAS circuit includes AVDD_LCM and AVEE_LCM",
    ]
    u2411["repair_links"] = [
        {
            "source": "Feishu Base cases CASE-0022 and CASE-0025",
            "page": "linked photo record recvqMSU2K5nvW",
            "faults": ["No display"],
            "instruction": "两条已修复案例均记录无显示与显示IC坏；仅用于优先定位 U2411。",
            "evidence_role": "field_case_context_only",
            "repair_causality_claim_allowed": False,
        }
    ]
    physical = build_physical_registration()
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
            "reference_mode": "reviewed_physical_photo_navigation",
            "point_map_image": "assets/board-atlas/xk67j/main-point-map-page-2.png",
            "point_map_source": "XK67J_MAIN_PCB_V1.0B Placement page 2",
            "point_map_note": "XK67J V1.0B 第2面点位图；三张 KM4n V1.0 实拍已完成板级坐标审核配准。",
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
            "status": "source_boundary_only",
            "title": "可执行 U2411 定位核对",
            "note": "无显示案例支持定位 U2411；缺少审核版电气检测标准与维修动作，路径将在资料边界停止。",
        },
        "repair_case_evidence": no_display_evidence,
        "repair_flows": [_no_display_flow(no_display_evidence)],
        "entities": entities,
    }


def main():
    payload = build_dataset(ROOT)
    output = ROOT / "knowledge-base/xk67j-cross-source-registration.json"
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"entities": len(payload["entities"]), "repair_flows": len(payload["repair_flows"])}))


if __name__ == "__main__":
    main()
