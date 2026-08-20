import {
  calculateRegistrationError,
  invertHomography,
  projectPoint,
  solveHomography,
  validateAnchorPairs,
  validateNormalizedPoint,
} from '../cross-source-registration/registration-core.js';
import {
  DEFECT_CATEGORIES,
  deriveQcResult,
  validateAnnotationGeometry,
} from './visual-qc-core.js';

const clone = (value) => (typeof structuredClone === 'function'
  ? structuredClone(value)
  : JSON.parse(JSON.stringify(value)));

function pendingQcResult(visualCase) {
  return {
    status: visualCase.quality?.status === 'retake' ? 'image_invalid' : 'needs_review',
    reviewed_at: null,
  };
}

function invalidateServerQcReview(visualCase) {
  delete visualCase.server_qc_review;
}

export function createHistory(initial, limit = 50) {
  return { past: [], current: clone(initial), future: [], limit };
}

export function commitHistory(history, next) {
  return {
    ...history,
    past: [...history.past, clone(history.current)].slice(-history.limit),
    current: clone(next),
    future: [],
  };
}

export function undoHistory(history) {
  if (!history.past.length) return history;
  return {
    ...history,
    past: history.past.slice(0, -1),
    current: clone(history.past.at(-1)),
    future: [clone(history.current), ...history.future].slice(0, history.limit),
  };
}

export function redoHistory(history) {
  if (!history.future.length) return history;
  return {
    ...history,
    past: [...history.past, clone(history.current)].slice(-history.limit),
    current: clone(history.future[0]),
    future: history.future.slice(1),
  };
}

export function applyRegistration(visualCase, boardAnchors, imageAnchors, checkPoints) {
  const anchors = validateAnchorPairs(boardAnchors, imageAnchors);
  const matrix = solveHomography(anchors.source, anchors.target);
  const error = calculateRegistrationError(matrix, checkPoints);
  const next = clone(visualCase);
  const previousMatrix = visualCase.registration?.matrix;
  const registrationChanged = Array.isArray(previousMatrix)
    && previousMatrix.some((value, index) => Math.abs(value - matrix[index]) > 1e-9);
  if (registrationChanged) next.annotations = [];
  next.registration = {
    method: 'reviewed_manual_homography',
    status: 'draft',
    matrix,
    solve_anchors: anchors.source.map((board, index) => ({
      board,
      image: anchors.target[index],
    })),
    check_points: clone(checkPoints),
    error,
  };
  next.qc_result = pendingQcResult(next);
  return next;
}

export function updateDraftRegistration(visualCase, boardAnchors, imageAnchors) {
  if (!Array.isArray(boardAnchors) || !Array.isArray(imageAnchors)
    || boardAnchors.length !== imageAnchors.length || boardAnchors.length > 4) {
    throw new Error('Draft registration requires up to four paired anchors.');
  }
  const next = clone(visualCase);
  next.registration = {
    method: 'reviewed_manual_homography',
    status: 'draft',
    matrix: null,
    solve_anchors: boardAnchors.map((board, index) => ({
      board: validateNormalizedPoint(board),
      image: validateNormalizedPoint(imageAnchors[index]),
    })),
    check_points: [],
    error: { count: 0, rms: null, maximum: null, errors: [] },
  };
  next.annotations = [];
  next.qc_result = pendingQcResult(next);
  return next;
}

export function reviewRegistration(visualCase, reviewedAt = new Date().toISOString()) {
  if (!visualCase.registration?.matrix || visualCase.registration.solve_anchors?.length !== 4) {
    throw new Error('Registration requires four solved anchors before review.');
  }
  if (!visualCase.registration.check_points?.length) {
    throw new Error('Registration requires at least one independent check point before review.');
  }
  const next = clone(visualCase);
  next.registration.status = 'reviewed';
  next.registration.reviewed_at = reviewedAt;
  next.qc_result = pendingQcResult(next);
  return next;
}

export function finalizeQc(visualCase, reviewedAt = new Date().toISOString()) {
  if (visualCase.registration?.status !== 'reviewed') {
    throw new Error('QC requires reviewed registration.');
  }
  if ((visualCase.annotations || []).some(
    (annotation) => annotation.source !== 'human_annotation'
      || annotation.review_status === 'suspected',
  )) {
    throw new Error('QC cannot finalize while suspected or model-candidate annotations remain.');
  }
  const next = clone(visualCase);
  next.qc_result = {
    status: next.quality?.status === 'retake'
      ? 'image_invalid'
      : deriveQcResult(next.annotations, 'reviewed'),
    reviewed_at: reviewedAt,
  };
  return next;
}

function rectangleCorners(points) {
  const [first, second] = points;
  return [
    first,
    { x: second.x, y: first.y },
    second,
    { x: first.x, y: second.y },
  ];
}

function boardGeometryFromImage(imageGeometry, inverseMatrix) {
  const geometry = validateAnnotationGeometry(imageGeometry);
  const imagePoints = geometry.type === 'rectangle'
    ? rectangleCorners(geometry.points)
    : geometry.points;
  return validateAnnotationGeometry({
    type: 'polygon',
    points: imagePoints.map((point) => projectPoint(inverseMatrix, point)),
  });
}

export function addAnnotation(visualCase, {
  annotationId,
  category,
  imageGeometry,
  component = null,
  note = '',
}) {
  if (!DEFECT_CATEGORIES.includes(category)) throw new Error('Unsupported defect category.');
  if (!visualCase.registration?.matrix) throw new Error('Registration is required before annotation.');
  const validImageGeometry = validateAnnotationGeometry(imageGeometry);
  const boardGeometry = boardGeometryFromImage(
    validImageGeometry,
    invertHomography(visualCase.registration.matrix),
  );
  const next = clone(visualCase);
  next.annotations.push({
    annotation_id: annotationId,
    category,
    source: 'human_annotation',
    review_status: 'suspected',
    component: component ? clone(component) : null,
    image_geometry: validImageGeometry,
    board_geometry: boardGeometry,
    note,
  });
  invalidateServerQcReview(next);
  next.qc_result = pendingQcResult(next);
  return next;
}

export function updateAnnotation(visualCase, annotationId, changes) {
  const next = clone(visualCase);
  const annotation = next.annotations.find((item) => item.annotation_id === annotationId);
  if (!annotation) throw new Error('Annotation does not exist.');
  if (changes.category && !DEFECT_CATEGORIES.includes(changes.category)) {
    throw new Error('Unsupported defect category.');
  }
  Object.assign(annotation, clone(changes));
  invalidateServerQcReview(next);
  next.qc_result = pendingQcResult(next);
  return next;
}

export function removeAnnotation(visualCase, annotationId) {
  const next = clone(visualCase);
  next.annotations = next.annotations.filter((item) => item.annotation_id !== annotationId);
  invalidateServerQcReview(next);
  next.qc_result = pendingQcResult(next);
  return next;
}
