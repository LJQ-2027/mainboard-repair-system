# XK67J Shared-Board Compatibility Audit

Date: 2026-07-31

## Decision

The KM5 engineering package is accepted as the reference for one shared XK67J
board platform used by KM4n, KM4k, KM5, KM5n, and KM5s.

This is a board-platform compatibility decision, not a claim that the five sales
models have identical BOM, firmware, peripherals, component values, or repair
policy. KM5 is the source model, KM4n is physically checked, and KM4k, KM5n,
and KM5s are owner-confirmed aliases pending their own photo or revision checks.

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
- Variant-aware sales-model aliases: `KM4n`, `KM4k`, `KM5`, `KM5n`, and `KM5s`.
- Compile normalized two-side board geometry and footprint candidates.
- Compile exact schematic designator occurrences from the V1.0B source.
- Register the three unique KM4n photo byte streams after board compilation.
- Link source red-box regions only as source annotations pending designator review.

## Prohibited inference

- Do not rewrite the source revision from V1.0B to V1.0.
- Do not claim exact BOM/population equality across the five sales models.
- Do not infer component values, firmware behavior, peripheral configuration, or
  model-specific repair instructions from the shared layout alone.
- Do not create a Golden Sample, defect label, training label, or repair-causality
  conclusion from this compatibility decision.

## Implementation result

The first compiler increment is complete:

- catalog profile `xk67j-main-v1.0b` exposes the five aliases with separate
  evidence levels;
- the two Main Placement pages compile to 319 and 721 accepted designators,
  for 1,040 positions in total;
- the 28-page Main SCH compiles to 505 linked designators and 524 occurrences;
- twelve reviewed repair entities have both Placement locations and exact SCH
  page links;
- the seven-board batch acceptance gate passes all seven catalog profiles; and
- desktop plus 390 px browser QA passes point-map/model switching, both board
  sides, component selection, pan/drag, readable responsive layout, and zero
  runtime errors.

The Placement PDF describes package outlines primarily as path line segments,
not standard rectangle operators. The conservative compiler therefore recovered
zero footprint candidates. This does not mean that the source contains no
components; it means that the current automated result supports normalized
locations and board outline only. The workbench deliberately uses small generic
location geometry and does not claim exact package size or height.

All three independent KM4n image byte streams are complete-board repair-case
views. Two contain source red rectangles; those rectangles remain source
annotations, not defect labels. Automatic ORB/AKAZE registration against the
line-art point maps produced no valid candidate:

- exposed side, image `1a3e4b...`: ORB 45 matches / 10 inliers; AKAZE 40 / 4;
- shield side, image `57a9b1...`: ORB 22 / 4; AKAZE 30 / 5; and
- exposed side, image `28a193...`: ORB 54 / 20 but invalid projected shape;
  AKAZE 45 / 3.

Each photo is preserved as `manual_registration_required`. No reviewed
homography, Golden Sample, defect label, training row, field-accuracy result, or
repair causality has been created. The next evidence action is reviewed manual
four-point registration with independent check points; the next knowledge action
is a source-backed XK67J repair workflow, if one is supplied and reviewed.
