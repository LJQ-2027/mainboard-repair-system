import test from 'node:test';
import assert from 'node:assert/strict';

import {
  clampPanCenter,
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
