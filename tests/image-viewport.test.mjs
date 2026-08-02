import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ImageViewport,
  canStartImagePan,
  centerPoint,
  clampZoom,
  zoomAt,
} from '../assets/cross-source-registration/image-viewport.js';


function fakeElement({ width, height, layer = false }) {
  const listeners = new Map();
  const classes = new Set();
  return {
    clientWidth: width,
    clientHeight: height,
    offsetWidth: width,
    offsetHeight: height,
    dataset: {},
    style: {},
    addEventListener(type, handler) { listeners.set(type, handler); },
    dispatch(type, event) { listeners.get(type)?.(event); },
    getBoundingClientRect() { return { left: 0, top: 0 }; },
    setPointerCapture(pointerId) { this.capturedPointer = pointerId; },
    classList: {
      add(name) { classes.add(name); },
      remove(name) { classes.delete(name); },
      contains(name) { return classes.has(name); },
    },
    ...(layer ? { offsetWidth: width, offsetHeight: height } : {}),
  };
}

test('shared image math preserves zoom bounds and normalized focus', () => {
  assert.equal(clampZoom(0.2), 1);
  assert.equal(clampZoom(9), 8);
  assert.deepEqual(
    zoomAt({ scale: 1, x: 0, y: 0 }, 2, { x: 100, y: 50 }),
    { scale: 2, x: -100, y: -50 },
  );
  assert.deepEqual(
    centerPoint(
      { x: 0.25, y: 0.75 },
      { width: 1000, height: 500 },
      { width: 500, height: 300 },
      4,
    ),
    { scale: 4, x: -750, y: -1350 },
  );
});

test('image pan yields to controls and accepts primary touch-compatible pointers', () => {
  assert.equal(canStartImagePan({ interactive: false, button: 0 }), true);
  assert.equal(canStartImagePan({ interactive: true, button: 0 }), false);
  assert.equal(canStartImagePan({ interactive: false, button: 2 }), false);
});

test('pointer tracking pans only the captured pointer', () => {
  const view = fakeElement({ width: 600, height: 400 });
  const layer = fakeElement({ width: 1000, height: 700, layer: true });
  const viewport = new ImageViewport(view, layer);
  const target = { closest: () => null };

  view.dispatch('pointerdown', { target, button: 0, pointerId: 7, clientX: 20, clientY: 30 });
  view.dispatch('pointermove', { pointerId: 8, clientX: 200, clientY: 200 });
  assert.deepEqual(viewport.state, { scale: 1, x: 0, y: 0 });
  view.dispatch('pointermove', { pointerId: 7, clientX: 70, clientY: 90 });

  assert.deepEqual(viewport.state, { scale: 1, x: 50, y: 60 });
  assert.equal(view.capturedPointer, 7);
  assert.equal(view.classList.contains('dragging'), true);
  view.dispatch('pointerup', { pointerId: 7 });
  assert.equal(view.classList.contains('dragging'), false);
});

test('component focus centers an image-space coordinate', () => {
  const view = fakeElement({ width: 600, height: 400 });
  const layer = fakeElement({ width: 1200, height: 800, layer: true });
  const viewport = new ImageViewport(view, layer);

  viewport.focus({ x: 0.5, y: 0.25 }, 3);

  assert.deepEqual(viewport.state, { scale: 3, x: -1200, y: -200 });
  assert.equal(view.dataset.zoom, '300%');
});

test('image replacement resets navigation only when the asset changes', () => {
  const view = fakeElement({ width: 600, height: 400 });
  const layer = fakeElement({ width: 1200, height: 800, layer: true });
  const viewport = new ImageViewport(view, layer);
  viewport.replaceImage('photo-a');
  viewport.state = { scale: 4, x: 40, y: -20 };

  viewport.replaceImage('photo-a');
  assert.deepEqual(viewport.state, { scale: 4, x: 40, y: -20 });
  viewport.replaceImage('photo-b');
  assert.deepEqual(viewport.state, { scale: 1, x: 0, y: 0 });
  assert.equal(view.dataset.zoom, '100%');
});
