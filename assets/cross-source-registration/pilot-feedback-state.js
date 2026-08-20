export const PILOT_FEEDBACK_STORAGE_KEY = 'technician-pilot-feedback-v1';

const TARGET_STATUSES = new Set(['found', 'uncertain', 'not_found']);
const USEFULNESS_VALUES = new Set(['enough_to_continue', 'insufficient', 'not_applicable']);

function optionalString(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function feedbackContext(context = {}) {
  const boardKey = optionalString(context.boardKey);
  const model = optionalString(context.model);
  const boardVersion = optionalString(context.boardVersion);
  const kind = optionalString(context.intent?.kind);
  const label = optionalString(context.intent?.label);
  if (!boardKey || !model || !boardVersion || !kind || !label) {
    throw new Error('Pilot feedback requires an exact board, model, version, and intent');
  }
  return {
    board_key: boardKey,
    model,
    board_version: boardVersion,
    intent: {
      kind,
      label,
      flow_id: optionalString(context.intent?.flowId),
      symptom_key: optionalString(context.intent?.symptomKey),
      boundary_only: context.intent?.boundaryOnly === true,
    },
    selected_component_id: optionalString(context.selectedComponentId),
    selected_case_id: optionalString(context.selectedCaseId),
  };
}

export function createPilotFeedback(context, values = {}, createdAt = new Date().toISOString(), feedbackId = null) {
  const targetStatus = optionalString(values.targetStatus);
  const usefulness = optionalString(values.usefulness);
  const note = optionalString(values.note);
  if (targetStatus && !TARGET_STATUSES.has(targetStatus)) throw new Error('Invalid target status');
  if (usefulness && !USEFULNESS_VALUES.has(usefulness)) throw new Error('Invalid usefulness status');
  if (!targetStatus && !usefulness) throw new Error('Select at least one feedback dimension');
  if (note && note.length > 500) throw new Error('Feedback note exceeds 500 characters');
  const normalizedDate = new Date(createdAt).toISOString();
  const generatedId = `feedback-${Date.parse(normalizedDate)}-${Math.random().toString(36).slice(2, 9)}`;
  return {
    schema_version: 'TECHNICIAN-PILOT-FEEDBACK-V1',
    feedback_id: optionalString(feedbackId) || generatedId,
    created_at: normalizedDate,
    context: feedbackContext(context),
    target_location: targetStatus,
    source_usefulness: usefulness,
    note,
  };
}

function normalizeRecord(record = {}) {
  if (record.schema_version !== 'TECHNICIAN-PILOT-FEEDBACK-V1') {
    throw new Error('Invalid pilot feedback schema');
  }
  const feedbackId = optionalString(record.feedback_id);
  if (!feedbackId) throw new Error('Invalid pilot feedback ID');
  const createdAt = new Date(record.created_at).toISOString();
  const targetLocation = optionalString(record.target_location);
  const sourceUsefulness = optionalString(record.source_usefulness);
  if (targetLocation && !TARGET_STATUSES.has(targetLocation)) throw new Error('Invalid target location');
  if (sourceUsefulness && !USEFULNESS_VALUES.has(sourceUsefulness)) throw new Error('Invalid source usefulness');
  if (!targetLocation && !sourceUsefulness) throw new Error('Missing pilot feedback dimension');
  const note = optionalString(record.note);
  if (note && note.length > 500) throw new Error('Feedback note exceeds 500 characters');
  const storedContext = record.context || {};
  return {
    schema_version: 'TECHNICIAN-PILOT-FEEDBACK-V1',
    feedback_id: feedbackId,
    created_at: createdAt,
    context: feedbackContext({
      boardKey: storedContext.board_key,
      model: storedContext.model,
      boardVersion: storedContext.board_version,
      intent: {
        kind: storedContext.intent?.kind,
        label: storedContext.intent?.label,
        flowId: storedContext.intent?.flow_id,
        symptomKey: storedContext.intent?.symptom_key,
        boundaryOnly: storedContext.intent?.boundary_only,
      },
      selectedComponentId: storedContext.selected_component_id,
      selectedCaseId: storedContext.selected_case_id,
    }),
    target_location: targetLocation,
    source_usefulness: sourceUsefulness,
    note,
  };
}

function validRecords(records = []) {
  return records.flatMap((record) => {
    try {
      return [normalizeRecord(record)];
    } catch {
      return [];
    }
  });
}

export function loadPilotFeedback(storage = window.localStorage) {
  try {
    const parsed = JSON.parse(storage.getItem(PILOT_FEEDBACK_STORAGE_KEY) || '[]');
    return Array.isArray(parsed) ? validRecords(parsed) : [];
  } catch {
    return [];
  }
}

export function savePilotFeedback(storage = window.localStorage, records = []) {
  storage.setItem(PILOT_FEEDBACK_STORAGE_KEY, JSON.stringify(validRecords(records)));
}

export function serializePilotFeedback(records = []) {
  const ordered = validRecords(records).sort((left, right) => (
    left.created_at.localeCompare(right.created_at) || left.feedback_id.localeCompare(right.feedback_id)
  ));
  return `${JSON.stringify({
    schema_version: 'TECHNICIAN-PILOT-FEEDBACK-EXPORT-V1',
    record_count: ordered.length,
    records: ordered,
  }, null, 2)}\n`;
}
