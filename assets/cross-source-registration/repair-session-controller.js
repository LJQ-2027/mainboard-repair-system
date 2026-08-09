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

export function beginRepairSession({
  storage,
  context,
  activeFlowId,
  flowById,
  declaredFlowIds,
  now = new Date().toISOString(),
  sessionId = null,
}) {
  const records = loadRepairSessions(storage);
  const recoveredSession = recoverRepairSession(records, context);
  if (recoveredSession) {
    try {
      const restored = restoreRepairSessionFlows(recoveredSession, declaredFlowIds);
      return {
        session: recoveredSession,
        activeFlowId: restored.activeFlowId,
        flowById: restored.flowById,
        recovered: true,
        persistenceError: null,
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
  return {
    session,
    activeFlowId,
    flowById,
    recovered: false,
    persistenceError: saveWithStatus(storage, [...records, session]),
  };
}

export function persistRepairSession({
  storage,
  session,
  activeFlowId,
  flowById,
  now = new Date().toISOString(),
}) {
  const updated = updateRepairSession(
    session,
    repairSessionSnapshot(activeFlowId, flowById),
    now,
  );
  const records = loadRepairSessions(storage);
  return {
    session: updated,
    persistenceError: saveWithStatus(storage, [...records, updated]),
  };
}

export function restartRepairSession({
  storage,
  session,
  context,
  activeFlowId,
  flowById,
  now = new Date().toISOString(),
  sessionId = null,
}) {
  const abandoned = abandonRepairSession(session, now);
  const replacement = createRepairSession(
    context,
    repairSessionSnapshot(activeFlowId, flowById),
    now,
    sessionId,
  );
  const records = loadRepairSessions(storage);
  return {
    session: replacement,
    abandonedSession: abandoned,
    persistenceError: saveWithStatus(storage, [...records, abandoned, replacement]),
  };
}
