import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildInspectionActionState,
  buildInspectionEntryIntent,
  buildInspectionTransform,
  buildInspectionToolbarState,
  canInspectComponent,
  resolveModelComponentActivation,
  enterComponentInspection,
  exitComponentInspection,
  inspectionOpacity,
  resolveInspectionKeyAction,
} from '../assets/cross-source-registration/component-inspection-state.js';

test('model component activation selects first and drills into an already-selected package', () => {
  const packageEntity = { component_id: 'cmp-u2001', inspection_profile: { profile_id: 'u2001-pmic-v1' } };
  const testPoint = { component_id: 'cmp-vbat1', inspection_profile: null };

  assert.equal(resolveModelComponentActivation(packageEntity, 'cmp-u4000', true), 'select');
  assert.equal(resolveModelComponentActivation(packageEntity, 'cmp-u2001', true), 'inspect');
  assert.equal(resolveModelComponentActivation(testPoint, 'cmp-vbat1', true), 'select');
  assert.equal(resolveModelComponentActivation(packageEntity, 'cmp-u2001', false), 'ignore');
  assert.equal(resolveModelComponentActivation(null, 'cmp-u2001', true), 'ignore');
});

const u2001 = {
  component_id: 'KM4-MAIN-U2001',
  side_id: 'main_page_2',
  inspection_profile: { profile_id: 'u2001-pmic-v1', fidelity: 'repair_visual' },
};

test('inspection capability requires an explicit data profile', () => {
  assert.equal(canInspectComponent(u2001), true);
  assert.equal(canInspectComponent({ ...u2001, inspection_profile: null }), false);
});

test('inspection action remains available from any source view', () => {
  assert.deepEqual(buildInspectionActionState({
    active: false,
    inspectable: true,
    ready: true,
  }), {
    hidden: false,
    disabled: false,
    label: '单体查看',
    title: '',
  });
  assert.equal(buildInspectionActionState({
    active: false,
    inspectable: false,
    ready: true,
  }).hidden, true);
  assert.equal(buildInspectionActionState({
    active: false,
    inspectable: true,
    ready: false,
  }).disabled, true);
});

test('inspection entry intent routes through model view and the component side', () => {
  assert.deepEqual(buildInspectionEntryIntent(u2001, 'photo', 'main_page_1'), {
    view: 'model',
    sideId: 'main_page_2',
    changeView: true,
    changeSide: true,
  });
  assert.deepEqual(buildInspectionEntryIntent(u2001, 'model', 'main_page_2'), {
    view: 'model',
    sideId: 'main_page_2',
    changeView: false,
    changeSide: false,
  });
  assert.equal(buildInspectionEntryIntent({ ...u2001, inspection_profile: null }, 'photo', 'main_page_1'), null);
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

test('inspection toolbar exposes component rotation and repurposes reset', () => {
  assert.deepEqual(buildInspectionToolbarState({
    active: true,
    ready: true,
    boardMode: 'pan',
  }), {
    boardControlsHidden: true,
    inspectionAngleHidden: true,
    panHidden: true,
    panDisabled: true,
    panPressed: false,
    rotateDisabled: false,
    rotatePressed: true,
    resetLabel: '恢复单体初始视角',
  });

  assert.deepEqual(buildInspectionToolbarState({
    active: false,
    ready: true,
    boardMode: 'pan',
  }), {
    boardControlsHidden: false,
    inspectionAngleHidden: false,
    panHidden: false,
    panDisabled: false,
    panPressed: true,
    rotateDisabled: false,
    rotatePressed: false,
    resetLabel: '显示全板并恢复俯视',
  });
});

test('inspection keyboard controls map only deliberate model commands', () => {
  assert.deepEqual(resolveInspectionKeyAction('ArrowLeft'), { rotationY: -0.12 });
  assert.deepEqual(resolveInspectionKeyAction('ArrowUp'), { rotationX: -0.09 });
  assert.deepEqual(resolveInspectionKeyAction('+'), { zoomFactor: 1.1 });
  assert.deepEqual(resolveInspectionKeyAction('-'), { zoomFactor: 0.9 });
  assert.deepEqual(resolveInspectionKeyAction('Home'), { reset: true });
  assert.deepEqual(resolveInspectionKeyAction('Escape'), { exit: true });
  assert.equal(resolveInspectionKeyAction('Tab'), null);
});
