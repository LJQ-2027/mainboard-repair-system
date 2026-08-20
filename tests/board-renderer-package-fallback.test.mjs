import assert from 'node:assert/strict';
import test from 'node:test';

import * as THREE from '../assets/vendor/three/three.module.min.js';
import {
  BoardRenderer,
  createPackageMesh,
} from '../assets/cross-source-registration/board-renderer.js';

const DIMENSIONS = Object.freeze({ x: 0.192, y: 0.16875, z: 0.032 });
const SHARED_BGA_PROFILES = Object.freeze([
  ['U4000', 'u4000-emmc-v1'],
  ['U0600', 'u0600-rf-device-v1'],
  ['connectivity', 'connectivity-bga-v1'],
]);
const BOARD_PART_NAMES = Object.freeze([
  'body',
  'orientation-marker',
  'substrate',
  'top',
]);

function resources(group) {
  const geometries = [];
  const materials = [];
  group.traverse((child) => {
    if (child.geometry) geometries.push(child.geometry);
    if (child.material) materials.push(child.material);
  });
  return { geometries, materials };
}

test('U2001 package creation prefers the reusable IC BGA visual', () => {
  const group = createPackageMesh({
    family: 'ic',
    visualAsset: 'reviewed-pmic',
    dimensions: DIMENSIONS,
    inspectionProfile: { profile_id: 'u2001-pmic-v1' },
  });

  assert.ok(group instanceof THREE.Group);
  assert.equal(group.userData.visualSpecId, 'ic-bga-u2001-repair-visual-v1');
  assert.equal(group.userData.visualFallbackReason, undefined);
  assert.deepEqual(
    group.userData.visualPartNames,
    ['body', 'orientation-marker', 'substrate', 'top'],
  );

  BoardRenderer.prototype.disposeObject.call({}, group);
});

SHARED_BGA_PROFILES.forEach(([designator, profileId]) => {
  test(`${designator} package creation returns the shared BGA visual`, () => {
    const group = createPackageMesh({
      family: 'ic',
      visualAsset: 'reviewed-bga',
      dimensions: DIMENSIONS,
      inspectionProfile: { profile_id: profileId },
    });

    assert.ok(group instanceof THREE.Group);
    assert.equal(
      group.userData.visualSpecId,
      'ic-bga-shared-package-repair-visual-v1',
    );
    assert.deepEqual(group.userData.visualPartNames, BOARD_PART_NAMES);
    assert.equal(group.userData.visualFallbackReason, undefined);

    BoardRenderer.prototype.disposeObject.call({}, group);
  });
});

test('unknown reviewed BGA profile returns a nonblank generic IC and disposes exactly once', () => {
  const group = createPackageMesh({
    family: 'ic',
    visualAsset: 'reviewed-bga',
    dimensions: DIMENSIONS,
    inspectionProfile: { profile_id: 'missing-reviewed-bga-spec' },
  });
  const parent = new THREE.Group();
  parent.add(group);
  const owned = resources(group);
  const disposalEvents = new Map(
    [...owned.geometries, ...owned.materials].map((resource) => [resource, 0]),
  );
  disposalEvents.forEach((_, resource) => {
    resource.addEventListener('dispose', () => {
      disposalEvents.set(resource, disposalEvents.get(resource) + 1);
    });
  });

  assert.ok(group instanceof THREE.Group);
  assert.ok(group.children.length > 0);
  assert.ok(group.children.some((child) => child instanceof THREE.Mesh));
  assert.equal(group.userData.visualSpecId, undefined);
  assert.equal(group.userData.visualFallbackReason, 'visual_spec_not_found');
  assert.equal(owned.geometries.length, 2);
  assert.equal(owned.materials.length, 2);

  const result = BoardRenderer.prototype.disposeObject.call({}, group);
  assert.deepEqual(result, {
    geometries: 2,
    textures: 0,
    materials: 2,
    failureCount: 0,
    cleanupWarning: null,
  });
  assert.equal(parent.children.includes(group), false);
  disposalEvents.forEach((count) => assert.equal(count, 1));
});
