import assert from 'node:assert/strict';
import test from 'node:test';

import * as THREE from '../assets/vendor/three/three.module.min.js';
import {
  buildComponentVisual,
  componentVisualBounds,
  disposeComponentVisual,
} from '../assets/cross-source-registration/component-visual-builder.js';
import {
  COMPONENT_VISUAL_MATERIALS,
  J6101_CONNECTOR_VISUAL_SPEC,
  U2001_PMIC_VISUAL_SPEC,
} from '../assets/cross-source-registration/component-visual-specs.js';

const DESCRIPTOR = Object.freeze({
  dimensions: Object.freeze({ x: 0.314, y: 0.09875, z: 0.045 }),
  inspectionProfile: Object.freeze({ profile_id: 'j6101-connector-v1' }),
});

const U2001_DESCRIPTOR = Object.freeze({
  dimensions: Object.freeze({ x: 0.96, y: 1.35, z: 0.18 }),
  inspectionProfile: Object.freeze({ profile_id: 'u2001-pmic-v1' }),
});

const BOARD_NAMES = Object.freeze([
  'base',
  'contact',
  'frame-east',
  'frame-north',
  'frame-south',
  'frame-west',
  'opening',
]);

const ISOLATED_NAMES = Object.freeze([
  'base',
  'contact',
  'frame-east',
  'frame-edges',
  'frame-north',
  'frame-south',
  'frame-west',
  'inner-lip-east',
  'inner-lip-north',
  'inner-lip-south',
  'inner-lip-west',
  'opening',
  'retention-east',
  'retention-west',
]);

const U2001_BOARD_NAMES = Object.freeze([
  'body',
  'orientation-marker',
  'substrate',
  'top',
]);

const U2001_ISOLATED_NAMES = Object.freeze([
  'body',
  'body-edges',
  'orientation-marker',
  'substrate',
  'substrate-edges',
  'top',
  'top-seam',
]);

function build(detailLevel = 'board', descriptor = DESCRIPTOR, dependencies) {
  const result = buildComponentVisual(descriptor, detailLevel, dependencies);
  assert.equal(result.fallbackReason, null);
  assert.ok(result.group instanceof THREE.Group);
  return result.group;
}

function directPartNames(group) {
  return group.children.map((child) => child.name).sort();
}

function resources(group) {
  const geometries = [];
  const materials = [];
  group.traverse((child) => {
    if (child.geometry) geometries.push(child.geometry);
    if (child.material) materials.push(child.material);
  });
  return { geometries, materials };
}

function snapshot(group) {
  const values = [];
  group.traverse((child) => {
    values.push({
      type: child.type,
      name: child.name,
      visualPart: child.userData.visualPart || null,
      position: child.position.toArray(),
      geometry: child.geometry
        ? Array.from(child.geometry.attributes.position.array)
        : null,
      material: child.material
        ? {
          type: child.material.type,
          color: child.material.color?.getHex() ?? null,
          roughness: child.material.roughness ?? null,
          metalness: child.material.metalness ?? null,
          opacity: child.material.opacity,
        }
        : null,
    });
  });
  return values;
}

function assertInsideFootprint(descriptor, detailLevel) {
  const group = build(detailLevel, descriptor);
  const box = new THREE.Box3().setFromObject(group);
  const tolerance = (value) => Math.max(1e-9, value * 1e-6);
  assert.ok(box.min.x >= -descriptor.dimensions.x / 2 - tolerance(descriptor.dimensions.x));
  assert.ok(box.max.x <= descriptor.dimensions.x / 2 + tolerance(descriptor.dimensions.x));
  assert.ok(box.min.y >= -descriptor.dimensions.y / 2 - tolerance(descriptor.dimensions.y));
  assert.ok(box.max.y <= descriptor.dimensions.y / 2 + tolerance(descriptor.dimensions.y));
  assert.ok(box.min.z >= -tolerance(descriptor.dimensions.z));
  assert.ok(box.max.z <= descriptor.dimensions.z + tolerance(descriptor.dimensions.z));
}

test('J6101 board builds with exact deterministic stage metadata and part names', () => {
  const group = build();
  assert.deepEqual(group.userData, {
    visualSpecId: 'connector-j6101-repair-visual-v1',
    visualSpecVersion: 1,
    visualAssetType: 'procedural',
    visualDetailLevel: 'board',
    visualStages: ['blockout', 'structure', 'material', 'polish'],
    visualPartNames: BOARD_NAMES,
    visualBoundaryNote: J6101_CONNECTOR_VISUAL_SPEC.boundary_note,
  });
  assert.deepEqual(directPartNames(group), BOARD_NAMES);
});

test('U2001 board builds deterministic IC BGA stages and named parts', () => {
  const group = build('board', U2001_DESCRIPTOR);
  assert.deepEqual(group.userData, {
    visualSpecId: 'ic-bga-u2001-repair-visual-v1',
    visualSpecVersion: 1,
    visualAssetType: 'procedural',
    visualDetailLevel: 'board',
    visualStages: ['blockout', 'structure', 'material', 'polish'],
    visualPartNames: U2001_BOARD_NAMES,
    visualBoundaryNote: U2001_PMIC_VISUAL_SPEC.boundary_note,
  });
  assert.deepEqual(directPartNames(group), U2001_BOARD_NAMES);
});

test('U2001 isolated detail adds only source-bounded package edges', () => {
  const board = build('board', U2001_DESCRIPTOR);
  const isolated = build('isolated', U2001_DESCRIPTOR);
  assert.deepEqual(isolated.userData.visualPartNames, U2001_ISOLATED_NAMES);
  assert.deepEqual(directPartNames(isolated), U2001_ISOLATED_NAMES);
  assert.ok(U2001_BOARD_NAMES.every((name) => U2001_ISOLATED_NAMES.includes(name)));
  ['substrate-edges', 'body-edges', 'top-seam'].forEach((name) => {
    assert.ok(isolated.getObjectByName(name) instanceof THREE.LineSegments);
    assert.equal(board.getObjectByName(name), undefined);
  });
});

test('U2001 hierarchy, material roles, and orientation cue remain explicit', () => {
  const group = build('isolated', U2001_DESCRIPTOR);
  const roles = {
    substrate: 'ic-substrate',
    body: 'molded-package',
    top: 'inset-top',
    'orientation-marker': 'orientation-marker',
  };
  Object.entries(roles).forEach(([partName, token]) => {
    const mesh = group.getObjectByName(partName);
    const expected = COMPONENT_VISUAL_MATERIALS[token];
    assert.ok(mesh instanceof THREE.Mesh);
    assert.equal(mesh.userData.visualMaterial, token);
    assert.equal(mesh.material.color.getHex(), expected.color);
    assert.equal(mesh.material.roughness, expected.roughness);
    assert.equal(mesh.material.metalness, expected.metalness);
  });
  assert.ok(group.getObjectByName('orientation-marker').geometry instanceof THREE.CylinderGeometry);

  const substrate = new THREE.Box3().setFromObject(group.getObjectByName('substrate'));
  const body = new THREE.Box3().setFromObject(group.getObjectByName('body'));
  const top = new THREE.Box3().setFromObject(group.getObjectByName('top'));
  const marker = new THREE.Box3().setFromObject(group.getObjectByName('orientation-marker'));
  assert.ok(body.min.z >= substrate.max.z - 1e-8);
  assert.ok(top.min.z >= body.max.z - U2001_DESCRIPTOR.dimensions.z * 0.03);
  assert.ok(top.max.z > body.max.z);
  assert.ok(marker.min.z >= top.min.z - 1e-8);
  assert.ok(marker.max.x > top.getCenter(new THREE.Vector3()).x);
  assert.ok(marker.max.y > top.getCenter(new THREE.Vector3()).y);
});

test('U2001 visual makes no ball grid, pad, marking, lead, or internal claim', () => {
  const group = build('isolated', U2001_DESCRIPTOR);
  const prohibited = /ball|pad|marking|lead|die|internal|pitch|vendor|millimet(?:er|re)|\bmm\b/i;
  group.traverse((child) => {
    assert.equal(prohibited.test(child.name), false, child.name);
    assert.equal(prohibited.test(child.userData.visualPart || ''), false);
  });
});

test('isolated detail is the exact named superset with edges and no pin geometry', () => {
  const board = build('board');
  const isolated = build('isolated');
  assert.deepEqual(isolated.userData.visualPartNames, ISOLATED_NAMES);
  assert.deepEqual(directPartNames(isolated), ISOLATED_NAMES);
  assert.ok(BOARD_NAMES.every((name) => ISOLATED_NAMES.includes(name)));
  assert.ok(isolated.getObjectByName('frame-edges') instanceof THREE.Group);
  isolated.getObjectByName('frame-edges').children.forEach((child) => {
    assert.ok(child instanceof THREE.LineSegments);
  });
  assert.equal(board.getObjectByName('frame-edges'), undefined);
});

test('part names and metadata do not make prohibited connector claims', () => {
  const group = build('isolated');
  const prohibited = /pin|pitch|solder|vendor[-_ ]?latch|spring|millimet(?:er|re)|\bmm\b/i;
  group.traverse((child) => {
    assert.equal(prohibited.test(child.name), false, child.name);
    assert.equal(prohibited.test(child.userData.visualPart || ''), false);
  });
  assert.equal(prohibited.test(JSON.stringify({
    visualSpecId: group.userData.visualSpecId,
    visualAssetType: group.userData.visualAssetType,
    visualDetailLevel: group.userData.visualDetailLevel,
    visualStages: group.userData.visualStages,
    visualPartNames: group.userData.visualPartNames,
  })), false);
});

test('every mesh has stable part metadata, shadows, and an independently owned resource pair', () => {
  const group = build('isolated');
  const meshes = [];
  group.traverse((child) => {
    if (!child.isMesh) return;
    meshes.push(child);
    assert.equal(child.name, child.userData.visualPart);
    assert.equal(child.castShadow, true);
    assert.equal(child.receiveShadow, true);
  });
  assert.equal(meshes.length, 13);
  assert.equal(new Set(meshes.map((mesh) => mesh.geometry)).size, meshes.length);
  assert.equal(new Set(meshes.map((mesh) => mesh.material)).size, meshes.length);
});

test('semantic material families come directly from the immutable catalog', () => {
  const group = build('isolated');
  const roles = {
    base: 'engineering-plastic',
    opening: 'recessed-polymer',
    contact: 'contact-metal',
    'frame-north': 'plated-metal',
    'retention-west': 'plated-metal',
    'inner-lip-east': 'plated-metal',
  };
  Object.entries(roles).forEach(([partName, token]) => {
    const mesh = group.getObjectByName(partName);
    const expected = COMPONENT_VISUAL_MATERIALS[token];
    assert.equal(mesh.userData.visualMaterial, token);
    assert.equal(mesh.material.color.getHex(), expected.color);
    assert.equal(mesh.material.roughness, expected.roughness);
    assert.equal(mesh.material.metalness, expected.metalness);
  });
  const edgeGroup = group.getObjectByName('frame-edges');
  edgeGroup.children.forEach((line) => {
    const expected = COMPONENT_VISUAL_MATERIALS['edge-line'];
    assert.equal(line.userData.visualMaterial, 'edge-line');
    assert.equal(line.material.color.getHex(), expected.color);
    assert.equal(line.material.opacity, expected.opacity);
  });
});

test('frame walls form a real opening around the recessed floor', () => {
  const group = build();
  const north = new THREE.Box3().setFromObject(group.getObjectByName('frame-north'));
  const south = new THREE.Box3().setFromObject(group.getObjectByName('frame-south'));
  const west = new THREE.Box3().setFromObject(group.getObjectByName('frame-west'));
  const east = new THREE.Box3().setFromObject(group.getObjectByName('frame-east'));
  const opening = new THREE.Box3().setFromObject(group.getObjectByName('opening'));
  assert.ok(opening.max.y < north.min.y);
  assert.ok(opening.min.y > south.max.y);
  assert.ok(opening.min.x > west.max.x);
  assert.ok(opening.max.x < east.min.x);
});

test('inner-lip rails meet at corners without positive-volume intersection', () => {
  const group = build('isolated');
  const boxes = Object.fromEntries(
    ['north', 'south', 'west', 'east'].map((side) => [
      side,
      new THREE.Box3().setFromObject(group.getObjectByName(`inner-lip-${side}`)),
    ]),
  );
  [
    ['north', 'west'],
    ['north', 'east'],
    ['south', 'west'],
    ['south', 'east'],
  ].forEach(([horizontal, vertical]) => {
    const first = boxes[horizontal];
    const second = boxes[vertical];
    const overlap = {
      x: Math.max(0, Math.min(first.max.x, second.max.x) - Math.max(first.min.x, second.min.x)),
      y: Math.max(0, Math.min(first.max.y, second.max.y) - Math.max(first.min.y, second.min.y)),
      z: Math.max(0, Math.min(first.max.z, second.max.z) - Math.max(first.min.z, second.min.z)),
    };
    assert.ok(first.intersectsBox(second));
    assert.ok(overlap.z > 0);
    assert.ok(overlap.x <= 1e-8 || overlap.y <= 1e-8, JSON.stringify(overlap));
    assert.ok(overlap.x * overlap.y * overlap.z <= 1e-12, JSON.stringify(overlap));
  });
});

test('board and isolated bounds stay within normal and extreme valid descriptors', () => {
  const descriptors = [
    DESCRIPTOR,
    {
      ...DESCRIPTOR,
      dimensions: { x: 1e-6, y: 20, z: 3e-5 },
    },
    {
      ...DESCRIPTOR,
      dimensions: { x: 15, y: 2e-6, z: 9 },
    },
  ];
  descriptors.forEach((descriptor) => {
    ['board', 'isolated'].forEach((detailLevel) => {
      assertInsideFootprint(descriptor, detailLevel);
      const bounds = componentVisualBounds(build(detailLevel, descriptor));
      Object.values(bounds).forEach((value) => {
        assert.equal(Number.isFinite(value), true);
        assert.ok(value > 0);
      });
      assert.ok(bounds.width <= descriptor.dimensions.x + Math.max(1e-9, descriptor.dimensions.x * 1e-6));
      assert.ok(bounds.depth <= descriptor.dimensions.y + Math.max(1e-9, descriptor.dimensions.y * 1e-6));
      assert.ok(bounds.height <= descriptor.dimensions.z + Math.max(1e-9, descriptor.dimensions.z * 1e-6));
    });
  });
});

test('U2001 board and isolated bounds stay inside normal and extreme descriptors', () => {
  const descriptors = [
    U2001_DESCRIPTOR,
    { ...U2001_DESCRIPTOR, dimensions: { x: 1e-6, y: 20, z: 3e-5 } },
    { ...U2001_DESCRIPTOR, dimensions: { x: 15, y: 2e-6, z: 9 } },
  ];
  descriptors.forEach((descriptor) => {
    ['board', 'isolated'].forEach((detailLevel) => {
      assertInsideFootprint(descriptor, detailLevel);
      const bounds = componentVisualBounds(build(detailLevel, descriptor));
      Object.values(bounds).forEach((value) => {
        assert.equal(Number.isFinite(value), true);
        assert.ok(value > 0);
      });
    });
  });
});

test('relationally overflowing IC BGA ratios fail after measured bounds validation', () => {
  const spec = structuredClone(U2001_PMIC_VISUAL_SPEC);
  spec.structure.marker.radius = 0.9;
  spec.structure.marker.offset_x = 0.9;
  spec.structure.marker.offset_y = 0.9;
  spec.structure.top.height = 1;
  spec.structure.top.lift = 1;
  assert.deepEqual(
    buildComponentVisual(U2001_DESCRIPTOR, 'board', {
      resolveSpec: () => spec,
    }),
    {
      group: null,
      fallbackReason: 'visual_bounds_exceeded',
    },
  );
});

test('unrepresentable underflow and overflow dimensions fail as invalid input', () => {
  [Number.MIN_VALUE, 1e-320, Number.MAX_VALUE].forEach((value) => {
    ['x', 'y', 'z'].forEach((axis) => {
      const descriptor = {
        ...DESCRIPTOR,
        dimensions: { ...DESCRIPTOR.dimensions, [axis]: value },
      };
      assert.deepEqual(buildComponentVisual(descriptor), {
        group: null,
        fallbackReason: 'invalid_dimensions',
      });
    });
  });
});

test('safe representable dimension boundaries retain finite positive bounds', () => {
  [
    { x: 1e-6, y: 1e-6, z: 1e-6 },
    { x: 100, y: 100, z: 100 },
  ].forEach((dimensions) => {
    const group = build('isolated', { ...DESCRIPTOR, dimensions });
    const bounds = componentVisualBounds(group);
    Object.values(bounds).forEach((value) => {
      assert.equal(Number.isFinite(value), true);
      assert.ok(value > 0);
    });
  });
});

test('repeated builds produce identical geometry and transforms', () => {
  assert.deepEqual(snapshot(build('isolated')), snapshot(build('isolated')));
  assert.deepEqual(
    snapshot(build('isolated', U2001_DESCRIPTOR)),
    snapshot(build('isolated', U2001_DESCRIPTOR)),
  );
});

test('U2001 builds own independent resources and dispose exactly once', () => {
  const first = build('isolated', U2001_DESCRIPTOR);
  const second = build('isolated', U2001_DESCRIPTOR);
  const firstResources = resources(first);
  const secondResources = resources(second);
  firstResources.geometries.forEach((geometry) => {
    assert.equal(secondResources.geometries.includes(geometry), false);
  });
  firstResources.materials.forEach((material) => {
    assert.equal(secondResources.materials.includes(material), false);
  });
  assert.deepEqual(disposeComponentVisual(first), {
    geometries: firstResources.geometries.length,
    materials: firstResources.materials.length,
    failureCount: 0,
    cleanupWarning: null,
  });
  assert.deepEqual(disposeComponentVisual(first), {
    geometries: 0,
    materials: 0,
    failureCount: 0,
    cleanupWarning: null,
  });
  assert.deepEqual(disposeComponentVisual(second), {
    geometries: secondResources.geometries.length,
    materials: secondResources.materials.length,
    failureCount: 0,
    cleanupWarning: null,
  });
});

test('builds do not share mutable geometry or material state', () => {
  const first = build('isolated');
  const second = build('isolated');
  const firstResources = resources(first);
  const secondResources = resources(second);
  assert.equal(new Set(firstResources.geometries).size, firstResources.geometries.length);
  assert.equal(new Set(firstResources.materials).size, firstResources.materials.length);
  firstResources.geometries.forEach((geometry) => {
    assert.equal(secondResources.geometries.includes(geometry), false);
  });
  firstResources.materials.forEach((material) => {
    assert.equal(secondResources.materials.includes(material), false);
  });
  first.getObjectByName('base').material.color.setHex(0xff00ff);
  assert.equal(
    second.getObjectByName('base').material.color.getHex(),
    COMPONENT_VISUAL_MATERIALS['engineering-plastic'].color,
  );
});

test('fallbacks are stable and fail soft for profiles, details, and dimensions', () => {
  const cases = [
    [
      { ...DESCRIPTOR, inspectionProfile: { profile_id: 'unknown' } },
      'board',
      'visual_spec_not_found',
    ],
    [{ ...DESCRIPTOR, dimensions: { x: 0, y: 1, z: 1 } }, 'board', 'invalid_dimensions'],
    [{ ...DESCRIPTOR, dimensions: { x: 1, y: Number.NaN, z: 1 } }, 'board', 'invalid_dimensions'],
    [{ ...DESCRIPTOR, dimensions: { x: 1, y: 1 } }, 'board', 'invalid_dimensions'],
    [DESCRIPTOR, 'cinematic', 'unknown_detail_level'],
  ];
  cases.forEach(([descriptor, detailLevel, fallbackReason]) => {
    let result;
    assert.doesNotThrow(() => {
      result = buildComponentVisual(descriptor, detailLevel);
    });
    assert.deepEqual(result, { group: null, fallbackReason });
  });
  assert.deepEqual(buildComponentVisual(null), {
    group: null,
    fallbackReason: 'visual_spec_not_found',
  });
});

test('validator failures propagate the stable first error code without throwing', () => {
  const invalidSpec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  invalidSpec.spec_id = '';
  let result;
  assert.doesNotThrow(() => {
    result = buildComponentVisual(DESCRIPTOR, 'board', {
      resolveSpec: () => invalidSpec,
    });
  });
  assert.deepEqual(result, { group: null, fallbackReason: 'invalid_identity' });
});

test('throwing descriptor access paths fail soft with a stable build error', () => {
  const throwingInspectionProfile = {};
  Object.defineProperty(throwingInspectionProfile, 'inspectionProfile', {
    get() {
      throw new Error('inspection profile access failed');
    },
  });
  const throwingProfileId = {
    inspectionProfile: {},
  };
  Object.defineProperty(throwingProfileId.inspectionProfile, 'profile_id', {
    get() {
      throw new Error('profile ID access failed');
    },
  });

  [throwingInspectionProfile, throwingProfileId].forEach((descriptor) => {
    let result;
    assert.doesNotThrow(() => {
      result = buildComponentVisual(descriptor);
    });
    assert.deepEqual(result, { group: null, fallbackReason: 'visual_build_error' });
  });
});

test('throwing resolved spec access paths fail soft with a stable build error', () => {
  ['spec_id', 'materials', 'structure', 'detail_levels'].forEach((field) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    Object.defineProperty(spec, field, {
      configurable: true,
      get() {
        throw new Error(`${field} access failed`);
      },
    });
    let result;
    assert.doesNotThrow(() => {
      result = buildComponentVisual(DESCRIPTOR, 'board', {
        resolveSpec: () => spec,
      });
    });
    assert.deepEqual(result, { group: null, fallbackReason: 'visual_build_error' });
  });
});

test('late build failure disposes every partially allocated resource and returns no group', () => {
  const geometryDispose = THREE.BufferGeometry.prototype.dispose;
  const materialDispose = THREE.Material.prototype.dispose;
  let geometryDisposals = 0;
  let materialDisposals = 0;
  THREE.BufferGeometry.prototype.dispose = function disposeGeometry() {
    geometryDisposals += 1;
    return geometryDispose.call(this);
  };
  THREE.Material.prototype.dispose = function disposeMaterial() {
    materialDisposals += 1;
    return materialDispose.call(this);
  };

  try {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    let identityReads = 0;
    Object.defineProperty(spec, 'spec_id', {
      configurable: true,
      get() {
        identityReads += 1;
        if (identityReads > 2) throw new Error('late identity access failed');
        return J6101_CONNECTOR_VISUAL_SPEC.spec_id;
      },
    });
    let result;
    assert.doesNotThrow(() => {
      result = buildComponentVisual(DESCRIPTOR, 'isolated', {
        resolveSpec: () => spec,
      });
    });
    assert.deepEqual(result, { group: null, fallbackReason: 'visual_build_error' });
    assert.equal(geometryDisposals, 17);
    assert.equal(materialDisposals, 17);
  } finally {
    THREE.BufferGeometry.prototype.dispose = geometryDispose;
    THREE.Material.prototype.dispose = materialDispose;
  }
});

test('component disposal owns original resources and ignores replacements and foreign children', () => {
  const first = build('isolated');
  const second = build('isolated');
  const firstResources = resources(first);
  const secondResources = resources(second);
  const firstEvents = new Map();
  const secondEvents = new Map();
  const foreignEvents = new Map();

  [...firstResources.geometries, ...firstResources.materials].forEach((resource) => {
    firstEvents.set(resource, 0);
    resource.addEventListener('dispose', () => {
      firstEvents.set(resource, firstEvents.get(resource) + 1);
    });
  });
  [...secondResources.geometries, ...secondResources.materials].forEach((resource) => {
    secondEvents.set(resource, 0);
    resource.addEventListener('dispose', () => {
      secondEvents.set(resource, secondEvents.get(resource) + 1);
    });
  });

  const base = first.getObjectByName('base');
  const detachedOwnedMaterial = base.material;
  const replacementGeometry = new THREE.BoxGeometry(1, 1, 1);
  const replacementMaterial = new THREE.MeshBasicMaterial();
  base.geometry = replacementGeometry;
  base.material = replacementMaterial;
  const foreignGeometry = new THREE.BoxGeometry(1, 1, 1);
  const foreignMaterial = new THREE.MeshBasicMaterial();
  first.add(new THREE.Mesh(foreignGeometry, foreignMaterial));
  [
    replacementGeometry,
    replacementMaterial,
    foreignGeometry,
    foreignMaterial,
  ].forEach((resource) => {
    foreignEvents.set(resource, 0);
    resource.addEventListener('dispose', () => {
      foreignEvents.set(resource, foreignEvents.get(resource) + 1);
    });
  });

  try {
    assert.ok(firstResources.materials.includes(detachedOwnedMaterial));
    assert.deepEqual(disposeComponentVisual(first), {
      geometries: firstResources.geometries.length,
      materials: firstResources.materials.length,
      failureCount: 0,
      cleanupWarning: null,
    });
    firstEvents.forEach((count) => assert.equal(count, 1));
    secondEvents.forEach((count) => assert.equal(count, 0));
    foreignEvents.forEach((count) => assert.equal(count, 0));

    assert.deepEqual(disposeComponentVisual(first), {
      geometries: 0,
      materials: 0,
      failureCount: 0,
      cleanupWarning: null,
    });
    firstEvents.forEach((count) => assert.equal(count, 1));
    foreignEvents.forEach((count) => assert.equal(count, 0));

    assert.deepEqual(disposeComponentVisual(second), {
      geometries: secondResources.geometries.length,
      materials: secondResources.materials.length,
      failureCount: 0,
      cleanupWarning: null,
    });
    secondEvents.forEach((count) => assert.equal(count, 1));
  } finally {
    replacementGeometry.dispose();
    replacementMaterial.dispose();
    foreignGeometry.dispose();
    foreignMaterial.dispose();
  }
});

test('component disposal attempts all owned resources when one disposal throws', () => {
  const group = build('isolated');
  const owned = resources(group);
  const allResources = [...owned.geometries, ...owned.materials];
  const attempts = new Map(allResources.map((resource) => [resource, 0]));
  const originals = new Map(allResources.map((resource) => [resource, resource.dispose]));
  const failingResource = allResources[0];

  allResources.forEach((resource) => {
    resource.dispose = function trackedDispose() {
      attempts.set(resource, attempts.get(resource) + 1);
      if (resource === failingResource) throw new Error('owned resource disposal failed');
      return originals.get(resource).call(this);
    };
  });

  let result;
  assert.doesNotThrow(() => {
    result = disposeComponentVisual(group);
  });

  attempts.forEach((count) => assert.equal(count, 1));
  assert.deepEqual(result, {
    geometries: owned.geometries.length,
    materials: owned.materials.length,
    failureCount: 1,
    cleanupWarning: 'previous_visual_cleanup_failed',
  });
});

test('componentVisualBounds returns finite Three.js Box3 dimensions', () => {
  const bounds = componentVisualBounds(build());
  assert.deepEqual(Object.keys(bounds), ['width', 'depth', 'height']);
  assert.ok(bounds.width > 0);
  assert.ok(bounds.depth > 0);
  assert.ok(bounds.height > 0);
  Object.values(bounds).forEach((value) => assert.equal(Number.isFinite(value), true));
});
