# BG6H/F069 Real-Case Pilot Implementation Plan

**Goal:** Add the exact F069 V1.2 board to the source-driven 2.5D catalog and
prepare the controlled real-case path without conflating BG6H/F069 with
BG6M/F069M or promoting HEIC photos into unsupported evidence.

## Task 1: Lock The Board Identity In Tests

- Extend `tests/test_board_profiles.py` with the exact profile contract.
- Add `tests/test_compile_f069_board.py` for both point-map pages and schematic
  recovery.
- Add `tests/test_build_f069_registration.py` for source-bounded entities and
  repair coverage.
- Extend `tests/board-catalog-state.test.mjs` so F069 and F069M resolve as
  separate boards.
- Run the focused tests and confirm they fail because the new profile and
  outputs do not exist.

## Task 2: Add And Compile The Board Profile

- Add `bg6h-f069` to `knowledge-base/board-compiler-profiles.json`.
- Use the exact Top20 point-map, schematic, and repair-guide paths.
- Render both engineering textures and compile geometry, side manifest, and
  schematic output with `scripts/compile_board.py`.
- Inspect both rendered textures and compiler audits.

## Task 3: Build The Cross-Source Dataset

- Add `scripts/build_f069_registration.py`.
- Bind only the reviewed entity subset to source-side geometry and exact
  schematic occurrences.
- Keep `VBAT1` point-map-only, exclude low-confidence inspection profiles, and
  leave repair flows empty with `source_available_pending_review`.
- Validate and publish `knowledge-base/f069-cross-source-registration.json`.

## Task 4: Add Catalog And Dynamic Acceptance

- Add the independent `bg6h-f069` board-catalog entry.
- Version the executable catalog acceptance away from the historical
  five-board name and generate deterministic six-board reports.
- Update runtime/deployment allowlists only where the new board assets are
  required.

## Task 5: Verify And Record The Pilot

- Run focused Python and Node tests.
- Run the complete Python and Node suites.
- Run the board compiler, dataset validator, catalog acceptance, JSON/diff,
  and UTF-8 checks.
- Start the local server and perform desktop/mobile browser QA for
  `?board=bg6h-f069`.
- Record exact outputs, evidence boundaries, the BG6/BG6H identity gate, and
  the HEIC follow-up in project documentation.

