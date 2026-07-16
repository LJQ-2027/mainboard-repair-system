import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = "Tecno-CM6-H8918手机主板维修专用操作指导书V1.0_20241218.pdf"
SCHEMATIC = "K6855_H8918_MAIN_PCB_V1.2维修原理图.pdf"


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
    return [{"source": SCHEMATIC, "page": pages, "facts": [f"Designator {designator}"]}]


def _repair_link(page, faults, instruction):
    return [{"source": GUIDE, "page": page, "faults": faults, "instruction": instruction}]


def _inspection(profile_id, note):
    return {
        "profile_id": profile_id,
        "fidelity": "repair_visual",
        "source_status": "category_based",
        "visual_note": note,
    }


def build_dataset(root=ROOT):
    page_one = _read_json(root, "knowledge-base/h8918-board-compiled-page-1.json")
    page_two = _read_json(root, "knowledge-base/h8918-board-compiled.json")
    components = _component_index(page_one, page_two)

    u1001_side, u1001 = components["U1001"]
    u2001_side, u2001 = components["U2001"]
    x2101_side, x2101 = components["X2101"]
    j6102_side, j6102 = components["J6102"]
    u5007_side, u5007 = components["U5007"]
    vbat1_side, vbat1 = components["VBAT1"]

    entities = [
        {
            "component_id": "H8918-MAIN-U1001",
            "designator": "U1001",
            "name": "Main processor IC",
            "category": "bga_ic",
            "module": "Processor",
            "side_id": u1001_side,
            "proxy_visibility": "concealed_by_shield",
            "geometry": _geometry(u1001, allow_footprint=False),
            "schematic_links": _schematic_link("U1001", "2-5"),
            "repair_links": _repair_link("11, 25", ["No power", "Display failure"], "完成供电、时钟或显示信号分支检测后，再按手册处理 U1001。"),
            "visual_profile": {"shape": "point", "height": 0.018, "engineering_dimension": False},
        },
        {
            "component_id": "H8918-MAIN-U2001",
            "designator": "U2001",
            "name": "Power management IC",
            "category": "bga_ic",
            "module": "Power management",
            "side_id": u2001_side,
            "proxy_visibility": "concealed_by_shield",
            "geometry": _geometry(u2001),
            "schematic_links": _schematic_link("U2001", "6-7"),
            "repair_links": _repair_link("11-12, 25", ["No power", "Display failure"], "检查电池输入与核心供电；仅在前置分支完成后处理 U2001。"),
            "visual_profile": {"shape": "square", "height": 0.055, "engineering_dimension": False},
            "inspection_profile": _inspection("u2001-pmic-v1", "外观、层高和封装细节为维修识别示意，不代表实测尺寸或工程封装。"),
        },
        {
            "component_id": "H8918-MAIN-X2101",
            "designator": "X2101",
            "name": "26 MHz crystal",
            "category": "crystal",
            "module": "Clock",
            "side_id": x2101_side,
            "proxy_visibility": "concealed_by_shield",
            "geometry": _geometry(x2101),
            "schematic_links": _schematic_link("X2101", "7"),
            "repair_links": _repair_link("11, 16", ["No power", "Clock failure"], "测量并记录 X2101 输出频率；资料参考值为 26 MHz。"),
            "measurement_profile": {
                "measurement_id": "x2101-frequency",
                "label": "X2101 输出频率",
                "quantity": "frequency",
                "unit": "MHz",
                "input_step": 0.1,
                "reference": {"kind": "nominal", "value": 26},
                "source_link_index": 0,
            },
            "visual_profile": {"shape": "rectangle", "height": 0.035, "engineering_dimension": False},
            "inspection_profile": _inspection("crystal-26mhz-v1", "晶振外观与层高为维修识别示意，不代表实测外壳尺寸、焊盘结构或内部构造。"),
        },
        {
            "component_id": "H8918-MAIN-J6102",
            "designator": "J6102",
            "name": "Display connector",
            "category": "connector",
            "module": "Display interconnect",
            "side_id": j6102_side,
            "proxy_visibility": "visible_in_reference",
            "geometry": _geometry(j6102, allow_footprint=False),
            "schematic_links": [],
            "repair_links": _repair_link("25", ["Display failure"], "检查 J6102 焊接、PIN 脚变形，并交叉验证 LCD。"),
            "visual_profile": {"shape": "point", "height": 0.018, "engineering_dimension": False},
        },
        {
            "component_id": "H8918-MAIN-U5007",
            "designator": "U5007",
            "name": "Wi-Fi connectivity IC",
            "category": "bga_ic",
            "module": "Connectivity",
            "side_id": u5007_side,
            "proxy_visibility": "concealed_by_shield",
            "geometry": _geometry(u5007),
            "schematic_links": _schematic_link("U5007", "17"),
            "repair_links": _repair_link("23", ["WiFi connection failure"], "检查 U5007 焊接及 VCN33_WBT、AVDD18_WBT 供电，再检查天线路径。"),
            "visual_profile": {"shape": "square", "height": 0.045, "engineering_dimension": False},
            "inspection_profile": _inspection("connectivity-bga-v1", "BGA 外观与层高为维修识别示意，不代表实测尺寸、焊球数量或工程封装。"),
        },
        {
            "component_id": "H8918-MAIN-VBAT1",
            "designator": "VBAT1",
            "name": "Battery input test point",
            "category": "test_point",
            "module": "Base power",
            "side_id": vbat1_side,
            "proxy_visibility": "visible_in_reference",
            "geometry": _geometry(vbat1, allow_footprint=False),
            "schematic_links": [],
            "repair_links": _repair_link("11-12", ["No power"], "测量 VBAT；手册给出的正常范围为 3.4-4.35 V。"),
            "measurement_profile": {
                "measurement_id": "vbat1-voltage",
                "label": "VBAT 电压",
                "quantity": "voltage",
                "unit": "V",
                "input_step": 0.01,
                "reference": {"kind": "range", "min": 3.4, "max": 4.35},
                "source_link_index": 0,
            },
            "visual_profile": {"shape": "point", "height": 0.006, "engineering_dimension": False},
        },
    ]

    no_power_flow = {
        "flow_id": "h8918-no-power-small-current-page-11",
        "entry_label": "不开机 · 小电流",
        "entry_order": 1,
        "entry_type": "known_fault",
        "title": "H8918 小电流不开机排查",
        "fault": "No power",
        "entry_component_id": "H8918-MAIN-X2101",
        "entry_step_id": "dcxo_check",
        "source": {"source": GUIDE, "page": "11"},
        "source_status": "reviewed",
        "steps": [
            {
                "step_id": "dcxo_check",
                "label": "26 MHz 时钟",
                "prompt": "X2101 的 26 MHz 输出是否正常？",
                "target_component_id": "H8918-MAIN-X2101",
                "measurements": [{"measurement_id": "x2101-frequency", "label": "X2101 输出频率", "unit": "MHz", "input_step": 0.1, "required": True, "reference": {"kind": "nominal", "value": 26}}],
                "choices": [
                    {"value": "normal", "label": "正常", "outcome": {"kind": "next", "step_id": "power_input_check"}},
                    {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "维修或更换 X2101", "target_component_id": "H8918-MAIN-X2101"}},
                ],
            },
            {
                "step_id": "power_input_check",
                "label": "PMIC 输入",
                "prompt": "U1001 / U4101 电源线输入电压是否正常？",
                "target_component_id": "H8918-MAIN-U2001",
                "choices": [
                    {"value": "normal", "label": "正常", "outcome": {"kind": "action", "label": "按手册重焊或更换 U1001 / U4101 / U4102", "target_component_id": "H8918-MAIN-U1001"}},
                    {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "维修或更换 U2001", "target_component_id": "H8918-MAIN-U2001"}},
                ],
            },
        ],
    }

    wifi_flow = {
        "flow_id": "h8918-wifi-page-23",
        "entry_label": "Wi-Fi 无法连接",
        "entry_order": 2,
        "entry_type": "known_fault",
        "title": "H8918 Wi-Fi 连接故障排查",
        "fault": "WiFi connection failure",
        "entry_component_id": "H8918-MAIN-U5007",
        "entry_step_id": "u5007_solder_check",
        "source": {"source": GUIDE, "page": "23"},
        "source_status": "reviewed",
        "steps": [
            {
                "step_id": "u5007_solder_check",
                "label": "四合一芯片",
                "prompt": "U5007 焊接是否正常？",
                "target_component_id": "H8918-MAIN-U5007",
                "choices": [
                    {"value": "normal", "label": "正常", "outcome": {"kind": "next", "step_id": "antenna_path_check"}},
                    {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "检测 VCN33_WBT / AVDD18_WBT，并重焊 U5007", "target_component_id": "H8918-MAIN-U5007"}},
                ],
            },
            {
                "step_id": "antenna_path_check",
                "label": "Wi-Fi 天线路径",
                "prompt": "Wi-Fi 天线路径是否正常？",
                "target_component_id": "H8918-MAIN-U5007",
                "choices": [
                    {"value": "normal", "label": "正常", "outcome": {"kind": "action", "label": "重焊或更换 U5007", "target_component_id": "H8918-MAIN-U5007"}},
                    {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "重装天线并重焊或更换天线外围器件", "target_component_id": "H8918-MAIN-U5007"}},
                ],
            },
        ],
    }

    display_flow = {
        "flow_id": "h8918-display-page-25",
        "entry_label": "LCD 无显示",
        "entry_order": 3,
        "entry_type": "known_fault",
        "title": "H8918 LCD 无显示排查",
        "fault": "Display failure",
        "entry_component_id": "H8918-MAIN-J6102",
        "entry_step_id": "display_connector_check",
        "source": {"source": GUIDE, "page": "25"},
        "source_status": "reviewed",
        "steps": [
            {
                "step_id": "display_connector_check",
                "label": "显示连接器",
                "prompt": "J6102 焊接、PIN 脚及 LCD 交叉验证是否正常？",
                "target_component_id": "H8918-MAIN-J6102",
                "choices": [
                    {"value": "normal", "label": "正常", "outcome": {"kind": "next", "step_id": "mipi_check"}},
                    {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "修复 J6102 或更换已确认故障的 LCD", "target_component_id": "H8918-MAIN-J6102"}},
                ],
            },
            {
                "step_id": "mipi_check",
                "label": "MIPI 信号",
                "prompt": "MIPI DATA / CLK 是否正常？",
                "target_component_id": "H8918-MAIN-U1001",
                "choices": [
                    {"value": "normal", "label": "正常", "outcome": {"kind": "next", "step_id": "lcd_drive_check"}},
                    {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "检查开短路并重焊或更换 U1001", "target_component_id": "H8918-MAIN-U1001"}},
                ],
            },
            {
                "step_id": "lcd_drive_check",
                "label": "LCD 驱动供电",
                "prompt": "LEDK / LEDA、AVDD / AVEE 是否正常？",
                "target_component_id": "H8918-MAIN-U2001",
                "choices": [
                    {"value": "normal", "label": "正常", "outcome": {"kind": "action", "label": "按手册处理 U1001 / U2001", "target_component_id": "H8918-MAIN-U2001"}},
                    {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "检查外围并重焊或更换 U2401", "target_component_id": "H8918-MAIN-U2001"}},
                ],
            },
        ],
    }

    return {
        "dataset_id": "H8918-MAIN-XREG-20260716",
        "board_id": page_two["board_id"],
        "model": "CM6",
        "compatible_models": ["CM6", "CM5"],
        "board_version": "H8918_MAIN_PCB_V1.2",
        "side_id": "main_page_2",
        "coordinate_system": "normalized_board_plane",
        "status": "source_compiled_pilot",
        "board_outline": page_two["board_outline"],
        "registration": {
            "proxy_image": "assets/vision-reference-gallery/cm6/embedded/page-011-image-01.jpg",
            "proxy_label": "Service Manual page 11 installed mainboard",
            "proxy_limit": "Installed shield-side context; not an isolated two-side main-board pair.",
            "proxy_note": "主板实物参考 · CM6维修手册第11页 · 屏蔽罩下器件不可直接观察",
            "point_map_image": "assets/board-atlas/h8918/main-point-map-page-2.png",
            "point_map_source": "H8918_MAIN_PCB_V1.2 零件位号图 page 2",
            "point_map_note": "点位图 · H8918_MAIN_PCB_V1.2 · 第2面",
            "method": "reviewed_four_anchor_homography",
            "confidence": "provisional_proxy",
            "anchors": [
                {"anchor_id": "board_top_left", "label": "PCB upper-left extent", "board": {"x": 0.02, "y": 0.02}, "image": {"x": 0.23, "y": 0.10}},
                {"anchor_id": "board_top_right", "label": "PCB upper-right extent", "board": {"x": 0.98, "y": 0.02}, "image": {"x": 0.74, "y": 0.11}},
                {"anchor_id": "board_bottom_right", "label": "PCB lower-right extent", "board": {"x": 0.98, "y": 0.98}, "image": {"x": 0.72, "y": 0.58}},
                {"anchor_id": "board_bottom_left", "label": "PCB lower-left extent", "board": {"x": 0.02, "y": 0.98}, "image": {"x": 0.20, "y": 0.58}},
            ],
        },
        "repair_flows": [no_power_flow, wifi_flow, display_flow],
        "entities": entities,
    }


def main():
    payload = build_dataset(ROOT)
    output = ROOT / "knowledge-base/h8918-cross-source-registration.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"entities": len(payload["entities"]), "repair_flows": len(payload["repair_flows"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
