import { validateNormalizedPoint } from '../cross-source-registration/registration-core.js';

export const DEFECT_CATEGORIES = Object.freeze([
  'burn_or_heat_damage',
  'corrosion_or_oxidation',
  'missing_component',
  'displaced_component',
  'connector_damage',
  'shield_or_structure_damage',
  'solder_anomaly',
  'foreign_material',
  'unknown_visible_anomaly',
]);

const roundCoordinate = (value) => Number(value.toFixed(6));

function polygonArea(points) {
  return Math.abs(points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length];
    return sum + point.x * next.y - next.x * point.y;
  }, 0) / 2);
}

export function validateAnnotationGeometry(geometry) {
  if (!geometry || !['rectangle', 'polygon'].includes(geometry.type)) {
    throw new Error('Annotation geometry type must be rectangle or polygon.');
  }
  const expectedCount = geometry.type === 'rectangle' ? 2 : 3;
  if (!Array.isArray(geometry.points) || geometry.points.length < expectedCount
    || (geometry.type === 'rectangle' && geometry.points.length !== 2)) {
    throw new Error(`${geometry.type} annotation has an invalid point count.`);
  }
  const points = geometry.points.map(validateNormalizedPoint);
  if (geometry.type === 'rectangle') {
    if (points[0].x === points[1].x || points[0].y === points[1].y) {
      throw new Error('Rectangle annotation must have positive width and height.');
    }
  } else if (polygonArea(points) === 0) {
    throw new Error('Polygon annotation must cover a positive area.');
  }
  return { type: geometry.type, points };
}

export function annotationCentroid(geometry) {
  const valid = validateAnnotationGeometry(geometry);
  const sum = valid.points.reduce(
    (result, point) => ({ x: result.x + point.x, y: result.y + point.y }),
    { x: 0, y: 0 },
  );
  return {
    x: roundCoordinate(sum.x / valid.points.length),
    y: roundCoordinate(sum.y / valid.points.length),
  };
}

function entityArea(entity) {
  const size = entity.geometry?.size;
  return Number.isFinite(size?.x) && Number.isFinite(size?.y) ? size.x * size.y : Infinity;
}

function containsPoint(entity, point) {
  const center = entity.geometry?.center;
  const size = entity.geometry?.size;
  if (![center?.x, center?.y, size?.x, size?.y].every(Number.isFinite)) return false;
  return Math.abs(point.x - center.x) <= size.x / 2
    && Math.abs(point.y - center.y) <= size.y / 2;
}

export function suggestEntityAtPoint(entities, sideId, point) {
  const normalizedPoint = validateNormalizedPoint(point);
  return [...(entities || [])]
    .filter((entity) => entity.side_id === sideId && containsPoint(entity, normalizedPoint))
    .sort((left, right) => entityArea(left) - entityArea(right))[0] || null;
}

export function deriveQcResult(annotations, registrationStatus) {
  if (registrationStatus !== 'reviewed') return 'needs_review';
  if ((annotations || []).some(
    (annotation) => annotation.source === 'human_annotation'
      && annotation.review_status === 'confirmed',
  )) {
    return 'confirmed_anomaly';
  }
  if ((annotations || []).some((annotation) => annotation.review_status !== 'not_defect')) {
    return 'needs_review';
  }
  return 'no_visible_anomaly';
}

export function createVisualQcCase({
  caseId,
  boardKey,
  boardId,
  sideId,
  captureStage,
  image,
  quality,
}) {
  return {
    schema_version: 'VISUAL-QC-CASE-V1',
    case_id: caseId,
    board_key: boardKey,
    board_id: boardId,
    side_id: sideId,
    storage_scope: 'local_only',
    capture_stage: captureStage,
    image: { ...image },
    quality: { ...quality },
    registration: {
      method: 'reviewed_manual_homography',
      status: 'draft',
      matrix: null,
      solve_anchors: [],
      check_points: [],
      error: { count: 0, rms: null, maximum: null },
    },
    annotations: [],
    qc_result: {
      status: 'needs_review',
      reviewed_at: null,
    },
  };
}
