# KM5 / KM4n XK67J Shared-Board Compatibility Audit

Date: 2026-07-31

## Decision

The KM5 engineering package is accepted for the KM4n cases as one shared XK67J
board-platform reference.

This is a board-platform compatibility decision, not a claim that KM5 and KM4n
are the same sales model or have identical BOM, firmware, peripherals, component
values, or repair policy.

## Evidence

| Layer | KM4n evidence | KM5 engineering source | Result |
| --- | --- | --- | --- |
| Board identity | physical silkscreen `XK67J_MAIN V1.0` | source PCB `XK67J_L6735-KM5_MAIN_PCB_V1.0B.pcb` | same XK67J platform; suffix retained |
| Main outline | photographed asymmetric outline and dual upper cut-outs | same normalized outline on both Placement pages | match |
| Mechanical landmarks | photographed major holes, SIM region, lower connectors, right-side cut-out | corresponding holes and `J6503`, `J6502`, `J6501`, `J6102`, `J6402`, `J2810` regions | match |
| Exposed component side | large left memory package, central power region, dense right RF/baseband region | `U4002`, `U2001`, `U3001`/`U3101` regions in the same arrangement | match |
| Shield/SIM side | full SIM assembly and shield-can layout | Page 1 package and shield regions align | match |
| Source usability | three unique KM4n image byte streams | two-page vector Placement and 28-page SCH | sufficient for compiler and reviewed registration |

An exploratory ORB comparison between vector drawings and physical photos was
weak because shields, source annotations, and line-art/raster appearance differ.
It is not used as compatibility proof. The decision rests on exact board identity
plus reviewed two-side structural landmarks.

## Allowed use

- One catalog board platform: `XK67J`.
- Variant-aware sales-model aliases: `KM5` and `KM4n`.
- Compile normalized two-side board geometry and footprint candidates.
- Compile exact schematic designator occurrences from the V1.0B source.
- Register the three unique KM4n photo byte streams after board compilation.
- Link source red-box regions only as source annotations pending designator review.

## Prohibited inference

- Do not rewrite the source revision from V1.0B to V1.0.
- Do not claim exact BOM/population equality across KM5 and KM4n.
- Do not infer component values, firmware behavior, peripheral configuration, or
  model-specific repair instructions from the shared layout alone.
- Do not create a Golden Sample, defect label, training label, or repair-causality
  conclusion from this compatibility decision.

## Next implementation increment

1. Add `XK67J` as a shared board-catalog profile with KM5/KM4n aliases and an
   explicit V1.0/V1.0B compatibility note.
2. Compile both Main Placement pages and the 28-page Main SCH.
3. Run the existing catalog/batch source audit.
4. Register and review the three unique KM4n image byte streams.
5. Keep any model-specific repair workflow unavailable until supporting source
   evidence is selected and reviewed.

