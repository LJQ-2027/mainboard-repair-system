import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = "TECNO_K6735_KL4-F201维修操作指导书_V1.0_20240705.pdf"
SCHEMATIC = "K6735_F201_MAIN_SCH_V1.2维修原理图20240614.pdf"


def _read_json(root, path):
    return json.loads((root / path).read_text(encoding="utf-8"))


def _component_index(*datasets):
    return {
        component["designator"]: (dataset["side_id"], component)
        for dataset in datasets
        for component in dataset["components"]
    }


def _geometry(component, *, allow_footprint=True):
    footprint = component.get("footprint") if allow_footprint else None
    if footprint and footprint["confidence"] in ("high", "medium"):
        return {
            "center": footprint["center"],
            "size": footprint["size"],
            "rotation": 0,
            "source_status": footprint["confidence"],
        }
    return {
        "center": component["center"],
        "size": {"x": 0.025, "y": 0.025},
        "rotation": 0,
        "source_status": component.get("footprint", {}).get("confidence", "location_only"),
    }


def _schematic_link(designator, pages):
    return [{
        "source": SCHEMATIC,
        "page": pages,
        "facts": [f"Designator {designator}"],
    }]


def build_dataset(root=ROOT):
    page_one = _read_json(root, "knowledge-base/kl4-board-compiled-page-1.json")
    page_two = _read_json(root, "knowledge-base/kl4-board-compiled.json")
    components = _component_index(page_one, page_two)

    u1001_side, u1001 = components["U1001"]
    u2001_side, u2001 = components["U2001"]
    x2100_side, x2100 = components["X2100"]
    entities = [
        {
            "component_id": "KL4-MAIN-U1001",
            "designator": "U1001",
            "name": "Main processor IC",
            "category": "bga_ic",
            "module": "Processor",
            "side_id": u1001_side,
            "proxy_visibility": "concealed_by_shield",
            "geometry": _geometry(u1001, allow_footprint=False),
            "schematic_links": _schematic_link("U1001", "3-5"),
            "repair_links": [{
                "source": GUIDE,
                "page": "9-11",
                "faults": ["No power"],
                "instruction": "按不开机电流分支完成供电和时钟检测后，再依据流程处理 U1001。",
            }],
            "visual_profile": {"shape": "point", "height": 0.018, "engineering_dimension": False},
        },
        {
            "component_id": "KL4-MAIN-U2001",
            "designator": "U2001",
            "name": "Power management IC",
            "category": "bga_ic",
            "module": "Power management",
            "side_id": u2001_side,
            "proxy_visibility": "concealed_by_shield",
            "geometry": _geometry(u2001),
            "schematic_links": _schematic_link("U2001", "6-7"),
            "repair_links": [{
                "source": GUIDE,
                "page": "8-11",
                "faults": ["No power"],
                "instruction": "记录 VDDCORE 与 VDDEMMCCORE 电压，并按不开机电流分支继续检测。",
            }],
            "visual_profile": {"shape": "square", "height": 0.055, "engineering_dimension": False},
            "inspection_profile": {
                "profile_id": "u2001-pmic-v1",
                "fidelity": "repair_visual",
                "source_status": "category_based",
                "visual_note": "外观、层高和封装细节为维修识别示意，不代表实测尺寸、焊球数量或工程封装。",
            },
        },
        {
            "component_id": "KL4-MAIN-X2100",
            "designator": "X2100",
            "name": "26 MHz crystal",
            "category": "crystal",
            "module": "Clock",
            "side_id": x2100_side,
            "proxy_visibility": "concealed_by_shield",
            "geometry": _geometry(x2100),
            "schematic_links": _schematic_link("X2100", "7"),
            "repair_links": [{
                "source": GUIDE,
                "page": "10, 15",
                "faults": ["No power", "Clock failure"],
                "instruction": "测量并记录 X2100 输出频率；资料参考值为 26 MHz。",
            }],
            "measurement_profile": {
                "measurement_id": "x2100-frequency",
                "label": "X2100 输出频率",
                "quantity": "frequency",
                "unit": "MHz",
                "input_step": 0.1,
                "reference": {"kind": "nominal", "value": 26},
                "source_link_index": 0,
            },
            "visual_profile": {"shape": "rectangle", "height": 0.035, "engineering_dimension": False},
            "inspection_profile": {
                "profile_id": "x2100-crystal-v1",
                "fidelity": "repair_visual",
                "source_status": "category_based",
                "visual_note": "晶振外观与层高为维修识别示意，不代表实测外壳尺寸、焊盘结构或内部构造。",
            },
        },
    ]

    flow = {
        "flow_id": "kl4-no-power-small-current-pages-10-11",
        "entry_label": "不开机",
        "entry_order": 1,
        "entry_type": "known_fault",
        "title": "KL4 小电流不开机排查",
        "fault": "No power",
        "entry_component_id": "KL4-MAIN-U2001",
        "entry_step_id": "rail_check",
        "source": {"source": GUIDE, "page": "10-11"},
        "source_status": "reviewed",
        "steps": [
            {
                "step_id": "rail_check",
                "label": "核心供电",
                "prompt": "VDDCORE / VDDEMMCCORE 电压是否正常？",
                "target_component_id": "KL4-MAIN-U2001",
                "measurements": [
                    {"measurement_id": "vddcore-voltage", "label": "VDDCORE 电压", "unit": "V", "input_step": 0.01, "required": True, "reference": {"kind": "nominal", "value": 1.15}},
                    {"measurement_id": "vddemmccore-voltage", "label": "VDDEMMCCORE 电压", "unit": "V", "input_step": 0.01, "required": True, "reference": {"kind": "nominal", "value": 3.3}},
                ],
                "choices": [
                    {"value": "normal", "label": "正常", "outcome": {"kind": "next", "step_id": "crystal_check"}},
                    {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "重焊或更换 U1001 OR U2001", "target_component_id": "KL4-MAIN-U2001"}},
                ],
            },
            {
                "step_id": "crystal_check",
                "label": "26 MHz 时钟",
                "prompt": "X2100 输出频率是否为 26 MHz？",
                "target_component_id": "KL4-MAIN-X2100",
                "measurements": [
                    {"measurement_id": "x2100-frequency", "label": "X2100 输出频率", "unit": "MHz", "input_step": 0.1, "required": True, "reference": {"kind": "nominal", "value": 26}},
                ],
                "choices": [
                    {"value": "normal", "label": "正常", "outcome": {"kind": "action", "label": "重焊或更换 U1001", "target_component_id": "KL4-MAIN-U1001"}},
                    {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "重焊或更换 X2100", "target_component_id": "KL4-MAIN-X2100"}},
                ],
            },
        ],
    }

    return {
        "dataset_id": "KL4-F201-XREG-20260716",
        "board_id": page_two["board_id"],
        "model": "KL4",
        "board_version": "F201_MAIN_V1.2",
        "side_id": "main_page_2",
        "coordinate_system": "normalized_board_plane",
        "status": "source_compiled_pilot",
        "board_outline": page_two["board_outline"],
        "registration": {
            "proxy_image": "assets/vision-reference-gallery/kl4/embedded/page-010-image-02.jpg",
            "proxy_label": "Service Manual page 10 installed mainboard",
            "proxy_limit": "Installed shield-side context; not an isolated two-side main-board pair.",
            "proxy_note": "主板实物参考 · KL4维修手册第10页 · 屏蔽罩下器件不可直接观察",
            "point_map_image": "assets/board-atlas/kl4-f201/main-point-map-page-2.png",
            "point_map_source": "F201_MAIN_V1.2_零件位号.pdf page 2",
            "point_map_note": "点位图 · F201_MAIN_V1.2 · 第2面",
            "method": "reviewed_four_anchor_homography",
            "confidence": "provisional_proxy",
            "anchors": [
                {"anchor_id": "board_top_left", "label": "PCB upper-left extent", "board": {"x": 0.02, "y": 0.02}, "image": {"x": 0.10, "y": 0.14}},
                {"anchor_id": "board_top_right", "label": "PCB upper-right extent", "board": {"x": 0.98, "y": 0.02}, "image": {"x": 0.82, "y": 0.13}},
                {"anchor_id": "board_bottom_right", "label": "PCB lower-right extent", "board": {"x": 0.98, "y": 0.98}, "image": {"x": 0.80, "y": 0.63}},
                {"anchor_id": "board_bottom_left", "label": "PCB lower-left extent", "board": {"x": 0.02, "y": 0.98}, "image": {"x": 0.12, "y": 0.64}},
            ],
        },
        "repair_flows": [flow],
        "entities": entities,
    }


def main():
    payload = build_dataset(ROOT)
    output = ROOT / "knowledge-base/kl4-cross-source-registration.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"entities": len(payload["entities"]), "repair_flows": len(payload["repair_flows"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
