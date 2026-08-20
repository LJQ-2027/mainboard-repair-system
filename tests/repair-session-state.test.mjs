import assert from 'node:assert/strict';
import test from 'node:test';

import {
  REPAIR_SESSION_STORAGE_KEY,
  abandonRepairSession,
  createRepairSession,
  loadRepairSessions,
  recoverRepairSession,
  saveRepairSessions,
  serializeRepairSessions,
  updateRepairSession,
} from '../assets/cross-source-registration/repair-session-state.js';

const identity = {
  boardKey: 'kl4-f151',
  model: 'KM4',
  boardVersion: 'F151 V1.2',
  intent: { kind: 'repair_flow', label: '不开机', flowId: 'no-power' },
  entryFlowId: 'no-power',
};

const activeFlow = {
  flowId: 'no-power',
  currentStepId: 'vbat',
  history: [],
  terminal: null,
  actionExecution: null,
  postActionCheck: null,
  closed: false,
  measurements: { vbat: { vbat1: 3.92 } },
};

const snapshot = (flowState = activeFlow) => ({
  activeFlowId: 'no-power',
  flowStates: { 'no-power': flowState },
});

function memoryStorage(initial = null) {
  const values = new Map(initial ? [[REPAIR_SESSION_STORAGE_KEY, initial]] : []);
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
}

test('creates a privacy-reduced active session from exact repair identity and flow state', () => {
  const session = createRepairSession(
    { ...identity, imei: 'must-not-leak' },
    snapshot(),
    '2026-08-09T10:00:00.000Z',
    'session-1',
  );

  assert.equal(session.schema_version, 'TECHNICIAN-REPAIR-SESSION-V1');
  assert.equal(session.status, 'active');
  assert.equal(session.identity.entry_flow_id, 'no-power');
  assert.equal(session.active_flow_id, 'no-power');
  assert.equal(session.flow_states['no-power'].measurements.vbat.vbat1, 3.92);
  assert.equal('imei' in session.identity, false);
});

test('derives completed and source-boundary status only from a closed active flow', () => {
  const session = createRepairSession(identity, snapshot(), '2026-08-09T10:00:00.000Z', 'session-2');
  const actionClosed = {
    ...activeFlow,
    currentStepId: null,
    terminal: { kind: 'action', label: '执行来源动作' },
    actionExecution: 'executed',
    postActionCheck: 'symptom_cleared',
    closed: true,
  };
  const boundaryClosed = {
    ...activeFlow,
    currentStepId: null,
    terminal: { kind: 'boundary', label: '资料到此停止' },
    closed: true,
  };

  assert.equal(updateRepairSession(session, snapshot(actionClosed), '2026-08-09T10:05:00.000Z').status, 'completed');
  assert.equal(updateRepairSession(session, snapshot(boundaryClosed), '2026-08-09T10:05:00.000Z').status, 'stopped_at_source_boundary');
  assert.equal(abandonRepairSession(session, '2026-08-09T10:06:00.000Z').status, 'abandoned');
});

test('recovers only the newest unfinished session with an exact identity match', () => {
  const older = createRepairSession(identity, snapshot(), '2026-08-09T10:00:00.000Z', 'session-old');
  const newer = createRepairSession(identity, snapshot(), '2026-08-09T11:00:00.000Z', 'session-new');
  const completed = updateRepairSession(newer, snapshot({ ...activeFlow, closed: true, currentStepId: null, terminal: { kind: 'boundary', label: 'stop' } }), '2026-08-09T11:05:00.000Z');

  assert.equal(recoverRepairSession([older, newer], identity).session_id, 'session-new');
  assert.equal(recoverRepairSession([older, completed], identity).session_id, 'session-old');
  assert.equal(recoverRepairSession([newer], { ...identity, model: 'KM5' }), null);
  assert.equal(recoverRepairSession([newer], { ...identity, entryFlowId: 'charge' }), null);
});

test('storage drops malformed records and retains only the newest fifty valid sessions', () => {
  const storage = memoryStorage('not-json');
  assert.deepEqual(loadRepairSessions(storage), []);
  const records = Array.from({ length: 52 }, (_, index) => createRepairSession(
    identity,
    snapshot(),
    `2026-08-09T${String(Math.floor(index / 60)).padStart(2, '0')}:${String(index % 60).padStart(2, '0')}:00.000Z`,
    `session-${String(index).padStart(2, '0')}`,
  ));
  saveRepairSessions(storage, [{ schema_version: 'UNSAFE' }, ...records]);
  const loaded = loadRepairSessions(storage);
  assert.equal(loaded.length, 50);
  assert.equal(loaded[0].session_id, 'session-02');
  assert.equal(loaded.at(-1).session_id, 'session-51');
});

test('export is deterministic and strips unknown privacy-bearing fields', () => {
  const second = createRepairSession(identity, snapshot(), '2026-08-09T11:00:00.000Z', 'session-b');
  const first = createRepairSession(identity, snapshot(), '2026-08-09T10:00:00.000Z', 'session-a');
  const unsafe = { ...first, customer_phone: 'secret', flow_states: { ...first.flow_states, unsafe: { diagnosis: 'replace' } } };
  const exported = JSON.parse(serializeRepairSessions([second, unsafe]));

  assert.equal(exported.schema_version, 'TECHNICIAN-REPAIR-SESSION-EXPORT-V1');
  assert.deepEqual(exported.sessions.map((item) => item.session_id), ['session-a', 'session-b']);
  assert.doesNotMatch(JSON.stringify(exported), /customer_phone|secret|diagnosis|replace/);
});
