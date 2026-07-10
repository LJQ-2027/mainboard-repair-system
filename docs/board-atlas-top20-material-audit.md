# Board Atlas Top20 Material Audit

Date: 2026-07-10

## Conclusion

The Top20 in-house material package is enough to build the source-based 2.5D board atlas. For this product layer, the supplied point map, schematic, and repair guide are the accepted source; the technician flow does not add engineering confirmation or manual calibration steps.

What is already strong:

- 11 in-house model packages are present.
- Most packages include main-board point maps or component-position PDFs.
- Many packages include repair guides and schematics.
- Several point-map PDFs are vector exports from Mentor Graphics, so they render cleanly into zoomable web images.
- KM4, KL4, CLA5, CM6, CK6N, X6880, KJ5, KM7K, BG6H, and related packages can seed the atlas pipeline.

What belongs to later capabilities rather than the atlas baseline:

- Real board front/back photos are needed for photo-to-map matching and visual QC, not for the point-map atlas.
- Labeled good-board and bad-board photos are needed to train a visual defect model.
- Verified repair cases and measurement records will improve fault ranking and SOP branching.
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
- Initial source-located modules: U2001 PMU, U1001 CPU/baseband, U4001 LPDDR4X, U4000 eMMC, X2100 clock, U2702/U2704 charging, U0600 RF, and J6101/VBUS1 connector area.
- First repair flow: "not sure, start basic board check" plus one direct fault path such as no power or no charging.

## Material Sufficiency By Capability

| Capability | Current support | Notes |
| --- | --- | --- |
| 2.5D board atlas viewer | Enough for MVP | Point-map PDFs can be rendered into web images. |
| Module highlighting | Available for KM4/F151 | Coordinates are extracted from the source point map and stored in normalized source space. |
| Component/test-point lookup | Available for the first flow | U1001, U2001, U4000, U4001, U0600, U2702/U2704, J6101, VBAT1, VBUS1, and X2100 are registered. |
| Fault-to-module highlighting | Available for MVP paths | Initial check, no-power, and not-charging paths use source-located modules. |
| SOP-guided measurement | Available for the first step of each path | VBAT, VBUS/VCHG, X2100, VDDCORE, and VDDEMMCCORE references come from the F151 repair guide. |
| Photo QC | Not enough | Real board photos and bad-photo examples are still needed. |
| Physical-photo to atlas alignment | Not enough for full automation | Need real photos and anchor-point pairs. Manual alignment can start later. |
| AI visual defect detection | Not enough for training | Need labeled abnormal photos. VLM-assisted review can be tested later. |

## Immediate Extraction Plan

1. Render KM4 main point-map PDF pages into committed web assets under `assets/board-atlas/km4-f151/`.
2. Register a board atlas JSON entry in `knowledge-base/board-atlas-mvp.json`.
3. Keep module regions, designators, test points, and source references together in the KM4 atlas JSON.
4. Reuse the same extraction and rendering pipeline for the next Top20 board package.
5. Collect real board photos when starting photo-to-map matching or visual QC.
