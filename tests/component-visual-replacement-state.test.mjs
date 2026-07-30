import assert from 'node:assert/strict';
import test from 'node:test';

async function loadReplacementState() {
  try {
    return await import('../assets/cross-source-registration/component-visual-replacement-state.js');
  } catch {
    return {};
  }
}

function vector(x, y, z) {
  return {
    x,
    y,
    z,
    copy(source) {
      this.x = source.x;
      this.y = source.y;
      this.z = source.z;
      return this;
    },
  };
}

function object(userData = {}) {
  const child = { userData: {}, isMesh: true, castShadow: false, receiveShadow: false };
  return {
    position: vector(1, 2, 3),
    rotation: vector(0.1, 0.2, 0.3),
    scale: vector(2, 3, 4),
    visible: false,
    renderOrder: 7,
    userData: { componentId: 'connector-1', retainedState: 'yes', ...userData },
    child,
    traverse(callback) {
      callback(this);
      callback(child);
    },
  };
}

test('failed component visual replacement keeps the previous object and maps fully intact', async () => {
  const { replaceComponentVisualState } = await loadReplacementState();
  assert.equal(typeof replaceComponentVisualState, 'function');
  const previous = object({ visualSpecId: 'connector-j6101-repair-visual-v1' });
  const renderObjects = new Map([['connector-1', previous]]);
  const meshes = new Map([['connector-1', previous]]);
  const events = [];

  const result = replaceComponentVisualState({
    componentId: 'connector-1',
    detailLevel: 'isolated',
    descriptor: {
      layer: 'body',
      selectable: true,
      componentVisualSpecId: 'connector-j6101-repair-visual-v1',
    },
    previous,
    buildVisual() {
      events.push('build');
      return { group: null, fallbackReason: 'visual_build_error' };
    },
    addObject() {
      events.push('add');
    },
    disposeObject() {
      events.push('dispose');
    },
    captureMaterialState() {
      events.push('capture');
    },
    renderObjects,
    meshes,
  });

  assert.equal(result.object, previous);
  assert.equal(result.replaced, false);
  assert.equal(result.fallbackReason, 'visual_build_error');
  assert.equal(previous.userData.visualFallbackReason, 'visual_build_error');
  assert.equal(renderObjects.get('connector-1'), previous);
  assert.equal(meshes.get('connector-1'), previous);
  assert.deepEqual(events, ['build']);
});

test('successful component visual replacement preserves transforms and swaps atomically', async () => {
  const { replaceComponentVisualState } = await loadReplacementState();
  assert.equal(typeof replaceComponentVisualState, 'function');
  const previous = object({
    visualSpecId: 'connector-j6101-repair-visual-v1',
    visualDetailLevel: 'board',
  });
  const next = object({
    visualSpecId: 'connector-j6101-repair-visual-v1',
    visualDetailLevel: 'isolated',
    retainedState: undefined,
  });
  next.position = vector(0, 0, 0);
  next.rotation = vector(0, 0, 0);
  next.scale = vector(1, 1, 1);
  next.visible = true;
  next.renderOrder = 0;
  const renderObjects = new Map([['connector-1', previous]]);
  const meshes = new Map([['connector-1', previous]]);
  const events = [];

  const result = replaceComponentVisualState({
    componentId: 'connector-1',
    detailLevel: 'isolated',
    descriptor: {
      layer: 'body',
      selectable: true,
      componentVisualSpecId: 'connector-j6101-repair-visual-v1',
    },
    previous,
    buildVisual() {
      events.push('build');
      return { group: next, fallbackReason: null };
    },
    addObject() {
      events.push('add');
      assert.equal(renderObjects.get('connector-1'), previous);
    },
    disposeObject(disposed) {
      events.push('dispose');
      assert.equal(disposed, previous);
      assert.equal(renderObjects.get('connector-1'), next);
      assert.equal(meshes.get('connector-1'), next);
    },
    captureMaterialState(captured) {
      events.push('capture');
      assert.equal(captured, next);
    },
    renderObjects,
    meshes,
  });

  assert.equal(result.object, next);
  assert.equal(result.replaced, true);
  assert.equal(result.fallbackReason, null);
  assert.deepEqual(
    { x: next.position.x, y: next.position.y, z: next.position.z },
    { x: previous.position.x, y: previous.position.y, z: previous.position.z },
  );
  assert.deepEqual(
    { x: next.rotation.x, y: next.rotation.y, z: next.rotation.z },
    { x: previous.rotation.x, y: previous.rotation.y, z: previous.rotation.z },
  );
  assert.deepEqual(
    { x: next.scale.x, y: next.scale.y, z: next.scale.z },
    { x: previous.scale.x, y: previous.scale.y, z: previous.scale.z },
  );
  assert.equal(next.visible, previous.visible);
  assert.equal(next.renderOrder, previous.renderOrder);
  assert.equal(next.userData.componentId, 'connector-1');
  assert.equal(next.userData.retainedState, 'yes');
  assert.equal(next.userData.visualDetailLevel, 'isolated');
  assert.equal(next.child.userData.componentId, 'connector-1');
  assert.equal(next.child.castShadow, true);
  assert.equal(next.child.receiveShadow, true);
  assert.deepEqual(events, ['build', 'capture', 'add', 'dispose']);
});
