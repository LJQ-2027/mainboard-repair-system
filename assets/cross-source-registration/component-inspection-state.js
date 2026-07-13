const IDLE_INSPECTION = Object.freeze({
  mode: 'idle',
  componentId: null,
  sideId: null,
  profileId: null,
});

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

export function canInspectComponent(entity) {
  return Boolean(entity?.inspection_profile?.profile_id);
}

export function enterComponentInspection(entity, activeSideId) {
  if (!canInspectComponent(entity) || entity.side_id !== activeSideId) return { ...IDLE_INSPECTION };
  return {
    mode: 'isolated',
    componentId: entity.component_id,
    sideId: entity.side_id,
    profileId: entity.inspection_profile.profile_id,
  };
}

export function exitComponentInspection() {
  return { ...IDLE_INSPECTION };
}

export function inspectionOpacity(activeComponentId, componentId) {
  if (!activeComponentId || activeComponentId === componentId) return 1;
  return 0.12;
}

export function buildInspectionTransform(dimensions, narrow = false) {
  const largestSide = Math.max(dimensions.x, dimensions.y, 0.001);
  return {
    scale: Math.round(clamp(0.42 / largestSide, 1.7, 2.6) * 1_000_000) / 1_000_000,
    lift: Math.round(clamp(dimensions.z * 2.4 + 0.08, 0.12, 0.2) * 1_000_000) / 1_000_000,
    zoom: narrow ? 1.9 : 2.25,
  };
}
