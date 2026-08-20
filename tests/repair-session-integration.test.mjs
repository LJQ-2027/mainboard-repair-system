import assert from 'node:assert/strict';
import test from 'node:test';

import {
  answerRepairFlow,
  createRepairFlowState,
  recordRepairFlowMeasurement,
} from '../assets/cross-source-registration/repair-flow-state.js';
import {
  createRepairSession,
  repairSessionSnapshot,
  restoreRepairSessionFlows,
  serializeRepairSessions,
} from '../assets/cross-source-registration/repair-session-state.js';

const profile = {
  flow_id: 'no-power',
  entry_step_id: 'vbat',
  steps: [{
    step_id: 'vbat',
    prompt: '记录 VBAT1',
    measurements: [{
      measurement_id: 'vbat1',
      label: 'VBAT1',
      unit: 'V',
      required: true,
      reference: { kind: 'range', min: 3.4, max: 4.35 },
    }],
    choices: [
      { value: 'normal', label: '范围内', outcome: { kind: 'action', label: '进入下一来源检查' } },
      { value: 'abnormal', label: '范围外', outcome: { kind: 'boundary', label: '停止并复核供电' } },
    ],
  }],
};

const identity = {
  boardKey: 'kl4-f151',
  model: 'KM4',
  boardVersion: 'F151 V1.2',
  intent: { kind: 'repair_flow', label: '不开机', flowId: 'no-power' },
  entryFlowId: 'no-power',
};

test('existing repair-flow state round trips without changing its declared branch', () => {
  const measured = recordRepairFlowMeasurement(
    profile,
    createRepairFlowState(profile),
    'vbat1',
    3.92,
  );
  const states = new Map([['no-power', measured]]);
  const session = createRepairSession(
    identity,
    repairSessionSnapshot('no-power', states),
    '2026-08-09T10:00:00.000Z',
    'session-roundtrip',
  );
  const parsed = JSON.parse(serializeRepairSessions([session])).sessions[0];
  const restored = restoreRepairSessionFlows(parsed, [profile]);

  assert.equal(restored.activeFlowId, 'no-power');
  assert.deepEqual(restored.flowById.get('no-power'), measured);
  assert.equal(answerRepairFlow(profile, restored.flowById.get('no-power'), 'normal').terminal.label, '进入下一来源检查');
});

test('restore fails closed when a stored flow is no longer declared by the dataset', () => {
  const session = createRepairSession(
    identity,
    repairSessionSnapshot('no-power', new Map([['no-power', createRepairFlowState(profile)]])),
    '2026-08-09T10:00:00.000Z',
    'session-stale',
  );
  assert.throws(
    () => restoreRepairSessionFlows(session, [{ ...profile, flow_id: 'different-flow' }]),
    /no longer declared/,
  );
});

test('restore rejects state that does not replay through the declared source graph', () => {
  const session = createRepairSession(
    identity,
    repairSessionSnapshot('no-power', new Map([['no-power', createRepairFlowState(profile)]])),
    '2026-08-09T10:00:00.000Z',
    'session-forged',
  );
  const forged = structuredClone(session);
  forged.flow_states['no-power'] = {
    ...forged.flow_states['no-power'],
    currentStepId: null,
    terminal: { kind: 'action', label: 'Replace an undeclared component' },
    actionExecution: 'pending',
  };
  assert.throws(
    () => restoreRepairSessionFlows(forged, [profile]),
    /does not match the declared graph/,
  );
});

test('restore rejects a declared flow that was not reached by a stored handoff', () => {
  const otherProfile = { ...profile, flow_id: 'not-charging' };
  const session = createRepairSession(
    identity,
    repairSessionSnapshot('not-charging', new Map([
      ['no-power', createRepairFlowState(profile)],
      ['not-charging', createRepairFlowState(otherProfile)],
    ])),
    '2026-08-09T10:00:00.000Z',
    'session-cross-flow',
  );
  assert.throws(
    () => restoreRepairSessionFlows(session, [profile, otherProfile]),
    /reachable handoff chain/,
  );
});
