import assert from 'node:assert/strict';
import test from 'node:test';

import { disposeGenericObjectResources } from '../assets/cross-source-registration/component-visual-disposal-state.js';

function disposable(name, failures, attempts) {
  return {
    name,
    dispose() {
      attempts.push(name);
      if (failures.has(name)) throw new Error(`${name} failed`);
    },
  };
}

test('generic disposal attempts every unique resource and always detaches the object', () => {
  const attempts = [];
  const failures = new Set(['geometry-a', 'texture-b', 'material-b']);
  const geometryA = disposable('geometry-a', failures, attempts);
  const geometryB = disposable('geometry-b', failures, attempts);
  const textureA = disposable('texture-a', failures, attempts);
  const textureB = disposable('texture-b', failures, attempts);
  const materialA = { ...disposable('material-a', failures, attempts), map: textureA };
  const materialB = { ...disposable('material-b', failures, attempts), map: textureB };
  let detached = 0;
  const children = [
    {
      geometry: geometryA,
      material: [materialA, materialB],
      userData: { labelTextures: { duplicate: textureA } },
    },
    {
      geometry: geometryB,
      material: materialA,
      userData: { labelTextures: { extra: textureB } },
    },
  ];
  const object = {
    traverse(callback) {
      children.forEach(callback);
    },
    removeFromParent() {
      detached += 1;
    },
  };

  const result = disposeGenericObjectResources(object);

  assert.deepEqual(new Set(attempts), new Set([
    'geometry-a',
    'geometry-b',
    'texture-a',
    'texture-b',
    'material-a',
    'material-b',
  ]));
  assert.equal(attempts.length, 6);
  assert.equal(detached, 1);
  assert.equal(result.cleanupWarning, 'previous_visual_cleanup_failed');
  assert.equal(result.failureCount, 3);
});

test('generic disposal reports clean completion', () => {
  const attempts = [];
  const resource = disposable('geometry', new Set(), attempts);
  let detached = 0;
  const object = {
    traverse(callback) {
      callback({ geometry: resource, material: null, userData: {} });
    },
    removeFromParent() {
      detached += 1;
    },
  };

  const result = disposeGenericObjectResources(object);

  assert.deepEqual(attempts, ['geometry']);
  assert.equal(detached, 1);
  assert.equal(result.cleanupWarning, null);
  assert.equal(result.failureCount, 0);
});
