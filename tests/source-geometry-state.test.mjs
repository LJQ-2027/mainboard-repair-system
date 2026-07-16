import assert from 'node:assert/strict';
import test from 'node:test';

import { mergeCompiledFootprint } from '../assets/cross-source-registration/source-geometry-state.js';


const entity = {
  geometry: {
    center: { x: 0.73, y: 0.8 },
    size: { x: 0.025, y: 0.025 },
    source_status: 'low',
  },
};

test('low-confidence footprint cannot replace a reviewed location', () => {
  const compiled = {
    footprint: {
      center: { x: 0.62, y: 0.79 },
      size: { x: 0.12, y: 0.16 },
      confidence: 'low',
    },
  };
  assert.deepEqual(mergeCompiledFootprint(entity, compiled), entity);
});

test('high-confidence footprint updates geometry without dropping entity fields', () => {
  const compiled = {
    footprint: {
      center: { x: 0.48, y: 0.64 },
      size: { x: 0.08, y: 0.11 },
      confidence: 'high',
    },
  };
  assert.deepEqual(mergeCompiledFootprint(entity, compiled).geometry, {
    center: compiled.footprint.center,
    size: compiled.footprint.size,
    source_status: 'high',
  });
});
