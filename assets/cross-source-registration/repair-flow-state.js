function stepMap(profile) {
  const steps = Array.isArray(profile?.steps) ? profile.steps : [];
  const byId = new Map();
  steps.forEach((step) => {
    if (!step?.step_id || byId.has(step.step_id)) throw new Error('Repair flow steps require unique identities');
    byId.set(step.step_id, step);
  });
  return byId;
}

export function createRepairFlowState(profile) {
  const byId = stepMap(profile);
  if (!profile?.flow_id || !byId.has(profile.entry_step_id)) {
    throw new Error('Repair flow requires a valid identity and entry step');
  }
  return {
    flowId: profile.flow_id,
    currentStepId: profile.entry_step_id,
    history: [],
    terminal: null,
    actionExecution: null,
    measurements: {},
  };
}

export function currentRepairFlowStep(profile, state) {
  if (!state?.currentStepId) return null;
  return stepMap(profile).get(state.currentStepId) || null;
}

export function answerRepairFlow(profile, state, choiceValue) {
  if (state.terminal) throw new Error('Repair flow is already at a terminal action');
  const current = currentRepairFlowStep(profile, state);
  if (!current) throw new Error('Repair flow has no active step');
  if (!repairFlowMeasurementsComplete(profile, state)) {
    throw new Error('Required repair flow measurements are incomplete');
  }
  const choice = current.choices?.find((candidate) => candidate.value === choiceValue);
  if (!choice) throw new RangeError(`Unknown repair flow choice: ${choiceValue}`);
  const outcome = choice.outcome || {};
  const history = [...state.history, { stepId: current.step_id, choice: choice.value }];
  if (outcome.kind === 'next') {
    if (!stepMap(profile).has(outcome.step_id)) throw new Error(`Unknown repair flow destination: ${outcome.step_id}`);
    return { ...state, currentStepId: outcome.step_id, history, terminal: null, actionExecution: null };
  }
  if ((outcome.kind === 'action' || outcome.kind === 'boundary') && outcome.label) {
    const terminal = { kind: outcome.kind, label: outcome.label };
    if (outcome.target_component_id) terminal.target_component_id = outcome.target_component_id;
    return {
      ...state,
      currentStepId: null,
      history,
      terminal,
      actionExecution: outcome.kind === 'action' ? 'pending' : null,
    };
  }
  throw new Error('Repair flow outcome must be a declared next step, action, or source boundary');
}

export function backRepairFlow(profile, state) {
  if (!state.history.length) return state;
  const history = state.history.slice(0, -1);
  const previous = state.history.at(-1);
  if (!stepMap(profile).has(previous.stepId)) throw new Error('Repair flow history points outside the graph');
  return { ...state, currentStepId: previous.stepId, history, terminal: null, actionExecution: null };
}

export function resetRepairFlow(profile) {
  return createRepairFlowState(profile);
}

export function repairFlowProgress(profile, state) {
  const activeId = state.currentStepId || state.history.at(-1)?.stepId;
  const index = profile.steps.findIndex((step) => step.step_id === activeId);
  return { current: index < 0 ? 0 : index + 1, total: profile.steps.length };
}

export function repairFlowTrail(profile, state) {
  const completed = new Set(state.history.map((entry) => entry.stepId));
  return profile.steps.map((step) => ({
    stepId: step.step_id,
    label: step.label || step.prompt,
    targetComponentId: step.target_component_id || null,
    status: step.step_id === state.currentStepId
      ? 'current'
      : completed.has(step.step_id) ? 'completed' : 'pending',
  }));
}

export function repairFlowTargetComponentId(profile, state) {
  const step = currentRepairFlowStep(profile, state);
  if (step?.target_component_id) return step.target_component_id;
  if (state.terminal?.target_component_id) return state.terminal.target_component_id;
  const previousStepId = state.history.at(-1)?.stepId;
  const previousStep = profile.steps.find((candidate) => candidate.step_id === previousStepId);
  return previousStep?.target_component_id || profile.entry_component_id || null;
}

export function setRepairFlowActionExecuted(state, executed) {
  if (state.terminal?.kind !== 'action') {
    throw new Error('Only a source action can record execution');
  }
  return { ...state, actionExecution: executed ? 'executed' : 'pending' };
}

export function repairFlowMeasurementsComplete(profile, state) {
  const step = currentRepairFlowStep(profile, state);
  if (!step) return true;
  const required = (step.measurements || []).filter((measurement) => measurement.required !== false);
  const values = state.measurements?.[step.step_id] || {};
  return required.every((measurement) => Number.isFinite(values[measurement.measurement_id]));
}

export function recordRepairFlowMeasurement(profile, state, measurementId, rawValue) {
  const step = currentRepairFlowStep(profile, state);
  if (!step) throw new Error('Repair flow has no active measurement step');
  const measurement = step.measurements?.find((candidate) => candidate.measurement_id === measurementId);
  if (!measurement) throw new RangeError(`Unknown repair flow measurement: ${measurementId}`);
  const value = typeof rawValue === 'number' ? rawValue : Number(String(rawValue).trim());
  if (!Number.isFinite(value)) throw new TypeError('Repair flow measurement must be finite');
  return {
    ...state,
    measurements: {
      ...state.measurements,
      [step.step_id]: {
        ...(state.measurements?.[step.step_id] || {}),
        [measurementId]: value,
      },
    },
  };
}
