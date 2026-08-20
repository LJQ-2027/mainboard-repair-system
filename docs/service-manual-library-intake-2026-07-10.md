# Service Manual Library Intake - 2026-07-10

## Source

- Original folder: `C:\Users\Mercurluto\Desktop\manual`
- Project-local binary library: `source-materials/service-manual-library/2026-07-10-desktop-manual/files`
- Binary policy: local project copy, excluded from Git history
- Integrity: SHA-256 recorded for every source and stored file

## Inventory

- Source entries: 125
- Unique files stored: 119
- Exact duplicate groups: 6
- Unique size: 1.437 GB
- Parseable files: 125
- Parse errors: 0

## Project Overlap

These manuals overlap models already present in the repair project:

- `CLA5`
- `CM5`
- `CM6`
- `KJ5`
- `KL4`
- `KM4`
- `X6880`

## Use In The Project

The library is a new service-manual source layer. It can contribute:

- board and sub-board photographs embedded in service manuals;
- disassembly order and connector locations;
- module names and parts-placement context;
- model aliases and visual references for board-photo recognition;
- training and repair-context material complementary to schematics and point maps.

Service manuals do not replace placement drawings or schematics. Extracted claims must retain the source file and page reference.

## Next Extraction Priority

Initial priority extraction is complete for KM4, KL4, CLA5, KJ5, CM5, CM6, and X6880:

- 26 source pages extracted;
- 96 embedded-image candidates retained with source-page traceability;
- 21 images visually reviewed and approved as structure or installed-board references;
- no manual supplied a clean isolated front/back main-board pair.

The next priority is to add physical-board photos supplied from the field, then align them with the approved manual references and existing point maps.

The complete per-file inventory, hashes, duplicate mappings, model tags, and parse checks are stored in `knowledge-base/service-manual-library-2026-07-10.json`.

The extracted visual library is stored in `knowledge-base/vision-reference-gallery.json` and `assets/vision-reference-gallery/`.
