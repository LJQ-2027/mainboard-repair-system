# U2001 Multi-Family Component Visual Refinement Design

## Status

Approved for implementation by Milo's standing confirmation on 2026-07-31.

## Goal

Refine KM4/F151 U2001 into the second reusable `ComponentVisualSpec`
sample and prove that the visual pipeline supports more than the J6101
connector family.

The result must:

- preserve the reviewed U2001 identity, footprint, board side, repair links,
  and inspection behavior;
- add an `ic_bga` visual family without a U2001-specific renderer branch;
- keep J6101 behavior and visual output compatible;
- support deterministic board and isolated detail levels;
- retain fail-soft fallback and exact resource ownership;
- avoid unsupported package, ball-grid, marking, and internal claims.

## Source Boundary

Existing source material proves:

- designator `U2001`;
- category `bga_ic`;
- module `Power management`;
- board side `main_page_2`;
- normalized reviewed location and footprint;
- inspection profile `u2001-pmic-v1`;
- schematic occurrences and source-linked repair guidance;
- category-based repair-visual fidelity.

Existing source material does not prove:

- exact package family or vendor package code;
- measured package dimensions or layer heights;
- exact ball count, pitch, or bottom-side layout;
- solder-pad or solder-mask geometry;
- manufacturer markings or top-surface text;
- die, bond, substrate routing, or internal construction.

The visual must therefore remain a category-based repair-recognition model.
It may show a generic layered IC package, but cannot imply an engineering
digital twin.

## Chosen Architecture

### Family Compiler Registry

Keep one shared `ComponentVisualSpec` identity, metadata, validation, detail,
ownership, fallback, and disposal contract. Add a family compiler registry in
the DOM-free Three.js builder:

```text
family -> validator shape contract -> stage compiler

connector -> connector structure roles -> connector stages
ic_bga    -> IC/BGA structure roles    -> IC/BGA stages
```

The builder resolves a validated spec, selects the compiler by `spec.family`,
and executes the canonical stages:

1. `blockout`
2. `structure`
3. `material`
4. `polish`

Unknown families fail soft with a stable reason and preserve the existing
renderer fallback.

This design is preferred over a free-form primitive list because family
contracts remain auditable and source boundaries remain explicit. It is
preferred over Blender/GLB for this increment because current U2001 sources do
not establish package-specific geometry.

### Catalog

Add `U2001_PMIC_VISUAL_SPEC` and map `u2001-pmic-v1` to it.

Identity:

- `spec_id`: `ic-bga-u2001-repair-visual-v1`
- `family`: `ic_bga`
- `asset_type`: `procedural`
- `source_status`: `category_based`
- `fidelity`: `repair_visual`

Shared material tokens remain immutable. Add only semantic tokens needed by
the IC family, such as dark substrate, molded package, inset top, orientation
marker, and edge line. Tokens describe appearance, not vendor composition.

### U2001 Visual Hierarchy

Board detail:

- `substrate`
- `body`
- `top`
- `orientation-marker`

Isolated detail adds:

- `substrate-edges`
- `body-edges`
- `top-seam`

All dimensions are normalized ratios of the existing render descriptor's
bounded footprint and visual height.

The body uses a restrained rounded/chamfered package silhouette. The top is a
subtle inset surface rather than a fabricated label. The orientation marker is
a generic package-orientation cue and does not claim the actual manufacturer
marking, pin numbering, or exact corner convention.

No ball, pin, pad, solder, routing, die, or text geometry is allowed.

## Validation

The validator becomes family-aware without weakening the J6101 contract.

Each supported family declares:

- required material roles;
- required structure roles;
- the exact numeric shape of each structure role;
- permitted detail-part names;
- allowed source claims;
- family-specific prohibited claims.

Validation must reject:

- an unsupported family;
- connector roles in an `ic_bga` spec or IC roles in a connector spec;
- missing or additional structure fields;
- missing or unknown material roles;
- invalid normalized ratios;
- detail parts not produced by the selected family;
- duplicate profile mappings or duplicate detail parts;
- package-specific or engineering claims outside the source boundary.

Malformed input must never throw.

## Builder And Renderer

The builder owns:

- family dispatch;
- deterministic stages;
- normalized geometry;
- semantic materials;
- stable part metadata;
- bounds enforcement;
- exact geometry/material ownership and disposal.

The renderer continues to own:

- board placement and transforms;
- selection and picking;
- inspection entry/exit;
- camera and context opacity;
- browser QA metadata;
- fail-soft generic package fallback.

After migration, `addInspectionPmicPackage()` is removed from
`board-renderer.js`. U2001 must reach the renderer only through
`componentVisualSpecId` and the reusable builder.

Existing `reviewed-pmic` remains as the compatibility-facing visual asset
label for inspection metadata and browser selectors.

## Interaction And Failure Semantics

U2001 uses the existing transaction contract:

- build/capture/add/map failures before commit retain the previous visual;
- successful commit makes the new visual authoritative;
- cleanup failure after commit records a warning and never revives stale
  geometry;
- board-to-isolated and isolated-to-board transitions preserve component
  identity, transforms, selection maps, return behavior, and camera state;
- invalid U2001 specs render the existing generic IC package fallback rather
  than a blank component; the removed PMIC-specific geometry is not restored.

No new control, view, modal, or technician workflow is introduced.

## Testing

### Automated

- Catalog resolution and deep immutability for both families.
- Family-aware schema rejection and malformed-input fuzz coverage.
- Deterministic named parts and stages for U2001 board/isolated levels.
- Finite positive bounds within the descriptor footprint and height.
- No unsupported ball, pin, pad, solder, die, routing, or marking part names.
- Independent mutable resources across repeated builds.
- Exact, idempotent, fail-soft disposal.
- U2001 descriptor-to-spec mapping.
- J6101 catalog, validation, geometry, fallback, replacement, and interaction
  regression.
- Renderer source assertion that no U2001/PMIC procedural geometry remains.

### Browser

At desktop `1600x900` and mobile `390x844`:

- open KM4/F151 `main_page_2`;
- select U2001 and verify board detail metadata;
- enter isolated view and verify `reviewed-pmic`;
- confirm the layered package is visible and fully contained;
- rotate, zoom, reset, return, and Escape;
- verify board detail restoration and selected identity;
- re-check J6101 entry/exit;
- record nonblank canvas evidence, overflow, control readability, and runtime
  errors.

## Acceptance

The increment is complete only when:

1. U2001 resolves to `ic-bga-u2001-repair-visual-v1`.
2. Connector and IC/BGA specs are independently and strictly validated.
3. U2001 board and isolated visuals are visibly layered and deterministic.
4. `board-renderer.js` contains no U2001-specific PMIC geometry function.
5. Invalid U2001 specs retain a nonblank fail-soft fallback.
6. J6101 remains unchanged in behavior and source boundary.
7. Automated suites pass.
8. Desktop and mobile browser interaction and visual QA pass.
9. Documentation records exact verification and the non-CAD boundary.

## Deferred

- U4000/U0600 migration to a shared BGA spec.
- X2100 crystal migration.
- Blender/GLB asset loading and versioning.
- Package-specific markings or bottom-side geometry.
- Board-wide component refinement.
- Any field-accuracy or defect-recognition claim.
