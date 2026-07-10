# Vision Reference Gallery Extraction - 2026-07-10

## Scope

Seven models shared by the existing Top20 material set and the Service Manual library were processed:

- KM4
- KL4
- CLA5
- KJ5
- CM5
- CM6
- X6880

## Result

- 7 canonical PDF manuals selected after SHA-256 duplicate removal.
- 26 source pages retained based on main-board, PCBA, PCB, exploded-view, and disassembly evidence.
- 96 embedded images extracted at source resolution.
- 21 images approved after visual review: 3 per model.
- Each model has one exploded-structure overview, one installed-main-board reference, and one installed-sub-board reference.

Every gallery asset retains its source manual, page number, dimensions, SHA-256, model aliases, and known board-version association.

## Accuracy Boundary

These Service Manuals provide useful assembly and board-region context, but they do not provide a clean isolated main-board front/back photo pair for any of the seven models. The gallery therefore uses:

- `weak` references for exploded structure views;
- `medium` references for installed main-board and sub-board closeups;
- `unknown` board side when TOP/BOTTOM is not explicitly supported by source evidence.

The system does not infer TOP or BOTTOM from the phone assembly orientation.

## Board Associations

| Model | Main board | Sub board | Standard isolated front/back pair |
| --- | --- | --- | --- |
| KM4 | F151_MAIN_PCB_V1.2 | F151_SUB_PCB_1_V1.1 | Missing |
| KL4 | F201_MAIN_V1.2 | F201_SUB_SCH_1_V1.2 | Missing |
| CLA5 | H8910_MAIN_PCB_V1.1 | H8910_SUB_PCB_1_V1.0 | Missing |
| KJ5 | H6931_MAIN_PCB_V1.0 / V1.2 | Unresolved in current index | Missing |
| CM5 | H8918_MAIN_PCB_V1.2 | H8918_SUB_PCB_2_V1.2 | Missing |
| CM6 | H8918_MAIN_PCB_V1.2 | H8918_SUB_PCB_1_V1.3 | Missing |
| X6880 | H8912_MAIN_PCB_V1.1 | H8912_SUB_PCB_1_V1.1 | Missing |

## Outputs

- `assets/vision-reference-gallery/index.html`
- `assets/vision-reference-gallery/<model>/source-pages/`
- `assets/vision-reference-gallery/<model>/embedded/`
- `knowledge-base/vision-reference-gallery.json`
- `knowledge-base/vision-reference-review.json`
- `scripts/build_vision_reference_gallery.py`
- `tests/test_build_vision_reference_gallery.py`

## Next Step

When physical-board photos arrive, add them as strong references with known model, board revision, and board side. The first recognition demo should then test photo quality, model/side matching, and point-map alignment against these references.
