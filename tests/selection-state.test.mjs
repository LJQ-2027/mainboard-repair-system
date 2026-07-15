import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildSelectionState,
  entityListModelRevealOptions,
  findEntityAtPoint,
  nearestPointerTarget,
} from '../assets/cross-source-registration/selection-state.js';

const entity = {
  component_id: 'KM4-MAIN-U2001',
  designator: 'U2001',
  geometry: { center: { x: 0.5, y: 0.6 }, size: { x: 0.1, y: 0.12 } },
  schematic_links: [{ source: 'schematic.pdf', page: '8' }],
  repair_links: [{ source: 'guide.pdf', page: '10' }],
};

test('selection state keeps one identity across every view', () => {
  const state = buildSelectionState(entity, [1, 0, 0.1, 0, 1, 0.2, 0, 0, 1]);
  assert.equal(state.componentId, 'KM4-MAIN-U2001');
  assert.deepEqual(state.boardPoint, { x: 0.5, y: 0.6 });
  assert.deepEqual(state.photoPoint, { x: 0.6, y: 0.8 });
  assert.equal(state.schematicLinks.length, 1);
  assert.equal(state.repairLinks.length, 1);
});

test('point picking returns the smallest entity containing the point', () => {
  const large = { ...entity, component_id: 'large', geometry: { center: { x: 0.5, y: 0.5 }, size: { x: 0.5, y: 0.5 } } };
  const small = { ...entity, component_id: 'small', geometry: { center: { x: 0.5, y: 0.5 }, size: { x: 0.1, y: 0.1 } } };
  assert.equal(findEntityAtPoint([large, small], { x: 0.52, y: 0.52 }).component_id, 'small');
  assert.equal(findEntityAtPoint([large, small], { x: 0.9, y: 0.9 }), null);
});

test('dense marker picking resolves the dot nearest the actual pointer', () => {
  const targets = [
    { id: 'U2001', center: { x: 100, y: 100 } },
    { id: 'U4000', center: { x: 112, y: 108 } },
    { id: 'VBUS1', center: { x: 300, y: 300 } },
  ];
  assert.equal(nearestPointerTarget(targets, { x: 111, y: 107 }), 'U4000');
  assert.equal(nearestPointerTarget(targets, { x: 101, y: 99 }), 'U2001');
  assert.equal(nearestPointerTarget([], { x: 0, y: 0 }), null);
});

test('entity list selection reveals the model workspace only on narrow model viewports', () => {
  assert.deepEqual(entityListModelRevealOptions({
    activeView: 'model',
    viewportWidth: 390,
    reducedMotion: false,
  }), { behavior: 'smooth', block: 'start' });
  assert.equal(entityListModelRevealOptions({
    activeView: 'photo',
    viewportWidth: 390,
    reducedMotion: false,
  }), null);
  assert.equal(entityListModelRevealOptions({
    activeView: 'model',
    viewportWidth: 821,
    reducedMotion: false,
  }), null);
});

test('entity list model reveal respects reduced motion and includes the mobile breakpoint', () => {
  assert.deepEqual(entityListModelRevealOptions({
    activeView: 'model',
    viewportWidth: 820,
    reducedMotion: true,
  }), { behavior: 'auto', block: 'start' });
});
