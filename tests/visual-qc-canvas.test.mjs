import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createViewport,
  imageFrame,
  normalizedToScreen,
  screenToNormalized,
  zoomViewportAt,
} from '../assets/visual-qc-workbench/canvas-stage.js';

test('canvas viewport fits the complete image and preserves normalized coordinates', () => {
  const viewport = createViewport();
  const frame = imageFrame({ width: 800, height: 600 }, { width: 1600, height: 900 }, viewport);

  assert.deepEqual(frame, { x: 0, y: 75, width: 800, height: 450 });
  const screen = normalizedToScreen({ x: 0.25, y: 0.75 }, frame);
  assert.deepEqual(screenToNormalized(screen, frame), { x: 0.25, y: 0.75 });
});

test('zoom keeps the normalized image point beneath the cursor', () => {
  const canvas = { width: 800, height: 600 };
  const image = { width: 1600, height: 900 };
  const pointer = { x: 600, y: 300 };
  const before = imageFrame(canvas, image, createViewport());
  const normalized = screenToNormalized(pointer, before);
  const zoomed = zoomViewportAt(createViewport(), 2, pointer, canvas, image);
  const after = imageFrame(canvas, image, zoomed);
  const restored = normalizedToScreen(normalized, after);

  assert.ok(Math.abs(restored.x - pointer.x) < 1e-9);
  assert.ok(Math.abs(restored.y - pointer.y) < 1e-9);
});
