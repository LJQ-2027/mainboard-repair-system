# KJ6 / KM4 / KM4s Engineering Source Intake

Date: 2026-07-31

## Result

The owner-supplied folder contained eight PDF files. Four F151 files are exact
SHA-256 duplicates of the existing KM4/F151 package. Four files add new source
coverage:

| Product | Board | New coverage | Status |
| --- | --- | --- | --- |
| TECNO KJ6 | H897 MAIN V1.2 | two-page placement plus 28-page schematic | mainboard compiler may start |
| TECNO KM4s | H6932 SUB PCB 1 V1.0 | two-page placement plus three-page schematic | sub-board reference only |
| TECNO KM4 | F151 MAIN/SUB | no new bytes | existing canonical package retained |
| TECNO KM4n | XK67J MAIN V1.0 | none | exact-reference gate remains blocked |

## H897 validation

- Placement: two landscape vector pages with extractable designator text,
  board outlines, package outlines, pads, holes, and side-specific geometry.
- Schematic: 28 pages with extractable designator/net text and readable vector
  drawings.
- The source identity is exact `H897 MAIN V1.2`; it matches the board marking
  and KJ6 case records already preserved from Feishu.
- The files can be processed by the existing normalized-coordinate point-map
  compiler and schematic adapter. A new board profile, reviewed side mapping,
  and source-bounded entity/repair-flow selection are still required before the
  board appears in the technician workbench.

## Boundaries

- The H897 engineering reference removes the prior registration/reference gate
  for KJ6 only. It does not itself register or label any repair-case photo.
- Existing red rectangles in source photos remain source-provided annotations,
  not defect labels or automated detections.
- H6932 is explicitly sub-board-only in this intake. No KM4s mainboard modeling
  claim is allowed from it.
- KM4/F151 cannot substitute for KM4n/XK67J, and the XK67J reference gate remains
  open.

## Next implementation increment

1. Add `KJ6-H897` to the board catalog with reviewed logical side mapping.
2. Compile both placement pages into normalized footprints and board geometry.
3. Compile exact schematic designator occurrences.
4. Select only source-supported repair entities and flows.
5. Register the eight unique H897 repair-case images as supporting evidence;
   treat shielded or cropped images according to their actual visibility.
6. Run the existing board batch audit and desktop/mobile interaction QA before
   making H897 available to technicians.

