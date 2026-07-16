import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMATIC = "J6765_F069M_MAIN_SCH_维修原理图_V1.0.pdf"


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


def _inspection(profile_id, note):
    return {
        "profile_id": profile_id,
        "fidelity": "repair_visual",
        "source_status": "category_based",
        "visual_note": note,
    }


def _schematic_link(schematic, designator):
    pages = sorted({item["page"] for item in schematic["components"][designator]})
    return [{
        "source": SCHEMATIC,
        "page": ", ".join(str(page) for page in pages),
        "facts": [f"Exact schematic designator {designator}"],
    }]


def _entity(components, schematic, designator, *, name, category, module, shape="square",
            height=0.04, inspection_profile=None):
    side_id, component = components[designator]
    entity = {
        "component_id": f"F069M-MAIN-{designator}",
        "designator": designator,
        "name": name,
        "category": category,
        "module": module,
        "side_id": side_id,
        "proxy_visibility": "point_map_only",
        "geometry": _geometry(component),
        "schematic_links": _schematic_link(schematic, designator),
        "repair_links": [],
        "visual_profile": {"shape": shape, "height": height, "engineering_dimension": False},
    }
    if inspection_profile and entity["geometry"]["source_status"] in ("high", "medium"):
        entity["inspection_profile"] = _inspection(
            inspection_profile,
            "封装外观和层高为维修识别示意；当前资料未提供实测尺寸、焊盘或内部构造。",
        )
    return entity


def build_dataset(root=ROOT):
    page_one = _read_json(root, "knowledge-base/f069m-board-compiled-page-1.json")
    page_two = _read_json(root, "knowledge-base/f069m-board-compiled-page-2.json")
    schematic = _read_json(root, "knowledge-base/f069m-schematic-compiled.json")
    components = _component_index(page_one, page_two)

    entities = [
        _entity(components, schematic, "U1001", name="UMS9230 main processor", category="bga_ic", module="Processor",
                inspection_profile="processor-bga-v1", height=0.05),
        _entity(components, schematic, "U2001", name="Power management IC", category="bga_ic", module="Power management",
                inspection_profile="pmic-bga-v1", height=0.05),
        _entity(components, schematic, "U4000", name="64 GB eMMC storage", category="bga_ic", module="Storage",
                inspection_profile="storage-bga-v1", height=0.045),
        _entity(components, schematic, "U4001", name="LPDDR4x memory", category="bga_ic", module="Memory",
                inspection_profile="memory-bga-v1", height=0.045),
        _entity(components, schematic, "U5002", name="UMS2631 wireless connectivity IC", category="bga_ic", module="Wireless connectivity",
                inspection_profile="connectivity-bga-v1", height=0.045),
        _entity(components, schematic, "U0600", name="SR3595D RF front-end IC", category="ic", module="RF front end",
                inspection_profile="rf-front-end-ic-v1", height=0.035),
        _entity(components, schematic, "J6101", name="LCM display connector", category="connector", module="Display interconnect",
                shape="rectangle", height=0.022, inspection_profile="display-connector-v1"),
        _entity(components, schematic, "J6202", name="Camera connector", category="connector", module="Camera interconnect",
                shape="rectangle", height=0.022, inspection_profile="camera-connector-v1"),
        _entity(components, schematic, "J6250", name="Front camera connector", category="connector", module="Front camera interconnect",
                shape="rectangle", height=0.022, inspection_profile="camera-connector-v1"),
        _entity(components, schematic, "VBUS1", name="USB VBUS test point", category="test_point", module="USB power input",
                shape="point", height=0.006),
    ]

    return {
        "dataset_id": "F069M-MAIN-XREG-20260717",
        "board_id": page_two["board_id"],
        "model": "BG6M",
        "compatible_models": ["BG6M"],
        "board_version": "F069M_MAIN_PCB_V1.0",
        "side_id": "main_page_2",
        "coordinate_system": "normalized_board_plane",
        "status": "source_compiled_reference_only",
        "board_outline": page_two["board_outline"],
        "registration": {
            "reference_mode": "point_map_only",
            "point_map_image": "assets/board-atlas/f069m/main-point-map-page-2.png",
            "point_map_source": "F069M_MAIN_PCB_V1.0 零件位号图 page 2",
            "point_map_note": "点位图 · F069M_MAIN_PCB_V1.0 · 第2面 · 当前资料未提供独立主板实物图",
            "method": "normalized_point_map_registration",
            "confidence": "source_compiled",
        },
        "repair_coverage": {
            "status": "source_unavailable",
            "title": "暂无可执行维修流程",
            "note": "当前资料包仅包含点位图和维修原理图，未提供维修手册。可以定位器件并查看原理图依据，但系统不会生成检测步骤或维修动作。",
        },
        "repair_flows": [],
        "entities": entities,
    }


def main():
    payload = build_dataset(ROOT)
    output = ROOT / "knowledge-base/f069m-cross-source-registration.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"entities": len(payload["entities"]), "repair_flows": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
