import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildCameraFrame,
  buildRenderDescriptor,
  resolvePackageFamily,
} from '../assets/cross-source-registration/model-profiles.js';

function component(category, confidence, size = { x: 0.04, y: 0.06 }) {
  return {
    component_id: `test-${category}-${confidence}`,
    designator: 'U1',
    category,
    footprint: {
      center: { x: 0.5, y: 0.5 },
      size,
      confidence,
    },
  };
}

test('package families collapse source categories into reusable visual assets', () => {
  assert.equal(resolvePackageFamily('bga_ic'), 'ic');
  assert.equal(resolvePackageFamily('capacitor'), 'passive');
  assert.equal(resolvePackageFamily('resistor'), 'passive');
  assert.equal(resolvePackageFamily('test_point'), 'test-point');
  assert.equal(resolvePackageFamily('unknown'), 'generic');
});

test('only high-confidence footprints become elevated package bodies', () => {
  const high = buildRenderDescriptor(component('ic', 'high'));
  const medium = buildRenderDescriptor(component('ic', 'medium'));
  const low = buildRenderDescriptor(component('ic', 'low'));

  assert.equal(high.layer, 'body');
  assert.ok(high.dimensions.z > 0);
  assert.equal(medium.layer, 'outline');
  assert.equal(medium.dimensions.z, 0);
  assert.equal(low, null);
});

test('reviewed low-confidence test points remain selectable markers without fake height', () => {
  const descriptor = buildRenderDescriptor(component('test_point', 'low'), { reviewed: true });
  assert.equal(descriptor.layer, 'marker');
  assert.equal(descriptor.selectable, true);
  assert.equal(descriptor.dimensions.z, 0);
});

test('visual profiles cap implausible source dimensions and heights', () => {
  const descriptor = buildRenderDescriptor(component('connector', 'high', { x: 0.8, y: 0.9 }));
  assert.ok(descriptor.dimensions.x <= 0.36);
  assert.ok(descriptor.dimensions.y <= 0.24);
  assert.ok(descriptor.dimensions.z <= 0.055);
});

test('orthographic frame contains the whole board at wide and narrow aspect ratios', () => {
  const wide = buildCameraFrame(16 / 9);
  const narrow = buildCameraFrame(9 / 16);

  assert.ok(wide.right - wide.left >= 2.16);
  assert.ok(wide.top - wide.bottom >= 1.36);
  assert.ok(narrow.right - narrow.left >= 2.16);
  assert.ok(narrow.top - narrow.bottom > 1.36);
  assert.deepEqual(wide.position, { x: 0, y: 0, z: 4 });
});
