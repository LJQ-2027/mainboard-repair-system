import test from 'node:test';
import assert from 'node:assert/strict';

import {
  canStartPointMapPan,
  centerPoint,
  clampZoom,
  zoomAt,
} from '../assets/cross-source-registration/point-map-viewport.js';

test('clampZoom keeps the point map within its readable zoom range', () => {
  assert.equal(clampZoom(0.5), 1);
  assert.equal(clampZoom(3.5), 3.5);
  assert.equal(clampZoom(12), 8);
});

test('zoomAt preserves the board point beneath the pointer', () => {
  const next = zoomAt({ scale: 1, x: 0, y: 0 }, 2, { x: 300, y: 200 });
  assert.deepEqual(next, { scale: 2, x: -300, y: -200 });
});

test('centerPoint places a normalized board coordinate at viewport center', () => {
  const next = centerPoint(
    { x: 0.25, y: 0.75 },
    { width: 1200, height: 800 },
    { width: 600, height: 400 },
    3,
  );
  assert.deepEqual(next, { scale: 3, x: -600, y: -1600 });
});

test('point-map pan yields pointer input to interactive markers', () => {
  assert.equal(canStartPointMapPan({ interactive: false, button: 0 }), true);
  assert.equal(canStartPointMapPan({ interactive: true, button: 0 }), false);
  assert.equal(canStartPointMapPan({ interactive: false, button: 2 }), false);
});
