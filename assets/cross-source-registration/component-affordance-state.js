const STATES = Object.freeze({
  idle: {
    color: 0xd0a63b,
    opacity: 0.58,
    labelOpacity: 0.72,
    labelPixels: { width: 68, height: 20 },
    emissiveIntensity: 0,
  },
  hovered: {
    color: 0xf3d77f,
    opacity: 0.96,
    labelOpacity: 1,
    labelPixels: { width: 76, height: 22 },
    emissiveIntensity: 0.025,
  },
  selected: {
    color: 0xf2c94c,
    opacity: 1,
    labelOpacity: 1,
    labelPixels: { width: 76, height: 22 },
    emissiveIntensity: 0.06,
  },
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

export function buildScreenAwareHitScale(hitArea, worldPerPixel, minimumPixels) {
  return {
    x: Math.max(1, (worldPerPixel.x * minimumPixels) / hitArea.x),
    y: Math.max(1, (worldPerPixel.y * minimumPixels) / hitArea.y),
  };
}

export function placeHoverTooltip({ pointer, viewport, tooltip, gap = 12, margin = 8 }) {
  const horizontal = pointer.x + gap + tooltip.width + margin <= viewport.width ? 'right' : 'left';
  const vertical = pointer.y - gap - tooltip.height >= margin ? 'above' : 'below';
  const preferredX = horizontal === 'right'
    ? pointer.x + gap
    : pointer.x - gap - tooltip.width;
  const preferredY = vertical === 'above'
    ? pointer.y - gap - tooltip.height
    : pointer.y + gap;
  return {
    x: Math.max(margin, Math.min(preferredX, viewport.width - tooltip.width - margin)),
    y: Math.max(margin, Math.min(preferredY, viewport.height - tooltip.height - margin)),
    horizontal,
    vertical,
  };
}

export function buildScreenLabelPositions(items, {
  viewport,
  labelPixels = { width: 76, height: 22 },
  gap = 4,
  margin = 8,
} = {}) {
  const halfWidth = labelPixels.width / 2;
  const halfHeight = labelPixels.height / 2;
  const horizontalStep = labelPixels.width + gap;
  const verticalStep = labelPixels.height + gap;
  const clamp = (position) => ({
    x: Math.max(margin + halfWidth, Math.min(position.x, viewport.width - margin - halfWidth)),
    y: Math.max(margin + halfHeight, Math.min(position.y, viewport.height - margin - halfHeight)),
  });
  const rectangle = (position) => ({
    left: position.x - halfWidth,
    right: position.x + halfWidth,
    top: position.y - halfHeight,
    bottom: position.y + halfHeight,
  });
  const placed = [];
  const overlaps = (candidate) => {
    const box = rectangle(candidate);
    return placed.some((position) => {
      const other = rectangle(position);
      return box.left < other.right && box.right > other.left
        && box.top < other.bottom && box.bottom > other.top;
    });
  };
  const offsets = [
    [0, -1], [0, 1], [-1, 0], [1, 0],
    [-1, -1], [1, -1], [-1, 1], [1, 1],
    [0, -2], [0, 2], [-1, -2], [1, -2], [-1, 2], [1, 2],
  ];
  return items.map((item) => {
    const candidates = offsets.map(([column, row]) => clamp({
      x: item.anchor.x + column * horizontalStep,
      y: item.anchor.y + row * verticalStep,
    }));
    let candidate = candidates.find((position, index) => (
      candidates.findIndex((other) => other.x === position.x && other.y === position.y) === index
      && !overlaps(position)
    ));
    if (!candidate) {
      const grid = [];
      for (let y = margin + halfHeight; y <= viewport.height - margin - halfHeight; y += verticalStep) {
        for (let x = margin + halfWidth; x <= viewport.width - margin - halfWidth; x += horizontalStep) {
          grid.push({ x, y });
        }
      }
      grid.sort((a, b) => (
        Math.hypot(a.x - item.anchor.x, a.y - item.anchor.y)
        - Math.hypot(b.x - item.anchor.x, b.y - item.anchor.y)
      ));
      candidate = grid.find((position) => !overlaps(position));
    }
    const position = { id: item.id, ...candidate };
    placed.push(position);
    return position;
  });
}

export function resolveAffordancePresentation({ selected = false, hovered = false } = {}) {
  if (selected) return { ...STATES.selected };
  if (hovered) return { ...STATES.hovered };
  return { ...STATES.idle };
}
