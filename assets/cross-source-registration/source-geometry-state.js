const PROMOTED_FOOTPRINT_CONFIDENCE = new Set(['high', 'medium']);

export function mergeCompiledFootprint(entity, compiled) {
  const footprint = compiled?.footprint;
  if (!footprint || !PROMOTED_FOOTPRINT_CONFIDENCE.has(footprint.confidence)) return entity;
  return {
    ...entity,
    geometry: {
      ...entity.geometry,
      center: footprint.center,
      size: footprint.size,
      source_status: footprint.confidence,
    },
  };
}
