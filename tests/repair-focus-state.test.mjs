import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildEntityTarget,
  buildModuleTarget,
  isPointInFocus,
  polygonBounds,
  resetFocusView,
  resolveTargetSide,
} from '../assets/cross-source-registration/repair-focus-state.js';

const boardId = 'BOARD-KM4-F151-MAIN-V1.2';
const powerModule = {
  moduleId: 'power_pmu',
  sideId: 'main_page_2',
  designators: ['U2001'],
  polygon: [[0.42, 0.48], [0.66, 0.48], [0.66, 0.76], [0.42, 0.76]],
};
const entity = {
  component_id: 'KM4-MAIN-P2-U2001',
  designator: 'U2001',
  side_id: 'main_page_2',
  geometry: { center: { x: 0.542, y: 0.669 }, size: { x: 0.08, y: 0.07 } },
};

test('polygon bounds preserve the normalized center and size', () => {
  assert.deepEqual(polygonBounds(powerModule.polygon), {
    center: { x: 0.54, y: 0.62 },
    size: { x: 0.24, y: 0.28 },
  });
});

test('entity target uses its source-backed module as the repair focus region', () => {
  assert.deepEqual(buildEntityTarget(boardId, entity, [powerModule]), {
    boardId,
    sideId: 'main_page_2',
    targetType: 'entity',
    targetId: 'KM4-MAIN-P2-U2001',
    focusRegion: polygonBounds(powerModule.polygon),
    recommendedSideId: 'main_page_2',
    moduleId: 'power_pmu',
  });
});

test('entity without a module gets a conservative local focus region', () => {
  const target = buildEntityTarget(boardId, entity, []);
  assert.deepEqual(target.focusRegion, {
    center: { x: 0.542, y: 0.669 },
    size: { x: 0.18, y: 0.18 },
  });
  assert.equal(target.moduleId, null);
});

test('module target keeps the source side and polygon bounds', () => {
  assert.deepEqual(buildModuleTarget(boardId, powerModule), {
    boardId,
    sideId: 'main_page_2',
    targetType: 'module',
    targetId: 'power_pmu',
    focusRegion: polygonBounds(powerModule.polygon),
    recommendedSideId: 'main_page_2',
    moduleId: 'power_pmu',
  });
});

test('side resolution preserves a valid current side and never guesses without a recommendation', () => {
  const bothSides = { availableSideIds: ['main_page_1', 'main_page_2'], recommendedSideId: 'main_page_2' };
  assert.equal(resolveTargetSide(bothSides, 'main_page_1'), 'main_page_1');
  assert.equal(resolveTargetSide(bothSides, 'unknown'), 'main_page_2');
  assert.equal(resolveTargetSide({ availableSideIds: [], recommendedSideId: null }, 'main_page_1'), 'main_page_1');
});

test('full-board reset clears only the camera focus', () => {
  const target = buildEntityTarget(boardId, entity, [powerModule]);
  assert.deepEqual(resetFocusView({ target, activeSideId: 'main_page_2', focusRegion: target.focusRegion }), {
    target,
    activeSideId: 'main_page_2',
    focusRegion: null,
  });
});

test('focus membership limits labels to the local repair region', () => {
  const region = { center: { x: 0.5, y: 0.5 }, size: { x: 0.2, y: 0.3 } };
  assert.equal(isPointInFocus({ x: 0.58, y: 0.62 }, region), true);
  assert.equal(isPointInFocus({ x: 0.78, y: 0.5 }, region), false);
  assert.equal(isPointInFocus({ x: 0.78, y: 0.5 }, null), true);
});
