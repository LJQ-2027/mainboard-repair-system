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
  return {
    componentId: entity?.component_id || null,
    faults,
    steps,
    selectedFault: faults[0] || null,
    result: 'pending',
  };
}

export function selectGuidanceFault(state, fault) {
  if (!state.faults.includes(fault)) throw new RangeError(`Unknown guidance fault: ${fault}`);
  if (state.selectedFault === fault) return state;
  return { ...state, selectedFault: fault, result: 'pending' };
}

export function recordGuidanceResult(state, result) {
  if (!GUIDANCE_RESULTS.has(result)) throw new RangeError(`Unknown guidance result: ${result}`);
  if (!state.steps.length && result !== 'pending') throw new Error('Cannot record a result without a source step');
  return { ...state, result };
}

export function guidanceProgress(state) {
  return {
    completed: state.result === 'pending' ? 0 : Math.min(1, state.steps.length),
    total: state.steps.length,
  };
}
