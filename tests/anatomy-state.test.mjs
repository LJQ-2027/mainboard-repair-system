import test from 'node:test';
import assert from 'node:assert/strict';

import {
  extractModuleRegions,
  extractShieldRegions,
  getShieldPresentation,
  isPointCovered,
  shouldShowLabels,
} from '../assets/cross-source-registration/anatomy-state.js';

test('shield extraction keeps only source-classified shield regions', () => {
  const geometry = { regions: [
    { geometry_id: 'shield-a', category: 'shield_region', center: { x: 0.5, y: 0.5 }, size: { x: 0.2, y: 0.3 }, polygon: [[0.4, 0.5], [0.5, 0.35], [0.6, 0.5], [0.5, 0.65]], semantic_status: 'unresolved_geometry' },
    { geometry_id: 'other-a', category: 'source_geometry', center: { x: 0.2, y: 0.2 }, size: { x: 0.1, y: 0.1 } },
  ] };
  assert.deepEqual(extractShieldRegions(geometry), [{
    shieldId: 'shield-a',
    center: { x: 0.5, y: 0.5 },
    size: { x: 0.2, y: 0.3 },
    polygon: [[0.4, 0.5], [0.5, 0.35], [0.6, 0.5], [0.5, 0.65]],
    sourceStatus: 'unresolved_geometry',
  }]);
});

test('anatomy modes consistently control shields and covered package bodies', () => {
  assert.deepEqual(getShieldPresentation('installed'), { visible: true, opacity: 0.96, coveredBodiesVisible: false });
  assert.deepEqual(getShieldPresentation('xray'), { visible: true, opacity: 0.3, coveredBodiesVisible: true });
  assert.deepEqual(getShieldPresentation('removed'), { visible: false, opacity: 0, coveredBodiesVisible: true });
  assert.deepEqual(getShieldPresentation('invalid'), getShieldPresentation('removed'));
});

test('point coverage uses normalized shield bounds with optional padding', () => {
  const shield = { center: { x: 0.5, y: 0.5 }, size: { x: 0.2, y: 0.3 } };
  assert.equal(isPointCovered({ x: 0.55, y: 0.62 }, shield), true);
  assert.equal(isPointCovered({ x: 0.7, y: 0.5 }, shield), false);
  assert.equal(isPointCovered({ x: 0.605, y: 0.5 }, shield, 0.01), true);
});

test('point coverage follows a source polygon when one is available', () => {
  const shield = {
    center: { x: 0.5, y: 0.5 },
    size: { x: 0.4, y: 0.4 },
    polygon: [[0.5, 0.3], [0.7, 0.5], [0.5, 0.7], [0.3, 0.5]],
  };
  assert.equal(isPointCovered({ x: 0.5, y: 0.5 }, shield), true);
  assert.equal(isPointCovered({ x: 0.68, y: 0.68 }, shield), false);
});

test('module extraction keeps only valid source-backed polygons for the requested side', () => {
  const atlas = { boards: [{ modules: [
    { module_id: 'power', name: 'Power', side_id: 'main_page_2', polygon: [[0.1, 0.2], [0.3, 0.2], [0.3, 0.4], [0.1, 0.4]], designators: ['U1'], status: 'source_overlay' },
    { module_id: 'other-side', name: 'Other', side_id: 'main_page_1', polygon: [[0, 0], [1, 0], [1, 1]], designators: ['U2'], status: 'source_overlay' },
    { module_id: 'draft', name: 'Draft', side_id: 'main_page_2', polygon: [], status: 'draft' },
  ] }] };
  assert.deepEqual(extractModuleRegions(atlas, 'main_page_2'), [{
    moduleId: 'power',
    name: 'Power',
    designators: ['U1'],
    polygon: [[0.1, 0.2], [0.3, 0.2], [0.3, 0.4], [0.1, 0.4]],
  }]);
});

test('designator labels appear only after the repair view is zoomed in', () => {
  assert.equal(shouldShowLabels(1), false);
  assert.equal(shouldShowLabels(1.54), false);
  assert.equal(shouldShowLabels(1.55), true);
  assert.equal(shouldShowLabels(3), true);
});
