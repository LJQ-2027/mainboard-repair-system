# BG6H/F069 Real-Case Pilot Design

## Objective

Compile the existing BG6H/F069 main-board engineering sources into the reusable
2.5D board contract, then make that exact board identity available to the
controlled visual and repair-case pipelines. The first pilot uses the F069
V1.2 point map and schematic already preserved in the Top20 package. It does
not silently reuse the different BG6M/F069M V1.0 board.

## Source Identity

- Stable board key: `bg6h-f069`
- Board ID: `BOARD-F069-MAIN-V1.2`
- Source model identity: `BG6H`
- Main board revision: `F069_MAIN_PCB_V1.2`
- Point map: `F069_MAIN_PCB_V1.2_位号图_20230823（A4）.pdf`
- Schematic: `F069_MAIN_PCB_V1.2 维修原理图 20230804.pdf`
- Repair guide: `TECNO_J6563_BG6h-F069_维修操作指导书_V1.0_20231108.docx`

The overseas case table names the device `BG6`, while the engineering package
names it `BG6H/BG6h/J6563`. The board compiler may proceed because the board
revision is exact. `BG6` is not added to `compatible_models` and those case
revisions are not staged until Milo confirms that the collection label refers
to the BG6H sales model rather than a different model.

## Board Package

The existing generic board compiler renders and compiles the two source pages.
It publishes:

- `assets/board-atlas/bg6h-f069/main-point-map-page-1.png`
- `assets/board-atlas/bg6h-f069/main-point-map-page-2.png`
- `knowledge-base/f069-board-compiled-page-1.json`
- `knowledge-base/f069-board-compiled-page-2.json`
- `knowledge-base/f069-board-sides.json`
- `knowledge-base/f069-schematic-compiled.json`
- `knowledge-base/f069-cross-source-registration.json`

The reviewed entity subset covers the processor, PMIC, storage, memory,
wireless connectivity, RF front end, display connector, rear/front camera
connectors, crystal, battery location, and USB input location. Exact schematic
links are required for every component except `VBAT1`, which remains an
explicit point-map-only measurement location because the exact standalone
schematic designator is absent.

## Registration Dataset

The cross-source dataset uses point-map geometry and exact standalone
schematic occurrences only. High/medium footprint candidates may receive the
existing category-based inspection profile. Low-confidence candidates remain
location-only and cannot claim package dimensions.

The repair guide is declared as an available source, but this increment does
not promote the older automatically generated SOP drafts into reviewed repair
flows. `repair_coverage.status` is `source_available_pending_review`, and
`repair_flows` remains empty until a source-page review produces bounded,
technician-facing steps.

The initial registration reference is `point_map_only`. The newly collected
photos are not bound during compilation because all F069 attachments are HEIC
and the governed source package currently accepts only JPEG, PNG, and WebP.

## Catalog And Acceptance

The board receives its own `repair-workbench-boards.json` entry and is loaded
through the same query contract as the existing five boards. The historic
five-board evidence remains valid, but the executable catalog audit becomes a
dynamic board-catalog acceptance artifact with a new audit ID and report
filenames. It must pass all existing cross-source, geometry, schematic, and
repair-boundary validation for six boards.

## Real-Case Boundary

Feishu CASE-002 through CASE-005 have photos but only in HEIC. CASE-006 has no
photo. None enters the append-only repair-case source in this increment.

The next admission sequence is:

1. Confirm `BG6` in the collection table is the same sales model as the source
   package identity `BG6H/BG6h`.
2. Add deterministic HEIC decoding that preserves the original bytes and
   records the derivative hash and conversion tool/version.
3. Stage exact source packages by declared role.
4. Audit the source library.
5. Stage repair-case revisions using the new `bg6h-f069` catalog identity.
6. Run physical registration acceptance only on selected photo packages.

No image becomes a Golden Sample, defect label, QC conclusion, or training
sample through board compilation or repair-case staging.

## Verification

- Profile tests prove exact source and output identities.
- Geometry tests prove both pages compile, reviewed identities remain on their
  source side, normalized outlines exist, and confidence limits are preserved.
- Schematic tests prove reviewed exact identities and the deliberate `VBAT1`
  exception.
- Registration tests prove no invented repair flow, measurement tolerance, or
  package inspection.
- Catalog tests prove F069 and F069M remain distinct.
- The complete Python and Node suites, JSON validation, diff check, and strict
  UTF-8 scan must pass.
- Browser QA opens `?board=bg6h-f069`, switches both sides, selects reviewed
  entities, and checks desktop and 390 px layouts with no runtime error or
  overflow.

