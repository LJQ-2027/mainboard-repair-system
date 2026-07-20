import test from 'node:test';
import assert from 'node:assert/strict';

import {
  applyServerJobResult,
  createRegistrationReviewDescriptor,
  createServerSyncState,
  createUploadDescriptor,
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
    sha256: 'a'.repeat(64),
  });
  assert.equal(descriptor.idempotencyKey, createServerSyncState(visualCase()).idempotency_key);
});

test('automatic result remains a draft candidate until server review succeeds', () => {
  const accepted = {
    case_id: 'vqc_server_case',
    image: { image_id: 'img_server' },
    job: { job_id: 'job_server', status: 'queued' },
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

  assert.equal(updated.storage_scope, 'server_authoritative_with_local_draft');
  assert.equal(updated.server_sync.status, 'candidate_ready');
  assert.equal(updated.registration.method, 'automatic_feature_homography');
  assert.equal(updated.registration.status, 'draft');
  assert.deepEqual(updated.registration.matrix, job.result.registration.board_to_image_matrix);
  assert.equal(updated.quality.score, 91);
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
  });

  assert.deepEqual(automatic, { decision: 'accept_automatic', notes: '' });
  assert.equal(manual.decision, 'accept_manual');
  assert.deepEqual(manual.anchors[2], { board: [1, 1], image: [1, 1] });
  assert.equal(manual.board_to_image_matrix.length, 9);
});
