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
    removeFromParent() {
      this.parent?.delete(this);
      this.parent = null;
    },
  };
}

function reusableDescriptor() {
  return {
    layer: 'body',
    selectable: true,
    componentVisualSpecId: 'connector-j6101-repair-visual-v1',
  };
}

function replacementFixture(detailLevel = 'isolated') {
  const previous = object({
    visualSpecId: 'connector-j6101-repair-visual-v1',
    visualDetailLevel: detailLevel === 'isolated' ? 'board' : 'isolated',
  });
  const next = object({
    visualSpecId: 'connector-j6101-repair-visual-v1',
    visualDetailLevel: detailLevel,
  });
  const scene = new Set([previous]);
  previous.parent = scene;
  const renderObjects = new Map([['connector-1', previous]]);
  const meshes = new Map([['connector-1', previous]]);
  const disposals = new Map();
  const options = {
    componentId: 'connector-1',
    detailLevel,
    descriptor: reusableDescriptor(),
    previous,
    buildVisual() {
      return { group: next, fallbackReason: null };
    },
    addObject(candidate) {
      scene.add(candidate);
      candidate.parent = scene;
    },
    removeObject(candidate) {
      candidate.removeFromParent();
    },
    disposeObject(candidate) {
      disposals.set(candidate, (disposals.get(candidate) || 0) + 1);
      candidate.removeFromParent();
    },
    captureMaterialState() {},
    renderObjects,
    meshes,
  };
  return {
    disposals,
    meshes,
    next,
    options,
    previous,
    renderObjects,
    scene,
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
  assert.equal(result.detailCommitted, false);
  assert.equal(result.currentDetailLevel, undefined);
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
  assert.equal(result.detailCommitted, true);
  assert.equal(result.currentDetailLevel, 'isolated');
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

test('failed board restoration stays isolated and a later retry commits board detail', async () => {
  const { replaceComponentVisualState } = await loadReplacementState();
  assert.equal(typeof replaceComponentVisualState, 'function');
  const isolated = object({
    visualSpecId: 'connector-j6101-repair-visual-v1',
    visualDetailLevel: 'isolated',
  });
  const board = object({
    visualSpecId: 'connector-j6101-repair-visual-v1',
    visualDetailLevel: 'board',
  });
  const renderObjects = new Map([['connector-1', isolated]]);
  const meshes = new Map([['connector-1', isolated]]);
  const events = [];
  let attempts = 0;
  const options = {
    componentId: 'connector-1',
    detailLevel: 'board',
    descriptor: {
      layer: 'body',
      selectable: true,
      componentVisualSpecId: 'connector-j6101-repair-visual-v1',
    },
    previous: isolated,
    buildVisual() {
      attempts += 1;
      events.push(`build-${attempts}`);
      return attempts === 1
        ? { group: null, fallbackReason: 'visual_build_error' }
        : { group: board, fallbackReason: null };
    },
    addObject() {
      events.push('add-board');
    },
    disposeObject(disposed) {
      events.push(`dispose-${disposed.userData.visualDetailLevel}`);
    },
    captureMaterialState() {
      events.push('capture-board');
    },
    renderObjects,
    meshes,
  };

  const failed = replaceComponentVisualState(options);
  assert.deepEqual({
    object: failed.object,
    replaced: failed.replaced,
    detailCommitted: failed.detailCommitted,
    currentDetailLevel: failed.currentDetailLevel,
    fallbackReason: failed.fallbackReason,
  }, {
    object: isolated,
    replaced: false,
    detailCommitted: false,
    currentDetailLevel: 'isolated',
    fallbackReason: 'visual_build_error',
  });
  assert.equal(renderObjects.get('connector-1'), isolated);
  assert.equal(meshes.get('connector-1'), isolated);
  assert.deepEqual(events, ['build-1']);

  const committed = replaceComponentVisualState(options);
  assert.equal(committed.object, board);
  assert.equal(committed.replaced, true);
  assert.equal(committed.detailCommitted, true);
  assert.equal(committed.currentDetailLevel, 'board');
  assert.equal(committed.fallbackReason, null);
  assert.equal(renderObjects.get('connector-1'), board);
  assert.equal(meshes.get('connector-1'), board);
  assert.deepEqual(events, ['build-1', 'build-2', 'capture-board', 'add-board', 'dispose-isolated']);
});

test('legacy inspectable visuals commit enter and exit as unchanged no-ops', async () => {
  const { replaceComponentVisualState } = await loadReplacementState();
  assert.equal(typeof replaceComponentVisualState, 'function');
  const legacy = object({
    inspectionProfileId: 'u2001-pmic-v1',
    legacyMaterialState: 'retained',
  });
  const originalUserData = { ...legacy.userData };
  const renderObjects = new Map([['legacy-1', legacy]]);
  const meshes = new Map([['legacy-1', legacy]]);
  const events = [];
  const options = {
    componentId: 'legacy-1',
    descriptor: {
      layer: 'body',
      selectable: true,
      componentVisualSpecId: null,
    },
    previous: legacy,
    buildVisual() {
      events.push('build');
      return { group: null, fallbackReason: 'unexpected' };
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
  };

  const entered = replaceComponentVisualState({ ...options, detailLevel: 'isolated' });
  const exited = replaceComponentVisualState({ ...options, detailLevel: 'board' });

  [entered, exited].forEach((result) => {
    assert.equal(result.object, legacy);
    assert.equal(result.replaced, false);
    assert.equal(result.detailCommitted, true);
    assert.equal(result.currentDetailLevel, undefined);
    assert.equal(result.fallbackReason, null);
  });
  assert.equal(renderObjects.get('legacy-1'), legacy);
  assert.equal(meshes.get('legacy-1'), legacy);
  assert.deepEqual(legacy.userData, originalUserData);
  assert.deepEqual(events, []);
});

test('persistent isolated build failure keeps board mode usable until a later retry', async () => {
  const { replaceComponentVisualState } = await loadReplacementState();
  const fixture = replacementFixture('isolated');
  let buildFails = true;
  let buildCalls = 0;
  fixture.options.buildVisual = () => {
    buildCalls += 1;
    return buildFails
      ? { group: null, fallbackReason: 'visual_build_error' }
      : { group: fixture.next, fallbackReason: null };
  };

  const failedEntries = ['enter', 'exit', 'side', 'view', 'select', 'reset'].map(() => (
    replaceComponentVisualState(fixture.options)
  ));

  failedEntries.forEach((result) => {
    assert.equal(result.detailCommitted, false);
    assert.equal(result.object, fixture.previous);
    assert.equal(result.fallbackReason, 'visual_build_error');
  });
  assert.equal(fixture.renderObjects.get('connector-1'), fixture.previous);
  assert.equal(fixture.meshes.get('connector-1'), fixture.previous);
  assert.deepEqual([...fixture.scene], [fixture.previous]);
  assert.equal(fixture.disposals.size, 0);

  buildFails = false;
  const retried = replaceComponentVisualState(fixture.options);
  assert.equal(retried.detailCommitted, true);
  assert.equal(retried.object, fixture.next);
  assert.equal(buildCalls, 7);
});

for (const failure of [
  {
    name: 'material capture',
    reason: 'visual_replacement_capture_failed',
    install(fixture) {
      fixture.options.captureMaterialState = () => {
        throw new Error('capture failed');
      };
    },
  },
  {
    name: 'scene add',
    reason: 'visual_replacement_add_failed',
    install(fixture) {
      fixture.options.addObject = (candidate) => {
        fixture.scene.add(candidate);
        candidate.parent = fixture.scene;
        throw new Error('add failed after attachment');
      };
    },
  },
  {
    name: 'render object map commit',
    reason: 'visual_replacement_commit_failed',
    install(fixture) {
      const originalSet = fixture.renderObjects.set.bind(fixture.renderObjects);
      let failed = false;
      fixture.renderObjects.set = (key, value) => {
        if (!failed && value === fixture.next) {
          failed = true;
          originalSet(key, value);
          throw new Error('render map failed');
        }
        if (failed && value === fixture.previous) {
          throw new Error('render map rollback override failed');
        }
        return originalSet(key, value);
      };
    },
  },
  {
    name: 'selectable mesh map commit',
    reason: 'visual_replacement_commit_failed',
    install(fixture) {
      const originalSet = fixture.meshes.set.bind(fixture.meshes);
      let failed = false;
      fixture.meshes.set = (key, value) => {
        if (!failed && value === fixture.next) {
          failed = true;
          originalSet(key, value);
          throw new Error('mesh map failed');
        }
        return originalSet(key, value);
      };
    },
  },
  {
    name: 'previous object disposal',
    reason: 'visual_replacement_dispose_failed',
    install(fixture) {
      const baseDispose = fixture.options.disposeObject;
      fixture.options.disposeObject = (candidate) => {
        if (candidate === fixture.previous) throw new Error('previous disposal failed');
        baseDispose(candidate);
      };
    },
  },
]) {
  test(`${failure.name} failure rolls back replacement without throwing or leaking`, async () => {
    const { replaceComponentVisualState } = await loadReplacementState();
    const fixture = replacementFixture('isolated');
    failure.install(fixture);

    let result;
    assert.doesNotThrow(() => {
      result = replaceComponentVisualState(fixture.options);
    });

    assert.deepEqual({
      object: result.object,
      replaced: result.replaced,
      detailCommitted: result.detailCommitted,
      currentDetailLevel: result.currentDetailLevel,
      fallbackReason: result.fallbackReason,
    }, {
      object: fixture.previous,
      replaced: false,
      detailCommitted: false,
      currentDetailLevel: 'board',
      fallbackReason: failure.reason,
    });
    assert.equal(fixture.renderObjects.get('connector-1'), fixture.previous);
    assert.equal(fixture.meshes.get('connector-1'), fixture.previous);
    assert.equal(fixture.scene.has(fixture.previous), true);
    assert.equal(fixture.scene.has(fixture.next), false);
    assert.equal(fixture.disposals.get(fixture.next), 1);
    assert.equal(fixture.previous.userData.visualFallbackReason, failure.reason);
  });
}
