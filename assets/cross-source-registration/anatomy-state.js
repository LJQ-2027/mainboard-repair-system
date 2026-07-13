const PRESENTATIONS = {
  installed: { visible: true, opacity: 0.96, coveredBodiesVisible: false },
  xray: { visible: true, opacity: 0.3, coveredBodiesVisible: true },
  removed: { visible: false, opacity: 0, coveredBodiesVisible: true },
};

export function extractShieldRegions(geometryData) {
  return (geometryData?.regions || [])
    .filter((region) => region.category === 'shield_region' && region.center && region.size)
    .map((region) => ({
      shieldId: region.geometry_id,
      center: { ...region.center },
      size: { ...region.size },
      polygon: region.polygon?.map(([x, y]) => [x, y]) || null,
      sourceStatus: region.semantic_status || 'unresolved_geometry',
    }));
}

export function getShieldPresentation(mode) {
  return { ...(PRESENTATIONS[mode] || PRESENTATIONS.removed) };
}

export function isPointCovered(point, region, padding = 0) {
  const halfWidth = region.size.x / 2 + padding;
  const halfHeight = region.size.y / 2 + padding;
  const insideBounds = Math.abs(point.x - region.center.x) <= halfWidth
    && Math.abs(point.y - region.center.y) <= halfHeight;
  if (!insideBounds || !region.polygon?.length || padding > 0) return insideBounds;
  let inside = false;
  for (let index = 0, previous = region.polygon.length - 1; index < region.polygon.length; previous = index, index += 1) {
    const [x, y] = region.polygon[index];
    const [previousX, previousY] = region.polygon[previous];
    const intersects = (y > point.y) !== (previousY > point.y)
      && point.x < ((previousX - x) * (point.y - y)) / (previousY - y) + x;
    if (intersects) inside = !inside;
  }
  return inside;
}

export function extractModuleRegions(atlasData, sideId) {
  const modules = atlasData?.boards?.[0]?.modules || [];
  return modules
    .filter((module) => module.side_id === sideId && module.status === 'source_overlay' && module.polygon?.length >= 3)
    .map((module) => ({
      moduleId: module.module_id,
      name: module.name,
      designators: [...(module.designators || [])],
      polygon: module.polygon.map(([x, y]) => [x, y]),
    }));
}

export function shouldShowLabels(zoom, threshold = 1.55) {
  return zoom >= threshold;
}
