import assert from 'node:assert/strict';
import test from 'node:test';

import {
  analyzeImageQuality,
  cosineSimilarity,
  extractFeatureVector,
  rankModelCandidates,
  rankReferenceCandidates,
} from '../assets/vision-recognition-demo/vision-core.js';


function solidImage(width, height, value) {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < data.length; i += 4) {
    data[i] = value;
    data[i + 1] = value;
    data[i + 2] = value;
    data[i + 3] = 255;
  }
  return { data, width, height };
}

function checkerImage(width, height, low = 20, high = 235) {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const offset = (y * width + x) * 4;
      const value = (x + y) % 2 === 0 ? low : high;
      data[offset] = value;
      data[offset + 1] = value;
      data[offset + 2] = value;
      data[offset + 3] = 255;
    }
  }
  return { data, width, height };
}

test('overexposed image is rejected with highlight guidance', () => {
  const result = analyzeImageQuality(solidImage(900, 700, 255));
  assert.equal(result.status, 'retake');
  assert.ok(result.metrics.highlightClipping > 0.95);
  assert.ok(result.guidance.some((item) => item.code === 'overexposed'));
});

test('checkerboard has higher sharpness and contrast than flat gray', () => {
  const sharp = analyzeImageQuality(checkerImage(900, 700));
  const flat = analyzeImageQuality(solidImage(900, 700, 128));
  assert.ok(sharp.metrics.sharpness > flat.metrics.sharpness);
  assert.ok(sharp.metrics.contrast > flat.metrics.contrast);
});

test('quality analysis uses original dimensions after browser downsampling', () => {
  const image = checkerImage(64, 64);
  image.sourceWidth = 1200;
  image.sourceHeight = 900;
  const result = analyzeImageQuality(image);
  assert.equal(result.metrics.width, 1200);
  assert.equal(result.metrics.height, 900);
  assert.ok(!result.guidance.some((item) => item.code === 'low_resolution'));
});

test('feature vector is finite and normalized', () => {
  const vector = extractFeatureVector(checkerImage(64, 64));
  const magnitude = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0));
  assert.ok(vector.length >= 100);
  assert.ok(vector.every(Number.isFinite));
  assert.ok(Math.abs(magnitude - 1) < 1e-9);
});

test('cosine similarity returns one for the same vector', () => {
  const vector = extractFeatureVector(checkerImage(64, 64));
  assert.ok(Math.abs(cosineSimilarity(vector, vector) - 1) < 1e-9);
});

test('exact reference ranks first and keeps metadata', () => {
  const query = extractFeatureVector(checkerImage(64, 64));
  const flat = extractFeatureVector(solidImage(64, 64, 128));
  const ranked = rankReferenceCandidates(query, [
    { model: 'KL4', role: 'installed_mainboard', vector: flat },
    { model: 'KM4', role: 'installed_mainboard', vector: query },
  ]);
  assert.equal(ranked[0].model, 'KM4');
  assert.equal(ranked[0].role, 'installed_mainboard');
  assert.ok(ranked[0].similarity > ranked[1].similarity);
});

test('model ranking keeps only the strongest reference per model', () => {
  const query = extractFeatureVector(checkerImage(64, 64));
  const flat = extractFeatureVector(solidImage(64, 64, 128));
  const ranked = rankModelCandidates(query, [
    { model: 'KM4', role: 'structure', vector: flat },
    { model: 'KM4', role: 'main', vector: query },
    { model: 'KL4', role: 'main', vector: flat },
  ]);
  assert.deepEqual(ranked.map((item) => item.model), ['KM4', 'KL4']);
  assert.equal(ranked[0].role, 'main');
});
