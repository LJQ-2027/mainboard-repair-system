import { createVisualQcCase } from './visual-qc-core.js';

const clone = (value) => (typeof structuredClone === 'function'
  ? structuredClone(value)
  : JSON.parse(JSON.stringify(value)));

const TERMINAL_JOB_STATES = new Set(['succeeded', 'failed']);

export class VisualQcClientError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'VisualQcClientError';
    this.code = code;
  }
}

export function normalizeServerCaptureSession(serverSession, checklist) {
  if (!serverSession) return null;
  return {
    schema_version: serverSession.schema_version,
    session_id: serverSession.session_id,
    setup_id: serverSession.setup_id,
    expected_side_ids: clone(serverSession.expected_side_ids || []),
    captured_side_ids: clone(serverSession.captured_side_ids || []),
    pair_status: serverSession.pair_status,
    checklist: clone(checklist || serverSession.checklist || {}),
  };
}

export function createServerSyncState(visualCase) {
  const caseId = visualCase?.case_id;
  const sha256 = visualCase?.image?.sha256;
  if (!caseId || !sha256) throw new Error('Case id and image SHA-256 are required for server sync.');
  return {
    schema_version: 'VISUAL-QC-SERVER-SYNC-V1',
    status: 'local_draft',
    idempotency_key: `visual-qc:${caseId}:${sha256.slice(0, 16)}`,
    attempt_count: 0,
    progress: 0,
    server_case_id: null,
    server_image_id: null,
    job_id: null,
    job_status: null,
    last_error: null,
    updated_at: new Date().toISOString(),
  };
}

export function transitionServerSync(syncState, event) {
  const next = clone(syncState);
  next.updated_at = new Date().toISOString();
  if (event.type === 'upload_started') {
    next.status = 'uploading';
    next.attempt_count += 1;
    next.progress = 0;
    next.last_error = null;
  } else if (event.type === 'upload_progress') {
    next.status = 'uploading';
    next.progress = Math.max(0, Math.min(1, Number(event.progress) || 0));
  } else if (event.type === 'upload_accepted') {
    next.status = 'queued';
    next.progress = 1;
    next.server_case_id = event.caseId;
    next.server_image_id = event.imageId;
    next.job_id = event.jobId;
    next.job_status = event.jobStatus || 'queued';
    next.last_error = null;
  } else if (event.type === 'job_snapshot') {
    next.job_status = event.snapshot.status;
    next.status = event.snapshot.status === 'failed' ? 'failed' : event.snapshot.status;
    next.last_error = event.snapshot.error?.message || null;
  } else if (event.type === 'upload_failed') {
    next.status = 'upload_failed';
    next.last_error = event.message || 'Upload failed.';
  } else if (event.type === 'sync_interrupted') {
    next.status = 'sync_interrupted';
    next.last_error = event.message || 'Server status could not be refreshed.';
  } else {
    throw new Error(`Unsupported server sync transition: ${event.type}`);
  }
  return next;
}

async function jsonRequest(
  url,
  {
    actorId,
    actorRole = null,
    method = 'GET',
    body = null,
  } = {},
) {
  const response = await fetch(url, {
    method,
    cache: 'no-store',
    headers: {
      'X-Actor-Id': actorId,
      ...(actorRole ? { 'X-Actor-Role': actorRole } : {}),
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : null,
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(
      payload?.detail?.message || payload?.detail || `Server returned ${response.status}.`,
    );
    error.status = response.status;
    error.code = payload?.detail?.code || 'server_request_failed';
    throw error;
  }
  return payload;
}

async function blobRequest(url, { actorId, actorRole = null } = {}) {
  const response = await fetch(url, {
    cache: 'no-store',
    headers: {
      'X-Actor-Id': actorId,
      ...(actorRole ? { 'X-Actor-Role': actorRole } : {}),
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const error = new Error(
      payload?.detail?.message || payload?.detail || `Server returned ${response.status}.`,
    );
    error.status = response.status;
    error.code = payload?.detail?.code || 'server_request_failed';
    throw error;
  }
  return response.blob();
}

export function getVisualQcIdentity(apiBase, actorId, actorRole = null) {
  return jsonRequest(`${apiBase.replace(/\/$/, '')}/identity`, {
    actorId,
    actorRole,
  });
}

export function getVisualQcTrainingManifest(apiBase, actorId, actorRole = 'reviewer') {
  return jsonRequest(`${apiBase.replace(/\/$/, '')}/datasets/training-manifest`, {
    actorId,
    actorRole,
  });
}

export function getVisualQcCocoDataset(apiBase, actorId, actorRole = 'reviewer') {
  return jsonRequest(`${apiBase.replace(/\/$/, '')}/datasets/coco`, {
    actorId,
    actorRole,
  });
}

export function getVisualQcDatasetAudit(apiBase, actorId, actorRole = 'reviewer') {
  return jsonRequest(`${apiBase.replace(/\/$/, '')}/datasets/audit`, {
    actorId,
    actorRole,
  });
}

export function getVisualQcDatasetBundle(apiBase, actorId, actorRole = 'reviewer') {
  return blobRequest(`${apiBase.replace(/\/$/, '')}/datasets/bundle`, {
    actorId,
    actorRole,
  });
}

export function listVisualQcAdminCases(
  apiBase,
  actorId,
  actorRole,
  filters = {},
) {
  const page = Number(filters.page ?? 1);
  const pageSize = Number(filters.pageSize ?? 25);
  if (!Number.isInteger(page) || page < 1) {
    throw new VisualQcClientError('invalid_admin_case_page', 'Case page must be a positive integer.');
  }
  if (!Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100) {
    throw new VisualQcClientError(
      'invalid_admin_case_page_size',
      'Case page size must be between 1 and 100.',
    );
  }
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  for (const [source, target] of [
    ['boardKey', 'board_key'],
    ['sideId', 'side_id'],
    ['captureStage', 'capture_stage'],
    ['state', 'state'],
  ]) {
    if (filters[source]) query.set(target, String(filters[source]));
  }
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/admin/cases?${query}`,
    { actorId, actorRole },
  );
}

export function getVisualQcAdminCase(apiBase, actorId, actorRole, caseId) {
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/admin/cases/${encodeURIComponent(caseId)}`,
    { actorId, actorRole },
  );
}

export function getVisualQcAdminCaseImage(apiBase, actorId, actorRole, caseId) {
  return blobRequest(
    `${apiBase.replace(/\/$/, '')}/admin/cases/${encodeURIComponent(caseId)}/image`,
    { actorId, actorRole },
  );
}

function restorationError(code, message) {
  throw new VisualQcClientError(code, message);
}

async function blobSha256(blob) {
  if (!globalThis.crypto?.subtle) {
    restorationError('image_hash_unavailable', 'SHA-256 is unavailable in this browser.');
  }
  const digest = await globalThis.crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, '0'))
    .join('');
}

async function decodedBlobDimensions(blob) {
  if (Number.isInteger(blob.width) && Number.isInteger(blob.height)) {
    return { width: blob.width, height: blob.height };
  }
  if (typeof globalThis.createImageBitmap !== 'function') {
    restorationError(
      'image_decode_unavailable',
      'Image dimensions cannot be verified in this browser.',
    );
  }
  try {
    const bitmap = await globalThis.createImageBitmap(blob);
    const dimensions = { width: bitmap.width, height: bitmap.height };
    bitmap.close?.();
    return dimensions;
  } catch {
    restorationError('image_decode_failed', 'The server image cannot be decoded.');
  }
  return null;
}

function pointPair(pair) {
  return {
    board: { x: pair.board[0], y: pair.board[1] },
    image: { x: pair.image[0], y: pair.image[1] },
  };
}

export async function restoreAdminServerCase(serverCase, imageBlob) {
  if (serverCase?.schema_version !== 'VISUAL-QC-SERVER-CASE-V3') {
    restorationError(
      'unsupported_server_schema',
      'The server case schema is not supported by this workbench.',
    );
  }
  if (!serverCase.job?.result) {
    restorationError(
      'missing_server_job_result',
      'The server case has no persisted processing result.',
    );
  }
  if (!(imageBlob instanceof Blob)) {
    restorationError('invalid_server_image', 'The server case image is unavailable.');
  }
  const imageHash = await blobSha256(imageBlob);
  if (imageHash !== serverCase.image?.sha256) {
    restorationError('image_hash_mismatch', 'The server image SHA-256 does not match its case.');
  }
  const dimensions = await decodedBlobDimensions(imageBlob);
  if (
    dimensions.width !== serverCase.image?.width
    || dimensions.height !== serverCase.image?.height
  ) {
    restorationError(
      'image_dimension_mismatch',
      'The decoded server image dimensions do not match its case.',
    );
  }

  const session = serverCase.capture_session || {};
  const visualCase = createVisualQcCase({
    caseId: serverCase.case_id,
    boardKey: serverCase.board_key,
    boardId: serverCase.board_id,
    sideId: serverCase.side_id,
    captureStage: serverCase.capture_stage,
    captureSession: {
      sessionId: session.session_id,
      setupId: session.setup_id,
      expectedSideIds: session.expected_side_ids,
      capturedSideIds: session.captured_side_ids,
      checklist: session.checklist?.items,
      confirmedAt: session.checklist?.confirmed_at,
    },
    image: {
      file_name: serverCase.image.original_filename,
      mime_type: serverCase.image.mime_type,
      byte_size: serverCase.image.byte_size,
      width: serverCase.image.width,
      height: serverCase.image.height,
      sha256: serverCase.image.sha256,
      evidence_role: serverCase.evidence_role,
    },
    quality: serverCase.job.result.quality,
  });
  let restored = applyServerJobResult(visualCase, serverCase, serverCase.job);
  restored.intake = clone(serverCase.intake || { batch_id: null, entry_id: null });
  restored.server_sync.qualified_handoff = clone(serverCase.qualified_handoff);

  const registrationReview = serverCase.server_registration_review;
  if (registrationReview) {
    if (
      registrationReview.case_id !== serverCase.case_id
      || registrationReview.job_id !== serverCase.job.job_id
    ) {
      restorationError(
        'stale_registration_review',
        'The registration review does not belong to the current server case result.',
      );
    }
    restored.registration = {
      method: registrationReview.method,
      status: 'reviewed',
      matrix: clone(registrationReview.board_to_image_matrix),
      solve_anchors: (registrationReview.anchors || []).map(pointPair),
      check_points: (registrationReview.check_points || []).map(pointPair),
      error: clone(registrationReview.error || {
        count: 0,
        rms: null,
        maximum: null,
      }),
      reviewed_at: registrationReview.created_at,
      server_review_id: registrationReview.review_id,
      server_candidate: clone(serverCase.job.result.registration),
    };
    restored.server_sync.status = 'registration_reviewed';
  }

  const qcReview = serverCase.server_qc_review;
  if (qcReview) {
    if (
      !registrationReview
      || qcReview.case_id !== serverCase.case_id
      || qcReview.registration_review_id !== registrationReview.review_id
    ) {
      restorationError(
        'stale_qc_review',
        'The final QC review does not belong to the current registration review.',
      );
    }
    restored.annotations = clone(qcReview.annotations || []);
    restored.qc_result = {
      status: qcReview.qc_result,
      reviewed_at: qcReview.created_at,
    };
    restored = applyFinalQcReview(restored, qcReview);
    restored.server_sync.status = 'completed';
  }
  return { visualCase: restored, imageBlob };
}

export function getVisualQcJob(apiBase, actorId, jobId) {
  return jsonRequest(`${apiBase.replace(/\/$/, '')}/jobs/${encodeURIComponent(jobId)}`, {
    actorId,
  });
}

export function getVisualQcCaptureSession(apiBase, actorId, captureSessionId) {
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/capture-sessions/${encodeURIComponent(captureSessionId)}`,
    { actorId },
  );
}

export function retryVisualQcJob(apiBase, actorId, jobId) {
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/jobs/${encodeURIComponent(jobId)}/retry`,
    { actorId, method: 'POST' },
  );
}

export async function pollVisualQcJob({
  jobId,
  getJob,
  wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
  onSnapshot = () => {},
  intervalMilliseconds = 800,
  maximumAttempts = 150,
}) {
  for (let attempt = 0; attempt < maximumAttempts; attempt += 1) {
    const snapshot = await getJob(jobId);
    onSnapshot(snapshot);
    if (TERMINAL_JOB_STATES.has(snapshot.status)) return snapshot;
    await wait(intervalMilliseconds);
  }
  throw new Error('Visual-QC processing did not finish within the polling window.');
}

export function applyServerJobResult(visualCase, acceptedCase, jobSnapshot) {
  if (jobSnapshot?.status !== 'succeeded') {
    throw new Error('A succeeded server job is required.');
  }
  const result = jobSnapshot.result;
  if (result?.schema_version !== 'VISUAL-QC-SERVER-JOB-RESULT-V1') {
    throw new Error('Unsupported visual-QC server result.');
  }
  const registration = result.registration;
  const next = clone(visualCase);
  const baseSync = next.server_sync || createServerSyncState(next);
  next.schema_version = 'VISUAL-QC-CASE-V2';
  next.storage_scope = 'server_authoritative_with_local_draft';
  next.quality = clone(result.quality);
  if (acceptedCase.capture_session) {
    next.capture_session = normalizeServerCaptureSession(
      acceptedCase.capture_session,
    );
  }
  next.server_sync = {
    ...baseSync,
    status: registration.status === 'candidate' ? 'candidate_ready' : 'manual_required',
    progress: 1,
    server_case_id: acceptedCase.case_id,
    server_image_id: acceptedCase.image.image_id,
    job_id: jobSnapshot.job_id,
    job_status: jobSnapshot.status,
    last_error: null,
    updated_at: new Date().toISOString(),
  };
  if (registration.status === 'candidate') {
    next.registration = {
      method: registration.method,
      status: 'draft',
      matrix: clone(registration.board_to_image_matrix),
      solve_anchors: [],
      check_points: [],
      error: {
        count: registration.evidence?.inlier_count || 0,
        rms: registration.evidence?.reprojection_rms ?? null,
        maximum: registration.evidence?.reprojection_maximum ?? null,
      },
      server_candidate: clone(registration),
    };
  } else {
    next.registration = {
      method: 'reviewed_manual_four_point',
      status: 'draft',
      matrix: null,
      solve_anchors: [],
      check_points: [],
      error: { count: 0, rms: null, maximum: null },
      fallback_reason: registration.failure?.code || registration.fallback?.reason_code || 'manual_required',
    };
  }
  next.annotations = [];
  next.qc_result = {
    status: next.quality.status === 'retake' ? 'image_invalid' : 'needs_review',
    reviewed_at: null,
  };
  return next;
}

export function createRegistrationReviewDescriptor(registration) {
  if (registration?.method === 'automatic_feature_homography') {
    return { decision: 'accept_automatic', notes: '' };
  }
  if (!Array.isArray(registration?.matrix) || registration.matrix.length !== 9
    || !Array.isArray(registration.solve_anchors) || registration.solve_anchors.length !== 4) {
    throw new Error('Manual server review requires a solved four-point registration.');
  }
  return {
    decision: 'accept_manual',
    board_to_image_matrix: [...registration.matrix],
    anchors: registration.solve_anchors.map((pair) => ({
      board: [pair.board.x, pair.board.y],
      image: [pair.image.x, pair.image.y],
    })),
    check_points: (registration.check_points || []).map((pair) => ({
      board: [pair.board.x, pair.board.y],
      image: [pair.image.x, pair.image.y],
    })),
    error: clone(registration.error || {
      count: 0,
      rms: null,
      maximum: null,
    }),
    notes: '',
  };
}

export function reviewVisualQcRegistration({
  apiBase,
  actorId,
  serverCaseId,
  registration,
}) {
  const body = createRegistrationReviewDescriptor(registration);
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/cases/${encodeURIComponent(serverCaseId)}/registration-reviews`,
    { actorId, method: 'POST', body },
  );
}

export function createFinalQcReviewDescriptor(visualCase) {
  const status = visualCase?.qc_result?.status;
  if (!['no_visible_anomaly', 'confirmed_anomaly'].includes(status)) {
    throw new Error('Final QC review requires a completed human QC result.');
  }
  const annotations = visualCase.annotations || [];
  if (annotations.some(
    (annotation) => annotation.source !== 'human_annotation'
      || !['confirmed', 'not_defect'].includes(annotation.review_status),
  )) {
    throw new Error('Final QC review cannot contain unresolved annotations.');
  }
  return {
    qc_result: status,
    annotations: clone(annotations),
    notes: '',
  };
}

export function reviewVisualQcCase({
  apiBase,
  actorId,
  serverCaseId,
  visualCase,
}) {
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/cases/${encodeURIComponent(serverCaseId)}/qc-reviews`,
    {
      actorId,
      method: 'POST',
      body: createFinalQcReviewDescriptor(visualCase),
    },
  );
}

export function applyFinalQcReview(visualCase, review) {
  const next = clone(visualCase);
  next.server_qc_review = clone(review);
  return next;
}

function normalizedCaptureSetupId(value) {
  const captureSetupId = String(value || '').trim();
  if (!captureSetupId || captureSetupId.length > 128) {
    throw new Error('Capture setup id is required and must not exceed 128 characters.');
  }
  return captureSetupId;
}

export function createGoldenSampleDescriptor(visualCase, captureSetupId, confirmedNormal) {
  if (!visualCase?.server_sync?.server_case_id && !visualCase?.case_id) {
    throw new Error('A server case is required for Golden Sample approval.');
  }
  if (!confirmedNormal) {
    throw new Error('Golden Sample approval requires an explicit normal-board confirmation.');
  }
  return {
    case_id: visualCase.server_sync?.server_case_id || visualCase.case_id,
    capture_setup_id: normalizedCaptureSetupId(captureSetupId),
    confirmed_normal: true,
  };
}

export function approveGoldenSample({
  apiBase,
  actorId,
  actorRole,
  visualCase,
  captureSetupId,
  confirmedNormal,
}) {
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/golden-samples`,
    {
      actorId,
      actorRole,
      method: 'POST',
      body: createGoldenSampleDescriptor(visualCase, captureSetupId, confirmedNormal),
    },
  );
}

export function getActiveGoldenSample(
  apiBase,
  actorId,
  { boardKey, sideId, captureSetupId },
) {
  const query = new URLSearchParams({
    board_key: boardKey,
    side_id: sideId,
    capture_setup_id: normalizedCaptureSetupId(captureSetupId),
    allow_missing: 'true',
  });
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/golden-samples/active?${query}`,
    { actorId },
  );
}

export function createDifferenceJobDescriptor(captureSetupId) {
  return { capture_setup_id: normalizedCaptureSetupId(captureSetupId) };
}

export function createDifferenceJob({
  apiBase,
  actorId,
  serverCaseId,
  captureSetupId,
}) {
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/cases/${encodeURIComponent(serverCaseId)}/difference-jobs`,
    {
      actorId,
      method: 'POST',
      body: createDifferenceJobDescriptor(captureSetupId),
    },
  );
}

export function reviewDifferenceCandidate({
  apiBase,
  actorId,
  jobId,
  candidateId,
  decision,
  defectCategory = null,
  notes = '',
}) {
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/jobs/${encodeURIComponent(jobId)}/candidate-reviews`,
    {
      actorId,
      method: 'POST',
      body: {
        candidate_id: candidateId,
        decision,
        defect_category: decision === 'confirmed' ? defectCategory : null,
        notes,
      },
    },
  );
}

export async function getVisualQcArtifact(apiBase, actorId, artifactId) {
  const response = await fetch(
    `${apiBase.replace(/\/$/, '')}/artifacts/${encodeURIComponent(artifactId)}`,
    {
      cache: 'no-store',
      headers: { 'X-Actor-Id': actorId },
    },
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const error = new Error(
      payload?.detail?.message || payload?.detail || `Server returned ${response.status}.`,
    );
    error.status = response.status;
    error.code = payload?.detail?.code || 'server_request_failed';
    throw error;
  }
  return response.blob();
}

export function applyGoldenSample(visualCase, goldenSample) {
  const next = clone(visualCase);
  next.visual_comparison = {
    ...(next.visual_comparison || {}),
    capture_setup_id: goldenSample.capture_setup_id,
    golden_sample: clone(goldenSample),
    difference: next.visual_comparison?.difference || null,
  };
  return next;
}

export function applyDifferenceJobResult(visualCase, jobSnapshot) {
  if (jobSnapshot?.status !== 'succeeded'
    || jobSnapshot.result?.schema_version !== 'VISUAL-QC-DIFFERENCE-CANDIDATES-V1') {
    throw new Error('A succeeded visual-QC difference job is required.');
  }
  const next = clone(visualCase);
  next.visual_comparison = {
    ...(next.visual_comparison || {}),
    difference: {
      job_id: jobSnapshot.job_id,
      status: jobSnapshot.result.status,
      source: 'model_candidate',
      requires_human_review: true,
      evidence: clone(jobSnapshot.result.evidence || {}),
      heatmap: clone(jobSnapshot.result.heatmap || null),
      candidates: clone(jobSnapshot.result.candidates || []),
      updated_at: new Date().toISOString(),
    },
  };
  next.qc_result = {
    status: 'needs_review',
    reviewed_at: null,
  };
  return next;
}

export function applyCandidateReview(visualCase, review) {
  const next = clone(visualCase);
  const candidates = next.visual_comparison?.difference?.candidates;
  if (!Array.isArray(candidates)) throw new Error('Difference candidates are unavailable.');
  const candidate = candidates.find((item) => item.candidate_id === review.candidate_id);
  if (!candidate) throw new Error('Difference candidate was not found.');
  candidate.review_status = review.decision;
  candidate.human_review = clone(review);
  next.visual_comparison.difference.updated_at = new Date().toISOString();
  if (candidates.some((item) => item.review_status === 'confirmed')) {
    next.qc_result = {
      status: 'confirmed_anomaly',
      reviewed_at: review.created_at || new Date().toISOString(),
    };
  } else if (candidates.length && candidates.every((item) => item.review_status === 'rejected')) {
    next.qc_result = {
      status: 'no_visible_anomaly',
      reviewed_at: review.created_at || new Date().toISOString(),
    };
  } else {
    next.qc_result = {
      status: 'needs_review',
      reviewed_at: null,
    };
  }
  return next;
}
