import test from 'node:test';
import assert from 'node:assert/strict';

import {
  addAnnotation,
  applyRegistration,
  commitHistory,
  createHistory,
  finalizeQc,
  redoHistory,
  reviewRegistration,
  updateAnnotation,
  updateDraftRegistration,
  undoHistory,
} from '../assets/visual-qc-workbench/visual-qc-state.js';
import { createVisualQcCase } from '../assets/visual-qc-workbench/visual-qc-core.js';

function draftCase() {
  return createVisualQcCase({
    caseId: 'case-001',
    boardKey: 'km4-f151',
    boardId: 'BOARD-KM4-F151-MAIN-V1.2',
    sideId: 'main_page_2',
    captureStage: 'before_repair',
    image: {
      fileName: 'board.jpg',
      mimeType: 'image/jpeg',
      width: 1200,
      height: 900,
      sha256: 'a'.repeat(64),
    },
    quality: { status: 'good', score: 90, metrics: {} },
  });
}

const boardAnchors = [
  { x: 0.1, y: 0.1 },
  { x: 0.9, y: 0.1 },
  { x: 0.9, y: 0.9 },
  { x: 0.1, y: 0.9 },
];
const imageAnchors = [
  { x: 0.2, y: 0.15 },
  { x: 0.85, y: 0.2 },
  { x: 0.8, y: 0.85 },
  { x: 0.15, y: 0.8 },
];

test('history restores and reapplies immutable visual QC snapshots', () => {
  let history = createHistory({ value: 1 });
  history = commitHistory(history, { value: 2 });
  history = commitHistory(history, { value: 3 });
  history = undoHistory(history);
  assert.deepEqual(history.current, { value: 2 });
  history = redoHistory(history);
  assert.deepEqual(history.current, { value: 3 });
});

test('registration remains draft until an independent check point is present', () => {
  const registered = applyRegistration(draftCase(), boardAnchors, imageAnchors, []);

  assert.equal(registered.registration.status, 'draft');
  assert.equal(registered.registration.solve_anchors.length, 4);
  assert.throws(() => reviewRegistration(registered), /check point/i);

  const checked = applyRegistration(registered, boardAnchors, imageAnchors, [
    { board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } },
  ]);
  const reviewed = reviewRegistration(checked, '2026-07-17T12:00:00Z');
  assert.equal(reviewed.registration.status, 'reviewed');
  assert.equal(reviewed.qc_result.status, 'needs_review');
  assert.equal(reviewed.qc_result.reviewed_at, null);

  const finalized = finalizeQc(reviewed, '2026-07-17T12:05:00Z');
  assert.equal(finalized.qc_result.status, 'no_visible_anomaly');
  assert.equal(finalized.qc_result.reviewed_at, '2026-07-17T12:05:00Z');
});

test('partial anchor pairs remain recoverable as a draft without a matrix', () => {
  const visualCase = updateDraftRegistration(
    draftCase(),
    [boardAnchors[0], boardAnchors[1]],
    [imageAnchors[0], imageAnchors[1]],
  );

  assert.equal(visualCase.registration.status, 'draft');
  assert.equal(visualCase.registration.matrix, null);
  assert.equal(visualCase.registration.solve_anchors.length, 2);
  assert.equal(visualCase.qc_result.status, 'needs_review');
});

test('human annotation remains suspected until explicitly confirmed', () => {
  let visualCase = applyRegistration(draftCase(), boardAnchors, imageAnchors, [
    { board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } },
  ]);
  visualCase = reviewRegistration(visualCase, '2026-07-17T12:00:00Z');
  visualCase = addAnnotation(visualCase, {
    annotationId: 'annotation-001',
    category: 'burn_or_heat_damage',
    imageGeometry: {
      type: 'rectangle',
      points: [{ x: 0.3, y: 0.3 }, { x: 0.4, y: 0.4 }],
    },
    component: null,
  });

  assert.equal(visualCase.annotations[0].source, 'human_annotation');
  assert.equal(visualCase.annotations[0].review_status, 'suspected');
  assert.equal(visualCase.qc_result.status, 'needs_review');
});

test('QC cannot finalize while suspected annotations remain', () => {
  let visualCase = applyRegistration(draftCase(), boardAnchors, imageAnchors, [
    { board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } },
  ]);
  visualCase = reviewRegistration(visualCase);
  visualCase = addAnnotation(visualCase, {
    annotationId: 'annotation-001',
    category: 'burn_or_heat_damage',
    imageGeometry: {
      type: 'rectangle',
      points: [{ x: 0.3, y: 0.3 }, { x: 0.4, y: 0.4 }],
    },
  });

  assert.throws(() => finalizeQc(visualCase), /suspected/i);
});

test('editing reviewed annotations invalidates the synchronized server QC review', () => {
  let visualCase = applyRegistration(draftCase(), boardAnchors, imageAnchors, [
    { board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } },
  ]);
  visualCase = reviewRegistration(visualCase);
  visualCase.server_qc_review = {
    qc_review_id: 'qcrev-001',
    version: 1,
    training_status: 'eligible',
  };
  visualCase.annotations = [{
    annotation_id: 'annotation-001',
    category: 'burn_or_heat_damage',
    source: 'human_annotation',
    review_status: 'confirmed',
    component: null,
    image_geometry: {
      type: 'rectangle',
      points: [{ x: 0.2, y: 0.2 }, { x: 0.3, y: 0.3 }],
    },
    board_geometry: {
      type: 'polygon',
      points: [
        { x: 0.2, y: 0.2 },
        { x: 0.3, y: 0.2 },
        { x: 0.3, y: 0.3 },
        { x: 0.2, y: 0.3 },
      ],
    },
    note: '',
  }];

  const updated = updateAnnotation(visualCase, 'annotation-001', {
    review_status: 'not_defect',
  });

  assert.equal(updated.server_qc_review, undefined);
  assert.equal(updated.qc_result.status, 'needs_review');
});

test('changing a solved registration invalidates annotations projected by the old matrix', () => {
  let visualCase = applyRegistration(draftCase(), boardAnchors, imageAnchors, [
    { board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } },
  ]);
  visualCase = reviewRegistration(visualCase);
  visualCase = addAnnotation(visualCase, {
    annotationId: 'annotation-001',
    category: 'missing_component',
    imageGeometry: {
      type: 'rectangle',
      points: [{ x: 0.3, y: 0.3 }, { x: 0.4, y: 0.4 }],
    },
  });

  const sameRegistration = applyRegistration(visualCase, boardAnchors, imageAnchors, [
    { board: { x: 0.6, y: 0.6 }, image: { x: 0.6, y: 0.6 } },
  ]);
  assert.equal(sameRegistration.annotations.length, 1);

  const changedImageAnchors = imageAnchors.map((point, index) => (
    index === 2 ? { x: point.x - 0.05, y: point.y } : point
  ));
  const changedRegistration = applyRegistration(
    sameRegistration,
    boardAnchors,
    changedImageAnchors,
    [{ board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } }],
  );
  assert.equal(changedRegistration.annotations.length, 0);
});

test('registration and annotation cannot overwrite an invalid image QC result', () => {
  const invalid = draftCase();
  invalid.quality.status = 'retake';
  invalid.qc_result = { status: 'image_invalid', reviewed_at: null };

  let visualCase = applyRegistration(invalid, boardAnchors, imageAnchors, [
    { board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } },
  ]);
  visualCase = reviewRegistration(visualCase);
  visualCase = addAnnotation(visualCase, {
    annotationId: 'annotation-001',
    category: 'burn_or_heat_damage',
    imageGeometry: {
      type: 'rectangle',
      points: [{ x: 0.45, y: 0.45 }, { x: 0.5, y: 0.5 }],
    },
  });
  visualCase = {
    ...visualCase,
    annotations: visualCase.annotations.map((annotation) => ({
      ...annotation,
      review_status: 'confirmed',
    })),
  };

  assert.equal(visualCase.qc_result.status, 'image_invalid');
  assert.equal(finalizeQc(visualCase).qc_result.status, 'image_invalid');
});
