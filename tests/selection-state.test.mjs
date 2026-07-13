import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSelectionState, findEntityAtPoint } from '../assets/cross-source-registration/selection-state.js';

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
