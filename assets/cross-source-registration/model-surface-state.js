export function createSurfaceLoadState() {
  return { requestId: 0, sideId: null, status: 'idle' };
}

export function beginSurfaceLoad(state, sideId) {
  return {
    requestId: state.requestId + 1,
    sideId,
    status: 'loading',
  };
}

export function finishSurfaceLoad(state, requestId, failed = false) {
  if (requestId !== state.requestId) return state;
  return {
    ...state,
    status: failed ? 'error' : 'ready',
  };
}
