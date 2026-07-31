# Shared BGA Component Visual Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate U4000, U0600, and the existing connectivity BGA profiles from renderer-owned geometry to one source-bounded shared BGA `ComponentVisualSpec`.

**Architecture:** Add one immutable shared specification to the existing catalog and reuse the validated `ic_bga` family compiler. Remove the renderer-owned BGA geometry branch while retaining `reviewed-bga` as provenance metadata and the generic IC as a nonblank fail-soft fallback.

**Tech Stack:** JavaScript ES modules, Three.js, Node.js test runner, Python unittest, installed Chrome with Playwright fallback, static browser application.

---

## File Structure

- Modify `assets/cross-source-registration/component-visual-specs.js`: add and register the shared BGA specification.
- Modify `assets/cross-source-registration/board-renderer.js`: remove renderer-owned BGA geometry and keep generic IC fallback.
- Modify `tests/component-visual-specs.test.mjs`: verify shared profile identity, source boundary, immutability, and duplicate safety.
- Modify `tests/component-visual-builder.test.mjs`: verify shared BGA descriptors, deterministic scaling, bounds, ownership, disposal, and prohibited claims.
- Modify `tests/model-profiles.test.mjs`: verify descriptor-to-spec identity for all shared profiles.
- Modify `tests/model-toolbar.test.mjs`: verify removal of renderer-owned BGA geometry.
- Modify `tests/board-renderer-package-fallback.test.mjs`: execute shared visual and generic fallback behavior.
- Modify `docs/km4-cross-source-registration-2026-07-13.md`: record the delivered boundary and validation.
- Modify this plan as evidence is produced.
- Create ignored P3 evidence under `output/playwright/shared-bga-component-visual/`.

### Task 1: Add the shared BGA specification

**Files:**
- Modify: `tests/component-visual-specs.test.mjs`
- Modify: `assets/cross-source-registration/component-visual-specs.js`

- [x] **Step 1: Write failing shared-catalog tests**

Add imports and assertions equivalent to:

```js
import {
  SHARED_BGA_VISUAL_SPEC,
  U2001_PMIC_VISUAL_SPEC,
  resolveComponentVisualSpec,
} from '../assets/cross-source-registration/component-visual-specs.js';

test('reviewed storage RF and connectivity BGA profiles share one visual spec', () => {
  const profiles = [
    'u4000-emmc-v1',
    'u0600-rf-device-v1',
    'connectivity-bga-v1',
  ];
  profiles.forEach((profileId) => {
    assert.equal(resolveComponentVisualSpec(profileId), SHARED_BGA_VISUAL_SPEC);
  });
  assert.equal(
    SHARED_BGA_VISUAL_SPEC.spec_id,
    'ic-bga-shared-package-repair-visual-v1',
  );
  assert.notEqual(SHARED_BGA_VISUAL_SPEC, U2001_PMIC_VISUAL_SPEC);
});

test('shared BGA evidence boundary rejects package engineering claims', () => {
  assert.equal(SHARED_BGA_VISUAL_SPEC.family, 'ic_bga');
  assert.equal(SHARED_BGA_VISUAL_SPEC.source_status, 'category_based');
  assert.equal(SHARED_BGA_VISUAL_SPEC.fidelity, 'repair_visual');
  assert.match(SHARED_BGA_VISUAL_SPEC.boundary_note, /不代表/);
  [
    'exact_ball_count',
    'exact_ball_pitch',
    'exact_pad_layout',
    'vendor_package',
    'die_or_internal_structure',
    'package_marking',
  ].forEach((claim) => {
    assert.ok(SHARED_BGA_VISUAL_SPEC.acceptance.prohibited_claims.includes(claim));
  });
});
```

Also assert deep immutability and duplicate catalog rejection when any shared profile collides with another spec.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs
```

Expected: FAIL because `SHARED_BGA_VISUAL_SPEC` is not exported and the profiles do not resolve through the component-visual catalog.

- [x] **Step 3: Add the immutable shared BGA specification**

Add:

```js
export const SHARED_BGA_VISUAL_SPEC = Object.freeze({
  spec_id: 'ic-bga-shared-package-repair-visual-v1',
  version: 1,
  asset_type: 'procedural',
  family: 'ic_bga',
  inspection_profiles: Object.freeze([
    'u4000-emmc-v1',
    'u0600-rf-device-v1',
    'connectivity-bga-v1',
  ]),
  source_status: 'category_based',
  fidelity: 'repair_visual',
  boundary_note: 'BGA 类 IC 结构为维修识别示意，不代表准确封装、球数、球距、焊盘、丝印、内部结构、方向点或工程尺寸。',
  claims: Object.freeze([
    'ic_package_silhouette',
    'substrate_body_hierarchy',
    'generic_orientation_cue',
  ]),
  materials: Object.freeze({
    substrate: 'ic-substrate',
    body: 'molded-package',
    top: 'inset-top',
    marker: 'orientation-marker',
    edge: 'edge-line',
  }),
  structure: Object.freeze({
    substrate: Object.freeze({
      width: 1,
      depth: 1,
      height: 0.18,
      radius: 0.045,
    }),
    body: Object.freeze({
      width: 0.92,
      depth: 0.92,
      height: 0.66,
      radius: 0.065,
      lift: 0.18,
    }),
    top: Object.freeze({
      width: 0.72,
      depth: 0.68,
      height: 0.045,
      radius: 0.05,
      lift: 0.84,
    }),
    marker: Object.freeze({
      radius: 0.04,
      offset_x: 0.31,
      offset_y: 0.31,
      height: 0.02,
      lift: 0.89,
    }),
  }),
  detail_levels: Object.freeze({
    board: Object.freeze([
      'substrate',
      'body',
      'top',
      'orientation-marker',
    ]),
    isolated: Object.freeze([
      'substrate',
      'body',
      'top',
      'orientation-marker',
      'substrate-edges',
      'body-edges',
      'top-seam',
    ]),
  }),
  stages: Object.freeze(['blockout', 'structure', 'material', 'polish']),
  acceptance: Object.freeze({
    ratio_min: 0.02,
    ratio_max: 1,
    prohibited_claims: U2001_PMIC_VISUAL_SPEC.acceptance.prohibited_claims,
  }),
});
```

Register it in the production catalog beside J6101 and U2001. Do not add designator-specific logic.

- [x] **Step 4: Run the catalog suite and verify GREEN**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs
```

Expected: all catalog and validator tests pass for connector, U2001, and shared BGA specs.

- [x] **Step 5: Commit the catalog slice**

```powershell
git add assets/cross-source-registration/component-visual-specs.js tests/component-visual-specs.test.mjs
git commit -m "feat: add shared BGA component visual spec"
```

### Task 2: Prove shared-family compilation across descriptors

**Files:**
- Modify: `tests/component-visual-builder.test.mjs`
- Modify `assets/cross-source-registration/component-visual-builder.js` only if a failing test reveals a genuine family defect.

- [x] **Step 1: Write failing multi-profile builder tests**

Define representative descriptors:

```js
const U4000_DESCRIPTOR = Object.freeze({
  dimensions: Object.freeze({ x: 0.26, y: 0.22, z: 0.032 }),
  inspectionProfile: Object.freeze({ profile_id: 'u4000-emmc-v1' }),
});

const U0600_DESCRIPTOR = Object.freeze({
  dimensions: Object.freeze({ x: 0.2, y: 0.175, z: 0.032 }),
  inspectionProfile: Object.freeze({ profile_id: 'u0600-rf-device-v1' }),
});

const CONNECTIVITY_DESCRIPTOR = Object.freeze({
  dimensions: Object.freeze({ x: 0.11, y: 0.09, z: 0.032 }),
  inspectionProfile: Object.freeze({ profile_id: 'connectivity-bga-v1' }),
});
```

For every descriptor assert:

```js
assert.equal(
  group.userData.visualSpecId,
  'ic-bga-shared-package-repair-visual-v1',
);
assert.deepEqual(group.userData.visualPartNames, [
  'body',
  'orientation-marker',
  'substrate',
  'top',
]);
```

For isolated detail require the exact edge superset. Also assert:

- every build stays within descriptor bounds;
- snapshots are deterministic;
- resources are independently owned;
- disposal is exact and idempotent;
- no part or metadata claims balls, pads, leads, markings, vendor package, die, internals, or millimeter dimensions;
- U2001 still reports its own spec id and unchanged part set.

- [x] **Step 2: Run the focused builder test and verify RED**

Run:

```powershell
node --test tests/component-visual-builder.test.mjs
```

Expected: FAIL with `visual_spec_not_found` for the shared profiles.

- [x] **Step 3: Implement only defects exposed by the test**

The existing `ic_bga` compiler should compile the new spec without production-code changes. If it does not, fix only the family-general defect demonstrated by the failing assertion; do not introduce profile or designator branches.

- [x] **Step 4: Run builder and catalog tests and verify GREEN**

Run:

```powershell
node --test tests/component-visual-builder.test.mjs tests/component-visual-specs.test.mjs
```

Expected: all shared BGA, U2001, and J6101 tests pass.

- [x] **Step 5: Commit the builder proof**

```powershell
git add tests/component-visual-builder.test.mjs assets/cross-source-registration/component-visual-builder.js
git commit -m "test: prove shared BGA visual compilation"
```

If the builder requires no production change, stage only the test file.

### Task 3: Migrate descriptor and renderer ownership

**Files:**
- Modify: `tests/model-profiles.test.mjs`
- Modify: `tests/model-toolbar.test.mjs`
- Modify: `tests/board-renderer-package-fallback.test.mjs`
- Modify: `assets/cross-source-registration/board-renderer.js`

- [x] **Step 1: Write failing descriptor and renderer tests**

For each shared profile, build a reviewed BGA descriptor and assert:

```js
assert.equal(
  descriptor.componentVisualSpecId,
  'ic-bga-shared-package-repair-visual-v1',
);
assert.equal(descriptor.visualAsset, 'reviewed-bga');
assert.equal(descriptor.family, 'ic');
```

Update source assertions:

```js
assert.doesNotMatch(rendererSource, /function addInspectionBgaPackage/);
assert.doesNotMatch(rendererSource, /visualAsset === 'reviewed-bga'/);
assert.match(rendererSource, /else if \(descriptor\.family === 'ic'\) addIcPackage/);
```

Add executable `createPackageMesh()` assertions for U4000, U0600, and connectivity profiles. Add one missing-profile descriptor:

```js
{
  family: 'ic',
  visualAsset: 'reviewed-bga',
  dimensions: DIMENSIONS,
  inspectionProfile: { profile_id: 'missing-bga-spec' },
}
```

Require a nonblank generic IC, `visual_spec_not_found`, and exact generic disposal.

- [x] **Step 2: Run the focused renderer tests and verify RED**

Run:

```powershell
node --test tests/model-profiles.test.mjs tests/model-toolbar.test.mjs tests/board-renderer-package-fallback.test.mjs
```

Expected: descriptor identity tests fail until Task 1 is implemented; renderer source tests fail while `addInspectionBgaPackage()` remains.

- [x] **Step 3: Remove renderer-owned BGA geometry**

Delete `addInspectionBgaPackage()` and remove:

```js
if (descriptor.visualAsset === 'reviewed-bga') {
  addInspectionBgaPackage(group, descriptor);
}
```

Let the existing reusable-builder-first path return registered shared BGA groups. Let the existing `descriptor.family === 'ic'` branch provide generic fallback.

Do not remove `reviewed-bga` from `model-profiles.js`; it remains provenance/UI metadata.

- [x] **Step 4: Run renderer, replacement, and disposal regressions**

Run:

```powershell
node --test tests/model-profiles.test.mjs tests/model-toolbar.test.mjs tests/board-renderer-package-fallback.test.mjs tests/component-visual-builder.test.mjs tests/component-visual-replacement-state.test.mjs tests/component-visual-disposal-state.test.mjs
```

Expected: all tests pass; U4000/U0600/connectivity use the shared spec, unknown BGA profiles remain nonblank, and U2001/J6101 replacement behavior is unchanged.

- [x] **Step 5: Commit the renderer migration**

```powershell
git add assets/cross-source-registration/board-renderer.js tests/model-profiles.test.mjs tests/model-toolbar.test.mjs tests/board-renderer-package-fallback.test.mjs
git commit -m "refactor: route reviewed BGA profiles through visual builder"
```

### Task 4: Run full automated validation

**Files:**
- Modify only if validation reveals a defect owned by Tasks 1-3.

- [ ] **Step 1: Run JavaScript syntax checks**

```powershell
node --check assets/cross-source-registration/component-visual-specs.js
node --check assets/cross-source-registration/component-visual-validator.js
node --check assets/cross-source-registration/component-visual-builder.js
node --check assets/cross-source-registration/board-renderer.js
```

Expected: every command exits `0`.

- [ ] **Step 2: Run the complete Node suite**

```powershell
node --test tests/*.test.mjs
```

Expected: zero failures.

- [ ] **Step 3: Run source-bound Python tests**

```powershell
G:\Programming\mainboard-repair-system\.venv\Scripts\python.exe -m unittest tests.test_validate_cross_source_registration tests.test_compile_km4_board tests.test_ai_proxy_static -v
```

Expected: all 27 tests pass.

- [ ] **Step 4: Run repository and encoding checks**

```powershell
git diff --check
git status --short
```

Strictly decode every changed text file as UTF-8 and reject U+FFFD.

### Task 5: Perform desktop and mobile P3

**Files:**
- Evidence only: `output/playwright/shared-bga-component-visual/`
- Modify implementation files only if browser QA reveals a defect.

- [ ] **Step 1: Verify the real local route**

Open:

```text
http://127.0.0.1:8899/assets/cross-source-registration/?board=km4-f151
```

Confirm HTTP 200 and no startup error.

- [ ] **Step 2: Verify desktop shared BGA states**

At 1600x900:

1. select U4000;
2. verify board metadata and enter isolation;
3. rotate, pan where available, zoom, reset, return, and re-enter;
4. repeat for U0600;
5. confirm both report `ic-bga-shared-package-repair-visual-v1`;
6. confirm `inspectionVisualAsset=reviewed-bga`;
7. confirm fallback and cleanup diagnostics are empty;
8. regress U2001 and J6101;
9. inspect hover, selected, focus, return, and control readability;
10. confirm no labels or controls overlap.

- [ ] **Step 3: Verify mobile touch states**

At 390x844:

1. select U4000 and U0600 from the entity list;
2. enter isolation;
3. exercise native one-finger rotation and two-finger pinch;
4. reset and return;
5. confirm the return action stays visible;
6. confirm no horizontal overflow, clipping, or overlap.

- [ ] **Step 4: Verify one connectivity-BGA board**

Open one catalog route containing `connectivity-bga-v1`, select its reviewed package, and confirm it reports the same shared spec without runtime errors. If the route is reference-only, preserve that source boundary and inspect only the package interaction.

- [ ] **Step 5: Capture evidence**

Save desktop/mobile board, isolated, rotated/touch, U2001/J6101 regression, and connectivity screenshots. Write `qa-summary.json` with:

- routes and viewports;
- browser path and Chrome-plugin fallback status;
- metadata;
- interaction results;
- overlap/overflow counts;
- contrast/readability observations;
- console/page errors;
- canvas-only pixel statistics;
- source boundary;
- pass/fail result.

### Task 6: Close project facts

**Files:**
- Modify: `docs/km4-cross-source-registration-2026-07-13.md`
- Modify: this plan
- Modify: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Overview.md`
- Modify: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Agent Entry.md`
- Modify: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`

- [ ] **Step 1: Record the delivered boundary**

Record:

- shared spec id and profile ids;
- U2001 separate-spec compatibility;
- removal of renderer-owned BGA geometry;
- exact test counts;
- P3 routes, viewports, interactions, and evidence paths;
- material boundary and residual risks;
- local branch and commit hashes;
- no P4/deployment.

- [ ] **Step 2: Run independent final review**

Review the complete implementation from `a6917af..HEAD`. Fix P1/P2 findings and re-run affected validation.

- [ ] **Step 3: Run Project Closeout Check**

Verify Git, Vault, ledger, P0-P4, encoding, remote-sync state, and handoff.

- [ ] **Step 4: Commit implementation documentation**

```powershell
git add docs/km4-cross-source-registration-2026-07-13.md docs/superpowers/plans/2026-07-31-shared-bga-component-visual.md
git commit -m "docs: verify shared BGA visual migration"
```

- [ ] **Step 5: Commit the enablement ledger**

```powershell
git -C G:\Programming\mainboard-repair-enablement add PROJECT_LEDGER.md
git -C G:\Programming\mainboard-repair-enablement commit -m "docs: record shared BGA visual migration"
```

Do not push while `Milo Status.md` reports GitHub push unavailable or unstable.

## Acceptance Checklist

1. U4000, U0600, and connectivity profiles resolve to one shared BGA spec.
2. U2001 retains its separately named PMIC spec on the same compiler.
3. Shared BGA visuals are deterministic, source-bounded, and descriptor-bound.
4. Renderer-owned BGA geometry is removed.
5. Unknown reviewed-BGA profiles retain nonblank generic IC fallback.
6. No knowledge-base source relationship changes.
7. J6101 and U2001 regressions pass.
8. P0-P3, encoding, Git, Vault, and ledger checks pass.
9. P4 is explicitly not applicable and no deployment occurs.
