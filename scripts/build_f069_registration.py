import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = "F069_MAIN_PCB_V1.2 维修原理图 20230804.pdf"
POINT_MAP = "F069_MAIN_PCB_V1.2_位号图_20230823（A4）.pdf"
REPAIR_GUIDE = "TECNO_J6563_BG6h-F069_维修操作指导书_V1.0_20231108.docx"


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
        "source_status": footprint["confidence"] if footprint else "location_only",
    }


def _inspection(profile_id):
    return {
        "profile_id": profile_id,
        "fidelity": "repair_visual",
        "source_status": "category_based",
        "visual_note": "封装外观和层高为维修识别示意；当前资料未提供实测尺寸、焊盘或内部构造。",
    }


def _schematic_links(schematic, designator):
    occurrences = schematic["components"].get(designator, [])
    if not occurrences:
        return []
    pages = sorted({item["page"] for item in occurrences})
    return [{
        "source": SCHEMATIC,
        "page": ", ".join(str(page) for page in pages),
        "facts": [f"Exact schematic designator {designator}"],
    }]


def _entity(
    components,
    schematic,
    designator,
    *,
    name,
    category,
    module,
    shape="square",
    height=0.04,
    inspection_profile=None,
    repair_links=None,
    source_boundary=None,
):
    side_id, component = components[designator]
    entity = {
        "component_id": f"F069-MAIN-{designator}",
        "designator": designator,
        "name": name,
        "category": category,
        "module": module,
        "side_id": side_id,
        "proxy_visibility": "point_map_only",
        "geometry": _geometry(component),
        "schematic_links": _schematic_links(schematic, designator),
        "repair_links": repair_links or [],
        "visual_profile": {
            "shape": shape,
            "height": height,
            "engineering_dimension": False,
        },
    }
    if source_boundary:
        entity["source_boundary"] = source_boundary
    if inspection_profile and entity["geometry"]["source_status"] in ("high", "medium"):
        entity["inspection_profile"] = _inspection(inspection_profile)
    return entity


def build_dataset(root=ROOT):
    page_one = _read_json(root, "knowledge-base/f069-board-compiled-page-1.json")
    page_two = _read_json(root, "knowledge-base/f069-board-compiled-page-2.json")
    schematic = _read_json(root, "knowledge-base/f069-schematic-compiled.json")
    components = _component_index(page_one, page_two)

    entities = [
        _entity(
            components,
            schematic,
            "U1001",
            name="UMS9230 main processor",
            category="bga_ic",
            module="Processor",
            inspection_profile="processor-bga-v1",
            height=0.05,
        ),
        _entity(
            components,
            schematic,
            "U2001",
            name="UMP510G power management IC",
            category="bga_ic",
            module="Power management",
            inspection_profile="pmic-bga-v1",
            height=0.05,
        ),
        _entity(
            components,
            schematic,
            "U4000",
            name="eMMC storage",
            category="bga_ic",
            module="Storage",
            inspection_profile="storage-bga-v1",
            height=0.045,
        ),
        _entity(
            components,
            schematic,
            "U4001",
            name="LPDDR4x memory",
            category="bga_ic",
            module="Memory",
            inspection_profile="memory-bga-v1",
            height=0.045,
        ),
        _entity(
            components,
            schematic,
            "U5002",
            name="Wireless connectivity IC",
            category="bga_ic",
            module="Wireless connectivity",
            inspection_profile="connectivity-bga-v1",
            height=0.045,
        ),
        _entity(
            components,
            schematic,
            "U0600",
            name="SR3595D RF front-end IC",
            category="ic",
            module="RF front end",
            inspection_profile="rf-front-end-ic-v1",
            height=0.035,
        ),
        _entity(
            components,
            schematic,
            "J6101",
            name="LCM display connector",
            category="connector",
            module="Display interconnect",
            shape="rectangle",
            height=0.022,
            inspection_profile="display-connector-v1",
        ),
        _entity(
            components,
            schematic,
            "J6202",
            name="Rear camera connector",
            category="connector",
            module="Rear camera interconnect",
            shape="rectangle",
            height=0.022,
            inspection_profile="camera-connector-v1",
        ),
        _entity(
            components,
            schematic,
            "J6250",
            name="Front camera connector",
            category="connector",
            module="Front camera interconnect",
            shape="rectangle",
            height=0.022,
            inspection_profile="camera-connector-v1",
        ),
        _entity(
            components,
            schematic,
            "X2100",
            name="26 MHz crystal",
            category="crystal",
            module="System clock",
            shape="rectangle",
            height=0.02,
            inspection_profile="crystal-package-v1",
        ),
        _entity(
            components,
            schematic,
            "VBAT1",
            name="Battery supply location",
            category="test_point",
            module="Battery power",
            shape="point",
            height=0.006,
            source_boundary="point_map_and_unreviewed_guide",
            repair_links=[{
                "source": REPAIR_GUIDE,
                "page": "不开机章节（DOCX，无固定页码）",
                "faults": ["No power"],
                "instruction": "维修指导书包含 VBAT 检查，但本轮尚未转译为审核过的可执行流程。",
            }],
        ),
        _entity(
            components,
            schematic,
            "VBUS1",
            name="USB VBUS input location",
            category="test_point",
            module="USB power input",
            shape="point",
            height=0.006,
        ),
    ]

    return {
        "dataset_id": "F069-MAIN-XREG-20260724",
        "board_id": page_two["board_id"],
        "model": "BG6H",
        "compatible_models": ["BG6H", "BG6h"],
        "board_version": "F069_MAIN_PCB_V1.2",
        "side_id": "main_page_2",
        "coordinate_system": "normalized_board_plane",
        "status": "source_compiled_reference_only",
        "board_outline": page_two["board_outline"],
        "registration": {
            "reference_mode": "point_map_only",
            "point_map_image": "assets/board-atlas/bg6h-f069/main-point-map-page-2.png",
            "point_map_source": f"{POINT_MAP} page 2",
            "point_map_note": "点位图 · F069_MAIN_PCB_V1.2 · 第2面 · 实拍 HEIC 尚未进入受控来源包",
            "method": "normalized_point_map_registration",
            "confidence": "source_compiled",
        },
        "repair_coverage": {
            "status": "source_available_pending_review",
            "title": "维修资料待转译",
            "note": "维修指导书已经入库，但本轮仅建立精确板型和来源关系；尚未形成审核过的检测步骤或维修动作。",
            "source": (
                "source-materials/manufacturing-center/top20-model-board-assets/"
                "2026-07-02-inhouse-top20/packages/BG6H-F069/"
                f"{REPAIR_GUIDE}"
            ),
        },
        "repair_flows": [],
        "entities": entities,
    }


def main():
    payload = build_dataset(ROOT)
    output = ROOT / "knowledge-base/f069-cross-source-registration.json"
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"entities": len(payload["entities"]), "repair_flows": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
