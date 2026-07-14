const round = (value) => Math.round(value * 1_000_000) / 1_000_000;

export function polygonBounds(polygon) {
  if (!polygon?.length) return null;
  const xs = polygon.map(([x]) => x);
  const ys = polygon.map(([, y]) => y);
  const minimumX = Math.min(...xs);
  const maximumX = Math.max(...xs);
  const minimumY = Math.min(...ys);
  const maximumY = Math.max(...ys);
  return {
    center: { x: round((minimumX + maximumX) / 2), y: round((minimumY + maximumY) / 2) },
    size: { x: round(maximumX - minimumX), y: round(maximumY - minimumY) },
  };
}

function localEntityRegion(entity) {
  const geometry = entity.geometry || entity.footprint;
  const width = Math.max(0.18, (geometry?.size?.x || 0) * 2);
  const height = Math.max(0.18, (geometry?.size?.y || 0) * 2);
  return {
    center: { ...geometry.center },
    size: { x: round(width), y: round(height) },
  };
}

export function buildEntityTarget(boardId, entity, modules) {
  const module = modules.find((candidate) => candidate.designators.includes(entity.designator) && candidate.sideId === entity.side_id);
  return {
    boardId,
    sideId: entity.side_id,
    targetType: 'entity',
    targetId: entity.component_id,
    focusRegion: module ? polygonBounds(module.polygon) : localEntityRegion(entity),
    recommendedSideId: entity.side_id,
    moduleId: module?.moduleId || null,
  };
}

export function buildModuleTarget(boardId, module) {
  return {
    boardId,
    sideId: module.sideId,
    targetType: 'module',
    targetId: module.moduleId,
    focusRegion: polygonBounds(module.polygon),
    recommendedSideId: module.sideId,
    moduleId: module.moduleId,
  };
}

export function moduleOverlayId(target) {
  return target?.targetType === 'module' ? target.moduleId || null : null;
}

export function resolveTargetSide(target, currentSideId) {
  if (target.availableSideIds?.includes(currentSideId)) return currentSideId;
  return target.recommendedSideId || currentSideId;
}

export function isPointInFocus(point, region, padding = 0.015) {
  if (!region) return true;
  return Math.abs(point.x - region.center.x) <= region.size.x / 2 + padding
    && Math.abs(point.y - region.center.y) <= region.size.y / 2 + padding;
}

export function nextSideId(sideIds, currentSideId) {
  if (!sideIds.length) return null;
  const currentIndex = sideIds.indexOf(currentSideId);
  return sideIds[(currentIndex + 1) % sideIds.length];
}

export function resetFocusView(state) {
  return { ...state, focusRegion: null };
}
