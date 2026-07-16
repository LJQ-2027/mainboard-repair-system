import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildCameraFrame,
  buildDefaultBoardRotation,
  buildEngineeringSurfacePresentation,
  buildFocusFrame,
  buildRenderDescriptor,
  buildSelectionRadius,
  buildUnresolvedMarkerPresentation,
  resolveInspectionVisualAsset,
  resolvePackageFamily,
} from '../assets/cross-source-registration/model-profiles.js';

test('engineering surface stays readable without washing out elevated packages', () => {
  assert.deepEqual(buildEngineeringSurfacePresentation(), {
    boardColor: 0x285e51,
    boardEdgeColor: 0xb4823a,
    surfaceOpacity: 0.76,
  });
});

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

test('unresolved geometry markers do not reuse selection or fault colors', () => {
  const presentation = buildUnresolvedMarkerPresentation();
  assert.notEqual(presentation.color, 0xf2c94c);
  assert.notEqual(presentation.color, 0xef5b3f);
  assert.equal(presentation.opacity < 0.75, true);
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

test('portrait workspaces rotate the wide board and fit its rotated bounds', () => {
  const aspect = 320 / 454;
  const rotation = buildDefaultBoardRotation(aspect);
  const frame = buildCameraFrame(aspect, rotation);
  const width = frame.right - frame.left;
  const height = frame.top - frame.bottom;

  assert.equal(rotation, Math.PI / 2);
  assert.equal(buildDefaultBoardRotation(16 / 9), 0);
  assert.equal(buildDefaultBoardRotation(390 / 454), Math.PI / 2);
  assert.ok(width >= 1.8 && width < 1.9);
  assert.ok(height >= 2.55 && height < 2.7);
  assert.ok((1.25 / width) > 0.65);
  assert.ok((2 / height) > 0.75);
});

test('repair focus swaps its padded bounds with the portrait board orientation', () => {
  const region = { center: { x: 0.6, y: 0.4 }, size: { x: 0.2, y: 0.1 } };
  const landscape = buildFocusFrame(region, 320 / 454, 0);
  const portrait = buildFocusFrame(region, 320 / 454, Math.PI / 2);
  assert.notEqual(portrait.zoom, landscape.zoom);
  assert.deepEqual(portrait.center, landscape.center);
});

test('repair focus frame converts a normalized region into a bounded world camera target', () => {
  const frame = buildFocusFrame({ center: { x: 0.6, y: 0.4 }, size: { x: 0.24, y: 0.28 } }, 1.6);
  assert.deepEqual(frame.center, { x: 0.2, y: 0.125 });
  assert.equal(frame.zoom >= 1.35 && frame.zoom <= 2.2, true);
});

test('repair focus zoom remains contextual for huge and tiny regions', () => {
  const huge = buildFocusFrame({ center: { x: 0.5, y: 0.5 }, size: { x: 0.9, y: 0.9 } }, 1.6);
  const tinyWide = buildFocusFrame({ center: { x: 0.5, y: 0.5 }, size: { x: 0.01, y: 0.01 } }, 1.6);
  const tinyNarrow = buildFocusFrame({ center: { x: 0.5, y: 0.5 }, size: { x: 0.01, y: 0.01 } }, 0.82);
  assert.equal(huge.zoom, 1.35);
  assert.equal(tinyWide.zoom, 1.9);
  assert.equal(tinyNarrow.zoom, 2.2);
});

test('selection radius stays restrained at both package-size extremes', () => {
  assert.equal(buildSelectionRadius({ x: 0.26, y: 0.22 }), 0.09);
  assert.equal(buildSelectionRadius({ x: 0.01, y: 0.008 }), 0.022);
});

test('reviewed inspection profile survives compilation into the render descriptor', () => {
  const source = component('bga_ic', 'reviewed', { x: 0.096, y: 0.135 });
  source.inspection_profile = { profile_id: 'u2001-pmic-v1', fidelity: 'repair_visual' };
  const descriptor = buildRenderDescriptor(source, { reviewed: true });
  assert.deepEqual(descriptor.inspectionProfile, source.inspection_profile);
});

test('reviewed inspection profiles select only source-approved refined package assets', () => {
  assert.equal(resolveInspectionVisualAsset({ profile_id: 'u2001-pmic-v1' }), 'reviewed-pmic');
  assert.equal(resolveInspectionVisualAsset({ profile_id: 'u4000-emmc-v1' }), 'reviewed-bga');
  assert.equal(resolveInspectionVisualAsset({ profile_id: 'u0600-rf-device-v1' }), 'reviewed-bga');
  assert.equal(resolveInspectionVisualAsset({ profile_id: 'j6101-connector-v1' }), 'reviewed-connector');
  assert.equal(resolveInspectionVisualAsset({ profile_id: 'x2100-crystal-v1' }), 'reviewed-crystal');
  assert.equal(resolveInspectionVisualAsset({ profile_id: 'crystal-26mhz-v1' }), 'reviewed-crystal');
  assert.equal(resolveInspectionVisualAsset({ profile_id: 'connectivity-bga-v1' }), 'reviewed-bga');
  assert.equal(resolveInspectionVisualAsset({ profile_id: 'unreviewed-ic-v1' }), 'standard');
  assert.equal(resolveInspectionVisualAsset(null), 'standard');

  const source = component('bga_ic', 'reviewed', { x: 0.096, y: 0.135 });
  source.inspection_profile = { profile_id: 'u4000-emmc-v1', fidelity: 'repair_visual' };
  assert.equal(buildRenderDescriptor(source, { reviewed: true }).visualAsset, 'reviewed-bga');
});
