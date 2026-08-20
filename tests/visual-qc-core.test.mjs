import test from 'node:test';
import assert from 'node:assert/strict';

import {
  annotationCentroid,
  captureChecklistStatus,
  createVisualQcCase,
  deriveQcResult,
  deriveCapturePairStatus,
  suggestEntityAtPoint,
  updateCaptureChecklist,
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
    captureSession: {
      sessionId: 'capture-session-001',
      setupId: 'standard-bench',
      expectedSideIds: ['main_page_1', 'main_page_2'],
      checklist: {
        board_and_side_confirmed: true,
        focus_and_lens_confirmed: true,
        lighting_and_occlusion_confirmed: true,
      },
    },
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
  assert.equal(visualCase.capture_session.session_id, 'capture-session-001');
  assert.equal(visualCase.capture_session.checklist.status, 'confirmed');
  assert.equal(visualCase.capture_session.pair_status, 'pair_in_progress');
});

test('capture checklist and board-side pair status are deterministic', () => {
  assert.equal(captureChecklistStatus({
    board_and_side_confirmed: true,
    focus_and_lens_confirmed: true,
    lighting_and_occlusion_confirmed: true,
  }), 'confirmed');
  assert.equal(captureChecklistStatus({
    board_and_side_confirmed: true,
    focus_and_lens_confirmed: false,
    lighting_and_occlusion_confirmed: true,
  }), 'pending');
  assert.equal(captureChecklistStatus({}, 'proxy_sample'), 'not_applicable');

  assert.equal(
    deriveCapturePairStatus(['main_page_1', 'main_page_2'], ['main_page_1']),
    'pair_in_progress',
  );
  assert.equal(
    deriveCapturePairStatus(['main_page_1', 'main_page_2'], ['main_page_2', 'main_page_1']),
    'pair_complete',
  );
  assert.equal(deriveCapturePairStatus(['main_page_1'], ['main_page_1']), 'single_side');
});

test('capture checklist confirmation is immutable and timestamped only when complete', () => {
  const original = createVisualQcCase({
    caseId: 'case-002',
    boardKey: 'km4-f151',
    boardId: 'BOARD-KM4-F151-MAIN-V1.2',
    sideId: 'main_page_1',
    captureStage: 'before_repair',
    captureSession: {
      sessionId: 'capture-session-002',
      expectedSideIds: ['main_page_1', 'main_page_2'],
    },
    image: { evidence_role: 'physical_capture' },
    quality: { status: 'good', score: 90, metrics: {} },
  });
  let updated = updateCaptureChecklist(
    original,
    'board_and_side_confirmed',
    true,
    '2026-07-20T11:00:00.000Z',
  );
  updated = updateCaptureChecklist(
    updated,
    'focus_and_lens_confirmed',
    true,
    '2026-07-20T11:01:00.000Z',
  );
  updated = updateCaptureChecklist(
    updated,
    'lighting_and_occlusion_confirmed',
    true,
    '2026-07-20T11:02:00.000Z',
  );

  assert.equal(original.capture_session.checklist.status, 'pending');
  assert.equal(updated.capture_session.checklist.status, 'confirmed');
  assert.equal(
    updated.capture_session.checklist.confirmed_at,
    '2026-07-20T11:02:00.000Z',
  );
  assert.throws(
    () => updateCaptureChecklist(updated, 'unknown_item', true),
    /unsupported capture checklist item/i,
  );
});

test('a second local board side preserves the same capture pair before upload', () => {
  const visualCase = createVisualQcCase({
    caseId: 'case-003',
    boardKey: 'km4-f151',
    boardId: 'BOARD-KM4-F151-MAIN-V1.2',
    sideId: 'main_page_1',
    captureStage: 'before_repair',
    captureSession: {
      sessionId: 'capture-session-003',
      expectedSideIds: ['main_page_1', 'main_page_2'],
      capturedSideIds: ['main_page_2'],
    },
    image: { evidence_role: 'physical_capture' },
    quality: { status: 'good', score: 90, metrics: {} },
  });

  assert.deepEqual(
    visualCase.capture_session.captured_side_ids,
    ['main_page_2', 'main_page_1'],
  );
  assert.equal(visualCase.capture_session.pair_status, 'pair_complete');
});

test('QC result is based only on reviewed human annotations', () => {
  assert.equal(deriveQcResult([], 'reviewed'), 'no_visible_anomaly');
  assert.equal(deriveQcResult([{ source: 'human_annotation', review_status: 'confirmed' }], 'reviewed'), 'confirmed_anomaly');
  assert.equal(deriveQcResult([{ source: 'model_candidate', review_status: 'suspected' }], 'reviewed'), 'needs_review');
  assert.equal(deriveQcResult([], 'draft'), 'needs_review');
});
