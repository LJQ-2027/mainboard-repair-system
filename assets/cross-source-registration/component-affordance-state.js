const STATES = Object.freeze({
  idle: {
    color: 0xd0a63b,
    opacity: 0.58,
    labelOpacity: 0.72,
    labelPixels: { width: 68, height: 20 },
    labelVariant: 'idle',
  },
  hovered: {
    color: 0xf3d77f,
    opacity: 0.96,
    labelOpacity: 1,
    labelPixels: { width: 76, height: 22 },
    labelVariant: 'hovered',
  },
  selected: {
    color: 0xf2c94c,
    opacity: 1,
    labelOpacity: 1,
    labelPixels: { width: 76, height: 22 },
    labelVariant: 'selected',
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
  preferredSlots = new Map(),
  obstacles = [],
} = {}) {
  const halfWidth = labelPixels.width / 2;
  const halfHeight = labelPixels.height / 2;
  if (!viewport
    || viewport.width < labelPixels.width + margin * 2
    || viewport.height < labelPixels.height + margin * 2) return [];
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
  const intersects = (left, right) => (
    left.left < right.right && left.right > right.left
    && left.top < right.bottom && left.bottom > right.top
  );
  const placed = [];
  const expandedObstacles = obstacles.map((obstacle) => ({
    left: obstacle.left - gap,
    right: obstacle.right + gap,
    top: obstacle.top - gap,
    bottom: obstacle.bottom + gap,
  }));
  const intersectsObstacle = (position) => expandedObstacles
    .some((obstacle) => intersects(rectangle(position), obstacle));
  const overlaps = (candidate) => {
    const box = rectangle(candidate);
    return placed.some((position) => {
      const other = rectangle(position);
      return intersects(box, other);
    });
  };
  const offsets = [
    [0, -1], [0, 1], [-1, 0], [1, 0],
    [-1, -1], [1, -1], [-1, 1], [1, 1],
    [0, -2], [0, 2], [-1, -2], [1, -2], [-1, 2], [1, 2],
  ];
  return items.map((item) => {
    const preferredSlot = preferredSlots.get(item.id);
    const slotOrder = Number.isInteger(preferredSlot) && offsets[preferredSlot]
      ? [preferredSlot, ...offsets.keys()].filter((slot, index, slots) => slots.indexOf(slot) === index)
      : [...offsets.keys()];
    const expandedExclusion = item.exclusion ? {
      left: item.exclusion.left - gap,
      right: item.exclusion.right + gap,
      top: item.exclusion.top - gap,
      bottom: item.exclusion.bottom + gap,
    } : null;
    const exclusionCenters = expandedExclusion ? [
      { x: item.anchor.x, y: expandedExclusion.top - halfHeight },
      { x: item.anchor.x, y: expandedExclusion.bottom + halfHeight },
      { x: expandedExclusion.left - halfWidth, y: item.anchor.y },
      { x: expandedExclusion.right + halfWidth, y: item.anchor.y },
      { x: expandedExclusion.left - halfWidth, y: expandedExclusion.top - halfHeight },
      { x: expandedExclusion.right + halfWidth, y: expandedExclusion.top - halfHeight },
      { x: expandedExclusion.left - halfWidth, y: expandedExclusion.bottom + halfHeight },
      { x: expandedExclusion.right + halfWidth, y: expandedExclusion.bottom + halfHeight },
      { x: item.anchor.x, y: expandedExclusion.top - halfHeight - verticalStep },
      { x: item.anchor.x, y: expandedExclusion.bottom + halfHeight + verticalStep },
      { x: expandedExclusion.left - halfWidth, y: expandedExclusion.top - halfHeight - verticalStep },
      { x: expandedExclusion.right + halfWidth, y: expandedExclusion.top - halfHeight - verticalStep },
      { x: expandedExclusion.left - halfWidth, y: expandedExclusion.bottom + halfHeight + verticalStep },
      { x: expandedExclusion.right + halfWidth, y: expandedExclusion.bottom + halfHeight + verticalStep },
    ] : null;
    const candidates = slotOrder.map((slot) => {
      const [column, row] = offsets[slot];
      return {
        slot,
        ...clamp(exclusionCenters?.[slot] || {
          x: item.anchor.x + column * horizontalStep,
          y: item.anchor.y + row * verticalStep,
        }),
      };
    });
    let candidate = candidates.find((position, index) => (
      candidates.findIndex((other) => other.x === position.x && other.y === position.y) === index
      && !overlaps(position)
      && (!expandedExclusion || !intersects(rectangle(position), expandedExclusion))
      && !intersectsObstacle(position)
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
      const fallback = grid.find((position) => (
        !overlaps(position)
        && (!expandedExclusion || !intersects(rectangle(position), expandedExclusion))
        && !intersectsObstacle(position)
      ));
      candidate = fallback ? { slot: null, ...fallback } : null;
    }
    if (!candidate) return null;
    const position = { id: item.id, ...candidate };
    placed.push(position);
    return position;
  }).filter(Boolean);
}

export function buildLabelLeaderSegment({
  anchor,
  label,
  exclusion = null,
  labelPixels = { width: 76, height: 22 },
  minimumDistance = 48,
  anchorPadding = 8,
  componentPadding = 4,
  minimumVisibleLength = 8,
} = {}) {
  const dx = label.x - anchor.x;
  const dy = label.y - anchor.y;
  const distance = Math.hypot(dx, dy);
  if (!exclusion && distance < minimumDistance) return null;
  const unit = { x: dx / distance, y: dy / distance };
  const halfWidth = labelPixels.width / 2;
  const halfHeight = labelPixels.height / 2;
  const edgeDistance = Math.min(
    Math.abs(unit.x) > Number.EPSILON ? halfWidth / Math.abs(unit.x) : Number.POSITIVE_INFINITY,
    Math.abs(unit.y) > Number.EPSILON ? halfHeight / Math.abs(unit.y) : Number.POSITIVE_INFINITY,
  );
  const componentEdgeDistance = exclusion ? Math.min(
    unit.x > Number.EPSILON
      ? (exclusion.right - anchor.x) / unit.x
      : (unit.x < -Number.EPSILON ? (exclusion.left - anchor.x) / unit.x : Number.POSITIVE_INFINITY),
    unit.y > Number.EPSILON
      ? (exclusion.bottom - anchor.y) / unit.y
      : (unit.y < -Number.EPSILON ? (exclusion.top - anchor.y) / unit.y : Number.POSITIVE_INFINITY),
  ) : 0;
  const startDistance = exclusion ? componentEdgeDistance + componentPadding : anchorPadding;
  const endDistance = distance - edgeDistance;
  if (endDistance - startDistance < minimumVisibleLength) return null;
  const round = (value) => Math.round(value * 1_000_000) / 1_000_000;
  return {
    start: {
      x: round(anchor.x + unit.x * startDistance),
      y: round(anchor.y + unit.y * startDistance),
    },
    end: {
      x: round(label.x - unit.x * edgeDistance),
      y: round(label.y - unit.y * edgeDistance),
    },
  };
}

export function resolveAffordancePresentation({ selected = false, hovered = false } = {}) {
  if (selected) return { ...STATES.selected };
  if (hovered) return { ...STATES.hovered };
  return { ...STATES.idle };
}
