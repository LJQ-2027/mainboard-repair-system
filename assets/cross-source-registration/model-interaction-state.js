const TRANSITION_PHASES = new Set(['inspection', 'side']);

export function createModelInteractionState() {
  return { phase: 'ready', transitionId: 0, pendingFocus: false };
}

export function canAcceptModelInteraction(state) {
  return state.phase === 'ready';
}

export function beginModelTransition(state, phase) {
  if (!canAcceptModelInteraction(state) || !TRANSITION_PHASES.has(phase)) return state;
  return { ...state, phase, transitionId: state.transitionId + 1 };
}

export function completeModelTransition(state, transitionId) {
  if (state.transitionId !== transitionId) return state;
  return { ...state, phase: 'ready' };
}

export function recordSelectionIntent(state, explicit) {
  return explicit ? { ...state, pendingFocus: true } : state;
}

export function consumePendingFocus(state) {
  return { ...state, pendingFocus: false };
}

export function transformBoardCenter(center, rotation) {
  const cosZ = Math.cos(rotation.z || 0);
  const sinZ = Math.sin(rotation.z || 0);
  const cosX = Math.cos(rotation.x || 0);
  return {
    x: center.x * cosZ - center.y * sinZ,
    y: (center.x * sinZ + center.y * cosZ) * cosX,
  };
}
