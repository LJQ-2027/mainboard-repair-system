import {
  abandonRepairSession,
  createRepairSession,
  loadRepairSessions,
  recoverRepairSession,
  repairSessionSnapshot,
  restoreRepairSessionFlows,
  saveRepairSessions,
  updateRepairSession,
} from './repair-session-state.js';
import { resetRepairFlow } from './repair-flow-state.js';

function saveWithStatus(storage, records) {
  try {
    saveRepairSessions(storage, records);
    return null;
  } catch {
    return 'Unable to save repair session';
  }
}

export function isRepairSessionEligible(dataset, flow) {
  if (!flow?.flow_id) return false;
  return dataset?.status !== 'source_compiled_reference_only'
    && dataset?.repair_coverage?.status !== 'source_boundary_only';
}

export function repairSessionStartState(profile, state) {
  return state?.closed ? resetRepairFlow(profile) : state;
}

export function beginRepairSession({
  storage,
  context,
  activeFlowId,
  flowById,
  declaredFlows,
  pendingRecords = [],
  now = new Date().toISOString(),
  sessionId = null,
}) {
  const records = loadRepairSessions(storage);
  const availableRecords = [...records, ...pendingRecords];
  const recoveredSession = recoverRepairSession(availableRecords, context);
  if (recoveredSession) {
    try {
      const restored = restoreRepairSessionFlows(recoveredSession, declaredFlows);
      const persistenceError = pendingRecords.length
        ? saveWithStatus(storage, availableRecords)
        : null;
      return {
        session: recoveredSession,
        activeFlowId: restored.activeFlowId,
        flowById: restored.flowById,
        recovered: true,
        persistenceError,
        pendingRecords: persistenceError ? pendingRecords : [],
      };
    } catch {
      // A stale dataset cannot restore old state; begin from the current declared flow.
    }
  }
  const session = createRepairSession(
    context,
    repairSessionSnapshot(activeFlowId, flowById),
    now,
    sessionId,
  );
  const retryRecords = [...pendingRecords, session];
  const persistenceError = saveWithStatus(storage, [...records, ...retryRecords]);
  return {
    session,
    activeFlowId,
    flowById,
    recovered: false,
    persistenceError,
    pendingRecords: persistenceError ? retryRecords : [],
  };
}

export function persistRepairSession({
  storage,
  session,
  activeFlowId,
  flowById,
  pendingRecords = [],
  now = new Date().toISOString(),
}) {
  const updated = updateRepairSession(
    session,
    repairSessionSnapshot(activeFlowId, flowById),
    now,
  );
  const records = loadRepairSessions(storage);
  const retryRecords = [
    ...pendingRecords.filter((record) => record.session_id !== updated.session_id),
    updated,
  ];
  const persistenceError = saveWithStatus(storage, [...records, ...retryRecords]);
  return {
    session: updated,
    persistenceError,
    pendingRecords: persistenceError ? retryRecords : [],
  };
}

export function restartRepairSession({
  storage,
  session,
  context,
  activeFlowId,
  flowById,
  pendingRecords = [],
  now = new Date().toISOString(),
  sessionId = null,
}) {
  const abandoned = session.status === 'active'
    ? abandonRepairSession(session, now)
    : session;
  const replacement = createRepairSession(
    context,
    repairSessionSnapshot(activeFlowId, flowById),
    now,
    sessionId,
  );
  const records = loadRepairSessions(storage);
  const replacementIds = new Set([abandoned.session_id, replacement.session_id]);
  const retryRecords = [
    ...pendingRecords.filter((record) => !replacementIds.has(record.session_id)),
    abandoned,
    replacement,
  ];
  const persistenceError = saveWithStatus(storage, [...records, ...retryRecords]);
  return {
    session: replacement,
    abandonedSession: abandoned,
    persistenceError,
    pendingRecords: persistenceError ? retryRecords : [],
  };
}
