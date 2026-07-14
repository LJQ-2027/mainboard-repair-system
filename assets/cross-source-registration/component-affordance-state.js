const STATES = Object.freeze({
  idle: { color: 0xd0a63b, opacity: 0.58, labelOpacity: 0.72, emissiveIntensity: 0 },
  hovered: { color: 0xf3d77f, opacity: 0.96, labelOpacity: 1, emissiveIntensity: 0.025 },
  selected: { color: 0xf2c94c, opacity: 1, labelOpacity: 1, emissiveIntensity: 0.06 },
});

export function buildCornerSegments(dimensions, padding = 0.008) {
  const halfWidth = dimensions.x / 2;
  const halfHeight = dimensions.y / 2;
  const left = -halfWidth - padding;
  const right = halfWidth + padding;
  const bottom = -halfHeight - padding;
  const top = halfHeight + padding;
  const leg = Math.max(0.008, Math.min(0.018, Math.min(dimensions.x, dimensions.y) * 0.24));
  return [
    [{ x: left, y: top }, { x: left + leg, y: top }],
    [{ x: left, y: top }, { x: left, y: top - leg }],
    [{ x: right, y: top }, { x: right - leg, y: top }],
    [{ x: right, y: top }, { x: right, y: top - leg }],
    [{ x: left, y: bottom }, { x: left + leg, y: bottom }],
    [{ x: left, y: bottom }, { x: left, y: bottom + leg }],
    [{ x: right, y: bottom }, { x: right - leg, y: bottom }],
    [{ x: right, y: bottom }, { x: right, y: bottom + leg }],
  ];
}

export function buildHitArea(dimensions, minimum = 0.035, padding = 0.012) {
  return {
    x: Math.max(dimensions.x, minimum) + padding,
    y: Math.max(dimensions.y, minimum) + padding,
  };
}

export function buildLabelPositions(items, labelWidth = 0.13, laneHeight = 0.034) {
  const placed = [];
  return items.map((item) => {
    const baseY = item.center.y + item.dimensions.y / 2 + 0.025;
    const direction = baseY > 0.56 ? -1 : 1;
    let y = baseY;
    while (placed.some((position) => (
      Math.abs(position.x - item.center.x) < labelWidth
      && Math.abs(position.y - y) < laneHeight
    ))) y += laneHeight * direction;
    const position = {
      id: item.id,
      x: item.center.x,
      y: Math.round(y * 1_000_000) / 1_000_000,
    };
    placed.push(position);
    return position;
  });
}

export function resolveAffordancePresentation({ selected = false, hovered = false } = {}) {
  if (selected) return { ...STATES.selected };
  if (hovered) return { ...STATES.hovered };
  return { ...STATES.idle };
}
