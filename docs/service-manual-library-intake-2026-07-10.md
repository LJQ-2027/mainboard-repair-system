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

1. KM4, KL4, CLA5, KJ5, CM5, CM6, and X6880 overlap with existing structured models.
2. Extract board-photo pages and model/board identifiers from those manuals first.
3. Build reference-image candidates for the visual-recognition demo.
4. Add newly covered models only after their model aliases and board versions are identified.

The complete per-file inventory, hashes, duplicate mappings, model tags, and parse checks are stored in `knowledge-base/service-manual-library-2026-07-10.json`.
