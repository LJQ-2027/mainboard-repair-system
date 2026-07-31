# U2001 Component Visual Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a source-bounded U2001 power-management IC visual and generalize `ComponentVisualSpec` into a validated connector plus IC/BGA family pipeline without changing technician interaction behavior.

**Architecture:** Keep the catalog, validator, and Three.js builder DOM-free. Add an `ic_bga` family contract and compiler beside the existing `connector` family, then migrate U2001 away from renderer-owned PMIC geometry while retaining a generic IC fail-soft fallback.

**Tech Stack:** JavaScript ES modules, Three.js, Node.js test runner, Python unittest, Playwright with installed Chrome, static browser application.

---

## File Structure

- Modify `assets/cross-source-registration/component-visual-specs.js`: add immutable IC/BGA materials, the U2001 repair-visual specification, and a duplicate-safe profile catalog.
- Modify `assets/cross-source-registration/component-visual-validator.js`: replace connector-global shape rules with strict family contracts.
- Modify `assets/cross-source-registration/component-visual-builder.js`: add a family compiler registry and an IC/BGA staged compiler while preserving shared ownership and disposal.
- Modify `assets/cross-source-registration/board-renderer.js`: remove U2001-specific PMIC geometry and retain generic IC fallback.
- Modify `tests/component-visual-specs.test.mjs`: test U2001 identity, evidence boundaries, family validation, duplicate profiles, and J6101 regression.
- Modify `tests/component-visual-builder.test.mjs`: test IC/BGA names, stages, bounds, details, disposal, malformed inputs, and connector regression.
- Modify `tests/model-profiles.test.mjs`: verify U2001 descriptor-to-spec mapping and compatibility metadata.
- Modify `tests/model-toolbar.test.mjs`: assert renderer migration and nonblank generic fallback.
- Modify `docs/km4-cross-source-registration-2026-07-13.md`: record the implementation and its evidence boundary.
- Modify this plan as each task is completed.
- Create ignored evidence under `output/playwright/u2001-component-visual-refinement/`.

### Task 1: Add the U2001 catalog entry

**Files:**
- Modify: `tests/component-visual-specs.test.mjs`
- Modify: `assets/cross-source-registration/component-visual-specs.js`

- [ ] **Step 1: Write failing U2001 catalog tests**

Add imports and assertions equivalent to:

```js
import {
  COMPONENT_VISUAL_MATERIALS,
  J6101_CONNECTOR_VISUAL_SPEC,
  U2001_PMIC_VISUAL_SPEC,
  buildComponentVisualSpecCatalog,
  resolveComponentVisualSpec,
} from '../assets/cross-source-registration/component-visual-specs.js';

test('U2001 resolves through the approved category-based PMIC profile', () => {
  assert.equal(
    resolveComponentVisualSpec('u2001-pmic-v1'),
    U2001_PMIC_VISUAL_SPEC,
  );
  assert.equal(U2001_PMIC_VISUAL_SPEC.spec_id, 'ic-bga-u2001-repair-visual-v1');
  assert.equal(U2001_PMIC_VISUAL_SPEC.family, 'ic_bga');
  assert.equal(U2001_PMIC_VISUAL_SPEC.source_status, 'category_based');
  assert.equal(U2001_PMIC_VISUAL_SPEC.fidelity, 'repair_visual');
});

test('the U2001 evidence boundary rejects package engineering claims', () => {
  assert.deepEqual(U2001_PMIC_VISUAL_SPEC.claims, [
    'ic_package_silhouette',
    'substrate_body_hierarchy',
    'generic_orientation_cue',
  ]);
  assert.match(U2001_PMIC_VISUAL_SPEC.boundary_note, /不代表/);
  assert.ok(U2001_PMIC_VISUAL_SPEC.acceptance.prohibited_claims.includes('exact_ball_count'));
  assert.ok(U2001_PMIC_VISUAL_SPEC.acceptance.prohibited_claims.includes('exact_ball_pitch'));
});

test('catalog construction rejects duplicate inspection profiles', () => {
  assert.throws(
    () => buildComponentVisualSpecCatalog([
      J6101_CONNECTOR_VISUAL_SPEC,
      { ...U2001_PMIC_VISUAL_SPEC, inspection_profiles: ['j6101-connector-v1'] },
    ]),
    /Duplicate inspection profile/,
  );
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs
```

Expected: FAIL because `U2001_PMIC_VISUAL_SPEC` and `buildComponentVisualSpecCatalog` are not exported.

- [ ] **Step 3: Add immutable IC/BGA materials and U2001 specification**

Add material tokens with stable names:

```js
'ic-substrate': Object.freeze({ color: 0x31443d, roughness: 0.66, metalness: 0.08 }),
'molded-package': Object.freeze({ color: 0x171d1b, roughness: 0.58, metalness: 0.12 }),
'inset-top': Object.freeze({ color: 0x232a27, roughness: 0.52, metalness: 0.16 }),
'orientation-marker': Object.freeze({ color: 0xaab3ad, roughness: 0.45, metalness: 0.2 }),
```

Add `U2001_PMIC_VISUAL_SPEC` with:

```js
{
  spec_id: 'ic-bga-u2001-repair-visual-v1',
  version: 1,
  asset_type: 'procedural',
  family: 'ic_bga',
  inspection_profiles: ['u2001-pmic-v1'],
  source_status: 'category_based',
  fidelity: 'repair_visual',
  claims: [
    'ic_package_silhouette',
    'substrate_body_hierarchy',
    'generic_orientation_cue',
  ],
  materials: {
    substrate: 'ic-substrate',
    body: 'molded-package',
    top: 'inset-top',
    marker: 'orientation-marker',
    edge: 'edge-line',
  },
  structure: {
    substrate: { width: 1, depth: 1, height: 0.12, radius: 0.045 },
    body: { width: 0.88, depth: 0.88, height: 0.62, radius: 0.065, lift: 0.12 },
    top: { width: 0.74, depth: 0.74, height: 0.055, radius: 0.05, lift: 0.72 },
    marker: { radius: 0.045, offset_x: 0.31, offset_y: 0.31, height: 0.025, lift: 0.775 },
  },
  detail_levels: {
    board: ['substrate', 'body', 'top', 'orientation-marker'],
    isolated: [
      'substrate',
      'body',
      'top',
      'orientation-marker',
      'substrate-edges',
      'body-edges',
      'top-seam',
    ],
  },
  stages: ['blockout', 'structure', 'material', 'polish'],
}
```

Use the same prohibited-claim policy as the connector plus:

```js
'exact_ball_count',
'exact_ball_pitch',
'exact_pad_layout',
'vendor_package',
'die_or_internal_structure',
'package_marking',
```

Export `buildComponentVisualSpecCatalog(specs)` and build the production map from both approved specs. Throw on duplicate profile IDs.

- [ ] **Step 4: Run the catalog test and verify the new identity tests pass**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs
```

Expected: U2001 catalog tests pass; validator tests may still fail because `ic_bga` has no contract yet.

- [ ] **Step 5: Commit the catalog slice**

```powershell
git add assets/cross-source-registration/component-visual-specs.js tests/component-visual-specs.test.mjs
git commit -m "feat: add U2001 component visual specification"
```

### Task 2: Generalize validation by component family

**Files:**
- Modify: `tests/component-visual-specs.test.mjs`
- Modify: `assets/cross-source-registration/component-visual-validator.js`

- [ ] **Step 1: Write failing family-contract tests**

Cover these mutations with exact expected codes:

```js
[
  [{ ...U2001_PMIC_VISUAL_SPEC, family: 'unknown' }, 'unsupported_family', 'family'],
  [{ ...U2001_PMIC_VISUAL_SPEC, materials: { ...U2001_PMIC_VISUAL_SPEC.materials, pins: 'plated-metal' } }, 'unknown_material_role', 'materials.pins'],
  [{ ...U2001_PMIC_VISUAL_SPEC, structure: { ...U2001_PMIC_VISUAL_SPEC.structure, balls: {} } }, 'unknown_structure_role', 'structure.balls'],
  [{ ...U2001_PMIC_VISUAL_SPEC, detail_levels: { ...U2001_PMIC_VISUAL_SPEC.detail_levels, board: ['substrate', 'ball-grid'] } }, 'undeclared_detail_part', 'detail_levels.board[1]'],
  [{ ...U2001_PMIC_VISUAL_SPEC, claims: [...U2001_PMIC_VISUAL_SPEC.claims, 'exact_ball_count'] }, 'prohibited_claim', 'claims'],
]
```

Also retain all current J6101 assertions and add a malformed-input matrix for `null`, arrays, missing sections, `NaN`, `Infinity`, negative ratios, duplicate parts, and unknown dimensions. `validateComponentVisualSpec()` must return an error object and never throw.

- [ ] **Step 2: Run the validator test and verify it fails**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs
```

Expected: FAIL with missing `ic_bga` role support or an `unsupported_family` mismatch.

- [ ] **Step 3: Introduce strict family contracts**

Define one immutable registry:

```js
const FAMILY_CONTRACTS = Object.freeze({
  connector: Object.freeze({
    materialRoles: Object.freeze(['base', 'opening', 'frame', 'contact', 'edge']),
    structureShapes: CONNECTOR_STRUCTURE_SHAPES,
    detailPartsByStructure: CONNECTOR_DETAIL_PARTS,
  }),
  ic_bga: Object.freeze({
    materialRoles: Object.freeze(['substrate', 'body', 'top', 'marker', 'edge']),
    structureShapes: Object.freeze({
      substrate: Object.freeze(['width', 'depth', 'height', 'radius']),
      body: Object.freeze(['width', 'depth', 'height', 'radius', 'lift']),
      top: Object.freeze(['width', 'depth', 'height', 'radius', 'lift']),
      marker: Object.freeze(['radius', 'offset_x', 'offset_y', 'height', 'lift']),
    }),
    detailPartsByStructure: Object.freeze({
      substrate: Object.freeze(['substrate', 'substrate-edges']),
      body: Object.freeze(['body', 'body-edges']),
      top: Object.freeze(['top', 'top-seam']),
      marker: Object.freeze(['orientation-marker']),
    }),
  }),
});
```

Resolve the contract after metadata validation. Emit `unsupported_family` when absent, then run materials, structures, and declared-detail checks only against that contract. Preserve canonical stage, ratio, claim, and malformed-input behavior.

- [ ] **Step 4: Run both family test matrices**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs
```

Expected: all tests pass for `connector` and `ic_bga`.

- [ ] **Step 5: Commit the validator slice**

```powershell
git add assets/cross-source-registration/component-visual-validator.js tests/component-visual-specs.test.mjs
git commit -m "refactor: validate component visuals by family"
```

### Task 3: Add the IC/BGA staged compiler

**Files:**
- Modify: `tests/component-visual-builder.test.mjs`
- Modify: `assets/cross-source-registration/component-visual-builder.js`

- [ ] **Step 1: Write failing U2001 builder tests**

Use a U2001 descriptor with finite `{ x, y, z }` dimensions and assert:

```js
assert.deepEqual(directPartNames(boardGroup), [
  'substrate',
  'body',
  'top',
  'orientation-marker',
]);
assert.deepEqual(boardGroup.userData.visualStages, [
  'blockout',
  'structure',
  'material',
  'polish',
]);
assert.equal(boardGroup.userData.visualFamily, 'ic_bga');
assert.equal(boardGroup.userData.visualSpecId, 'ic-bga-u2001-repair-visual-v1');
```

For `isolated`, also require:

```js
['substrate-edges', 'body-edges', 'top-seam']
```

Assert every computed bound remains inside the descriptor footprint and height, repeated builds produce identical snapshots, different descriptors do not share geometry or materials, and double disposal reports zero resources on the second call.

- [ ] **Step 2: Run the focused builder test and verify it fails**

Run:

```powershell
node --test tests/component-visual-builder.test.mjs
```

Expected: FAIL because the current builder executes connector-only stages for `ic_bga`.

- [ ] **Step 3: Refactor connector stages behind a compiler registry**

Keep current connector geometry unchanged, but group its stage handlers:

```js
const FAMILY_COMPILERS = Object.freeze({
  connector: Object.freeze({
    blockout: connectorBlockout,
    structure: connectorStructure,
    material: connectorMaterial,
    polish: connectorPolish,
  }),
  ic_bga: Object.freeze({
    blockout: icBgaBlockout,
    structure: icBgaStructure,
    material: icBgaMaterial,
    polish: icBgaPolish,
  }),
});
```

`buildComponentVisual()` must validate first, resolve the family compiler, execute the canonical stage list, and return `{ group, fallbackReason: null }`. Unsupported or invalid specs must return `{ group: null, fallbackReason }` without leaking owned resources.

- [ ] **Step 4: Implement the IC/BGA stages**

Build only source-bounded visual parts:

```js
function icBgaBlockout(context) {
  addPart(context, 'substrate', context.spec.structure.substrate, 'substrate');
}

function icBgaStructure(context) {
  addPart(context, 'body', context.spec.structure.body, 'body');
  addPart(context, 'top', context.spec.structure.top, 'top');
  addCircularPart(
    context,
    'orientation-marker',
    context.spec.structure.marker,
    'marker',
  );
}

function icBgaPolish(context) {
  addRoundedEdges(context, 'substrate-edges', 'substrate', 'edge');
  addRoundedEdges(context, 'body-edges', 'body', 'edge');
  addRoundedEdges(context, 'top-seam', 'top', 'edge');
}
```

`addCircularPart()` must scale marker radius, offsets, lift, and height from descriptor dimensions and use owned `CylinderGeometry`. The marker communicates orientation only; do not add balls, pads, text, leads, or internal layers.

- [ ] **Step 5: Run builder and catalog suites**

Run:

```powershell
node --test tests/component-visual-builder.test.mjs tests/component-visual-specs.test.mjs
```

Expected: all tests pass, including unchanged J6101 snapshots and disposal assertions.

- [ ] **Step 6: Commit the builder slice**

```powershell
git add assets/cross-source-registration/component-visual-builder.js tests/component-visual-builder.test.mjs
git commit -m "feat: compile IC BGA component visuals"
```

### Task 4: Migrate U2001 renderer ownership

**Files:**
- Modify: `tests/model-profiles.test.mjs`
- Modify: `tests/model-toolbar.test.mjs`
- Modify: `assets/cross-source-registration/board-renderer.js`

- [ ] **Step 1: Write failing descriptor and source-boundary tests**

Add a reviewed U2001 fixture and assert:

```js
const descriptor = buildRenderDescriptor(u2001, { reviewed: true });
assert.equal(descriptor.componentVisualSpecId, 'ic-bga-u2001-repair-visual-v1');
assert.equal(descriptor.visualAsset, 'reviewed-pmic');
```

Read `board-renderer.js` as source and assert:

```js
assert.doesNotMatch(source, /function addInspectionPmicPackage/);
assert.doesNotMatch(source, /visualAsset === 'reviewed-pmic'/);
assert.match(source, /if \(descriptor\.family === 'ic'\) addIcPackage/);
```

- [ ] **Step 2: Run focused integration tests and verify they fail**

Run:

```powershell
node --test tests/model-profiles.test.mjs tests/model-toolbar.test.mjs
```

Expected: descriptor mapping may pass after Task 1; renderer source assertions fail until the legacy PMIC path is removed.

- [ ] **Step 3: Remove renderer-owned U2001 geometry**

Delete `addInspectionPmicPackage()`. In `createPackageMesh()`:

1. call `buildComponentVisual(descriptor, detailLevel)`;
2. return the reusable group when present;
3. store its fallback reason when absent;
4. allow the existing `descriptor.family === 'ic'` branch to call `addIcPackage()`.

Keep `reviewed-pmic` in the descriptor as provenance-compatible UI metadata, but do not use it to choose geometry.

- [ ] **Step 4: Verify replacement and fallback regressions**

Run:

```powershell
node --test tests/model-profiles.test.mjs tests/model-toolbar.test.mjs tests/component-visual-builder.test.mjs tests/component-visual-replacement-state.test.mjs tests/component-visual-disposal-state.test.mjs
```

Expected: all tests pass; malformed U2001 specs remain nonblank through the generic IC fallback.

- [ ] **Step 5: Commit the renderer migration**

```powershell
git add assets/cross-source-registration/board-renderer.js tests/model-profiles.test.mjs tests/model-toolbar.test.mjs
git commit -m "refactor: route U2001 through component visual builder"
```

### Task 5: Run full automated validation

**Files:**
- Modify only if failures reveal a defect in files owned by Tasks 1-4.

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

Expected: all tests pass with zero failures.

- [ ] **Step 3: Run source-bound Python tests**

```powershell
G:\Programming\mainboard-repair-system\.venv\Scripts\python.exe -m unittest tests.test_validate_cross_source_registration tests.test_compile_km4_board tests.test_ai_proxy_static -v
```

Expected: 27 tests pass.

- [ ] **Step 4: Run repository and encoding checks**

```powershell
git diff --check
git status --short
```

Strictly decode every changed text file as UTF-8 and reject U+FFFD. Expected: no whitespace errors, no invalid UTF-8, and only intended files changed.

### Task 6: Perform desktop and mobile P3 browser QA

**Files:**
- Evidence only: `output/playwright/u2001-component-visual-refinement/`
- Modify owned implementation files only if visual or interaction defects are found.

- [ ] **Step 1: Start or verify the local static server**

Serve `G:\wt\mbr-j6101` on `127.0.0.1:8899` and open:

```text
http://127.0.0.1:8899/assets/cross-source-registration/?board=km4-f151
```

Expected: HTTP 200 and no page-level JavaScript errors.

- [ ] **Step 2: Verify desktop U2001 board and isolated states**

At `1600x900`:

1. select U2001 from the entity list;
2. confirm a distinct substrate, molded body, inset top, and orientation cue;
3. confirm no invented balls, pads, markings, leads, or internal structures;
4. enter isolated mode and confirm edge details appear;
5. rotate, pan, zoom, reset, return to board, and re-enter isolated mode;
6. confirm the component remains selectable and no UI text overlaps.

Record these data attributes:

```text
data-component-visual-spec="ic-bga-u2001-repair-visual-v1"
data-component-visual-detail="board" or "isolated"
data-inspection-visual-asset="reviewed-pmic"
data-component-visual-fallback=""
data-component-visual-cleanup=""
```

Save board, isolated, and rotated screenshots.

- [ ] **Step 3: Verify mobile touch behavior**

At `390x844`, repeat U2001 selection and isolated mode. Exercise native one-finger rotation and two-finger pinch/translation. Confirm the return action remains visible, the model is not clipped, labels do not overlap controls, and the same data attributes remain valid.

- [ ] **Step 4: Regress J6101**

Select J6101 at desktop and mobile widths. Confirm its board and isolated geometry, selection identity, return behavior, pan/rotation, and metadata remain unchanged.

- [ ] **Step 5: Capture a machine-readable QA summary**

Write `output/playwright/u2001-component-visual-refinement/qa-summary.json` containing viewport, interaction checks, console errors, page errors, component metadata, screenshot paths, and pass/fail values. The file is evidence only and remains ignored.

### Task 7: Close the project facts

**Files:**
- Modify: `docs/km4-cross-source-registration-2026-07-13.md`
- Modify: `docs/superpowers/plans/2026-07-31-u2001-component-visual-refinement.md`
- Modify: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Overview.md`
- Modify: `C:/Users/Mercurluto/OneDrive/AI/02_Projects/Programming/Mainboard Repair Enablement/Agent Entry.md`
- Modify: `G:/Programming/mainboard-repair-enablement/PROJECT_LEDGER.md`

- [ ] **Step 1: Document the delivered boundary**

Record:

- U2001 now uses the reusable `ic_bga` compiler;
- J6101 remains on the connector compiler;
- U2001 fidelity is category-based repair visualization;
- exact package, ball-grid, dimensions, markings, pads, and internals remain unsupported;
- desktop and mobile QA evidence paths;
- exact test counts and commit hashes.

- [ ] **Step 2: Mark plan checkboxes from actual evidence**

Change only completed steps to `[x]`. Do not mark browser or test steps complete without their corresponding output.

- [ ] **Step 3: Run the Project Closeout Check**

Verify Git status, local commits, Vault state, ledger state, automated validation, P3 evidence, encoding health, P4 applicability, remote-sync state, and handoff notes.

- [ ] **Step 4: Commit repository documentation**

```powershell
git add docs/km4-cross-source-registration-2026-07-13.md docs/superpowers/plans/2026-07-31-u2001-component-visual-refinement.md
git commit -m "docs: verify U2001 component visual refinement"
```

- [ ] **Step 5: Commit the enablement ledger separately**

```powershell
git -C G:\Programming\mainboard-repair-enablement add PROJECT_LEDGER.md
git -C G:\Programming\mainboard-repair-enablement commit -m "docs: record U2001 visual refinement"
```

Do not push while `Milo Status.md` reports GitHub push unavailable or unstable. Report the local branch, commits, tests, P3 evidence, material boundary, and remote-sync gap.

## Acceptance Checklist

1. U2001 resolves to `ic-bga-u2001-repair-visual-v1`.
2. The validator strictly supports `connector` and `ic_bga` without weakening J6101 checks.
3. U2001 board and isolated visuals are deterministic, footprint-bounded, and source-bounded.
4. `board-renderer.js` contains no U2001-specific PMIC geometry.
5. Invalid U2001 specs retain a nonblank generic IC fallback.
6. Replacement and disposal remain exact and leak-free.
7. J6101 behavior remains unchanged.
8. Node, Python, syntax, whitespace, and encoding checks pass.
9. Desktop and mobile P3 checks pass with evidence.
10. Git, Vault, project documentation, and ledger agree on the delivered state.
