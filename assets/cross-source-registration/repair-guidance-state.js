const GUIDANCE_RESULTS = new Set(['pending', 'normal', 'abnormal', 'uncertain']);

export function createRepairGuidance(entity) {
  const repairLinks = Array.isArray(entity?.repair_links) ? entity.repair_links : [];
  const faults = [...new Set(repairLinks.flatMap((link) => (
    Array.isArray(link.faults) ? link.faults.filter(Boolean) : []
  )))];
  const steps = repairLinks.flatMap((link, index) => {
    const instruction = typeof link.instruction === 'string' ? link.instruction.trim() : '';
    if (!instruction) return [];
    return [{
      stepId: `repair-${index}`,
      instruction,
      source: link.source || '',
      page: link.page || '',
    }];
  });
  const measurementProfile = entity?.measurement_profile || null;
  return {
    componentId: entity?.component_id || null,
    faults,
    steps,
    selectedFault: faults[0] || null,
    result: 'pending',
    resultSource: null,
    measurementProfile,
    measurement: { value: null, evaluation: 'unrecorded' },
  };
}

export function selectGuidanceFault(state, fault) {
  if (!state.faults.includes(fault)) throw new RangeError(`Unknown guidance fault: ${fault}`);
  if (state.selectedFault === fault) return state;
  return {
    ...state,
    selectedFault: fault,
    result: 'pending',
    resultSource: null,
    measurement: { value: null, evaluation: 'unrecorded' },
  };
}

export function recordGuidanceResult(state, result) {
  if (!GUIDANCE_RESULTS.has(result)) throw new RangeError(`Unknown guidance result: ${result}`);
  if (!state.steps.length && result !== 'pending') throw new Error('Cannot record a result without a source step');
  return { ...state, result, resultSource: result === 'pending' ? null : 'technician' };
}

export function guidanceProgress(state) {
  return {
    completed: state.result === 'pending' ? 0 : Math.min(1, state.steps.length),
    total: state.steps.length,
  };
}

export function recordGuidanceMeasurement(state, rawValue) {
  if (!state.measurementProfile) throw new Error('No source measurement profile is available');
  const value = typeof rawValue === 'number' ? rawValue : Number(String(rawValue).trim());
  if (!Number.isFinite(value)) throw new TypeError('Measurement value must be finite');
  const reference = state.measurementProfile.reference || { kind: 'record_only' };
  let evaluation = 'recorded';
  let result = state.result;
  let resultSource = state.resultSource;
  if (reference.kind === 'range') {
    if (!Number.isFinite(reference.min) || !Number.isFinite(reference.max) || reference.min > reference.max) {
      throw new TypeError('Measurement range must contain valid ordered bounds');
    }
    evaluation = value < reference.min
      ? 'below_range'
      : value > reference.max
        ? 'above_range'
        : 'within_range';
    result = evaluation === 'within_range' ? 'normal' : 'abnormal';
    resultSource = 'source_range';
  }
  return {
    ...state,
    result,
    resultSource,
    measurement: { value, evaluation },
  };
}
