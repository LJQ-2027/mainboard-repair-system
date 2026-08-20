import test from 'node:test';
import assert from 'node:assert/strict';

import {
  anchorZoomCenter,
  clampPanCenter,
  pinchZoom,
  resolveBoardInteractionMode,
  screenDeltaToPan,
} from '../assets/cross-source-registration/board-pan-state.js';

test('board interaction defaults to pan and accepts only known modes', () => {
  assert.equal(resolveBoardInteractionMode('pan'), 'pan');
  assert.equal(resolveBoardInteractionMode('rotate'), 'rotate');
  assert.equal(resolveBoardInteractionMode('inspect'), 'pan');
});

test('screen drag becomes zoom-aware orthographic camera movement', () => {
  assert.deepEqual(screenDeltaToPan({
    dx: 100,
    dy: 50,
    width: 1000,
    height: 500,
    frameWidth: 2,
    frameHeight: 1,
    zoom: 2,
  }), { x: -0.1, y: 0.05 });

  assert.deepEqual(screenDeltaToPan({
    dx: 100,
    dy: 50,
    width: 1000,
    height: 500,
    frameWidth: 2,
    frameHeight: 1,
    zoom: 4,
  }), { x: -0.05, y: 0.025 });
});

test('manual camera center remains inside board-relative pan bounds', () => {
  assert.deepEqual(clampPanCenter({ x: 3, y: -2 }), { x: 0.92, y: -0.62 });
  assert.deepEqual(clampPanCenter({ x: -3, y: 2 }), { x: -0.92, y: 0.62 });
  assert.deepEqual(clampPanCenter({ x: 0.2, y: -0.1 }), { x: 0.2, y: -0.1 });
});

test('pinch distance produces bounded model zoom', () => {
  assert.equal(pinchZoom({ startDistance: 80, currentDistance: 160, startZoom: 1, minimum: 0.72, maximum: 4.2 }), 2);
  assert.equal(pinchZoom({ startDistance: 100, currentDistance: 50, startZoom: 2, minimum: 0.72, maximum: 4.2 }), 1);
  assert.equal(pinchZoom({ startDistance: 10, currentDistance: 500, startZoom: 2, minimum: 0.72, maximum: 4.2 }), 4.2);
  assert.equal(pinchZoom({ startDistance: 0, currentDistance: 100, startZoom: 2, minimum: 0.72, maximum: 4.2 }), 2);
});

test('zoom anchoring keeps the board point beneath the pointer or pinch midpoint', () => {
  assert.deepEqual(anchorZoomCenter({
    camera: { x: 0, y: 0 },
    startNdc: { x: 0.5, y: 0 },
    currentNdc: { x: 0.5, y: 0 },
    frame: { width: 2, height: 1 },
    startZoom: 1,
    currentZoom: 2,
  }), { x: 0.25, y: 0 });

  assert.deepEqual(anchorZoomCenter({
    camera: { x: 0, y: 0 },
    startNdc: { x: 0.5, y: 0.5 },
    currentNdc: { x: 0.25, y: 0.25 },
    frame: { width: 2, height: 1 },
    startZoom: 1,
    currentZoom: 2,
  }), { x: 0.375, y: 0.1875 });
});
