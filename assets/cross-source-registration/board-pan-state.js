const PAN_LIMITS = Object.freeze({ x: 0.92, y: 0.62 });
const INTERACTION_MODES = new Set(['pan', 'rotate']);

function round(value) {
  return Math.round(value * 1_000_000) / 1_000_000;
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

export function resolveBoardInteractionMode(mode) {
  return INTERACTION_MODES.has(mode) ? mode : 'pan';
}

export function screenDeltaToPan({ dx, dy, width, height, frameWidth, frameHeight, zoom }) {
  const safeWidth = Math.max(width, 1);
  const safeHeight = Math.max(height, 1);
  const safeZoom = Math.max(zoom, 0.01);
  return {
    x: round(-(dx / safeWidth) * (frameWidth / safeZoom)),
    y: round((dy / safeHeight) * (frameHeight / safeZoom)),
  };
}

export function clampPanCenter(center) {
  return {
    x: round(clamp(center.x, -PAN_LIMITS.x, PAN_LIMITS.x)),
    y: round(clamp(center.y, -PAN_LIMITS.y, PAN_LIMITS.y)),
  };
}

export function pinchZoom({ startDistance, currentDistance, startZoom, minimum, maximum }) {
  if (!Number.isFinite(startDistance) || startDistance <= 0) return startZoom;
  const ratio = Math.max(currentDistance, 0) / startDistance;
  return round(clamp(startZoom * ratio, minimum, maximum));
}

export function anchorZoomCenter({ camera, startNdc, currentNdc, frame, startZoom, currentZoom }) {
  const safeStartZoom = Math.max(startZoom, 0.01);
  const safeCurrentZoom = Math.max(currentZoom, 0.01);
  const anchor = {
    x: camera.x + (startNdc.x * frame.width) / (2 * safeStartZoom),
    y: camera.y + (startNdc.y * frame.height) / (2 * safeStartZoom),
  };
  return {
    x: round(anchor.x - (currentNdc.x * frame.width) / (2 * safeCurrentZoom)),
    y: round(anchor.y - (currentNdc.y * frame.height) / (2 * safeCurrentZoom)),
  };
}
