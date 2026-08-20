import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateRegistrationError,
  invertHomography,
  projectPoint,
  projectPolygon,
  solveHomography,
  validateAnchorPairs,
  validateNormalizedPoint,
} from '../assets/cross-source-registration/registration-core.js';

test('normalized points stay inside the canonical board plane', () => {
  assert.deepEqual(validateNormalizedPoint({ x: 0.25, y: 0.75 }), { x: 0.25, y: 0.75 });
  assert.throws(() => validateNormalizedPoint({ x: 1.1, y: 0.2 }), /normalized/);
});

test('four anchors solve a perspective projection', () => {
  const source = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 }];
  const target = [{ x: 120, y: 80 }, { x: 520, y: 100 }, { x: 480, y: 420 }, { x: 90, y: 390 }];
  const matrix = solveHomography(source, target);

  target.forEach((expected, index) => {
    const actual = projectPoint(matrix, source[index]);
    assert.ok(Math.abs(actual.x - expected.x) < 1e-6);
    assert.ok(Math.abs(actual.y - expected.y) < 1e-6);
  });
});

test('inverse projection returns the normalized source point', () => {
  const source = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 }];
  const target = [{ x: 40, y: 60 }, { x: 640, y: 40 }, { x: 600, y: 460 }, { x: 70, y: 440 }];
  const matrix = solveHomography(source, target);
  const point = { x: 0.37, y: 0.64 };
  const restored = projectPoint(invertHomography(matrix), projectPoint(matrix, point));

  assert.ok(Math.abs(restored.x - point.x) < 1e-6);
  assert.ok(Math.abs(restored.y - point.y) < 1e-6);
});

test('polygon projection preserves vertex count', () => {
  const identity = [1, 0, 0, 0, 1, 0, 0, 0, 1];
  const polygon = [{ x: 0.1, y: 0.2 }, { x: 0.4, y: 0.2 }, { x: 0.3, y: 0.6 }];
  assert.deepEqual(projectPolygon(identity, polygon), polygon);
});

test('registration anchors reject duplicates and inconsistent winding', () => {
  const board = [{ x: 0.1, y: 0.1 }, { x: 0.9, y: 0.1 }, { x: 0.9, y: 0.9 }, { x: 0.1, y: 0.9 }];
  const image = [{ x: 0.2, y: 0.2 }, { x: 0.8, y: 0.2 }, { x: 0.8, y: 0.8 }, { x: 0.2, y: 0.8 }];

  assert.deepEqual(validateAnchorPairs(board, image), { source: board, target: image });
  assert.throws(
    () => validateAnchorPairs(board, [image[0], image[0], image[2], image[3]]),
    /duplicate/i,
  );
  assert.throws(
    () => validateAnchorPairs(board, [image[0], image[3], image[2], image[1]]),
    /order/i,
  );
});

test('registration error reports normalized RMS across independent check points', () => {
  const matrix = [1, 0, 0.1, 0, 1, 0.05, 0, 0, 1];
  const checks = [
    { board: { x: 0.2, y: 0.3 }, image: { x: 0.31, y: 0.35 } },
    { board: { x: 0.6, y: 0.7 }, image: { x: 0.7, y: 0.77 } },
  ];

  const result = calculateRegistrationError(matrix, checks);

  assert.equal(result.count, 2);
  assert.ok(Math.abs(result.rms - Math.sqrt(0.00025)) < 1e-9);
  assert.ok(Math.abs(result.maximum - 0.02) < 1e-9);
});
