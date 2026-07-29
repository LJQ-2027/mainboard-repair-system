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

function repairEvidenceAccess(actorRole) {
  if (actorRole !== 'reviewer') {
    throw new VisualQcClientError(
      'repair_evidence_reviewer_required',
      'Repair-evidence links are available to data administrators only.',
    );
  }
}

function immutable(value) {
  const copied = clone(value);
  const freeze = (item) => {
    if (!item || typeof item !== 'object' || Object.isFrozen(item)) return item;
    Object.freeze(item);
    Object.values(item).forEach(freeze);
    return item;
  };
  return freeze(copied);
}

function isSafeId(value) {
  return typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value);
}

function exactKeys(value, keys) {
  return value && typeof value === 'object'
    && Object.keys(value).length === keys.length
    && keys.every((key) => Object.hasOwn(value, key));
}

function validHealth(value) {
  return exactKeys(value, ['state', 'reasons']) && ['active', 'stale', 'unavailable'].includes(value.state)
    && Array.isArray(value.reasons) && new Set(value.reasons).size === value.reasons.length
    && value.reasons.every((reason) => new Set([
      'server_case_identity_mismatch', 'image_identity_mismatch', 'qualified_handoff_mismatch',
      'registration_job_mismatch', 'registration_review_mismatch', 'board_asset_mismatch',
      'server_case_missing', 'image_missing', 'registration_job_missing',
      'registration_review_missing', 'board_asset_missing',
      'link_authority_missing', 'link_authority_mismatch',
    ]).has(reason));
}

const hash = (value) => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const finite = (value) => typeof value === 'number' && Number.isFinite(value);
const point = (value) => exactKeys(value, ['x', 'y']) && finite(value.x) && finite(value.y)
  && value.x >= 0 && value.x <= 1 && value.y >= 0 && value.y <= 1;
const fixedBoundaries = (value, includeModel = false) => exactKeys(value, [
  'visual_defect_confirmed', 'qc_annotation_created', 'golden_approved',
  'training_label_allowed', 'repair_causality_confirmed', 'repair_instruction_allowed',
  'field_accuracy_claim_allowed', ...(includeModel ? ['model_identity_resolved'] : []),
]) && Object.entries(value).every(([key, item]) => key === 'model_identity_resolved'
  ? typeof item === 'boolean' : item === false);
const repositoryPath = (value) => typeof value === 'string' && value.length > 0
  && !/[\\<>:"|?*\x00-\x1F]/.test(value) && !value.startsWith('/')
  && !value.split('/').some((part) => !part || part === '.' || part === '..');
const counts = (value) => exactKeys(value, ['association', 'visibility', 'source_fact_superseded', 'binding_superseded'])
  && exactKeys(value.association, ['related', 'possibly_related', 'not_related', 'insufficient_evidence'])
  && exactKeys(value.visibility, ['not_assessed', 'visible', 'not_visible', 'occluded'])
  && Object.values(value.association).every((item) => Number.isInteger(item) && item >= 0)
  && Object.values(value.visibility).every((item) => Number.isInteger(item) && item >= 0)
  && Number.isInteger(value.source_fact_superseded) && value.source_fact_superseded >= 0
  && Number.isInteger(value.binding_superseded) && value.binding_superseded >= 0;

function validRegion(value) {
  if (exactKeys(value, ['kind', 'x', 'y', 'width', 'height']) && value.kind === 'normalized_rectangle') {
    return finite(value.x) && finite(value.y) && finite(value.width) && finite(value.height)
      && value.x >= 0 && value.y >= 0 && value.width > 0 && value.height > 0
      && value.x + value.width <= 1 && value.y + value.height <= 1;
  }
  return exactKeys(value, ['kind', 'points']) && value.kind === 'normalized_polygon'
    && Array.isArray(value.points) && value.points.length >= 3 && value.points.length <= 256
    && value.points.every(point);
}

function validEngineeringLocation(value, geometryStatus) {
  const normalizedPoint = exactKeys(value, ['kind', 'point']) && value.kind === 'normalized_point' && point(value.point);
  const footprint = exactKeys(value, ['kind', 'rectangle']) && value.kind === 'normalized_footprint'
    && exactKeys(value.rectangle, ['x', 'y', 'width', 'height'])
    && validRegion({ kind: 'normalized_rectangle', ...value.rectangle });
  return geometryStatus === 'low' ? normalizedPoint : normalizedPoint || footprint;
}

function validEvidenceBasis(value) {
  if (exactKeys(value, ['kind']) && ['repair_case_fact', 'engineering_identity'].includes(value.kind)) return true;
  return exactKeys(value, ['kind', 'observation_code']) && value.kind === 'human_observation'
    && ['target_visible', 'target_not_visible', 'target_occluded'].includes(value.observation_code);
}

function validEvidenceBases(value, visibilityStatus, target, associationStatus) {
  if (!Array.isArray(value) || value.length < 1 || value.length > 3 || !value.every(validEvidenceBasis)) return false;

  const identities = value.map((basis) => basis.kind === 'human_observation'
    ? `${basis.kind}:${basis.observation_code}`
    : basis.kind);
  if (new Set(identities).size !== identities.length) return false;

  const humanObservations = value.filter((basis) => basis.kind === 'human_observation');
  if (visibilityStatus === 'not_assessed' && humanObservations.length) return false;

  const observationForVisibility = {
    visible: 'target_visible',
    not_visible: 'target_not_visible',
    occluded: 'target_occluded',
  }[visibilityStatus];
  if (observationForVisibility && humanObservations.some(
    (basis) => basis.observation_code !== observationForVisibility,
  )) return false;

  if (associationStatus === 'related' && target?.kind === 'designator') {
    return target.engineering?.semantic_identity_proven === true
      && value.some((basis) => basis.kind === 'repair_case_fact')
      && value.some((basis) => basis.kind === 'engineering_identity');
  }
  return true;
}

function validManifest(value) {
  if (!exactKeys(value, ['schema_version', 'link_set_id', 'revision', 'previous_manifest_sha256', 'source_origin', 'repair_case_references', 'board', 'physical_evidence', 'bindings', 'boundaries'])
    || value.schema_version !== 'VISUAL-QC-REPAIR-EVIDENCE-LINK-V1' || !isSafeId(value.link_set_id)
    || !Number.isInteger(value.revision) || value.revision < 1
    || (value.revision === 1 ? value.previous_manifest_sha256 !== null : !hash(value.previous_manifest_sha256))
    || value.source_origin !== 'codex_operator' || !fixedBoundaries(value.boundaries)
    || !Array.isArray(value.repair_case_references) || !value.repair_case_references.length
    || !Array.isArray(value.physical_evidence) || !value.physical_evidence.length
    || !Array.isArray(value.bindings) || !value.bindings.length) return false;
  const board = value.board;
  if (!exactKeys(board, ['board_key', 'board_id', 'catalog_asset', 'compiled_sources', 'board_snapshot_sha256'])
    || !isSafeId(board.board_key) || !isSafeId(board.board_id) || !hash(board.board_snapshot_sha256)
    || !exactKeys(board.catalog_asset, ['path', 'sha256', 'entry_sha256']) || !hash(board.catalog_asset.sha256) || !hash(board.catalog_asset.entry_sha256)
    || !Array.isArray(board.compiled_sources) || !board.compiled_sources.length
    || !repositoryPath(board.catalog_asset.path)
    || !board.compiled_sources.every((item) => exactKeys(item, ['kind', 'path', 'sha256'])
      && isSafeId(item.kind) && repositoryPath(item.path) && hash(item.sha256))) return false;
  const repairCaseReferenceIds = new Set();
  if (!value.repair_case_references.every((item) => {
    const good = exactKeys(item, ['repair_case_reference_id', 'repair_case_id', 'revision', 'schema_version', 'manifest_sha256', 'board_key', 'board_id'])
    && isSafeId(item.repair_case_reference_id) && isSafeId(item.repair_case_id) && Number.isInteger(item.revision) && item.revision > 0
    && item.board_key === board.board_key && item.board_id === board.board_id
    && ['VISUAL-QC-REPAIR-CASE-SOURCE-V1', 'VISUAL-QC-REPAIR-CASE-SOURCE-V2'].includes(item.schema_version) && hash(item.manifest_sha256)
    && !repairCaseReferenceIds.has(item.repair_case_reference_id);
    if (good) repairCaseReferenceIds.add(item.repair_case_reference_id);
    return good;
  })) return false;
  const evidenceIds = new Set();
  const evidenceById = new Map();
  if (!value.physical_evidence.every((item) => {
    const registration = item.registration;
    const good = exactKeys(item, ['schema_version', 'physical_evidence_id', 'server_case_id', 'intake', 'board_key', 'board_id', 'side_id', 'capture_stage', 'evidence_role', 'qualified_handoff', 'qualified_handoff_sha256', 'image_id', 'image_sha256', 'job_id', 'registration_review_id', 'registration', 'physical_evidence_snapshot_sha256'])
      && item.schema_version === 'VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1' && isSafeId(item.physical_evidence_id) && isSafeId(item.server_case_id)
      && exactKeys(item.intake, ['batch_id', 'entry_id']) && isSafeId(item.intake.batch_id) && isSafeId(item.intake.entry_id)
      && isSafeId(item.board_key) && isSafeId(item.board_id) && isSafeId(item.side_id) && isSafeId(item.capture_stage)
      && item.board_key === board.board_key && item.board_id === board.board_id
      && isSafeId(item.image_id) && isSafeId(item.job_id) && isSafeId(item.registration_review_id)
      && item.evidence_role === 'physical_capture' && hash(item.qualified_handoff_sha256) && hash(item.image_sha256) && hash(item.physical_evidence_snapshot_sha256)
      && exactKeys(item.qualified_handoff, ['schema_version', 'handoff_schema_version', 'source_package_manifest_sha256', 'archived_intake_manifest_sha256', 'acceptance_report_sha256', 'acceptance_action', 'registration_review_required', 'field_accuracy_claim_allowed'])
      && item.qualified_handoff.schema_version === 'VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1' && item.qualified_handoff.handoff_schema_version === 'VISUAL-QC-PHYSICAL-HANDOFF-V1'
      && hash(item.qualified_handoff.source_package_manifest_sha256) && hash(item.qualified_handoff.archived_intake_manifest_sha256) && hash(item.qualified_handoff.acceptance_report_sha256)
      && ['automatic_candidate_review_required', 'manual_registration_required'].includes(item.qualified_handoff.acceptance_action) && item.qualified_handoff.registration_review_required === true && item.qualified_handoff.field_accuracy_claim_allowed === false
      && registration && exactKeys(registration, ['method', 'board_to_image_matrix', 'solve_anchors', 'independent_check_points', 'error']) && registration.method === 'reviewed_manual_four_point'
      && Array.isArray(registration.board_to_image_matrix) && registration.board_to_image_matrix.length === 9 && registration.board_to_image_matrix.every(finite)
      && Array.isArray(registration.solve_anchors) && registration.solve_anchors.length === 4 && registration.solve_anchors.every((pair) => exactKeys(pair, ['board', 'image']) && point(pair.board) && point(pair.image))
      && Array.isArray(registration.independent_check_points) && registration.independent_check_points.length >= 1 && registration.independent_check_points.every((pair) => exactKeys(pair, ['board', 'image']) && point(pair.board) && point(pair.image))
      && exactKeys(registration.error, ['count', 'rms', 'maximum']) && Number.isInteger(registration.error.count) && registration.error.count >= 1 && finite(registration.error.rms) && finite(registration.error.maximum);
    if (!good || evidenceIds.has(item.physical_evidence_id)) return false;
    evidenceIds.add(item.physical_evidence_id);
    evidenceById.set(item.physical_evidence_id, item);
    return true;
  })) return false;
  const bindingIds = new Set();
  const bindingsValid = value.bindings.every((item) => {
    const target = item.target;
    const source = item.source_fact;
    const evidence = evidenceById.get(item.physical_evidence_id);
    const good = exactKeys(item, ['binding_id', 'repair_case_reference_id', 'source_fact', 'target', 'physical_evidence_id', 'association_status', 'visibility_status', 'evidence_bases', 'supersedes_binding_id', 'boundaries'])
      && isSafeId(item.binding_id) && !bindingIds.has(item.binding_id)
      && repairCaseReferenceIds.has(item.repair_case_reference_id) && evidence
      && exactKeys(source, ['kind', 'fact_id', 'display', 'fact_sha256']) && ['reported_symptom', 'finding', 'repair_action', 'outcome'].includes(source.kind) && isSafeId(source.fact_id) && hash(source.fact_sha256) && exactKeys(source.display, ['text', 'claim_status']) && typeof source.display.text === 'string' && source.display.text.trim().length > 0 && (source.kind === 'finding' ? ['reported', 'suspected', 'documented'].includes(source.display.claim_status) : source.display.claim_status === null) && (source.kind !== 'outcome' || source.fact_id === 'outcome')
      && target && ['whole_board', 'board_region', 'designator'].includes(target.kind) && isSafeId(target.side_id)
      && target.side_id === evidence.side_id
      && (target.kind === 'whole_board' ? exactKeys(target, ['kind', 'side_id']) : true)
      && (target.kind === 'board_region' ? exactKeys(target, ['kind', 'side_id', 'region']) : true)
      && (target.kind !== 'board_region' || validRegion(target.region))
      && (target.kind !== 'designator' || (exactKeys(target, ['kind', 'side_id', 'engineering']) && target.engineering && exactKeys(target.engineering, ['component_id', 'designator', 'technician_category', 'location', 'evidence_descriptors', 'geometry_source_status', 'semantic_identity_proven', 'engineering_snapshot_sha256']) && isSafeId(target.engineering.component_id) && isSafeId(target.engineering.designator) && isSafeId(target.engineering.technician_category) && Array.isArray(target.engineering.evidence_descriptors) && target.engineering.evidence_descriptors.length >= 1 && target.engineering.evidence_descriptors.every((descriptor) => typeof descriptor === 'string' && descriptor.trim()) && ['high', 'medium', 'low'].includes(target.engineering.geometry_source_status) && validEngineeringLocation(target.engineering.location, target.engineering.geometry_source_status) && typeof target.engineering.semantic_identity_proven === 'boolean' && hash(target.engineering.engineering_snapshot_sha256)))
      && ['related', 'possibly_related', 'not_related', 'insufficient_evidence'].includes(item.association_status)
      && ['not_assessed', 'visible', 'not_visible', 'occluded'].includes(item.visibility_status)
      && validEvidenceBases(item.evidence_bases, item.visibility_status, target, item.association_status)
      && (item.supersedes_binding_id === null || isSafeId(item.supersedes_binding_id)) && fixedBoundaries(item.boundaries, true);
    if (good) bindingIds.add(item.binding_id);
    return Boolean(good);
  });
  if (!bindingsValid) return false;
  const bindingIndex = new Map(
    value.bindings.map((item, index) => [item.binding_id, index]),
  );
  const superseded = new Set();
  for (const [index, item] of value.bindings.entries()) {
    if (item.supersedes_binding_id === null) continue;
    const targetIndex = bindingIndex.get(item.supersedes_binding_id);
    if (targetIndex === undefined || targetIndex >= index
      || superseded.has(item.supersedes_binding_id)) return false;
    superseded.add(item.supersedes_binding_id);
  }
  return true;
}

function expectedRepairEvidenceCounts(manifest, bindingStates) {
  const association = {
    related: 0, possibly_related: 0, not_related: 0, insufficient_evidence: 0,
  };
  const visibility = {
    not_assessed: 0, visible: 0, not_visible: 0, occluded: 0,
  };
  for (const binding of manifest.bindings) {
    association[binding.association_status] += 1;
    visibility[binding.visibility_status] += 1;
  }
  return {
    association,
    visibility,
    source_fact_superseded: bindingStates.filter((item) => item.source_fact_superseded).length,
    binding_superseded: bindingStates.filter((item) => item.binding_superseded).length,
  };
}

function sameRepairEvidenceCounts(actual, expected) {
  return ['related', 'possibly_related', 'not_related', 'insufficient_evidence']
    .every((key) => actual.association[key] === expected.association[key])
    && ['not_assessed', 'visible', 'not_visible', 'occluded']
      .every((key) => actual.visibility[key] === expected.visibility[key])
    && actual.source_fact_superseded === expected.source_fact_superseded
    && actual.binding_superseded === expected.binding_superseded;
}

function validSummary(value) {
  return value && typeof value === 'object'
    && isSafeId(value.link_set_id)
    && Number.isInteger(value.revision) && value.revision >= 1
    && typeof value.manifest_sha256 === 'string' && /^[0-9a-f]{64}$/.test(value.manifest_sha256)
    && isSafeId(value.repair_case_id)
    && isSafeId(value.board?.board_key) && isSafeId(value.board?.board_id)
    && Array.isArray(value.server_case_ids) && value.server_case_ids.length > 0
    && value.server_case_ids.every(isSafeId)
    && validHealth(value.health)
    && counts(value.counts)
    && typeof value.imported_at === 'string' && value.imported_at.length > 0;
}

function validBindingState(value) {
  return exactKeys(value, [
    'binding_id', 'source_fact_superseded', 'replacement_fact_id',
    'binding_superseded', 'replacement_binding_id',
  ]) && isSafeId(value.binding_id)
    && typeof value.source_fact_superseded === 'boolean'
    && (value.replacement_fact_id === null || isSafeId(value.replacement_fact_id))
    && value.source_fact_superseded === (value.replacement_fact_id !== null)
    && typeof value.binding_superseded === 'boolean'
    && (value.replacement_binding_id === null || isSafeId(value.replacement_binding_id))
    && value.binding_superseded === (value.replacement_binding_id !== null);
}

function validateRepairEvidenceList(payload) {
  if (!exactKeys(payload, ['schema_version', 'links'])
    || payload?.schema_version !== 'VISUAL-QC-REPAIR-EVIDENCE-LINK-LIST-V1'
    || !Array.isArray(payload.links)
    || !payload.links.every(validSummary)) {
    throw new VisualQcClientError('invalid_repair_evidence_list', 'The repair-evidence list response is invalid.');
  }
  return immutable(payload);
}

function validateRepairEvidenceDetail(payload) {
  if (!exactKeys(payload, [
    'schema_version', 'link_set_id', 'revision', 'manifest_sha256', 'repair_case_id',
    'board', 'server_case_ids', 'counts', 'health', 'imported_at', 'binding_states', 'manifest',
  ]) || payload?.schema_version !== 'VISUAL-QC-REPAIR-EVIDENCE-LINK-DETAIL-V1'
    || !validSummary(payload)
    || !Array.isArray(payload.binding_states) || !payload.binding_states.every(validBindingState)
    || !validManifest(payload.manifest)
    || payload.manifest?.link_set_id !== payload.link_set_id
    || payload.manifest?.revision !== payload.revision
    || !Array.isArray(payload.manifest?.bindings)) {
    throw new VisualQcClientError('invalid_repair_evidence_detail', 'The repair-evidence detail response is invalid.');
  }
  const bindingIds = payload.manifest.bindings.map((item) => item.binding_id);
  const stateIds = payload.binding_states.map((item) => item.binding_id);
  const evidenceCaseIds = payload.manifest.physical_evidence.map((item) => item.server_case_id);
  const repairCaseIds = new Set(
    payload.manifest.repair_case_references.map((item) => item.repair_case_id),
  );
  const expectedCounts = expectedRepairEvidenceCounts(payload.manifest, payload.binding_states);
  if (new Set(stateIds).size !== stateIds.length
    || bindingIds.length !== stateIds.length
    || bindingIds.some((id) => !stateIds.includes(id))
    || new Set(evidenceCaseIds).size !== evidenceCaseIds.length
    || evidenceCaseIds.length !== payload.server_case_ids.length
    || evidenceCaseIds.some((id) => !payload.server_case_ids.includes(id))
    || repairCaseIds.size !== 1 || !repairCaseIds.has(payload.repair_case_id)
    || payload.board.board_key !== payload.manifest.board.board_key
    || payload.board.board_id !== payload.manifest.board.board_id
    || !sameRepairEvidenceCounts(payload.counts, expectedCounts)) {
    throw new VisualQcClientError('invalid_repair_evidence_detail', 'The repair-evidence detail response is invalid.');
  }
  return immutable(payload);
}

export function listRepairEvidenceLinks(apiBase, actorId, actorRole, filters = {}) {
  repairEvidenceAccess(actorRole);
  const allowed = new Set(['serverCaseId', 'repairCaseId']);
  if (Object.keys(filters).some((key) => !allowed.has(key))) {
    throw new VisualQcClientError('invalid_repair_evidence_filter', 'Unsupported repair-evidence filter.');
  }
  const query = new URLSearchParams();
  if (filters.serverCaseId) query.set('server_case_id', String(filters.serverCaseId));
  if (filters.repairCaseId) query.set('repair_case_id', String(filters.repairCaseId));
  const suffix = query.size ? `?${query}` : '';
  return jsonRequest(`${apiBase.replace(/\/$/, '')}/admin/repair-evidence-links${suffix}`, {
    actorId,
    actorRole,
  }).then(validateRepairEvidenceList);
}

export function getRepairEvidenceLinkDetail(apiBase, actorId, actorRole, linkSetId, revision) {
  repairEvidenceAccess(actorRole);
  if (typeof linkSetId !== 'string' || !linkSetId || !Number.isInteger(revision) || revision < 1) {
    throw new VisualQcClientError('invalid_repair_evidence_identity', 'Repair-evidence link identity is invalid.');
  }
  return jsonRequest(
    `${apiBase.replace(/\/$/, '')}/admin/repair-evidence-links/${encodeURIComponent(linkSetId)}/revisions/${encodeURIComponent(revision)}`,
    { actorId, actorRole },
  ).then(validateRepairEvidenceDetail);
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
