# J6101 Component Visual Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a visibly refined J6101 connector and a reusable, validated `ComponentVisualSpec` procedural modeling pipeline without changing source-backed board facts or technician interaction semantics.

**Architecture:** Add a DOM-free visual catalog and validator, then compile approved specifications through deterministic Three.js stages. `BoardRenderer` consumes the reusable builder, swaps J6101 between board and isolated detail groups while preserving identity and transforms, and falls back to the existing generic connector when a specification is unavailable or invalid.

**Tech Stack:** JavaScript ES modules, Three.js, Node built-in test runner, Python `unittest`, headed Chromium browser QA.

---

## File Structure

- Create `assets/cross-source-registration/component-visual-specs.js`: immutable material tokens, J6101 visual specification, and profile-to-spec catalog.
- Create `assets/cross-source-registration/component-visual-validator.js`: DOM-free schema and evidence-boundary validation.
- Create `assets/cross-source-registration/component-visual-builder.js`: deterministic Three.js geometry, materials, metadata, and detail-level construction.
- Modify `assets/cross-source-registration/board-renderer.js`: reusable builder integration, fail-soft fallback, detail-group replacement, and disposal.
- Modify `assets/cross-source-registration/model-profiles.js`: expose reusable visual-spec identity in render descriptors while retaining the existing asset label for compatibility.
- Create `tests/component-visual-specs.test.mjs`: catalog and validator unit coverage.
- Create `tests/component-visual-builder.test.mjs`: Three.js stage, geometry, detail-level, footprint, and fallback coverage.
- Modify `tests/model-profiles.test.mjs`: descriptor-to-spec mapping coverage.
- Modify `tests/model-toolbar.test.mjs`: renderer integration and no-J6101-specific-geometry assertions.
- Modify `docs/km4-cross-source-registration-2026-07-13.md`: record the new reusable visual pipeline, evidence boundary, test result, and browser evidence.
- Create ignored browser evidence under `output/playwright/j6101-component-visual-refinement/`.

### Task 1: Define And Validate ComponentVisualSpec

**Files:**
- Create: `assets/cross-source-registration/component-visual-specs.js`
- Create: `assets/cross-source-registration/component-visual-validator.js`
- Create: `tests/component-visual-specs.test.mjs`

- [ ] **Step 1: Write catalog and validator tests**

Create `tests/component-visual-specs.test.mjs`:

```js
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  COMPONENT_VISUAL_MATERIALS,
  J6101_CONNECTOR_VISUAL_SPEC,
  resolveComponentVisualSpec,
} from '../assets/cross-source-registration/component-visual-specs.js';
import {
  COMPONENT_VISUAL_STAGE_ORDER,
  validateComponentVisualSpec,
} from '../assets/cross-source-registration/component-visual-validator.js';

test('J6101 resolves through its reviewed inspection profile', () => {
  const spec = resolveComponentVisualSpec('j6101-connector-v1');
  assert.equal(spec.spec_id, 'connector-j6101-repair-visual-v1');
  assert.equal(spec.asset_type, 'procedural');
  assert.equal(resolveComponentVisualSpec('unknown-profile'), null);
});

test('the approved J6101 spec passes every source-bound validation rule', () => {
  assert.deepEqual(validateComponentVisualSpec(
    J6101_CONNECTOR_VISUAL_SPEC,
    COMPONENT_VISUAL_MATERIALS,
  ), { valid: true, errors: [] });
});

test('the validator rejects unsupported materials, stages, ratios, and detail claims', () => {
  const cases = [
    [{ ...J6101_CONNECTOR_VISUAL_SPEC, asset_type: 'invented' }, 'unsupported_asset_type'],
    [{ ...J6101_CONNECTOR_VISUAL_SPEC, stages: ['structure', 'blockout'] }, 'invalid_stage_order'],
    [{
      ...J6101_CONNECTOR_VISUAL_SPEC,
      structure: {
        ...J6101_CONNECTOR_VISUAL_SPEC.structure,
        frame: { ...J6101_CONNECTOR_VISUAL_SPEC.structure.frame, width: 1.4 },
      },
    }, 'ratio_out_of_range'],
    [{
      ...J6101_CONNECTOR_VISUAL_SPEC,
      materials: { ...J6101_CONNECTOR_VISUAL_SPEC.materials, frame: 'unknown-metal' },
    }, 'unknown_material'],
    [{
      ...J6101_CONNECTOR_VISUAL_SPEC,
      claims: [...J6101_CONNECTOR_VISUAL_SPEC.claims, 'exact_pin_count'],
    }, 'prohibited_claim'],
  ];

  cases.forEach(([spec, expectedCode]) => {
    const result = validateComponentVisualSpec(spec, COMPONENT_VISUAL_MATERIALS);
    assert.equal(result.valid, false);
    assert.ok(result.errors.some((error) => error.code === expectedCode));
  });
  assert.deepEqual(COMPONENT_VISUAL_STAGE_ORDER, ['blockout', 'structure', 'material', 'polish']);
});

test('detail levels reference unique declared part names', () => {
  const duplicate = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  duplicate.detail_levels.board.push(duplicate.detail_levels.board[0]);
  const result = validateComponentVisualSpec(duplicate, COMPONENT_VISUAL_MATERIALS);
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((error) => error.code === 'duplicate_part_name'));
});
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs
```

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `component-visual-specs.js`.

- [ ] **Step 3: Implement the immutable catalog**

Create `assets/cross-source-registration/component-visual-specs.js` with:

```js
export const COMPONENT_VISUAL_MATERIALS = Object.freeze({
  'engineering-plastic': Object.freeze({
    color: 0x2c3632, roughness: 0.64, metalness: 0.12,
  }),
  'recessed-polymer': Object.freeze({
    color: 0x0d1412, roughness: 0.74, metalness: 0.04,
  }),
  'plated-metal': Object.freeze({
    color: 0xbfc6c2, roughness: 0.27, metalness: 0.8,
  }),
  'contact-metal': Object.freeze({
    color: 0xc79a4b, roughness: 0.3, metalness: 0.74,
  }),
  'edge-line': Object.freeze({
    color: 0x66736d, opacity: 0.72,
  }),
});

export const J6101_CONNECTOR_VISUAL_SPEC = Object.freeze({
  spec_id: 'connector-j6101-repair-visual-v1',
  version: 1,
  asset_type: 'procedural',
  family: 'connector',
  inspection_profiles: Object.freeze(['j6101-connector-v1']),
  source_status: 'category_based',
  fidelity: 'repair_visual',
  boundary_note: '连接器结构为维修识别示意，不代表准确针脚、间距、卡扣或工程尺寸。',
  claims: Object.freeze(['connector_silhouette', 'recessed_opening', 'generic_contact_region']),
  materials: Object.freeze({
    base: 'engineering-plastic',
    opening: 'recessed-polymer',
    frame: 'plated-metal',
    contact: 'contact-metal',
    edge: 'edge-line',
  }),
  structure: Object.freeze({
    base: Object.freeze({ width: 1, depth: 1, height: 0.24, radius: 0.055 }),
    frame: Object.freeze({
      width: 0.94, depth: 0.88, height: 0.62, wall: 0.14, radius: 0.045, lift: 0.2,
    }),
    opening: Object.freeze({
      width: 0.64, depth: 0.34, height: 0.14, radius: 0.035, lift: 0.25,
    }),
    contact: Object.freeze({
      width: 0.56, depth: 0.075, height: 0.055, offset_y: 0.075, lift: 0.34,
    }),
    retention: Object.freeze({
      width: 0.075, depth: 0.68, height: 0.68, inset_x: 0.42, lift: 0.2,
    }),
    inner_lip: Object.freeze({
      width: 0.72, depth: 0.48, height: 0.08, wall: 0.055, lift: 0.48,
    }),
  }),
  detail_levels: Object.freeze({
    board: Object.freeze(['base', 'frame-north', 'frame-south', 'frame-west', 'frame-east', 'opening', 'contact']),
    isolated: Object.freeze([
      'base', 'frame-north', 'frame-south', 'frame-west', 'frame-east',
      'opening', 'contact', 'retention-west', 'retention-east',
      'inner-lip-north', 'inner-lip-south', 'inner-lip-west', 'inner-lip-east',
      'frame-edges',
    ]),
  }),
  stages: Object.freeze(['blockout', 'structure', 'material', 'polish']),
  acceptance: Object.freeze({
    ratio_min: 0.02,
    ratio_max: 1,
    prohibited_claims: Object.freeze([
      'exact_pin_count', 'exact_pin_pitch', 'vendor_latch',
      'solder_foot_array', 'internal_spring_geometry', 'millimeter_dimensions',
    ]),
  }),
});

const SPEC_BY_INSPECTION_PROFILE = new Map(
  J6101_CONNECTOR_VISUAL_SPEC.inspection_profiles.map((profileId) => [
    profileId,
    J6101_CONNECTOR_VISUAL_SPEC,
  ]),
);

export function resolveComponentVisualSpec(inspectionProfileId) {
  return SPEC_BY_INSPECTION_PROFILE.get(inspectionProfileId) || null;
}
```

- [ ] **Step 4: Implement deterministic validation**

Create `assets/cross-source-registration/component-visual-validator.js`:

```js
export const COMPONENT_VISUAL_STAGE_ORDER = Object.freeze([
  'blockout', 'structure', 'material', 'polish',
]);

const SUPPORTED_ASSET_TYPES = new Set(['procedural']);
const PROHIBITED_CLAIMS = new Set([
  'exact_pin_count', 'exact_pin_pitch', 'vendor_latch',
  'solder_foot_array', 'internal_spring_geometry', 'millimeter_dimensions',
]);

function error(code, path, message) {
  return Object.freeze({ code, path, message });
}

function numericLeaves(value, path = 'structure') {
  return Object.entries(value || {}).flatMap(([key, item]) => {
    const itemPath = `${path}.${key}`;
    if (typeof item === 'number') return [[itemPath, item]];
    if (item && typeof item === 'object') return numericLeaves(item, itemPath);
    return [];
  });
}

export function validateComponentVisualSpec(spec, materialCatalog = {}) {
  const errors = [];
  if (!spec?.spec_id || !Number.isInteger(spec?.version) || spec.version < 1) {
    errors.push(error('invalid_identity', 'spec_id', 'A stable ID and positive version are required.'));
  }
  if (!SUPPORTED_ASSET_TYPES.has(spec?.asset_type)) {
    errors.push(error('unsupported_asset_type', 'asset_type', 'Only procedural assets are supported.'));
  }
  if (JSON.stringify(spec?.stages) !== JSON.stringify(COMPONENT_VISUAL_STAGE_ORDER)) {
    errors.push(error('invalid_stage_order', 'stages', 'Build stages must use the canonical order.'));
  }
  Object.entries(spec?.materials || {}).forEach(([role, token]) => {
    if (!materialCatalog[token]) {
      errors.push(error('unknown_material', `materials.${role}`, `Unknown material token: ${token}`));
    }
  });
  numericLeaves(spec?.structure).forEach(([path, value]) => {
    if (!Number.isFinite(value) || value < spec.acceptance.ratio_min || value > spec.acceptance.ratio_max) {
      errors.push(error('ratio_out_of_range', path, 'Structure ratios must remain inside acceptance bounds.'));
    }
  });
  const claims = spec?.claims || [];
  claims.filter((claim) => PROHIBITED_CLAIMS.has(claim)).forEach((claim) => {
    errors.push(error('prohibited_claim', 'claims', `Unsupported engineering claim: ${claim}`));
  });
  Object.entries(spec?.detail_levels || {}).forEach(([level, names]) => {
    const unique = new Set(names);
    if (unique.size !== names.length) {
      errors.push(error('duplicate_part_name', `detail_levels.${level}`, 'Part names must be unique.'));
    }
  });
  return Object.freeze({ valid: errors.length === 0, errors: Object.freeze(errors) });
}
```

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit the validated specification layer**

```powershell
git add assets/cross-source-registration/component-visual-specs.js `
  assets/cross-source-registration/component-visual-validator.js `
  tests/component-visual-specs.test.mjs
git commit -m "feat: add validated component visual specs"
```

### Task 2: Build Deterministic Three.js Connector Geometry

**Files:**
- Create: `assets/cross-source-registration/component-visual-builder.js`
- Create: `tests/component-visual-builder.test.mjs`

- [ ] **Step 1: Write builder tests**

Create `tests/component-visual-builder.test.mjs`:

```js
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildComponentVisual,
  componentVisualBounds,
} from '../assets/cross-source-registration/component-visual-builder.js';

const descriptor = {
  dimensions: { x: 0.314, y: 0.09875, z: 0.045 },
  inspectionProfile: { profile_id: 'j6101-connector-v1' },
};

test('J6101 builds deterministic named stages and board parts', () => {
  const result = buildComponentVisual(descriptor, 'board');
  assert.equal(result.fallbackReason, null);
  assert.equal(result.group.userData.visualSpecId, 'connector-j6101-repair-visual-v1');
  assert.deepEqual(result.group.userData.visualStages, ['blockout', 'structure', 'material', 'polish']);
  assert.deepEqual(
    result.group.userData.visualPartNames,
    ['base', 'contact', 'frame-east', 'frame-north', 'frame-south', 'frame-west', 'opening'],
  );
});

test('isolated detail adds retention, inner lip, and edge treatment without pins', () => {
  const result = buildComponentVisual(descriptor, 'isolated');
  const names = result.group.userData.visualPartNames;
  assert.ok(names.includes('retention-west'));
  assert.ok(names.includes('inner-lip-north'));
  assert.ok(names.includes('frame-edges'));
  assert.equal(names.some((name) => /pin|solder|spring/i.test(name)), false);
});

test('board geometry stays inside the registered footprint', () => {
  const result = buildComponentVisual(descriptor, 'board');
  const bounds = componentVisualBounds(result.group);
  assert.ok(bounds.width <= descriptor.dimensions.x + 1e-6);
  assert.ok(bounds.depth <= descriptor.dimensions.y + 1e-6);
  assert.ok(bounds.height > 0 && bounds.height <= descriptor.dimensions.z + 1e-6);
});

test('unknown and invalid profiles return stable fail-soft reasons', () => {
  assert.equal(
    buildComponentVisual({ ...descriptor, inspectionProfile: { profile_id: 'unknown' } }, 'board').fallbackReason,
    'visual_spec_not_found',
  );
  assert.equal(buildComponentVisual({ ...descriptor, dimensions: { x: 0, y: 0, z: 0 } }, 'board').fallbackReason,
    'invalid_dimensions');
  assert.equal(buildComponentVisual(descriptor, 'cinematic').fallbackReason, 'unknown_detail_level');
});
```

- [ ] **Step 2: Run the builder tests and verify RED**

Run:

```powershell
node --test tests/component-visual-builder.test.mjs
```

Expected: FAIL with `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 3: Implement stage-driven geometry and semantic materials**

Create `assets/cross-source-registration/component-visual-builder.js`. The module
must:

```js
import * as THREE from '../vendor/three/three.module.min.js';
import {
  COMPONENT_VISUAL_MATERIALS,
  resolveComponentVisualSpec,
} from './component-visual-specs.js';
import { validateComponentVisualSpec } from './component-visual-validator.js';

function materialFor(spec, role) {
  const token = spec.materials[role];
  const values = COMPONENT_VISUAL_MATERIALS[token];
  if (role === 'edge') {
    return new THREE.LineBasicMaterial({
      color: values.color, transparent: true, opacity: values.opacity,
    });
  }
  return new THREE.MeshStandardMaterial(values);
}

function roundedShape(width, depth, radius) {
  const shape = new THREE.Shape();
  const x = -width / 2;
  const y = -depth / 2;
  shape.moveTo(x + radius, y);
  shape.lineTo(x + width - radius, y);
  shape.quadraticCurveTo(x + width, y, x + width, y + radius);
  shape.lineTo(x + width, y + depth - radius);
  shape.quadraticCurveTo(x + width, y + depth, x + width - radius, y + depth);
  shape.lineTo(x + radius, y + depth);
  shape.quadraticCurveTo(x, y + depth, x, y + depth - radius);
  shape.lineTo(x, y + radius);
  shape.quadraticCurveTo(x, y, x + radius, y);
  return shape;
}

function roundedPart(name, width, depth, height, radius, meshMaterial, lift = 0) {
  const geometry = new THREE.ExtrudeGeometry(roundedShape(width, depth, radius), {
    depth: height,
    bevelEnabled: true,
    bevelSize: Math.min(radius * 0.28, width * 0.02, depth * 0.02),
    bevelThickness: Math.min(height * 0.08, 0.0015),
    bevelSegments: 2,
  });
  const mesh = new THREE.Mesh(geometry, meshMaterial);
  mesh.name = name;
  mesh.userData.visualPart = name;
  mesh.position.z = lift;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function addFrameParts(group, spec, dimensions, allowed) {
  const frame = spec.structure.frame;
  const width = dimensions.x * frame.width;
  const depth = dimensions.y * frame.depth;
  const wallX = dimensions.x * frame.wall;
  const wallY = dimensions.y * frame.wall;
  const height = dimensions.z * frame.height;
  const lift = dimensions.z * frame.lift;
  const radius = Math.min(dimensions.x, dimensions.y) * frame.radius;
  const meshMaterial = materialFor(spec, 'frame');
  const parts = [
    ['frame-north', width - wallX * 2, wallY, 0, (depth - wallY) / 2],
    ['frame-south', width - wallX * 2, wallY, 0, -(depth - wallY) / 2],
    ['frame-west', wallX, depth, -(width - wallX) / 2, 0],
    ['frame-east', wallX, depth, (width - wallX) / 2, 0],
  ];
  parts.filter(([name]) => allowed.has(name)).forEach(([name, x, y, px, py]) => {
    const part = roundedPart(name, x, y, height, radius, meshMaterial.clone(), lift);
    part.position.x = px;
    part.position.y = py;
    group.add(part);
  });
}

function finishMetadata(group, spec, detailLevel) {
  const names = group.children
    .map((child) => child.userData.visualPart)
    .filter(Boolean)
    .sort();
  group.userData.visualSpecId = spec.spec_id;
  group.userData.visualSpecVersion = spec.version;
  group.userData.visualAssetType = spec.asset_type;
  group.userData.visualDetailLevel = detailLevel;
  group.userData.visualStages = [...spec.stages];
  group.userData.visualPartNames = names;
  group.userData.visualBoundaryNote = spec.boundary_note;
}

export function componentVisualBounds(group) {
  const bounds = new THREE.Box3().setFromObject(group);
  const size = new THREE.Vector3();
  bounds.getSize(size);
  return { width: size.x, depth: size.y, height: size.z };
}

export function buildComponentVisual(descriptor, detailLevel = 'board') {
  const profileId = descriptor?.inspectionProfile?.profile_id;
  const spec = resolveComponentVisualSpec(profileId);
  if (!spec) return { group: null, fallbackReason: 'visual_spec_not_found' };
  if (!['board', 'isolated'].includes(detailLevel)) {
    return { group: null, fallbackReason: 'unknown_detail_level' };
  }
  const dimensions = descriptor?.dimensions;
  if (!dimensions || Object.values(dimensions).some((value) => !Number.isFinite(value) || value <= 0)) {
    return { group: null, fallbackReason: 'invalid_dimensions' };
  }
  const validation = validateComponentVisualSpec(spec, COMPONENT_VISUAL_MATERIALS);
  if (!validation.valid) return { group: null, fallbackReason: validation.errors[0].code };

  const group = new THREE.Group();
  const allowed = new Set(spec.detail_levels[detailLevel]);
  const base = spec.structure.base;
  if (allowed.has('base')) {
    group.add(roundedPart(
      'base',
      dimensions.x * base.width,
      dimensions.y * base.depth,
      dimensions.z * base.height,
      Math.min(dimensions.x, dimensions.y) * base.radius,
      materialFor(spec, 'base'),
    ));
  }
  addFrameParts(group, spec, dimensions, allowed);

  const addPart = (name, source, role, position = {}) => {
    if (!allowed.has(name)) return null;
    const part = roundedPart(
      name,
      dimensions.x * source.width,
      dimensions.y * source.depth,
      dimensions.z * source.height,
      Math.min(dimensions.x, dimensions.y) * (source.radius || 0.02),
      materialFor(spec, role),
      dimensions.z * source.lift,
    );
    part.position.x = dimensions.x * (position.x || 0);
    part.position.y = dimensions.y * (position.y || 0);
    group.add(part);
    return part;
  };

  addPart('opening', spec.structure.opening, 'opening');
  addPart('contact', spec.structure.contact, 'contact', {
    y: spec.structure.contact.offset_y,
  });

  const retention = spec.structure.retention;
  addPart('retention-west', retention, 'frame', { x: -retention.inset_x });
  addPart('retention-east', retention, 'frame', { x: retention.inset_x });

  const lip = spec.structure.inner_lip;
  const lipWidth = lip.width;
  const lipDepth = lip.depth;
  const lipWall = lip.wall;
  [
    ['inner-lip-north', { width: lipWidth, depth: lipWall, height: lip.height, radius: 0.02, lift: lip.lift }, { y: (lipDepth - lipWall) / 2 }],
    ['inner-lip-south', { width: lipWidth, depth: lipWall, height: lip.height, radius: 0.02, lift: lip.lift }, { y: -(lipDepth - lipWall) / 2 }],
    ['inner-lip-west', { width: lipWall, depth: lipDepth, height: lip.height, radius: 0.02, lift: lip.lift }, { x: -(lipWidth - lipWall) / 2 }],
    ['inner-lip-east', { width: lipWall, depth: lipDepth, height: lip.height, radius: 0.02, lift: lip.lift }, { x: (lipWidth - lipWall) / 2 }],
  ].forEach(([name, source, position]) => addPart(name, source, 'frame', position));

  if (allowed.has('frame-edges')) {
    const edgeSources = group.children.filter((child) => child.name.startsWith('frame-'));
    const edges = new THREE.Group();
    edges.name = 'frame-edges';
    edges.userData.visualPart = 'frame-edges';
    edgeSources.forEach((source) => {
      const edge = new THREE.LineSegments(
        new THREE.EdgesGeometry(source.geometry, 28),
        materialFor(spec, 'edge'),
      );
      edge.position.copy(source.position);
      edges.add(edge);
    });
    group.add(edges);
  }

  finishMetadata(group, spec, detailLevel);
  return { group, fallbackReason: null };
}
```

Before running tests, ensure each mesh uses the exact names from
`detail_levels`, source dimensions only through normalized ratios, and remains
inside the descriptor footprint.

- [ ] **Step 4: Run focused tests and inspect deterministic bounds**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs tests/component-visual-builder.test.mjs
```

Expected: 8 tests pass and no Node warning or unhandled rejection appears.

- [ ] **Step 5: Commit the procedural builder**

```powershell
git add assets/cross-source-registration/component-visual-builder.js `
  tests/component-visual-builder.test.mjs
git commit -m "feat: build staged connector visuals"
```

### Task 3: Integrate Reusable Visuals Into BoardRenderer

**Files:**
- Modify: `assets/cross-source-registration/model-profiles.js`
- Modify: `assets/cross-source-registration/board-renderer.js`
- Modify: `tests/model-profiles.test.mjs`
- Modify: `tests/model-toolbar.test.mjs`

- [ ] **Step 1: Write failing descriptor and renderer integration tests**

Add to `tests/model-profiles.test.mjs`:

```js
test('J6101 descriptor carries reusable visual-spec identity', () => {
  const source = component('connector', 'reviewed', { x: 0.157, y: 0.079 });
  source.inspection_profile = { profile_id: 'j6101-connector-v1', fidelity: 'repair_visual' };
  const descriptor = buildRenderDescriptor(source, { reviewed: true });
  assert.equal(descriptor.componentVisualSpecId, 'connector-j6101-repair-visual-v1');
});
```

Replace the old connector source-shape assertion in `tests/model-toolbar.test.mjs`
with:

```js
test('reviewed connector profiles use the reusable component visual builder', () => {
  assert.match(rendererSource, /buildComponentVisual/);
  assert.match(rendererSource, /replaceComponentVisualDetail/);
  assert.doesNotMatch(rendererSource, /function addInspectionConnectorPackage/);
  assert.doesNotMatch(rendererSource, /j6101/i);
});

test('component inspection switches visual detail and restores board detail', () => {
  const enterSource = rendererSource.slice(
    rendererSource.indexOf('async setComponentInspection'),
    rendererSource.indexOf('async resetComponentInspectionView'),
  );
  const exitSource = rendererSource.slice(
    rendererSource.indexOf('async clearComponentInspection'),
    rendererSource.indexOf('isComponentInspectionActive'),
  );
  assert.match(enterSource, /replaceComponentVisualDetail\(componentId, 'isolated'\)/);
  assert.match(exitSource, /replaceComponentVisualDetail\(componentId, 'board'\)/);
  assert.match(rendererSource, /visualFallbackReason/);
});
```

- [ ] **Step 2: Run the focused integration tests and verify RED**

Run:

```powershell
node --test tests/model-profiles.test.mjs tests/model-toolbar.test.mjs
```

Expected: FAIL because the descriptor has no `componentVisualSpecId` and the
renderer still owns `addInspectionConnectorPackage`.

- [ ] **Step 3: Resolve reusable visual identity in model profiles**

In `model-profiles.js`, import `resolveComponentVisualSpec` and add to the
descriptor:

```js
const componentVisualSpec = resolveComponentVisualSpec(
  component.inspection_profile?.profile_id,
);

return {
  // existing descriptor fields stay unchanged
  componentVisualSpecId: componentVisualSpec?.spec_id || null,
};
```

Do not remove `visualAsset`; existing browser selectors and compatibility tests
still use `reviewed-connector`.

- [ ] **Step 4: Replace connector-specific geometry with builder integration**

In `board-renderer.js`:

```js
import { buildComponentVisual } from './component-visual-builder.js';

function createPackageMesh(descriptor, detailLevel = 'board') {
  const refined = buildComponentVisual(descriptor, detailLevel);
  if (refined.group) return refined.group;

  const group = new THREE.Group();
  if (descriptor.visualAsset === 'reviewed-pmic') addInspectionPmicPackage(group, descriptor);
  else if (descriptor.visualAsset === 'reviewed-bga') addInspectionBgaPackage(group, descriptor);
  else if (descriptor.visualAsset === 'reviewed-crystal') addInspectionCrystalPackage(group, descriptor);
  else if (descriptor.family === 'passive') addPassivePackage(group, descriptor);
  else if (descriptor.family === 'ic') addIcPackage(group, descriptor);
  else if (descriptor.family === 'connector') addConnectorPackage(group, descriptor);
  else if (descriptor.family === 'crystal') addCrystalPackage(group, descriptor);
  else if (descriptor.family === 'inductor') addInductorPackage(group, descriptor);
  else if (descriptor.family === 'test-point') addTestPoint(group, descriptor);
  else if (descriptor.family === 'antenna') addFlatMetalPackage(group, descriptor);
  else addGenericPackage(group, descriptor);
  group.userData.visualFallbackReason = refined.fallbackReason;
  return group;
}
```

Delete `addInspectionConnectorPackage`. Keep the generic connector package as
the fail-soft fallback.

- [ ] **Step 5: Implement transform-preserving detail replacement**

Add renderer methods:

```js
disposeObject(object) {
  object.traverse((child) => {
    child.geometry?.dispose();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.filter(Boolean).forEach((item) => item.dispose());
  });
  object.removeFromParent();
}

replaceComponentVisualDetail(componentId, detailLevel) {
  const descriptor = this.descriptors.get(componentId);
  const previous = this.renderObjects.get(componentId);
  if (!descriptor || !previous || descriptor.layer !== 'body') return previous;
  const next = createPackageMesh(descriptor, detailLevel);
  if (!next.userData.visualSpecId && previous.userData.visualSpecId) return previous;

  next.position.copy(previous.position);
  next.rotation.copy(previous.rotation);
  next.scale.copy(previous.scale);
  next.visible = previous.visible;
  next.userData.componentId = componentId;
  next.traverse((child) => {
    child.userData.componentId = componentId;
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });
  captureMaterialState(next);
  this.group.add(next);
  this.renderObjects.set(componentId, next);
  if (descriptor.selectable) this.meshes.set(componentId, next);
  this.disposeObject(previous);
  this.container.dataset.componentVisualDetail = detailLevel;
  this.container.dataset.componentVisualSpec = next.userData.visualSpecId || '';
  this.container.dataset.componentVisualFallback = next.userData.visualFallbackReason || '';
  return next;
}
```

Call `replaceComponentVisualDetail(componentId, 'isolated')` before obtaining
the object and inspection snapshot in `setComponentInspection`. In
`clearComponentInspection`, animate the isolated object back to its saved board
transform, then call `replaceComponentVisualDetail(componentId, 'board')`
before clearing the snapshot.

After replacement, reapply inspection opacity/material snapshots and ensure the
selected identity, pick target, external label, affordance, camera, and
inspection profile remain unchanged.

- [ ] **Step 6: Run all model tests and verify GREEN**

Run:

```powershell
node --test tests/component-visual-specs.test.mjs `
  tests/component-visual-builder.test.mjs `
  tests/model-profiles.test.mjs `
  tests/model-toolbar.test.mjs `
  tests/component-inspection-state.test.mjs `
  tests/model-interaction-state.test.mjs
```

Expected: all focused tests pass.

- [ ] **Step 7: Commit renderer integration**

```powershell
git add assets/cross-source-registration/model-profiles.js `
  assets/cross-source-registration/board-renderer.js `
  tests/model-profiles.test.mjs tests/model-toolbar.test.mjs
git commit -m "feat: integrate reusable connector visuals"
```

### Task 4: Browser Visual And Interaction QA

**Files:**
- Evidence only: `output/playwright/j6101-component-visual-refinement/`
- Modify if defects are found: `assets/cross-source-registration/component-visual-specs.js`
- Modify if defects are found: `assets/cross-source-registration/component-visual-builder.js`
- Modify if defects are found: `assets/cross-source-registration/board-renderer.js`

- [ ] **Step 1: Start the actual local application**

Run from the worktree:

```powershell
G:\Programming\mainboard-repair-system\.venv\Scripts\python.exe ai_proxy_server.py
```

Expected: the app serves the repository worktree on a free local port. Record
the exact URL. Do not use a static mockup or the brainstorm companion for QA.

- [ ] **Step 2: Capture the board-level J6101 state at desktop**

Open:

```text
/assets/cross-source-registration/?board=km4-f151
```

At `1600x900`:

1. Select board side `main_page_2`.
2. Open the `2.5D 维修视图`.
3. Select J6101 from the entity list.
4. Assert `#modelCanvas` has:
   - `data-component-visual-spec="connector-j6101-repair-visual-v1"`;
   - `data-component-visual-detail="board"`;
   - empty `data-component-visual-fallback`.
5. Save `desktop-board-j6101.png`.
6. Sample the WebGL canvas and assert non-background pixels occupy a meaningful
   area around the selected component.

- [ ] **Step 3: Capture and exercise isolated-component inspection**

Enter `单体查看` and assert:

1. `data-component-visual-detail="isolated"`;
2. `data-inspection-visual-asset="reviewed-connector"`;
3. the selected component remains `KM4-MAIN-J6101`;
4. the board context becomes translucent;
5. no label leader or board-only anatomy control remains visible.

Perform:

- mouse drag in both axes;
- wheel zoom in and out;
- ArrowLeft, ArrowUp, `+`, `-`, and Home;
- return through the canvas-local return action;
- re-enter and exit with Escape.

Save:

- `desktop-isolated-j6101.png`;
- `desktop-isolated-j6101-rotated.png`;
- `desktop-board-restored.png`.

Assert there are zero page errors, zero console errors, and no horizontal or
vertical document overflow.

- [ ] **Step 4: Repeat the interaction matrix at 390 px touch width**

At `390x844`:

1. Select J6101 through the entity list and reveal the model.
2. Enter isolated view.
3. Rotate with a one-finger drag.
4. Zoom with a two-finger pinch.
5. Return to the board and verify the selected identity remains J6101.
6. Save `mobile-board-j6101.png` and `mobile-isolated-j6101.png`.

Assert:

- the component stays fully inside the canvas;
- buttons and text do not overlap;
- all text/control contrast is readable;
- the canvas is nonblank;
- the page has zero runtime errors.

- [ ] **Step 5: Compare visual acceptance against the baseline**

Use the pre-change screenshot or Git parent rendered at the same viewport.
Record a short `qa-summary.md` in the ignored evidence directory with:

```markdown
# J6101 Visual QA

- Route: http://127.0.0.1:8899/assets/cross-source-registration/?board=km4-f151
- Commit: output recorded from `git rev-parse HEAD`
- Desktop: board / isolated / rotated / restored passed
- Mobile: board / isolated / rotated / restored passed
- Source boundary: no individual pins, pitch, solder feet, vendor latch, or internals
- Visual hierarchy: base / frame / opening / contact region / retention separable
- Canvas: nonblank with component-region contrast
- Runtime: 0 page errors, 0 console errors
- Overflow: none
```

Replace the commit-output description with the 40-character value returned by
`git rev-parse HEAD` before acceptance. If any item fails, add a failing
automated assertion where possible, make the smallest source-bounded correction,
and repeat all affected screenshots.

### Task 5: Full Regression, Documentation, And Completion Audit

**Files:**
- Modify: `docs/km4-cross-source-registration-2026-07-13.md`
- Modify: `docs/superpowers/plans/2026-07-30-j6101-component-visual-refinement.md`

- [ ] **Step 1: Run the complete Node suite**

Run:

```powershell
node --test tests/*.test.mjs
```

Expected: all tests pass; the baseline was 250 tests before adding this feature.

- [ ] **Step 2: Run the source-bound Python regression**

Run:

```powershell
G:\Programming\mainboard-repair-system\.venv\Scripts\python.exe -m unittest `
  tests.test_validate_cross_source_registration `
  tests.test_compile_km4_board `
  tests.test_ai_proxy_static -v
```

Expected: 27 tests pass.

- [ ] **Step 3: Validate repository state**

Run:

```powershell
git diff --check
git status --short
git log --oneline -6
```

Expected: no whitespace errors; only intended source, test, documentation, and
ignored browser evidence changes are present.

- [ ] **Step 4: Document the verified result**

Append a dated section to `docs/km4-cross-source-registration-2026-07-13.md`
that records:

- the reusable `ComponentVisualSpec` architecture;
- J6101's five source-bounded visual layers;
- prohibited unsupported detail;
- fail-soft generic connector fallback;
- board/isolated detail switching;
- exact Node and Python test totals;
- exact browser route, desktop/mobile viewports, screenshot directory, canvas
  pixel result, overflow result, and runtime error counts;
- explicit statement that no engineering CAD accuracy or real pin geometry is
  claimed.

- [ ] **Step 5: Mark this plan with actual completion evidence**

Check completed boxes only after their corresponding command or visual
observation has been executed. Do not mark browser or full regression tasks
complete based on focused unit tests.

- [ ] **Step 6: Commit documentation and final verification record**

```powershell
git add docs/km4-cross-source-registration-2026-07-13.md `
  docs/superpowers/plans/2026-07-30-j6101-component-visual-refinement.md
git commit -m "docs: verify J6101 visual refinement"
```

- [ ] **Step 7: Perform requirement-by-requirement completion audit**

Verify current files and evidence prove:

1. J6101 uses a validated reusable visual specification.
2. The four build stages and named parts are deterministic.
3. Board and isolated detail levels both render and transition correctly.
4. Invalid/unknown specs fall back without a blank board.
5. Unsupported engineering details are absent.
6. Existing interaction semantics remain intact.
7. Automated suites pass.
8. Desktop and mobile browser evidence passes visual, interaction, canvas,
   overflow, contrast, and runtime gates.
9. Documentation reflects the exact verified state.

Only after all nine items are directly supported by current evidence may the
active goal be marked complete.
