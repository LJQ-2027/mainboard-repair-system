export const REPAIR_SESSION_STORAGE_KEY = 'technician-repair-sessions-v1';

const SESSION_SCHEMA = 'TECHNICIAN-REPAIR-SESSION-V1';
const ACTIVE_STATUS = 'active';
const TERMINAL_KINDS = new Set(['action', 'boundary', 'handoff']);
const ACTION_STATES = new Set(['pending', 'executed']);
const POST_ACTION_STATES = new Set(['pending', 'symptom_cleared', 'symptom_persists', 'uncertain']);
const MAX_SESSIONS = 50;

function requiredString(value, label) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} is required`);
  return value.trim();
}

function optionalString(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function normalizedDate(value, label) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) throw new Error(`${label} is invalid`);
  return date.toISOString();
}

function normalizeIdentity(context = {}) {
  const intent = context.intent || {};
  const kind = requiredString(intent.kind, 'Session intent kind');
  const label = requiredString(intent.label, 'Session intent label');
  const entryFlowId = requiredString(context.entryFlowId ?? context.entry_flow_id, 'Entry flow ID');
  return {
    board_key: requiredString(context.boardKey ?? context.board_key, 'Board key'),
    model: requiredString(context.model, 'Model'),
    board_version: requiredString(context.boardVersion ?? context.board_version, 'Board version'),
    intent: {
      kind,
      label,
      flow_id: optionalString(intent.flowId ?? intent.flow_id),
    },
    entry_flow_id: entryFlowId,
  };
}

function normalizeTerminal(terminal) {
  if (terminal == null) return null;
  if (typeof terminal !== 'object' || !TERMINAL_KINDS.has(terminal.kind)) {
    throw new Error('Invalid repair-flow terminal');
  }
  const normalized = {
    kind: terminal.kind,
    label: requiredString(terminal.label, 'Terminal label'),
  };
  const targetComponentId = optionalString(terminal.target_component_id);
  const flowId = optionalString(terminal.flowId ?? terminal.flow_id);
  if (targetComponentId) normalized.target_component_id = targetComponentId;
  if (terminal.kind === 'handoff') {
    if (!flowId) throw new Error('Handoff terminal requires a flow ID');
    normalized.flowId = flowId;
  }
  return normalized;
}

function normalizeMeasurements(measurements = {}) {
  if (!measurements || typeof measurements !== 'object' || Array.isArray(measurements)) return {};
  const normalized = {};
  Object.entries(measurements).forEach(([stepId, values]) => {
    if (!stepId.trim() || !values || typeof values !== 'object' || Array.isArray(values)) return;
    const stepValues = {};
    Object.entries(values).forEach(([measurementId, value]) => {
      if (measurementId.trim() && typeof value === 'number' && Number.isFinite(value)) {
        stepValues[measurementId] = value;
      }
    });
    if (Object.keys(stepValues).length) normalized[stepId] = stepValues;
  });
  return normalized;
}

function normalizeFlowState(value, expectedFlowId) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Invalid repair-flow state');
  }
  const flowId = requiredString(value.flowId, 'Flow state ID');
  if (flowId !== expectedFlowId) throw new Error('Flow state identity mismatch');
  const history = Array.isArray(value.history) ? value.history.map((entry) => ({
    stepId: requiredString(entry?.stepId, 'History step ID'),
    choice: requiredString(entry?.choice, 'History choice'),
  })) : [];
  const actionExecution = optionalString(value.actionExecution);
  const postActionCheck = optionalString(value.postActionCheck);
  if (actionExecution && !ACTION_STATES.has(actionExecution)) throw new Error('Invalid action state');
  if (postActionCheck && !POST_ACTION_STATES.has(postActionCheck)) throw new Error('Invalid post-action state');
  return {
    flowId,
    currentStepId: optionalString(value.currentStepId),
    history,
    terminal: normalizeTerminal(value.terminal),
    actionExecution,
    postActionCheck,
    closed: value.closed === true,
    measurements: normalizeMeasurements(value.measurements),
  };
}

function normalizeSnapshot(snapshot = {}) {
  const activeFlowId = requiredString(snapshot.activeFlowId ?? snapshot.active_flow_id, 'Active flow ID');
  const inputStates = snapshot.flowStates ?? snapshot.flow_states;
  if (!inputStates || typeof inputStates !== 'object' || Array.isArray(inputStates)) {
    throw new Error('Session flow states are required');
  }
  const flowStates = {};
  Object.entries(inputStates).forEach(([flowId, value]) => {
    try {
      flowStates[flowId] = normalizeFlowState(value, flowId);
    } catch {
      // Invalid extra flow snapshots carry no authority and are omitted.
    }
  });
  if (!flowStates[activeFlowId]) throw new Error('Active flow state is missing');
  return { activeFlowId, flowStates };
}

function statusFromSnapshot(snapshot) {
  const state = snapshot.flowStates[snapshot.activeFlowId];
  if (!state.closed) return ACTIVE_STATUS;
  return state.terminal?.kind === 'boundary' ? 'stopped_at_source_boundary' : 'completed';
}

function normalizeSession(record = {}) {
  if (record.schema_version !== SESSION_SCHEMA) throw new Error('Invalid repair session schema');
  const identity = normalizeIdentity(record.identity);
  const snapshot = normalizeSnapshot(record);
  const storedStatus = optionalString(record.status);
  const status = storedStatus === 'abandoned' ? 'abandoned' : statusFromSnapshot(snapshot);
  return {
    schema_version: SESSION_SCHEMA,
    session_id: requiredString(record.session_id, 'Session ID'),
    created_at: normalizedDate(record.created_at, 'Created time'),
    updated_at: normalizedDate(record.updated_at, 'Updated time'),
    status,
    identity,
    active_flow_id: snapshot.activeFlowId,
    flow_states: snapshot.flowStates,
  };
}

function validSessions(records = []) {
  if (!Array.isArray(records)) return [];
  return records.flatMap((record) => {
    try {
      return [normalizeSession(record)];
    } catch {
      return [];
    }
  });
}

function generatedSessionId(now) {
  return `repair-session-${Date.parse(now)}-${Math.random().toString(36).slice(2, 9)}`;
}

export function createRepairSession(context, snapshot, createdAt = new Date().toISOString(), sessionId = null) {
  const created = normalizedDate(createdAt, 'Created time');
  const normalizedSnapshot = normalizeSnapshot(snapshot);
  return normalizeSession({
    schema_version: SESSION_SCHEMA,
    session_id: optionalString(sessionId) || generatedSessionId(created),
    created_at: created,
    updated_at: created,
    status: statusFromSnapshot(normalizedSnapshot),
    identity: normalizeIdentity(context),
    active_flow_id: normalizedSnapshot.activeFlowId,
    flow_states: normalizedSnapshot.flowStates,
  });
}

export function updateRepairSession(session, snapshot, updatedAt = new Date().toISOString()) {
  const current = normalizeSession(session);
  if (current.status === 'abandoned') throw new Error('Abandoned repair session cannot be updated');
  const normalizedSnapshot = normalizeSnapshot(snapshot);
  return normalizeSession({
    ...current,
    updated_at: normalizedDate(updatedAt, 'Updated time'),
    status: statusFromSnapshot(normalizedSnapshot),
    active_flow_id: normalizedSnapshot.activeFlowId,
    flow_states: normalizedSnapshot.flowStates,
  });
}

export function abandonRepairSession(session, updatedAt = new Date().toISOString()) {
  const current = normalizeSession(session);
  return {
    ...current,
    updated_at: normalizedDate(updatedAt, 'Updated time'),
    status: 'abandoned',
  };
}

export function recoverRepairSession(records, context) {
  const identity = normalizeIdentity(context);
  return validSessions(records)
    .filter((session) => session.status === ACTIVE_STATUS && JSON.stringify(session.identity) === JSON.stringify(identity))
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at) || right.session_id.localeCompare(left.session_id))[0] || null;
}

export function loadRepairSessions(storage = window.localStorage) {
  try {
    return validSessions(JSON.parse(storage.getItem(REPAIR_SESSION_STORAGE_KEY) || '[]'));
  } catch {
    return [];
  }
}

export function saveRepairSessions(storage = window.localStorage, records = []) {
  const byId = new Map();
  validSessions(records).forEach((session) => {
    const prior = byId.get(session.session_id);
    if (!prior || prior.updated_at <= session.updated_at) byId.set(session.session_id, session);
  });
  const retained = [...byId.values()]
    .sort((left, right) => left.created_at.localeCompare(right.created_at) || left.session_id.localeCompare(right.session_id))
    .slice(-MAX_SESSIONS);
  storage.setItem(REPAIR_SESSION_STORAGE_KEY, JSON.stringify(retained));
  return retained;
}

export function serializeRepairSessions(records = []) {
  const sessions = validSessions(records).sort((left, right) => (
    left.created_at.localeCompare(right.created_at) || left.session_id.localeCompare(right.session_id)
  ));
  return `${JSON.stringify({
    schema_version: 'TECHNICIAN-REPAIR-SESSION-EXPORT-V1',
    session_count: sessions.length,
    sessions,
  }, null, 2)}\n`;
}
