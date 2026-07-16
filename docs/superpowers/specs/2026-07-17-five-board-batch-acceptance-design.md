# Five-Board Batch Acceptance Design

## Objective

Prove whether the current five board platforms form a sufficient reusable modeling baseline. The proof must come from an executable audit of committed source-derived outputs, not from board count alone.

## Selected Approach

Add a Python batch acceptance service that loads the board catalog and evaluates every board through the same contract. It produces deterministic JSON for tests and automation plus a concise Markdown report for project review.

A static checklist was rejected because it drifts from the datasets. Extending only the per-dataset validator was rejected because it cannot show which source arrangements and degradation paths the complete sample set covers.

## Acceptance Model

Each catalog board must pass these hard gates:

- catalog data, schematic, side manifest, and every side geometry path resolve;
- board identity agrees across registration, schematic, side manifest, and geometry outputs;
- catalog side ids exactly match manifest side ids and geometry keys;
- every geometry output contains a non-empty normalized board outline and accepted components;
- every reviewed registration entity resolves to its declared side and has source evidence;
- the existing cross-source validator returns no errors;
- repair coverage is either one or more validated flows or an explicit `source_unavailable` boundary;
- reference mode is either `photo_proxy` with a resolvable proxy or `point_map_only` without an invented photo requirement.

The report records non-failing coverage facts: physical source layout, compatible-model sharing, designator counts, schematic linkage, reviewed entities, repair-flow count, reference mode, and repair-coverage mode.

## Sufficiency Rule

The five-board baseline is sufficient for the current source-to-2.5D platform when all boards pass and the aggregate covers all of these risk classes:

1. at least five catalog boards;
2. more than one sales model sharing a board platform;
3. both photo-proxy and point-map-only references;
4. both repair-flow and reference-only repair coverage;
5. both shared multi-page and independent per-side point-map sources;
6. source-named sides beyond only `main_page_1` / `main_page_2`;
7. reviewed entities that intentionally remain location-only because geometry confidence is insufficient.

This sufficiency result applies only to the reusable modeling and source-linking pipeline. It does not prove visual defect recognition, physical-photo registration accuracy, CAD geometry, electrical connectivity inference, or field repair effectiveness.

## Outputs

- `scripts/board_batch_acceptance.py`: reusable audit and report rendering functions plus CLI.
- `tests/test_board_batch_acceptance.py`: hard-gate and aggregate-coverage tests.
- `reports/five-board-batch-acceptance.md`: deterministic human-readable evidence.
- `reports/five-board-batch-acceptance.json`: deterministic machine-readable evidence.

The CLI exits nonzero when a board fails a hard gate or the aggregate does not satisfy the declared risk coverage. It writes no report until the complete audit succeeds.

## Verification

Focused tests must first fail before implementation. Completion requires focused tests, the full Python and Node suites, dataset validation through the batch audit, UTF-8 checks, and `git diff --check`.

