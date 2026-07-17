import test from 'node:test';
import assert from 'node:assert/strict';

import {
  annotationCentroid,
  createVisualQcCase,
  deriveQcResult,
  suggestEntityAtPoint,
  validateAnnotationGeometry,
} from '../assets/visual-qc-workbench/visual-qc-core.js';

test('rectangle and polygon annotations stay in normalized board coordinates', () => {
  const rectangle = validateAnnotationGeometry({
    type: 'rectangle',
    points: [{ x: 0.2, y: 0.3 }, { x: 0.5, y: 0.7 }],
  });
  assert.deepEqual(annotationCentroid(rectangle), { x: 0.35, y: 0.5 });

  const polygon = validateAnnotationGeometry({
    type: 'polygon',
    points: [{ x: 0.1, y: 0.1 }, { x: 0.5, y: 0.1 }, { x: 0.3, y: 0.6 }],
  });
  assert.deepEqual(annotationCentroid(polygon), { x: 0.3, y: 0.266667 });

  assert.throws(
    () => validateAnnotationGeometry({ type: 'rectangle', points: [{ x: -0.1, y: 0 }, { x: 0.2, y: 0.2 }] }),
    /normalized/i,
  );
});

test('entity suggestion chooses the smallest footprint containing the annotation center', () => {
  const entities = [
    {
      component_id: 'BOARD-U1000',
      designator: 'U1000',
      side_id: 'main_page_1',
      geometry: { center: { x: 0.5, y: 0.5 }, size: { x: 0.4, y: 0.4 } },
    },
    {
      component_id: 'BOARD-U1001',
      designator: 'U1001',
      side_id: 'main_page_1',
      geometry: { center: { x: 0.5, y: 0.5 }, size: { x: 0.1, y: 0.1 } },
    },
  ];

  assert.equal(suggestEntityAtPoint(entities, 'main_page_1', { x: 0.5, y: 0.5 }).designator, 'U1001');
  assert.equal(suggestEntityAtPoint(entities, 'main_page_2', { x: 0.5, y: 0.5 }), null);
  assert.equal(suggestEntityAtPoint(entities, 'main_page_1', { x: 0.9, y: 0.9 }), null);
});

test('visual QC case starts as a local human annotation draft', () => {
  const visualCase = createVisualQcCase({
    caseId: 'case-001',
    boardKey: 'km4-f151',
    boardId: 'BOARD-KM4-F151-MAIN-V1.2',
    sideId: 'main_page_2',
    captureStage: 'before_repair',
    image: {
      fileName: 'board.jpg',
      mimeType: 'image/jpeg',
      width: 2400,
      height: 1800,
      sha256: 'a'.repeat(64),
    },
    quality: { status: 'good', score: 92, metrics: {} },
  });

  assert.equal(visualCase.schema_version, 'VISUAL-QC-CASE-V1');
  assert.equal(visualCase.storage_scope, 'local_only');
  assert.equal(visualCase.qc_result.status, 'needs_review');
  assert.deepEqual(visualCase.annotations, []);
});

test('QC result is based only on reviewed human annotations', () => {
  assert.equal(deriveQcResult([], 'reviewed'), 'no_visible_anomaly');
  assert.equal(deriveQcResult([{ source: 'human_annotation', review_status: 'confirmed' }], 'reviewed'), 'confirmed_anomaly');
  assert.equal(deriveQcResult([{ source: 'model_candidate', review_status: 'suspected' }], 'reviewed'), 'needs_review');
  assert.equal(deriveQcResult([], 'draft'), 'needs_review');
});
