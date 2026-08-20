import assert from 'node:assert/strict';
import test from 'node:test';

import { buildCaseNavigationState } from '../assets/cross-source-registration/case-navigation-state.js';


const contract = {
  schema_version: 'H897-CASE-NAVIGATION-V1',
  case_count: 2,
  unique_photo_count: 3,
  boundary: 'Case context only.',
  missing_fields: [
    { field_id: 'probe_location', label: '探针或检查位置', missing_case_count: 2 },
  ],
  cases: [
    {
      case_id: 'CASE-1',
      symptoms: ['不开机'],
      reported_finding: 'CPU bad',
      photo_sha256: ['a'.repeat(64)],
      navigation_scope: 'component_candidate',
      candidate_component_ids: ['H897-MAIN-U1001'],
      repair_causality_claim_allowed: false,
      defect_label_allowed: false,
      boundary: 'Candidate only.',
    },
    {
      case_id: 'CASE-2',
      symptoms: ['无法充电'],
      reported_finding: '充电IC坏',
      photo_sha256: ['b'.repeat(64), 'c'.repeat(64)],
      navigation_scope: 'board_only',
      candidate_component_ids: [],
      repair_causality_claim_allowed: false,
      defect_label_allowed: false,
      boundary: 'Board context only.',
    },
  ],
};

test('builds a deterministic source-bounded case selector', () => {
  const state = buildCaseNavigationState(contract);

  assert.equal(state.visible, true);
  assert.equal(state.summary, '2 条案例 · 3 个独立照片');
  assert.deepEqual(state.groups.map((item) => item.label), ['不开机', '无法充电']);
  assert.equal(state.activeGroup.label, '不开机');
  assert.deepEqual(state.options, [{ caseId: 'CASE-1', label: 'CASE-1' }]);
  assert.equal(state.activeCase.caseId, 'CASE-1');
});

test('selects a requested case and exposes only declared candidates', () => {
  const state = buildCaseNavigationState(contract, 'CASE-2');

  assert.equal(state.activeCase.caseId, 'CASE-2');
  assert.deepEqual(state.activeCase.symptoms, ['无法充电']);
  assert.equal(state.activeCase.finding, '充电IC坏');
  assert.deepEqual(state.activeCase.candidateComponentIds, []);
  assert.equal(state.activeCase.boardOnly, true);
  assert.equal(state.activeCase.photoCount, 2);
  assert.equal(state.missingFieldCount, 1);
});

test('filters cases by a preferred symptom group and counts unique source photos', () => {
  const grouped = structuredClone(contract);
  grouped.case_count = 3;
  grouped.unique_photo_count = 4;
  grouped.cases.push({
    ...structuredClone(grouped.cases[0]),
    case_id: 'CASE-3',
    photo_sha256: ['a'.repeat(64), 'd'.repeat(64)],
  });

  const state = buildCaseNavigationState(grouped, null, '不开机');

  assert.equal(state.activeGroup.key, '不开机');
  assert.equal(state.activeGroup.caseCount, 2);
  assert.equal(state.activeGroup.uniquePhotoCount, 2);
  assert.deepEqual(state.options.map((item) => item.caseId), ['CASE-1', 'CASE-3']);
  assert.equal(state.activeCase.caseId, 'CASE-1');
});

test('keeps preferred-case selection inside its source symptom group', () => {
  const state = buildCaseNavigationState(contract, 'CASE-2');

  assert.equal(state.activeGroup.label, '无法充电');
  assert.deepEqual(state.options, [{ caseId: 'CASE-2', label: 'CASE-2' }]);
  assert.equal(state.activeCase.caseId, 'CASE-2');
});

test('fails closed for unsupported or causality-enabling contracts', () => {
  assert.equal(buildCaseNavigationState({}).visible, false);
  const unsafe = structuredClone(contract);
  unsafe.cases[0].repair_causality_claim_allowed = true;
  assert.equal(buildCaseNavigationState(unsafe).visible, false);

  const contradictoryBoardCase = structuredClone(contract);
  contradictoryBoardCase.cases[1].candidate_component_ids = ['H897-MAIN-U2001'];
  assert.equal(buildCaseNavigationState(contradictoryBoardCase).visible, false);

  const emptyComponentCase = structuredClone(contract);
  emptyComponentCase.cases[0].candidate_component_ids = [];
  assert.equal(buildCaseNavigationState(emptyComponentCase).visible, false);
});
