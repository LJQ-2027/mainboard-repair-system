import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildCornerSegments,
  buildHitArea,
  buildLabelPositions,
  resolveAffordancePresentation,
} from '../assets/cross-source-registration/component-affordance-state.js';

test('interactive frame uses eight short segments outside the package footprint', () => {
  const segments = buildCornerSegments({ x: 0.1, y: 0.06 });
  assert.equal(segments.length, 8);
  assert.equal(segments.every((segment) => segment.length === 2), true);
  assert.equal(segments.every((segment) => segment.every((point) => Math.abs(point.x) > 0.05 || Math.abs(point.y) > 0.03)), true);
});

test('nearby component labels are assigned separate vertical lanes', () => {
  const positions = buildLabelPositions([
    { id: 'A', center: { x: 0, y: -0.4 }, dimensions: { x: 0.04, y: 0.02 } },
    { id: 'B', center: { x: 0.05, y: -0.4 }, dimensions: { x: 0.04, y: 0.02 } },
    { id: 'C', center: { x: 0.1, y: -0.4 }, dimensions: { x: 0.04, y: 0.02 } },
  ]);
  assert.equal(new Set(positions.map((position) => position.y)).size, 3);
  assert.deepEqual(positions.map((position) => position.id), ['A', 'B', 'C']);
});

test('reviewed components receive bounded hit areas without inheriting complex mesh bounds', () => {
  assert.deepEqual(buildHitArea({ x: 0.1, y: 0.06 }), { x: 0.112, y: 0.072 });
  assert.deepEqual(buildHitArea({ x: 0.008, y: 0.006 }), { x: 0.047, y: 0.047 });
});

test('affordance states reserve coral for faults instead of ordinary selection', () => {
  const idle = resolveAffordancePresentation({});
  const hovered = resolveAffordancePresentation({ hovered: true });
  const selected = resolveAffordancePresentation({ selected: true });

  assert.equal(idle.opacity < hovered.opacity, true);
  assert.equal(selected.opacity, 1);
  assert.notEqual(selected.color, 0xef5b3f);
  assert.equal(selected.labelOpacity, 1);
});

test('selection takes precedence over hover presentation', () => {
  assert.deepEqual(
    resolveAffordancePresentation({ selected: true, hovered: true }),
    resolveAffordancePresentation({ selected: true }),
  );
});
