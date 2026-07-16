import { projectPoint } from './registration-core.js';

const STACKED_WORKSPACE_MAX_WIDTH = 1100;

export function buildSelectionState(entity, registrationMatrix) {
  return {
    componentId: entity.component_id,
    designator: entity.designator,
    boardPoint: { ...entity.geometry.center },
    photoPoint: projectPoint(registrationMatrix, entity.geometry.center),
    schematicLinks: entity.schematic_links || [],
    repairLinks: entity.repair_links || [],
    entity,
  };
}

export function findEntityAtPoint(entities, point) {
  return entities
    .filter(({ geometry }) => Math.abs(point.x - geometry.center.x) <= geometry.size.x / 2
      && Math.abs(point.y - geometry.center.y) <= geometry.size.y / 2)
    .sort((left, right) => (left.geometry.size.x * left.geometry.size.y)
      - (right.geometry.size.x * right.geometry.size.y))[0] || null;
}

export function nearestPointerTarget(targets, pointer) {
  if (!targets.length) return null;
  return targets.reduce((nearest, target) => {
    const distance = Math.hypot(target.center.x - pointer.x, target.center.y - pointer.y);
    return !nearest || distance < nearest.distance ? { id: target.id, distance } : nearest;
  }, null).id;
}

export function entityListModelRevealOptions({
  activeView,
  viewportWidth,
  reducedMotion = false,
}) {
  if (activeView !== 'model' || viewportWidth > STACKED_WORKSPACE_MAX_WIDTH) return null;
  return {
    behavior: reducedMotion ? 'auto' : 'smooth',
    block: 'start',
  };
}
