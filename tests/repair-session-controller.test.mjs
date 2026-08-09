import assert from 'node:assert/strict';
import test from 'node:test';

import { createRepairFlowState, recordRepairFlowMeasurement } from '../assets/cross-source-registration/repair-flow-state.js';
import {
  beginRepairSession,
  isRepairSessionEligible,
  persistRepairSession,
  repairSessionStartState,
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
    blockWrites: () => { failWrites = true; },
    allowWrites: () => { failWrites = false; },
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
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-one', declaredFlows: [profile],
  });
  assert.equal(first.recovered, false);
  const measured = recordRepairFlowMeasurement(profile, first.flowById.get('no-power'), 'vbat1', 3.91);
  persistRepairSession({
    storage, session: first.session, activeFlowId: 'no-power', flowById: new Map([['no-power', measured]]),
    now: '2026-08-09T10:01:00.000Z',
  });

  const restored = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:02:00.000Z', sessionId: 'unused', declaredFlows: [profile],
  });
  assert.equal(restored.recovered, true);
  assert.equal(restored.session.session_id, 'session-one');
  assert.equal(restored.flowById.get('no-power').measurements.vbat.vbat1, 3.91);
});

test('restart abandons the prior record and begins a distinct active session', () => {
  const storage = memoryStorage();
  const first = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-old', declaredFlows: [profile],
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
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-complete', declaredFlows: [profile],
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
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-memory', declaredFlows: [profile],
  });
  assert.equal(result.session.session_id, 'session-memory');
  assert.equal(result.persistenceError, 'Unable to save repair session');
  assert.deepEqual(result.pendingRecords.map((record) => record.session_id), ['session-memory']);
});

test('same-flow entry resets a closed in-memory state before creating a successor', () => {
  const closed = { ...createRepairFlowState(profile), currentStepId: null, terminal: { kind: 'boundary', label: 'Stop' }, closed: true };
  assert.deepEqual(repairSessionStartState(profile, closed), createRepairFlowState(profile));
  const active = createRepairFlowState(profile);
  assert.equal(repairSessionStartState(profile, active), active);
});

test('a failed restart write retries the abandoned predecessor with the next save', () => {
  const storage = memoryStorage();
  const first = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-before-failure', declaredFlows: [profile],
  });
  storage.blockWrites();
  const failedRestart = restartRepairSession({
    storage, session: first.session, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:05:00.000Z', sessionId: 'session-after-failure',
  });
  assert.equal(failedRestart.pendingRecords.length, 2);
  storage.allowWrites();
  const retried = persistRepairSession({
    storage,
    session: failedRestart.session,
    activeFlowId: 'no-power',
    flowById: initialFlows(),
    pendingRecords: failedRestart.pendingRecords,
    now: '2026-08-09T10:06:00.000Z',
  });
  assert.equal(retried.persistenceError, null);
  assert.deepEqual(loadRepairSessions(storage).map(({ session_id, status }) => ({ session_id, status })), [
    { session_id: 'session-before-failure', status: 'abandoned' },
    { session_id: 'session-after-failure', status: 'active' },
  ]);
});

test('starting another task retries unsaved records before replacing in-memory context', () => {
  const storage = memoryStorage({ failWrites: true });
  const first = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-unsaved', declaredFlows: [profile],
  });
  storage.allowWrites();
  const otherProfile = { ...profile, flow_id: 'not-charging' };
  const otherContext = {
    ...context,
    intent: { kind: 'repair_flow', label: '不充电', flowId: 'not-charging' },
    entryFlowId: 'not-charging',
  };
  const second = beginRepairSession({
    storage,
    context: otherContext,
    activeFlowId: 'not-charging',
    flowById: new Map([['not-charging', createRepairFlowState(otherProfile)]]),
    declaredFlows: [otherProfile],
    pendingRecords: first.pendingRecords,
    now: '2026-08-09T10:01:00.000Z',
    sessionId: 'session-next-task',
  });
  assert.equal(second.persistenceError, null);
  assert.deepEqual(loadRepairSessions(storage).map((record) => record.session_id), [
    'session-unsaved',
    'session-next-task',
  ]);
});

test('repeated failed resets retain every predecessor until storage recovers', () => {
  const storage = memoryStorage({ failWrites: true });
  const first = beginRepairSession({
    storage, context, activeFlowId: 'no-power', flowById: initialFlows(),
    now: '2026-08-09T10:00:00.000Z', sessionId: 'session-round-one', declaredFlows: [profile],
  });
  const second = restartRepairSession({
    storage, session: first.session, context, activeFlowId: 'no-power', flowById: initialFlows(),
    pendingRecords: first.pendingRecords,
    now: '2026-08-09T10:01:00.000Z', sessionId: 'session-round-two',
  });
  const third = restartRepairSession({
    storage, session: second.session, context, activeFlowId: 'no-power', flowById: initialFlows(),
    pendingRecords: second.pendingRecords,
    now: '2026-08-09T10:02:00.000Z', sessionId: 'session-round-three',
  });
  assert.deepEqual(third.pendingRecords.map(({ session_id, status }) => ({ session_id, status })), [
    { session_id: 'session-round-one', status: 'abandoned' },
    { session_id: 'session-round-two', status: 'abandoned' },
    { session_id: 'session-round-three', status: 'active' },
  ]);
  storage.allowWrites();
  persistRepairSession({
    storage,
    session: third.session,
    activeFlowId: 'no-power',
    flowById: initialFlows(),
    pendingRecords: third.pendingRecords,
    now: '2026-08-09T10:03:00.000Z',
  });
  assert.deepEqual(loadRepairSessions(storage).map(({ session_id, status }) => ({ session_id, status })), [
    { session_id: 'session-round-one', status: 'abandoned' },
    { session_id: 'session-round-two', status: 'abandoned' },
    { session_id: 'session-round-three', status: 'active' },
  ]);
});
