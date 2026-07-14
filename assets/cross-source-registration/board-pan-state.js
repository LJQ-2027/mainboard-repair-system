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
