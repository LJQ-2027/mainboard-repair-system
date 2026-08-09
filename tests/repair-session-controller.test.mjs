import assert from 'node:assert/strict';
import test from 'node:test';

import { createRepairFlowState, recordRepairFlowMeasurement } from '../assets/cross-source-registration/repair-flow-state.js';
import {
  beginRepairSession,
  isRepairSessionEligible,
  persistRepairSession,
  restartRepairSession,
} from '../assets/cross-source-registration/repair-session-controller.js';
import { loadRepairSessions } from '../assets/cross-source-registration/repair-session-state.js';

const profile = {
  flow_id: 'no-power',
  entry_step_id: 'vbat',
  steps: [{
    step_id: 'vbat',
    measurements: [{ measurement_id: 'vbat1', required: true }],
    choices: [],
  }],
};

const context = {
  boardKey: 'kl4-f151',
  model: 'KM4',
  boardVersion: 'F151 V1.2',
  intent: { kind: 'repair_flow', label: '不开机', flowId: 'no-power' },
  entryFlowId: 'no-power',
};

function memoryStorage({ failWrites = false } = {}) {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => {
      if (failWrites) throw new Error('quota');
      values.set(key, value);
    },
  };
}

const initialFlows = () => new Map([['no-power', createRepairFlowState(profile)]]);

test('sessions are limited to executable reviewed datasets', () => {
  assert.equal(isRepairSessionEligible({ status: 'source_compiled_pilot' }, profile), true);
  assert.equal(isRepairSessionEligible({ status: 'proxy_registration_baseline' }, profile), true);
  assert.equal(isRepairSessionEligible({
    status: 'source_compiled_reference_only',
    repair_coverage: { status: 'source_boundary_only' },
  }, profile), false);
  assert.equal(isRepairSessionEligible({ status: 'source_compiled_pilot' }, null), false);
});

test('begin creates once and then restores the exact unfinished session', () => {
  const storage = memoryStorage();
  const first = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-one', declaredFlowIds: new Set(['no-power']),
  });
  assert.equal(first.recovered, false);
  const measured = recordRepairFlowMeasurement(profile, first.flowById.get('no-power'), 'vbat1', 3.91);
  persistRepairSession({
    storage, session: first.session, activeFlowId: 'no-power', flowById: new Map([['no-power', measured]]),
    now: '2026-08-09T10:01:00.000Z',
  });

  const restored = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:02:00.000Z', sessionId: 'unused', declaredFlowIds: new Set(['no-power']),
  });
  assert.equal(restored.recovered, true);
  assert.equal(restored.session.session_id, 'session-one');
  assert.equal(restored.flowById.get('no-power').measurements.vbat.vbat1, 3.91);
});

test('restart abandons the prior record and begins a distinct active session', () => {
  const storage = memoryStorage();
  const first = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-old', declaredFlowIds: new Set(['no-power']),
  });
  const restarted = restartRepairSession({
    storage, session: first.session, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:05:00.000Z', sessionId: 'session-new',
  });
  assert.equal(restarted.session.session_id, 'session-new');
  assert.equal(restarted.session.status, 'active');
  assert.deepEqual(loadRepairSessions(storage).map(({ session_id, status }) => ({ session_id, status })), [
    { session_id: 'session-old', status: 'abandoned' },
    { session_id: 'session-new', status: 'active' },
  ]);
});

test('starting a new round preserves a terminal session result', () => {
  const storage = memoryStorage();
  const first = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-complete', declaredFlowIds: new Set(['no-power']),
  });
  const completed = { ...first.session, status: 'completed' };
  const restarted = restartRepairSession({
    storage, session: completed, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:05:00.000Z', sessionId: 'session-next',
  });
  assert.equal(restarted.abandonedSession.status, 'completed');
  assert.equal(restarted.session.status, 'active');
});

test('storage failure is reported without blocking the in-memory flow', () => {
  const storage = memoryStorage({ failWrites: true });
  const result = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-memory', declaredFlowIds: new Set(['no-power']),
  });
  assert.equal(result.session.session_id, 'session-memory');
  assert.equal(result.persistenceError, 'Unable to save repair session');
});
