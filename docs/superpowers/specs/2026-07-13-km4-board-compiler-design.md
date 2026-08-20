# KM4/F151 Board Compiler Design

## Objective

Convert the supplied KM4/F151 point-map PDF into a source-traceable normalized board dataset that can drive the 2.5D model, photo registration, and later visual QC. The compiler replaces raster color guesses and manual per-board geometry with repeatable PDF extraction.

## Inputs And Outputs

The first input is `F151_MAIN_PCB_V1.2_位号图.pdf`. The compiler reads the page Form XObject, drawing operations, embedded font CMap, text placement matrices, rectangles, and paths.

The output records:

- source PDF, page, XObject, and coordinate bounds;
- decoded designator labels and source coordinates;
- normalized board coordinates;
- candidate footprint rectangles with extraction confidence;
- unresolved vector geometry retained without invented semantics;
- explicit compiler warnings and source evidence.

SCH and repair-manual compilation remain separate adapters that later enrich the same stable component identities.

## Extraction Pipeline

1. Locate the largest `/Form` XObject on the requested PDF page.
2. Parse its `/ToUnicode` CMap and decode `Tj`/`TJ` text objects.
3. Maintain the PDF graphics-state stack and concatenate `cm` transforms.
4. classify designators using board-specific prefix rules; reject BGA grid labels such as `A13`.
5. Extract transformed `re` rectangles and path bounds.
6. Pair each designator with a nearby plausible footprint using containment, distance, size, and uniqueness.
7. Normalize source coordinates to the Form XObject bounding box and preserve source-space coordinates for audit.
8. Emit deterministic JSON and validation statistics.

## Accuracy Boundary

The compiler may classify a label as a designator only when it decodes from the PDF font map and matches accepted board-designator syntax. Geometry without a reliable label remains unresolved. A candidate footprint is never treated as an exact package dimension unless the PDF relationship is unambiguous.

No Placement, BOM, Gerber, or PCB CAD is available. Therefore the output is a repair-grade normalized geometry model, not a manufacturing CAD reconstruction.

## Initial Acceptance

- Decode at least 90% of text objects supported by the embedded CMap.
- Recover all seven currently reviewed KM4/F151 page-2 entities.
- Emit deterministic normalized coordinates for every accepted designator.
- Associate candidate footprints where evidence is sufficient and preserve unresolved labels otherwise.
- Pass unit tests for CMap decoding, matrix transforms, designator filtering, rectangle extraction, and deterministic compilation.
