import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildInspectionTransform,
  canInspectComponent,
  enterComponentInspection,
  exitComponentInspection,
  inspectionOpacity,
} from '../assets/cross-source-registration/component-inspection-state.js';

const u2001 = {
  component_id: 'KM4-MAIN-U2001',
  side_id: 'main_page_2',
  inspection_profile: { profile_id: 'u2001-pmic-v1', fidelity: 'repair_visual' },
};

test('inspection capability requires an explicit data profile', () => {
  assert.equal(canInspectComponent(u2001), true);
  assert.equal(canInspectComponent({ ...u2001, inspection_profile: null }), false);
});

test('inspection enters only when the component is present on the active side', () => {
  assert.deepEqual(enterComponentInspection(u2001, 'main_page_2'), {
    mode: 'isolated',
    componentId: 'KM4-MAIN-U2001',
    sideId: 'main_page_2',
    profileId: 'u2001-pmic-v1',
  });
  assert.equal(enterComponentInspection(u2001, 'main_page_1').mode, 'idle');
});

test('inspection exit clears mode without changing the selected identity', () => {
  const active = enterComponentInspection(u2001, 'main_page_2');
  assert.deepEqual(exitComponentInspection(active), {
    mode: 'idle',
    componentId: null,
    sideId: null,
    profileId: null,
  });
});

test('isolated component remains solid while unrelated components become context', () => {
  assert.equal(inspectionOpacity('KM4-MAIN-U2001', 'KM4-MAIN-U2001'), 1);
  assert.equal(inspectionOpacity('KM4-MAIN-U2001', 'KM4-MAIN-U4000'), 0.12);
  assert.equal(inspectionOpacity(null, 'KM4-MAIN-U4000'), 1);
});

test('inspection transform is bounded across package and viewport sizes', () => {
  const desktop = buildInspectionTransform({ x: 0.19, y: 0.17, z: 0.032 }, false);
  const mobile = buildInspectionTransform({ x: 0.01, y: 0.008, z: 0.011 }, true);
  assert.equal(desktop.scale >= 1.7 && desktop.scale <= 2.6, true);
  assert.equal(mobile.scale >= 1.7 && mobile.scale <= 2.6, true);
  assert.equal(desktop.lift > 0, true);
  assert.equal(mobile.zoom < desktop.zoom, true);
  assert.equal(desktop.zoom <= 2.4, true);
});
