import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = "TECNO_CK6N-H6929手机主板维修指导书_V1.0_20230307.pdf"
SCHEMATIC = "H6929_MAIN_V1.1维修原理图.pdf"


def _read_json(root, path):
    return json.loads((root / path).read_text(encoding="utf-8"))


def _component_index(*datasets):
    return {
        component["designator"]: (dataset["side_id"], component)
        for dataset in datasets
        for component in dataset["components"]
    }


def _geometry(component):
    footprint = component.get("footprint")
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
        "source_status": "location_only",
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


def _entity(components, designator, *, name, category, module, schematic_pages, repair_page,
            faults, instruction, shape="square", height=0.04, inspection_profile=None):
    side_id, component = components[designator]
    entity = {
        "component_id": f"H6929-MAIN-{designator}",
        "designator": designator,
        "name": name,
        "category": category,
        "module": module,
        "side_id": side_id,
        "proxy_visibility": "point_map_only",
        "geometry": _geometry(component),
        "schematic_links": _schematic_link(designator, schematic_pages) if schematic_pages else [],
        "repair_links": _repair_link(repair_page, faults, instruction),
        "visual_profile": {"shape": shape, "height": height, "engineering_dimension": False},
    }
    if inspection_profile:
        entity["inspection_profile"] = _inspection(
            inspection_profile,
            "外观、层高和封装细节为维修识别示意，不代表实测尺寸、焊盘或内部构造。",
        )
    return entity


def build_dataset(root=ROOT):
    top = _read_json(root, "knowledge-base/h6929-board-compiled-top.json")
    bot = _read_json(root, "knowledge-base/h6929-board-compiled-bot.json")
    components = _component_index(top, bot)

    entities = [
        _entity(components, "U1001", name="Main processor IC", category="bga_ic", module="Processor",
                schematic_pages="2-5", repair_page="12-13, 28, 31", faults=["No power", "WiFi connection failure", "Display failure"],
                instruction="完成供电、时钟、无线或显示分支检查后，再按手册处理 U1001。", inspection_profile="processor-bga-v1"),
        _entity(components, "U2001", name="Power management IC", category="bga_ic", module="Power management",
                schematic_pages="6-7", repair_page="12-14, 31", faults=["No power", "Display failure"],
                instruction="检查电池输入与核心电源条件，再按手册处理 U2001。", inspection_profile="pmic-bga-v1"),
        _entity(components, "X2101", name="26 MHz crystal", category="crystal", module="Clock",
                schematic_pages="7", repair_page="13, 18", faults=["No power", "Clock failure"],
                instruction="测量并记录 X2101 输出；手册参考值为 26 MHz。", shape="rectangle", height=0.03,
                inspection_profile="crystal-26mhz-v1"),
        _entity(components, "U2304", name="Charging management IC", category="ic", module="Charging",
                schematic_pages="9", repair_page="12, 17", faults=["No power", "Not charging"],
                instruction="按无电流或不充电流程检查 U2304 输入输出，再决定返修或更换。", inspection_profile="charging-ic-v1"),
        _entity(components, "U2305", name="Charging input protection IC", category="ic", module="Charging input",
                schematic_pages="9", repair_page="17", faults=["Not charging"],
                instruction="先确认 U2305 的 VBUS 条件，再沿手册分支检查 J2101 或 U2304。", inspection_profile="charging-input-ic-v1"),
        _entity(components, "J2101", name="USB charging connector", category="connector", module="USB and charging",
                schematic_pages="7", repair_page="17", faults=["Not charging"],
                instruction="当 U2305 无 VBUS 时，检查并维修 J2101 及其输入路径。", shape="rectangle", height=0.025,
                inspection_profile="usb-connector-v1"),
        _entity(components, "U5003", name="Wi-Fi connectivity IC", category="bga_ic", module="Connectivity",
                schematic_pages="17", repair_page="28", faults=["WiFi connection failure"],
                instruction="检查 U5003、相关供电与天线路径，再按手册返修器件。", inspection_profile="connectivity-bga-v1"),
        _entity(components, "J6101", name="OLED display connector", category="connector", module="Display interconnect",
                schematic_pages="19", repair_page="31", faults=["Display failure"],
                instruction="先检查 J6101 焊接、PIN 脚和显示组件，再进入信号与驱动电压分支。", shape="rectangle", height=0.022,
                inspection_profile="display-connector-v1"),
        _entity(components, "U2404", name="Display power IC", category="ic", module="Display power",
                schematic_pages="10", repair_page="31", faults=["Display failure"],
                instruction="显示连接与信号正常后，检查显示驱动电压及 U2404。", inspection_profile="display-power-ic-v1"),
        _entity(components, "VBAT1", name="Battery input test point", category="test_point", module="Base power",
                schematic_pages=None, repair_page="12-14", faults=["No power"],
                instruction="测量 VBAT；手册给出的正常范围为 3.4-4.35 V。", shape="point", height=0.006),
    ]

    by_designator = {entity["designator"]: entity for entity in entities}
    by_designator["VBAT1"]["measurement_profile"] = {
        "measurement_id": "vbat1-voltage", "label": "VBAT 电压", "quantity": "voltage", "unit": "V",
        "input_step": 0.01, "reference": {"kind": "range", "min": 3.4, "max": 4.35}, "source_link_index": 0,
    }
    by_designator["X2101"]["measurement_profile"] = {
        "measurement_id": "x2101-frequency", "label": "X2101 输出频率", "quantity": "frequency", "unit": "MHz",
        "input_step": 0.1, "reference": {"kind": "nominal", "value": 26}, "source_link_index": 0,
    }

    flows = [
        {
            "flow_id": "h6929-no-power-zero-current-page-12", "entry_label": "不开机 · 0-10 mA", "entry_order": 1,
            "entry_type": "known_fault", "title": "H6929 无电流不开机排查", "fault": "No power",
            "entry_component_id": "H6929-MAIN-VBAT1", "entry_step_id": "vbat_check",
            "source": {"source": GUIDE, "page": "12"}, "source_status": "reviewed",
            "steps": [
                {"step_id": "vbat_check", "label": "电池输入", "prompt": "VBAT 是否在手册正常范围内？", "target_component_id": "H6929-MAIN-VBAT1",
                 "measurements": [{"measurement_id": "vbat1-voltage", "label": "VBAT 电压", "unit": "V", "input_step": 0.01, "required": True,
                                   "reference": {"kind": "range", "min": 3.4, "max": 4.35}}],
                 "choices": [{"value": "normal", "label": "正常", "outcome": {"kind": "next", "step_id": "power_key_check"}},
                             {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "检查电池连接器与 VBAT 输入路径", "target_component_id": "H6929-MAIN-VBAT1"}}]},
                {"step_id": "power_key_check", "label": "开机触发与供电", "prompt": "开机键电压与供电模块检查是否正常？", "target_component_id": "H6929-MAIN-U2001",
                 "choices": [{"value": "normal", "label": "正常", "outcome": {"kind": "action", "label": "按手册返修 U1001 / U2001 / U2304", "target_component_id": "H6929-MAIN-U2001"}},
                             {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "维修开机键或异常供电路径", "target_component_id": "H6929-MAIN-U2001"}}]},
            ],
        },
        {
            "flow_id": "h6929-no-power-small-current-page-13", "entry_label": "不开机 · 10-100 mA", "entry_order": 2,
            "entry_type": "known_fault", "title": "H6929 小电流不开机排查", "fault": "No power",
            "entry_component_id": "H6929-MAIN-X2101", "entry_step_id": "clock_check",
            "source": {"source": GUIDE, "page": "13"}, "source_status": "reviewed",
            "steps": [
                {"step_id": "clock_check", "label": "26 MHz 时钟", "prompt": "X2101 的 26 MHz 输出是否正常？", "target_component_id": "H6929-MAIN-X2101",
                 "measurements": [{"measurement_id": "x2101-frequency", "label": "X2101 输出频率", "unit": "MHz", "input_step": 0.1, "required": True,
                                   "reference": {"kind": "nominal", "value": 26}}],
                 "choices": [{"value": "normal", "label": "正常", "outcome": {"kind": "next", "step_id": "core_power_check"}},
                             {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "维修或更换 X2101", "target_component_id": "H6929-MAIN-X2101"}}]},
                {"step_id": "core_power_check", "label": "核心供电", "prompt": "U1001 相关电源线阻值与输入电压是否正常？", "target_component_id": "H6929-MAIN-U2001",
                 "choices": [{"value": "normal", "label": "正常", "outcome": {"kind": "action", "label": "按手册返修 U1001 及相关存储器件", "target_component_id": "H6929-MAIN-U1001"}},
                             {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "维修 U2001 / U2304 供电分支", "target_component_id": "H6929-MAIN-U2001"}}]},
            ],
        },
        {
            "flow_id": "h6929-no-charge-page-17", "entry_label": "无法充电", "entry_order": 3,
            "entry_type": "known_fault", "title": "H6929 不充电排查", "fault": "Not charging",
            "entry_component_id": "H6929-MAIN-U2305", "entry_step_id": "vbus_check",
            "source": {"source": GUIDE, "page": "17"}, "source_status": "reviewed",
            "steps": [
                {"step_id": "vbus_check", "label": "VBUS 输入", "prompt": "U2305 的 VBUS 是否正常？", "target_component_id": "H6929-MAIN-U2305",
                 "choices": [{"value": "present", "label": "正常", "outcome": {"kind": "next", "step_id": "charge_output_check"}},
                             {"value": "absent", "label": "异常", "outcome": {"kind": "action", "label": "维修 J2101 与 VBUS 输入路径", "target_component_id": "H6929-MAIN-J2101"}}]},
                {"step_id": "charge_output_check", "label": "充电输出", "prompt": "U2304 输出是否正常？", "target_component_id": "H6929-MAIN-U2304",
                 "choices": [{"value": "present", "label": "正常", "outcome": {"kind": "action", "label": "继续检查充电外围与连接状态", "target_component_id": "H6929-MAIN-U2304"}},
                             {"value": "absent", "label": "异常", "outcome": {"kind": "action", "label": "按手册检查并更换 U2305 或 U2304", "target_component_id": "H6929-MAIN-U2304"}}]},
            ],
        },
        {
            "flow_id": "h6929-display-page-31", "entry_label": "OLED 无显示", "entry_order": 4,
            "entry_type": "known_fault", "title": "H6929 OLED 无显示排查", "fault": "Display failure",
            "entry_component_id": "H6929-MAIN-J6101", "entry_step_id": "connector_check",
            "source": {"source": GUIDE, "page": "31"}, "source_status": "reviewed",
            "steps": [
                {"step_id": "connector_check", "label": "显示连接器", "prompt": "J6101 焊接、PIN 脚和显示组件是否正常？", "target_component_id": "H6929-MAIN-J6101",
                 "choices": [{"value": "normal", "label": "正常", "outcome": {"kind": "next", "step_id": "display_signal_check"}},
                             {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "维修 J6101 或更换已确认故障的显示组件", "target_component_id": "H6929-MAIN-J6101"}}]},
                {"step_id": "display_signal_check", "label": "显示信号", "prompt": "显示接口信号是否正常？", "target_component_id": "H6929-MAIN-U1001",
                 "choices": [{"value": "normal", "label": "正常", "outcome": {"kind": "next", "step_id": "display_power_check"}},
                             {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "检查线路并按手册处理 U1001", "target_component_id": "H6929-MAIN-U1001"}}]},
                {"step_id": "display_power_check", "label": "显示驱动供电", "prompt": "OLED 驱动电压是否正常？", "target_component_id": "H6929-MAIN-U2404",
                 "choices": [{"value": "normal", "label": "正常", "outcome": {"kind": "action", "label": "复核 U1001 / U2001 显示相关分支", "target_component_id": "H6929-MAIN-U2001"}},
                             {"value": "abnormal", "label": "异常", "outcome": {"kind": "action", "label": "检查外围并返修 U2404", "target_component_id": "H6929-MAIN-U2404"}}]},
            ],
        },
    ]

    return {
        "dataset_id": "H6929-MAIN-XREG-20260716", "board_id": bot["board_id"], "model": "CK6N",
        "compatible_models": ["CK6N"], "board_version": "H6929_MAIN_PCB_V1.1", "side_id": "main_bot",
        "coordinate_system": "normalized_board_plane", "status": "source_compiled_pilot", "board_outline": bot["board_outline"],
        "registration": {
            "reference_mode": "point_map_only",
            "point_map_image": "assets/board-atlas/h6929/main-point-map-bot.png",
            "point_map_source": "H6929_MAIN_PCB_V1.1 BOT 零件位号图",
            "point_map_note": "点位图 · H6929_MAIN_PCB_V1.1 · BOT 面 · 当前资料未提供独立主板实物图",
            "method": "normalized_point_map_registration", "confidence": "source_compiled",
        },
        "repair_flows": flows, "entities": entities,
    }


def main():
    payload = build_dataset(ROOT)
    output = ROOT / "knowledge-base/h6929-cross-source-registration.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"entities": len(payload["entities"]), "repair_flows": len(payload["repair_flows"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
