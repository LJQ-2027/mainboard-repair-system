# Shared BGA Component Visual Design

**Date:** 2026-07-31

**Status:** Approved for implementation by Milo's instruction to proceed without repeated confirmation

## Objective

Move the reviewed U4000 and U0600 package visuals from renderer-owned BGA geometry into the reusable `ComponentVisualSpec` pipeline. Preserve every other reviewed BGA profile that currently depends on the same renderer branch, while keeping U2001 as a separately named PMIC visual specification on the shared `ic_bga` compiler.

## Current State

The reusable component-visual pipeline currently supports:

- `connector-j6101-repair-visual-v1` through the `connector` compiler;
- `ic-bga-u2001-repair-visual-v1` through the `ic_bga` compiler;
- strict family validation;
- deterministic board and isolated detail levels;
- descriptor-bound geometry;
- independent resource ownership and exact disposal;
- fail-soft generic package fallback.

The renderer still owns `addInspectionBgaPackage()`. It is selected by `visualAsset === 'reviewed-bga'` and currently serves:

- `u4000-emmc-v1` on KM4/F151;
- `u0600-rf-device-v1` on KM4/F151;
- `connectivity-bga-v1` on H8918, H6929, F069, and F069M.

Deleting that renderer branch without migrating all three profile ids would silently degrade reviewed packages on other boards to the generic IC fallback.

## Source Boundary

The reviewed datasets establish only:

- package identity and designator;
- an IC/BGA category;
- normalized board footprint;
- category-based repair-visual fidelity;
- source notes that explicitly reject measured package dimensions, ball counts, pad layout, and internal construction.

They do not establish:

- exact package family or vendor package;
- exact ball count, pitch, or array;
- bottom-side pad layout;
- exact package marking;
- exact pin-one location;
- die or internal structure;
- millimeter dimensions.

The visible direction cue remains a generic orientation aid. Its stable positive-quadrant position (`offset_x: 0.31`, `offset_y: 0.31`) is not source-confirmed and must not be described as Pin 1 or a pin-one marker.

## Options Considered

### Option A: Add all BGA profiles to the U2001 specification

This minimizes code and would make all reviewed BGA packages use one spec id.

Rejected because `ic-bga-u2001-repair-visual-v1` is explicitly a U2001 PMIC identity. Mapping storage, RF, and connectivity packages to that id would pollute provenance and make browser diagnostics misleading.

### Option B: Add one shared BGA specification beside U2001

Create `ic-bga-shared-package-repair-visual-v1` for:

- `u4000-emmc-v1`;
- `u0600-rf-device-v1`;
- `connectivity-bga-v1`.

The specification uses the existing `ic_bga` family contract and compiler. U2001 retains its own spec id and normalized hierarchy.

Chosen because it proves both forms of reuse:

- multiple specs use one family compiler;
- multiple profile ids use one shared spec.

### Option C: Replace the old BGA geometry with Blender/GLB

Rejected for this increment. Current sources do not justify package-specific authored geometry, and GLB loading/versioning is a separate deferred architecture concern.

## Specification

Add `SHARED_BGA_VISUAL_SPEC`:

```js
{
  spec_id: 'ic-bga-shared-package-repair-visual-v1',
  version: 1,
  asset_type: 'procedural',
  family: 'ic_bga',
  inspection_profiles: [
    'u4000-emmc-v1',
    'u0600-rf-device-v1',
    'connectivity-bga-v1',
  ],
  source_status: 'category_based',
  fidelity: 'repair_visual',
}
```

The visible hierarchy remains:

- substrate;
- molded body;
- inset top;
- generic orientation cue;
- isolated-only substrate/body/top edge treatment.

The marker uses the normalized positive-quadrant offset `offset_x: 0.31` and `offset_y: 0.31`. This placement is only a stable generic cue, not a claim about Pin 1 or the package's real orientation.

The shared BGA structure may preserve the current reviewed-BGA proportions where they fit the normalized family contract. It must remain inside descriptor bounds for every valid descriptor.

The specification uses the complete IC/BGA prohibited-claim set already enforced by the validator.

## Catalog Contract

`buildComponentVisualSpecCatalog()` remains the single profile-to-spec registry.

Required behavior:

- all three shared BGA profiles resolve to the exact same frozen specification object;
- U2001 still resolves to `U2001_PMIC_VISUAL_SPEC`;
- J6101 still resolves to `J6101_CONNECTOR_VISUAL_SPEC`;
- duplicate profile ids across any specs fail catalog construction;
- production catalog construction includes all three approved specs.

No designator-specific condition may appear in the catalog, builder, or renderer.

## Builder Contract

The existing `ic_bga` compiler remains unchanged unless tests reveal a genuine shared-family defect.

Required behavior for U4000, U0600, and connectivity descriptors:

- board detail contains `substrate`, `body`, `top`, and `orientation-marker`;
- isolated detail adds only `substrate-edges`, `body-edges`, and `top-seam`;
- each build reports `ic-bga-shared-package-repair-visual-v1`;
- geometry is deterministic and descriptor-bound;
- different descriptors and repeated builds do not share mutable geometry or materials;
- disposal is exact and idempotent;
- names and metadata contain no ball, pad, marking, lead, vendor, die, internal, or millimeter claim.

## Renderer Migration

Delete `addInspectionBgaPackage()`.

`createPackageMesh()` continues to:

1. call `buildComponentVisual(descriptor, detailLevel)`;
2. return the reusable group when a registered spec succeeds;
3. preserve the stable fallback reason when it does not;
4. use `addIcPackage()` for any IC descriptor without a valid reusable spec.

Keep `reviewed-bga` as provenance-compatible `visualAsset` metadata for the UI and browser diagnostics. Do not use it to select geometry.

Executable renderer tests must prove:

- U4000 and U0600 use the shared spec;
- a connectivity profile uses the same shared spec;
- an unknown reviewed-BGA profile returns a nonblank generic IC;
- generic fallback resources are disposed exactly once;
- no renderer-owned BGA function or `visualAsset === 'reviewed-bga'` geometry branch remains.

## Data Compatibility

No knowledge-base JSON is changed in this increment.

Existing profile ids remain stable. The migration is resolved at render time through the component-visual catalog, so:

- KM4 U4000/U0600 retain their source identity and repair links;
- H8918/H6929/F069/F069M connectivity packages retain their source identity;
- `inspectionVisualAsset` remains `reviewed-bga`;
- new browser metadata exposes the shared `componentVisualSpec`;
- existing saved repair or inspection state remains compatible.

## UI And Interaction

No new control or workflow is introduced.

The existing interaction contract must remain:

- first activation selects;
- repeated activation enters single-component inspection;
- unrelated board context becomes transparent;
- mouse and one-finger drag rotate the isolated package;
- wheel and pinch zoom;
- reset retains inspection;
- return restores board state;
- board and isolated metadata update transactionally.

P3 must cover U4000 and U0600 at desktop and mobile widths, plus one non-KM4 connectivity-BGA route if its existing board route is locally available.

## Validation

### P0

- catalog resolution and identity tests;
- shared profile object identity;
- deterministic builder output;
- bounds and resource ownership;
- executable renderer replacement and fallback.

### P1

- complete Node suite;
- source-bound Python registration/compiler/static-route suite.

### P2

- syntax checks;
- `git diff --check`;
- strict UTF-8 and U+FFFD scan.

### P3

- real KM4 route at 1600x900 and 390x844;
- U4000 and U0600 board/isolated states;
- mouse/touch rotation, wheel/pinch zoom, reset, return, re-entry;
- selected/hover/focus readability;
- overlap, clipping, overflow, console, and page errors;
- J6101 and U2001 regression;
- nonblank canvas pixel checks.

### P4

Not applicable. This increment changes no API, server, database, deployment, external integration, or real evidence.

## Acceptance Criteria

1. U4000, U0600, and connectivity BGA profiles resolve to `ic-bga-shared-package-repair-visual-v1`.
2. U2001 retains `ic-bga-u2001-repair-visual-v1`.
3. All reviewed BGA profiles use the reusable `ic_bga` compiler.
4. `board-renderer.js` contains no renderer-owned BGA geometry.
5. Invalid or unknown reviewed-BGA profiles retain a nonblank generic IC fallback.
6. No knowledge-base profile id or repair relationship changes.
7. J6101 and U2001 behavior remains unchanged.
8. Automated and browser validation passes.
9. Documentation preserves the category-based, non-CAD boundary.

## Deferred

- X2100 crystal migration;
- Blender/GLB asset loading and versioning;
- exact markings or bottom-side geometry;
- package-specific pin-one claims;
- board-wide component refinement;
- field-accuracy or visual-defect claims.
