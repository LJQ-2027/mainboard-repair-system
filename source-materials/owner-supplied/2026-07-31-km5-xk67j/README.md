# KM5 / KM4n shared XK67J engineering-source intake

Received from Milo on 2026-07-31 from the desktop folder `KM5`.

## Compatibility decision

The engineering package is accepted as the reference package for the shared
XK67J board platform used by KM5 and the photographed KM4n cases.

Evidence:

- KM4n physical-board photographs show `XK67J_MAIN V1.0` silkscreen.
- The placement source identifies
  `XK67J_L6735-KM5_MAIN_PCB_V1.0B.pcb`.
- Mainboard outline, dual upper cut-outs, holes, SIM area, board-to-board
  connectors, and major component regions match on both sides.
- Main Placement has two extractable vector pages; Main SCH has 28 pages.

## Boundary

`V1.0B` is not rewritten as an exact `V1.0` document identity. The package is
approved for shared-platform geometry, normalized footprints, schematic
occurrences, 2.5D modeling, and reviewed KM4n photo registration. Sales-model
identity, BOM/population differences, component values, firmware, peripherals,
and repair instructions remain variant-aware and require their own source
support.

