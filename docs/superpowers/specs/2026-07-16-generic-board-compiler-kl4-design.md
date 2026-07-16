# Generic Board Compiler and KL4 Pilot Design

## Objective

Prove that the digital-board pipeline is reusable beyond KM4 by compiling the KL4/F201 main board from the same source-driven core and opening it in the existing technician workbench. The pilot must produce two board sides, schematic links, a reviewed component subset, and one source-backed small-current no-power repair flow without duplicating KM4 compiler logic.

## Scope

This increment includes:

- a validated board-profile format;
- a generic point-map and schematic compilation entry point;
- compatibility wrappers for the existing KM4 commands and outputs;
- KL4/F201 page textures, dual-side geometry, side manifest, and schematic index;
- a KL4 cross-source registration dataset for a reviewed component subset;
- the KL4 small-current no-power path from repair-guide pages 10-11;
- board-catalog-driven workbench loading through a board query parameter;
- automated data, regression, and browser validation.

This increment does not include physical-board defect recognition, inferred net connectivity, automatic interpretation of ambiguous flowchart arrows, exact CAD geometry, or unreviewed component functions. The installed-board service-manual image remains a provisional visual reference rather than a clean front/back physical-board pair.

## Source Selection

KL4/F201 is the second-board pilot because its package contains the main repair guide, 24-page main schematic, two-page main point map, sub-board materials, and reviewed installed-board references. It is also the third-ranked L4 model in the current source inventory with 508 records.

The initial repair flow is the small-current no-power branch on repair-guide pages 10-11. Its reviewed source sequence is:

1. Measure VDDCORE and VDDEMMCCORE.
2. If the technician judges the rails normal, measure X2100 output at 26 MHz.
3. Follow only the action or stop boundary explicitly shown by the guide.

Nominal values without tolerances remain technician-judged. The compiler must not convert proximity, repeated labels, or schematic co-occurrence into electrical connectivity.

## Approaches Considered

### Duplicate the KM4 scripts

This is fastest for KL4 but preserves model names, output paths, and quality thresholds in copied code. A third board would require another copy and make regression behavior diverge. Rejected.

### Configuration-driven generic compiler

A board profile supplies identity, source paths, side pages, texture outputs, reviewed designators, and quality gates. Shared code compiles every board, while small compatibility wrappers preserve existing KM4 commands. This has a moderate migration cost and directly proves reuse. Selected.

### Fully automatic source discovery

The pipeline could guess board identity, page roles, outputs, and reviewed entities from filenames and PDF structure. Current source packages contain inconsistent names, shared board platforms, and revision ambiguity, so silent misclassification would be more dangerous than explicit configuration. Deferred.

## Architecture

### Board profiles

`knowledge-base/board-compiler-profiles.json` is the source-controlled registry for compiler inputs. Each profile declares:

- `profile_id`, `model`, `board_id`, `board_version`, and component prefix;
- point-map and schematic source paths;
- default side and ordered side definitions;
- source PDF page, display label, texture output, compiled-data output, and crop bounds per side;
- reviewed designators required on each side and in the schematic;
- manifest, schematic, and cross-source output paths;
- visual reference path and its explicit accuracy boundary.

Profile validation rejects duplicate identities, missing files, non-normalized crop bounds, duplicate side pages, unresolved default sides, outputs outside the repository, and reviewed designators that are not uppercase standalone identifiers.

### Generic compilation service

`scripts/board_compiler/pipeline.py` owns profile validation, deterministic texture rendering, point-map compilation, side-manifest generation, and schematic indexing. It reuses the existing PDF primitive, outline, designator, and schematic modules. It accepts a repository root and profile object so tests can use temporary fixtures.

`scripts/compile_board.py --profile <profile_id>` is the public command. `--geometry-only`, `--schematic-only`, and `--side <side_id>` limit work without changing output contracts. The command prints a JSON audit and exits nonzero when a required designator, source file, board identity, or output invariant fails.

`scripts/compile_km4_board.py` and `scripts/compile_km4_schematic.py` remain compatibility wrappers. They load the KM4 profile and delegate to the generic pipeline, preserving current output paths and KM4 tests.

### Compiled outputs

Each board produces the same contracts already consumed by the renderer:

- one engineering texture and geometry JSON per side;
- one ordered side manifest;
- one schematic occurrence index;
- one cross-source registration dataset;
- one board-catalog entry describing the URLs needed by the workbench.

Generated JSON retains normalized coordinates and source provenance. It contains no guessed package type, function, net, measurement tolerance, or repair action.

### Workbench loading

`knowledge-base/repair-workbench-boards.json` maps a stable board key such as `km4-f151` or `kl4-f201` to the cross-source, default geometry, schematic, shield, atlas, and side-manifest URLs. The workbench reads `?board=<key>` and falls back to `km4-f151` only when the parameter is absent. An unknown key produces an explicit in-canvas load error and does not silently open another board.

The current page is not given a second model selector. In the complete product, model and board selection happen before this workbench; the query parameter is the standalone integration contract for the current prototype.

## KL4 Reviewed Dataset

The first KL4 dataset includes only source-recovered entities needed by the selected branch: U1001, U2001, X2100, VDDCORE, and VDDEMMCCORE when those standalone designators or test labels are recovered from the point map and schematic. A missing required identity fails the pilot instead of being substituted with a nearby component.

Entity geometry comes from the compiled point map. Schematic links come from exact standalone text runs. Repair links cite the KL4 guide pages. Inspection profiles are added only when package family and visual treatment are supported by the reviewed sources; rail labels remain measurement locations.

The KL4 installed-mainboard image at `assets/vision-reference-gallery/kl4/embedded/page-010-image-02.jpg` is the initial photo reference. Registration is explicitly marked provisional because the manual does not provide an isolated two-side main-board pair.

## Data Flow

1. Load and validate the selected board profile.
2. Render and crop each configured point-map page deterministically.
3. Decode PDF labels and vector rectangles into normalized side geometry.
4. Extract the board outline from the corresponding rendered texture.
5. Index exact schematic occurrences for compiled point-map identities.
6. Verify all reviewed KL4 identities against geometry and schematic outputs.
7. Merge only reviewed repair semantics into the KL4 cross-source dataset.
8. Resolve the board key in the workbench catalog and load the unchanged interaction modules.

## Error Handling

- Missing source files, Poppler, PDF forms, or output directories fail before publishing partial manifests.
- A side is not published when its required identities are incomplete.
- Schematic compilation reports linked, unlinked, and reviewed-recovery counts separately.
- Existing generated files are replaced only after the complete requested compilation succeeds.
- Workbench fetch failures identify the board key and failed asset class in the model-local status area.
- Ambiguous repair branches terminate at an explicit boundary; they never choose an action automatically.

## Quality Gates

- KM4 generic-pipeline output remains semantically equivalent to the current committed datasets.
- KL4 compiles both configured point-map pages with nonzero designators, candidate geometry, and board outlines.
- Every normalized center, footprint, crop, outline point, and registration anchor stays within `[0, 1]`.
- Every reviewed KL4 identity resolves on its declared side and in exact schematic occurrences.
- Board IDs match across profile, geometry, manifest, schematic, catalog, and registration outputs.
- The KL4 small-current flow passes graph, measurement, source, and target validation.
- Existing Node and Python suites remain green.
- Headed Chromium opens both `?board=km4-f151` and `?board=kl4-f201`, switches sides, selects each reviewed entity, enters available inspection, advances the KL4 flow, and reports zero runtime errors or horizontal overflow at desktop and 390 px.

## Delivery Sequence

1. Introduce and validate the board-profile registry.
2. Extract the generic compilation pipeline and migrate KM4 wrappers without output drift.
3. Add KL4 textures, geometry, side manifest, and schematic output.
4. Add reviewed KL4 cross-source entities and the small-current no-power flow.
5. Add board-catalog-driven workbench loading.
6. Run complete data, regression, and browser validation and record the pilot evidence.

## Success Criterion

The increment is complete when one generic command can rebuild the KM4 and KL4 source-derived board packages, and the same workbench can execute the reviewed KL4 small-current no-power path without board-specific frontend code.
