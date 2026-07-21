import test from 'node:test';
import assert from 'node:assert/strict';

import {
  applyCandidateReview,
  applyDifferenceJobResult,
  applyGoldenSample,
  applyServerJobResult,
  applyFinalQcReview,
  createDifferenceJobDescriptor,
  createFinalQcReviewDescriptor,
  createGoldenSampleDescriptor,
  createRegistrationReviewDescriptor,
  createServerSyncState,
  createUploadDescriptor,
  getVisualQcCocoDataset,
  getVisualQcDatasetAudit,
  getVisualQcIdentity,
  getVisualQcTrainingManifest,
  normalizeServerCaptureSession,
  pollVisualQcJob,
  transitionServerSync,
} from '../assets/visual-qc-workbench/visual-qc-server-client.js';


function visualCase() {
  return {
    schema_version: 'VISUAL-QC-CASE-V1',
    case_id: 'case-001',
    board_key: 'km4-f151',
    board_id: 'BOARD-KM4-F151-MAIN-V1.2',
    side_id: 'main_page_2',
    capture_stage: 'before_repair',
    storage_scope: 'local_only',
    capture_session: {
      schema_version: 'VISUAL-QC-CAPTURE-SESSION-V1',
      session_id: 'capture-session-001',
      setup_id: 'standard-bench',
      expected_side_ids: ['main_page_1', 'main_page_2'],
      captured_side_ids: ['main_page_2'],
      pair_status: 'pair_in_progress',
      checklist: {
        status: 'confirmed',
        items: {
          board_and_side_confirmed: true,
          focus_and_lens_confirmed: true,
          lighting_and_occlusion_confirmed: true,
        },
        confirmed_at: '2026-07-20T10:00:00.000Z',
      },
    },
    image: {
      file_name: 'board.jpg',
      mime_type: 'image/jpeg',
      sha256: 'a'.repeat(64),
      evidence_role: 'physical_capture',
    },
    quality: { status: 'usable', score: 72, metrics: {} },
    registration: {
      method: 'reviewed_manual_homography',
      status: 'draft',
      matrix: null,
      solve_anchors: [],
      check_points: [],
      error: { count: 0, rms: null, maximum: null },
    },
    annotations: [],
    qc_result: { status: 'needs_review', reviewed_at: null },
  };
}

test('server sync keeps a stable idempotency key across retry transitions', () => {
  const initial = createServerSyncState(visualCase());
  const uploading = transitionServerSync(initial, { type: 'upload_started' });
  const failed = transitionServerSync(uploading, {
    type: 'upload_failed',
    message: 'network unavailable',
  });
  const retrying = transitionServerSync(failed, { type: 'upload_started' });

  assert.equal(initial.idempotency_key, retrying.idempotency_key);
  assert.equal(retrying.attempt_count, 2);
  assert.equal(retrying.status, 'uploading');
  assert.equal(retrying.last_error, null);
});

test('upload descriptor preserves known board identity and physical evidence role', () => {
  const descriptor = createUploadDescriptor(visualCase(), createServerSyncState(visualCase()));

  assert.deepEqual(descriptor.fields, {
    board_key: 'km4-f151',
    side_id: 'main_page_2',
    capture_stage: 'before_repair',
    evidence_role: 'physical_capture',
    capture_session_id: 'capture-session-001',
    capture_setup_id: 'standard-bench',
    capture_checklist: JSON.stringify({
      status: 'confirmed',
      items: {
        board_and_side_confirmed: true,
        focus_and_lens_confirmed: true,
        lighting_and_occlusion_confirmed: true,
      },
      confirmed_at: '2026-07-20T10:00:00.000Z',
    }),
    sha256: 'a'.repeat(64),
  });
  assert.equal(descriptor.idempotencyKey, createServerSyncState(visualCase()).idempotency_key);
});

test('server identity replaces browser hints with the gateway assertion', async () => {
  const originalFetch = globalThis.fetch;
  let request = null;
  globalThis.fetch = async (url, options) => {
    request = { url, options };
    return {
      ok: true,
      status: 200,
      json: async () => ({
        schema_version: 'VISUAL-QC-IDENTITY-V1',
        actor_id: 'gateway-reviewer',
        role: 'reviewer',
      }),
    };
  };
  try {
    const identity = await getVisualQcIdentity(
      '/api/v1/visual-qc',
      'browser-hint',
      'technician',
    );

    assert.equal(identity.actor_id, 'gateway-reviewer');
    assert.equal(identity.role, 'reviewer');
    assert.equal(request.url, '/api/v1/visual-qc/identity');
    assert.equal(request.options.headers['X-Actor-Id'], 'browser-hint');
    assert.equal(request.options.headers['X-Actor-Role'], 'technician');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('reviewer dataset requests use all governed export and audit routes', async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options });
    return {
      ok: true,
      status: 200,
      json: async () => ({ schema_version: 'test' }),
    };
  };
  try {
    await getVisualQcTrainingManifest('/api/v1/visual-qc', 'reviewer-001', 'reviewer');
    await getVisualQcCocoDataset('/api/v1/visual-qc/', 'reviewer-001', 'reviewer');
    await getVisualQcDatasetAudit('/api/v1/visual-qc/', 'reviewer-001', 'reviewer');
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(requests.map((request) => request.url), [
    '/api/v1/visual-qc/datasets/training-manifest',
    '/api/v1/visual-qc/datasets/coco',
    '/api/v1/visual-qc/datasets/audit',
  ]);
  assert.ok(requests.every(
    (request) => request.options.headers['X-Actor-Role'] === 'reviewer',
  ));
});

test('automatic result remains a draft candidate until server review succeeds', () => {
  const accepted = {
    case_id: 'vqc_server_case',
    image: { image_id: 'img_server' },
    job: { job_id: 'job_server', status: 'queued' },
    capture_session: {
      schema_version: 'VISUAL-QC-CAPTURE-SESSION-V1',
      session_id: 'capture-session-001',
      setup_id: 'standard-bench',
      expected_side_ids: ['main_page_1', 'main_page_2'],
      captured_side_ids: ['main_page_1', 'main_page_2'],
      pair_status: 'pair_complete',
      checklist: { status: 'confirmed', items: {}, confirmed_at: null },
      board_key: 'km4-f151',
      board_id: 'BOARD-KM4-F151-MAIN-V1.2',
      cases: [{ case_id: 'vqc_server_case', side_id: 'main_page_2' }],
    },
  };
  const job = {
    job_id: 'job_server',
    status: 'succeeded',
    result: {
      schema_version: 'VISUAL-QC-SERVER-JOB-RESULT-V1',
      quality: {
        schema_version: 'VISUAL-QC-IMAGE-QUALITY-V1',
        status: 'good',
        score: 91,
        metrics: { sharpness: 18 },
        guidance: [],
      },
      registration: {
        schema_version: 'VISUAL-QC-REGISTRATION-CANDIDATE-V1',
        status: 'candidate',
        method: 'automatic_feature_homography',
        review_status: 'draft',
        board_to_image_matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
        evidence: { reprojection_rms: 0.003 },
      },
    },
  };

  const updated = applyServerJobResult(visualCase(), accepted, job);

  assert.equal(updated.schema_version, 'VISUAL-QC-CASE-V2');
  assert.equal(updated.storage_scope, 'server_authoritative_with_local_draft');
  assert.equal(updated.server_sync.status, 'candidate_ready');
  assert.equal(updated.registration.method, 'automatic_feature_homography');
  assert.equal(updated.registration.status, 'draft');
  assert.deepEqual(updated.registration.matrix, job.result.registration.board_to_image_matrix);
  assert.equal(updated.quality.score, 91);
  assert.equal(updated.capture_session.pair_status, 'pair_complete');
  assert.equal('board_key' in updated.capture_session, false);
  assert.equal('cases' in updated.capture_session, false);
});

test('server capture session is reduced to the exported case contract', () => {
  const normalized = normalizeServerCaptureSession({
    schema_version: 'VISUAL-QC-CAPTURE-SESSION-V1',
    session_id: 'capture-session-001',
    setup_id: 'standard-bench',
    expected_side_ids: ['main_page_1', 'main_page_2'],
    captured_side_ids: ['main_page_1', 'main_page_2'],
    pair_status: 'pair_complete',
    checklist: visualCase().capture_session.checklist,
    board_key: 'km4-f151',
    cases: [{ case_id: 'server-only' }],
  });

  assert.deepEqual(Object.keys(normalized), [
    'schema_version',
    'session_id',
    'setup_id',
    'expected_side_ids',
    'captured_side_ids',
    'pair_status',
    'checklist',
  ]);
});

test('manual-required result preserves the local four-point fallback', () => {
  const job = {
    job_id: 'job_server',
    status: 'succeeded',
    result: {
      schema_version: 'VISUAL-QC-SERVER-JOB-RESULT-V1',
      quality: { status: 'usable', score: 70, metrics: {}, guidance: [] },
      registration: {
        status: 'manual_required',
        method: null,
        board_to_image_matrix: null,
        failure: { code: 'insufficient_matches' },
        fallback: { method: 'reviewed_manual_four_point' },
      },
    },
  };

  const updated = applyServerJobResult(
    visualCase(),
    {
      case_id: 'vqc_server_case',
      image: { image_id: 'img_server' },
      job: { job_id: 'job_server' },
    },
    job,
  );

  assert.equal(updated.server_sync.status, 'manual_required');
  assert.equal(updated.registration.method, 'reviewed_manual_four_point');
  assert.equal(updated.registration.matrix, null);
  assert.equal(updated.registration.fallback_reason, 'insufficient_matches');
});

test('job polling stops on a persisted terminal state', async () => {
  const snapshots = [
    { job_id: 'job-1', status: 'queued' },
    { job_id: 'job-1', status: 'running' },
    { job_id: 'job-1', status: 'succeeded', result: {} },
  ];
  const seen = [];

  const terminal = await pollVisualQcJob({
    jobId: 'job-1',
    getJob: async () => snapshots.shift(),
    wait: async () => {},
    onSnapshot: (snapshot) => seen.push(snapshot.status),
    maximumAttempts: 5,
  });

  assert.equal(terminal.status, 'succeeded');
  assert.deepEqual(seen, ['queued', 'running', 'succeeded']);
});

test('registration review descriptor keeps automatic and manual evidence distinct', () => {
  const automatic = createRegistrationReviewDescriptor({
    method: 'automatic_feature_homography',
    matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
    solve_anchors: [],
  });
  const manual = createRegistrationReviewDescriptor({
    method: 'reviewed_manual_homography',
    matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
    solve_anchors: [
      { board: { x: 0, y: 0 }, image: { x: 0, y: 0 } },
      { board: { x: 1, y: 0 }, image: { x: 1, y: 0 } },
      { board: { x: 1, y: 1 }, image: { x: 1, y: 1 } },
      { board: { x: 0, y: 1 }, image: { x: 0, y: 1 } },
    ],
    check_points: [
      { board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } },
    ],
    error: { count: 1, rms: 0, maximum: 0 },
  });

  assert.deepEqual(automatic, { decision: 'accept_automatic', notes: '' });
  assert.equal(manual.decision, 'accept_manual');
  assert.deepEqual(manual.anchors[2], { board: [1, 1], image: [1, 1] });
  assert.deepEqual(manual.check_points[0], {
    board: [0.5, 0.5],
    image: [0.5, 0.5],
  });
  assert.deepEqual(manual.error, { count: 1, rms: 0, maximum: 0 });
  assert.equal(manual.board_to_image_matrix.length, 9);
});

test('final QC review descriptor contains only resolved human evidence', () => {
  const reviewedCase = visualCase();
  reviewedCase.qc_result = {
    status: 'confirmed_anomaly',
    reviewed_at: '2026-07-20T12:00:00.000Z',
  };
  reviewedCase.annotations = [{
    annotation_id: 'annotation-001',
    category: 'burn_or_heat_damage',
    source: 'human_annotation',
    review_status: 'confirmed',
    image_geometry: {
      type: 'polygon',
      points: [{ x: 0.2, y: 0.2 }, { x: 0.3, y: 0.2 }, { x: 0.3, y: 0.3 }],
    },
    board_geometry: {
      type: 'polygon',
      points: [{ x: 0.2, y: 0.2 }, { x: 0.3, y: 0.2 }, { x: 0.3, y: 0.3 }],
    },
    component: null,
    note: '',
  }];

  const descriptor = createFinalQcReviewDescriptor(reviewedCase);
  const synchronized = applyFinalQcReview(reviewedCase, {
    qc_review_id: 'qcrev-001',
    version: 1,
    training_status: 'eligible',
    created_at: '2026-07-20T12:01:00.000Z',
  });

  assert.equal(descriptor.qc_result, 'confirmed_anomaly');
  assert.equal(descriptor.annotations.length, 1);
  assert.equal(synchronized.server_qc_review.version, 1);
  assert.equal(synchronized.server_qc_review.training_status, 'eligible');
});

test('Golden approval descriptor requires an explicit normal-board confirmation', () => {
  assert.throws(
    () => createGoldenSampleDescriptor(visualCase(), 'bench-a', false),
    /explicit normal-board confirmation/i,
  );

  const descriptor = createGoldenSampleDescriptor(visualCase(), 'bench-a', true);

  assert.deepEqual(descriptor, {
    case_id: 'case-001',
    capture_setup_id: 'bench-a',
    confirmed_normal: true,
  });
});

test('Golden state preserves the active version and capture setup', () => {
  const updated = applyGoldenSample(visualCase(), {
    golden_sample_id: 'gold-002',
    capture_setup_id: 'bench-a',
    status: 'active',
    version: 2,
    source_sha256: 'b'.repeat(64),
  });

  assert.equal(updated.visual_comparison.capture_setup_id, 'bench-a');
  assert.equal(updated.visual_comparison.golden_sample.version, 2);
  assert.equal(updated.visual_comparison.golden_sample.status, 'active');
});

test('difference result remains a review queue and never confirms a defect', () => {
  const descriptor = createDifferenceJobDescriptor('bench-a');
  assert.deepEqual(descriptor, { capture_setup_id: 'bench-a' });

  const updated = applyDifferenceJobResult(visualCase(), {
    job_id: 'job-difference',
    status: 'succeeded',
    result: {
      schema_version: 'VISUAL-QC-DIFFERENCE-CANDIDATES-V1',
      status: 'candidate_review_required',
      source: 'model_candidate',
      requires_human_review: true,
      heatmap: { artifact_id: 'artifact-001', mime_type: 'image/png' },
      candidates: [{
        candidate_id: 'candidate_001',
        source: 'model_candidate',
        review_status: 'pending',
        board_bbox: [0.2, 0.3, 0.4, 0.5],
        area_fraction: 0.04,
        mean_difference: 52,
        maximum_difference: 180,
      }],
    },
  });

  assert.equal(updated.visual_comparison.difference.status, 'candidate_review_required');
  assert.equal(updated.visual_comparison.difference.candidates[0].review_status, 'pending');
  assert.equal(updated.visual_comparison.difference.candidates[0].source, 'model_candidate');
  assert.equal(updated.qc_result.status, 'needs_review');
});

test('candidate review records human decision without overwriting model evidence', () => {
  const withDifference = applyDifferenceJobResult(visualCase(), {
    job_id: 'job-difference',
    status: 'succeeded',
    result: {
      schema_version: 'VISUAL-QC-DIFFERENCE-CANDIDATES-V1',
      status: 'candidate_review_required',
      candidates: [{
        candidate_id: 'candidate_001',
        source: 'model_candidate',
        review_status: 'pending',
        board_bbox: [0.2, 0.3, 0.4, 0.5],
      }],
      heatmap: { artifact_id: 'artifact-001' },
    },
  });
  const reviewed = applyCandidateReview(withDifference, {
    candidate_review_id: 'review-001',
    candidate_id: 'candidate_001',
    decision: 'confirmed',
    defect_category: 'burn_or_thermal_damage',
    label_source: 'human_annotation',
  });

  const candidate = reviewed.visual_comparison.difference.candidates[0];
  assert.equal(candidate.source, 'model_candidate');
  assert.equal(candidate.review_status, 'confirmed');
  assert.equal(candidate.human_review.label_source, 'human_annotation');
  assert.equal(reviewed.qc_result.status, 'confirmed_anomaly');
});
