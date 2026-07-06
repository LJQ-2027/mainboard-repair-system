# Board Atlas Top20 Material Audit

Date: 2026-07-06

## Conclusion

The Top20 in-house material package is enough to start a 2.5D board atlas MVP, but not enough to make a production-grade technician workflow without more confirmation.

What is already strong:

- 11 in-house model packages are present.
- Most packages include main-board point maps or component-position PDFs.
- Many packages include repair guides and schematics.
- Several point-map PDFs are vector exports from Mentor Graphics, so they render cleanly into zoomable web images.
- KM4, KL4, CLA5, CM6, CK6N, X6880, KJ5, KM7K, BG6H, and related packages can seed the atlas pipeline.

What is still missing:

- Real board front/back photos are not registered in `model-board-assets.json`.
- Engineering confirmation is still pending for board version and sales-model applicability.
- Repair boundaries are not confirmed for overseas local technicians.
- Verified repair cases and measurement records are still missing.
- Some file names have archive-encoding mojibake; the files can still be used, but durable display names should be normalized from package metadata.

## Why The Materials Are Useful For 2.5D

The board atlas does not need a full CAD or 3D model in the first stage. It needs:

1. A board image layer.
2. A module overlay layer.
3. A component and test-point layer.
4. A fault-path layer.
5. A SOP current-step layer.

The point-map PDFs already provide a usable board geometry layer and visible component/test-point references. They can be rendered to PNG tiles or high-resolution PNGs, then overlaid with modules, hotspots, and SOP step markers.

## Sample Rendering Check

Rendered samples were inspected locally from:

- KM4 / F151 main point map: 2 pages, A4, vector PDF.
- CLA5 / H8910 main point map: 2 pages, letter, vector PDF.
- CK6N / H6929 main TOP point map: 1 page, letter, vector PDF.

Visual result:

- The board outline is clear.
- Component designators are visible after zoom.
- TOP/BOT style pages are suitable for front/back atlas sides.
- These are more useful than text-only repair-guide links for a technician workflow.

## MVP Candidate

Use KM4 / F151 as the first board atlas sample:

- It is a high-priority model in the L4 report.
- Its package has a repair guide, main schematic, main point map, sub-board schematic, and sub-board point map.
- The main point-map PDF renders into two clean pages.

First MVP scope:

- Model: KM4 / F151.
- Board version: F151_MAIN_PCB_V1.2.
- Atlas sides: main page 1 and main page 2 from the point-map PDF.
- Initial modules: power, charging, memory, CPU/main control, RF/network, connectors.
- First repair flow: "not sure, start basic board check" plus one direct fault path such as no power or no charging.

## Material Sufficiency By Capability

| Capability | Current support | Notes |
| --- | --- | --- |
| 2.5D board atlas viewer | Enough for MVP | Point-map PDFs can be rendered into web images. |
| Module highlighting | Enough for manual overlay | Module polygons still need manual annotation or extraction from guides. |
| Component/test-point lookup | Partial | Designators are visible; machine-readable coordinates still need annotation or parsing. |
| Fault-to-module highlighting | Partial | Some related faults exist, but mappings need engineering review. |
| SOP-guided measurement | Partial | Repair guides and SOP drafts exist; they need technician-friendly extraction. |
| Photo QC | Not enough | Real board photos and bad-photo examples are still needed. |
| Physical-photo to atlas alignment | Not enough for full automation | Need real photos and anchor-point pairs. Manual alignment can start later. |
| AI visual defect detection | Not enough for training | Need labeled abnormal photos. VLM-assisted review can be tested later. |

## Immediate Extraction Plan

1. Render KM4 main point-map PDF pages into committed web assets under `assets/board-atlas/km4-f151/`.
2. Register a board atlas JSON entry in `knowledge-base/board-atlas-mvp.json`.
3. Add initial module polygons and hotspot placeholders for the KM4 atlas.
4. Connect a repair-flow screen to this JSON in a later frontend task.
5. Ask for real board photos only after the point-map-driven MVP is visible, so Manufacturing Center can see exactly what photos are needed.

