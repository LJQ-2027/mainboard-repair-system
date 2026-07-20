const clone = (value) => (typeof structuredClone === 'function'
  ? structuredClone(value)
  : JSON.parse(JSON.stringify(value)));

const TERMINAL_JOB_STATES = new Set(['succeeded', 'failed']);

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

export function createUploadDescriptor(visualCase, syncState) {
  if (!visualCase || !syncState?.idempotency_key) {
    throw new Error('Visual case and server sync state are required.');
  }
  return {
    idempotencyKey: syncState.idempotency_key,
    fields: {
      board_key: visualCase.board_key,
      side_id: visualCase.side_id,
      capture_stage: visualCase.capture_stage,
      evidence_role: visualCase.image?.evidence_role === 'physical_capture'
        ? 'physical_capture'
        : 'service_manual_proxy',
      sha256: visualCase.image?.sha256,
    },
  };
}

function parseResponse(xhr) {
  let body = null;
  try {
    body = JSON.parse(xhr.responseText || 'null');
  } catch {
    body = null;
  }
  if (xhr.status >= 200 && xhr.status < 300) return body;
  const message = body?.detail?.message || body?.detail || `Server returned ${xhr.status}.`;
  const error = new Error(message);
  error.status = xhr.status;
  error.code = body?.detail?.code || 'server_request_failed';
  throw error;
}

export function uploadVisualQcCase({
  apiBase,
  actorId,
  visualCase,
  imageBlob,
  syncState,
  onProgress = () => {},
  XMLHttpRequestClass = globalThis.XMLHttpRequest,
}) {
  if (!XMLHttpRequestClass) throw new Error('XMLHttpRequest is unavailable.');
  const descriptor = createUploadDescriptor(visualCase, syncState);
  const form = new FormData();
  Object.entries(descriptor.fields).forEach(([key, value]) => form.append(key, value));
  form.append('file', imageBlob, visualCase.image.file_name || 'board-image');

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequestClass();
    xhr.open('POST', `${apiBase.replace(/\/$/, '')}/cases`);
    xhr.setRequestHeader('X-Actor-Id', actorId);
    xhr.setRequestHeader('Idempotency-Key', descriptor.idempotencyKey);
    xhr.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable) return;
      onProgress(event.loaded / event.total);
    });
    xhr.addEventListener('load', () => {
      try {
        resolve(parseResponse(xhr));
      } catch (error) {
        reject(error);
      }
    });
    xhr.addEventListener('error', () => reject(new Error('Network upload failed.')));
    xhr.addEventListener('abort', () => reject(new Error('Upload was cancelled.')));
    xhr.send(form);
  });
}

async function jsonRequest(url, { actorId, method = 'GET', body = null } = {}) {
  const response = await fetch(url, {
    method,
    cache: 'no-store',
    headers: {
      'X-Actor-Id': actorId,
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

export function getVisualQcJob(apiBase, actorId, jobId) {
  return jsonRequest(`${apiBase.replace(/\/$/, '')}/jobs/${encodeURIComponent(jobId)}`, {
    actorId,
  });
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
  next.storage_scope = 'server_authoritative_with_local_draft';
  next.quality = clone(result.quality);
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
