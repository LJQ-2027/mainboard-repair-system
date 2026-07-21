import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

import {
  ADMIN_CASE_STATE_LABELS,
  buildVisualQcAccessState,
  clampAdminCasePage,
  normalizeAdminCaseFilters,
} from '../assets/visual-qc-workbench/admin-catalog-state.js';


const html = await readFile(
  new URL('../assets/visual-qc-workbench/index.html', import.meta.url),
  'utf8',
);
const css = await readFile(
  new URL('../assets/visual-qc-workbench/styles.css', import.meta.url),
  'utf8',
);
const app = await readFile(
  new URL('../assets/visual-qc-workbench/app.js', import.meta.url),
  'utf8',
);
const client = await readFile(
  new URL('../assets/visual-qc-workbench/visual-qc-server-client.js', import.meta.url),
  'utf8',
);


test('data administrator workbench exposes one compact server case catalog', () => {
  assert.match(html, /主板视觉数据工作台/);
  assert.match(html, /id="serverCasesButton"/);
  assert.match(html, /id="serverCasesDialog"/);
  assert.match(html, /id="serverCaseStateFilter"/);
  assert.match(html, /id="serverCasesList"/);
  assert.match(html, /id="serverCasesPreviousButton"/);
  assert.match(html, /id="serverCasesNextButton"/);
  assert.doesNotMatch(html, /审核员工具/);
  assert.match(css, /\.server-case-row\s*\{[^}]*border-bottom:/s);
  assert.doesNotMatch(css, /\.server-case-row\s*\{[^}]*border-radius:/s);
});

test('admin catalog state labels and filters use fixed server values', () => {
  assert.deepEqual(Object.keys(ADMIN_CASE_STATE_LABELS), [
    'processing',
    'processing_failed',
    'manual_registration_required',
    'registration_review_required',
    'ready_for_human_qc',
    'completed',
  ]);
  assert.deepEqual(
    normalizeAdminCaseFilters({
      boardKey: ' km4-f151 ',
      sideId: ' main_page_2 ',
      captureStage: 'before_repair',
      state: 'ready_for_human_qc',
    }),
    {
      boardKey: 'km4-f151',
      sideId: 'main_page_2',
      captureStage: 'before_repair',
      state: 'ready_for_human_qc',
    },
  );
  assert.equal(normalizeAdminCaseFilters({ state: 'invented' }).state, '');
  assert.equal(clampAdminCasePage(-4, 0, 25), 1);
  assert.equal(clampAdminCasePage(9, 51, 25), 3);
});

test('technician access state hides every visual data intake and governance control', () => {
  const technician = buildVisualQcAccessState('technician');
  const dataAdmin = buildVisualQcAccessState('reviewer');

  for (const capability of [
    'imageIntake',
    'proxyLoading',
    'serverSync',
    'goldenManagement',
    'serverCatalog',
    'datasetExport',
  ]) {
    assert.equal(technician[capability], false, capability);
    assert.equal(dataAdmin[capability], true, capability);
  }
  assert.equal(technician.roleLabel, '只读');
  assert.equal(dataAdmin.roleLabel, '数据管理员');
  assert.match(app, /if \(!dataAdminAccess\(\)\) return;/);
  assert.match(app, /actorRole:\s*VISUAL_QC_ACTOR_ROLE/);
  assert.match(client, /setRequestHeader\('X-Actor-Role', actorRole\)/);
});
