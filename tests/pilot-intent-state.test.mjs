import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildPilotIntentOptions,
  caseSymptomKey,
  encodePilotIntent,
  resolvePilotIntent,
} from '../assets/cross-source-registration/pilot-intent-state.js';


const board = {
  model: 'KJ6',
  compatible_models: ['KJ6'],
  board_version: 'H897_MAIN_PCB_V1.2',
};

const flowDataset = {
  repair_flows: [
    {
      flow_id: 'no-power',
      entry_type: 'known_fault',
      entry_label: '无法开机',
      entry_component_id: 'BOARD-U1',
    },
    {
      flow_id: 'precheck',
      entry_type: 'precheck',
      entry_label: '不确定，先做初步排查',
      entry_component_id: 'BOARD-TP1',
    },
  ],
};

function sourceCase(caseId, symptoms, digest) {
  return {
    case_id: caseId,
    symptoms,
    reported_finding: 'Source finding',
    photo_sha256: [digest],
    navigation_scope: 'board_only',
    candidate_component_ids: [],
    repair_causality_claim_allowed: false,
    defect_label_allowed: false,
    boundary: 'Navigation only.',
  };
}

const caseDataset = {
  repair_flows: [],
  case_navigation: {
    schema_version: 'H897-CASE-NAVIGATION-V1',
    case_count: 4,
    cases: [
      sourceCase('CASE-1', ['不开机'], 'a'.repeat(64)),
      sourceCase('CASE-2', ['不开机'], 'b'.repeat(64)),
      sourceCase('CASE-3', ['连接器损坏', '不开机'], 'c'.repeat(64)),
      sourceCase('CASE-4', ['不开机', '连接器损坏'], 'c'.repeat(64)),
    ],
  },
};

test('builds one selector containing known flows, grouped source symptoms, and initial check', () => {
  const flowOptions = buildPilotIntentOptions(flowDataset);
  assert.deepEqual(flowOptions.map((item) => item.kind), ['repair_flow', 'initial_check']);
  assert.equal(flowOptions[0].label, '无法开机');
  assert.equal(flowOptions[1].flowId, 'precheck');

  const caseOptions = buildPilotIntentOptions(caseDataset);
  assert.deepEqual(caseOptions.map((item) => item.kind), [
    'case_symptom',
    'case_symptom',
    'initial_check',
  ]);
  assert.equal(caseOptions[0].caseCount + caseOptions[1].caseCount, 4);
  assert.equal(caseOptions.find((item) => item.label === '不开机').uniquePhotoCount, 2);
  assert.equal(
    caseSymptomKey(['连接器损坏', '不开机']),
    caseSymptomKey(['不开机', '连接器损坏']),
  );
});

test('round trips an exact repair flow intent through query parameters', () => {
  const option = buildPilotIntentOptions(flowDataset)[0];
  const query = encodePilotIntent(
    { boardKey: 'kj6-h897', model: 'KJ6' },
    option,
  );

  const resolved = resolvePilotIntent({
    boardKey: 'kj6-h897',
    board,
    dataset: flowDataset,
    query,
  });

  assert.equal(query.get('intent'), 'repair_flow');
  assert.deepEqual(resolved, {
    valid: true,
    legacy: false,
    kind: 'repair_flow',
    label: '无法开机',
    model: 'KJ6',
    flowId: 'no-power',
    symptomKey: null,
    boundaryOnly: false,
  });
});

test('resolves a declared initial flow and a truthful boundary when none exists', () => {
  const withFlow = resolvePilotIntent({
    boardKey: 'kj6-h897',
    board,
    dataset: flowDataset,
    query: new URLSearchParams('board=kj6-h897&model=KJ6&intent=initial_check'),
  });
  const withoutFlow = resolvePilotIntent({
    boardKey: 'kj6-h897',
    board,
    dataset: caseDataset,
    query: new URLSearchParams('board=kj6-h897&model=KJ6&intent=initial_check'),
  });

  assert.equal(withFlow.flowId, 'precheck');
  assert.equal(withFlow.boundaryOnly, false);
  assert.equal(withoutFlow.valid, true);
  assert.equal(withoutFlow.flowId, null);
  assert.equal(withoutFlow.boundaryOnly, true);
});

test('resolves only a declared H897 symptom group', () => {
  const option = buildPilotIntentOptions(caseDataset).find((item) => item.label === '不开机');
  const resolved = resolvePilotIntent({
    boardKey: 'kj6-h897',
    board,
    dataset: caseDataset,
    query: encodePilotIntent({ boardKey: 'kj6-h897', model: 'KJ6' }, option),
  });

  assert.equal(resolved.valid, true);
  assert.equal(resolved.kind, 'case_symptom');
  assert.equal(resolved.symptomKey, option.symptomKey);

  const stale = resolvePilotIntent({
    boardKey: 'kj6-h897',
    board,
    dataset: caseDataset,
    query: new URLSearchParams('board=kj6-h897&model=KJ6&intent=case_symptom&symptom=missing'),
  });
  assert.equal(stale.valid, false);
  assert.equal(stale.reason, 'unknown_case_symptom');
});

test('rejects cross-board, unknown-model, and unknown-flow intents without fallback', () => {
  const cases = [
    ['board=other&model=KJ6&intent=repair_flow&flow=no-power', 'board_mismatch'],
    ['board=kj6-h897&model=KM4&intent=repair_flow&flow=no-power', 'model_mismatch'],
    ['board=kj6-h897&model=KJ6&intent=repair_flow&flow=missing', 'unknown_repair_flow'],
  ];
  cases.forEach(([query, reason]) => {
    const resolved = resolvePilotIntent({
      boardKey: 'kj6-h897',
      board,
      dataset: flowDataset,
      query: new URLSearchParams(query),
    });
    assert.equal(resolved.valid, false);
    assert.equal(resolved.reason, reason);
  });
});

test('rejects parameters that belong to a different intent kind', () => {
  assert.equal(resolvePilotIntent({
    boardKey: 'kj6-h897', board, dataset: flowDataset, query: 'board=kj6-h897&model=KJ6&intent=initial_check&flow=no-power',
  }).reason, 'unexpected_intent_parameter');
  assert.equal(resolvePilotIntent({
    boardKey: 'kj6-h897', board, dataset: flowDataset, query: 'board=kj6-h897&model=KJ6&intent=repair_flow&flow=no-power&symptom=x',
  }).reason, 'unexpected_symptom_parameter');
  assert.equal(resolvePilotIntent({
    boardKey: 'kj6-h897', board, dataset: caseDataset, query: 'board=kj6-h897&model=KJ6&intent=case_symptom&symptom=不开机&flow=no-power',
  }).reason, 'unexpected_flow_parameter');
});

test('recognizes a direct legacy workbench URL without manufacturing an intent', () => {
  const resolved = resolvePilotIntent({
    boardKey: 'kj6-h897',
    board,
    dataset: caseDataset,
    query: new URLSearchParams('board=kj6-h897'),
  });

  assert.deepEqual(resolved, {
    valid: false,
    legacy: true,
    reason: 'pilot_intent_absent',
  });
});

test('rejects a partial pilot contract instead of treating it as a legacy URL', () => {
  const resolved = resolvePilotIntent({
    boardKey: 'kj6-h897',
    board,
    dataset: caseDataset,
    query: 'board=kj6-h897&model=KM4',
  });

  assert.equal(resolved.valid, false);
  assert.equal(resolved.legacy, false);
  assert.equal(resolved.reason, 'incomplete_pilot_intent');
});
