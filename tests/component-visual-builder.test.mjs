import assert from 'node:assert/strict';
import test from 'node:test';

import * as THREE from '../assets/vendor/three/three.module.min.js';
import {
  buildComponentVisual,
  componentVisualBounds,
} from '../assets/cross-source-registration/component-visual-builder.js';
import {
  COMPONENT_VISUAL_MATERIALS,
  J6101_CONNECTOR_VISUAL_SPEC,
} from '../assets/cross-source-registration/component-visual-specs.js';

const DESCRIPTOR = Object.freeze({
  dimensions: Object.freeze({ x: 0.314, y: 0.09875, z: 0.045 }),
  inspectionProfile: Object.freeze({ profile_id: 'j6101-connector-v1' }),
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

test('repeated builds produce identical geometry and transforms', () => {
  assert.deepEqual(snapshot(build('isolated')), snapshot(build('isolated')));
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

test('componentVisualBounds returns finite Three.js Box3 dimensions', () => {
  const bounds = componentVisualBounds(build());
  assert.deepEqual(Object.keys(bounds), ['width', 'depth', 'height']);
  assert.ok(bounds.width > 0);
  assert.ok(bounds.depth > 0);
  assert.ok(bounds.height > 0);
  Object.values(bounds).forEach((value) => assert.equal(Number.isFinite(value), true));
});
