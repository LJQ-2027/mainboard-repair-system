const SCHEMA_VERSION = 'H897-CASE-NAVIGATION-V1';
const SHA256_PATTERN = /^[a-f0-9]{64}$/i;
const SCOPES = new Set(['board_only', 'component_candidate', 'component_group_candidate']);

function unavailableState(reason) {
  return {
    visible: false,
    reason,
    summary: '',
    options: [],
    activeCase: null,
    missingFieldCount: 0,
    boundary: '',
  };
}

function validCase(item = {}) {
  const candidateIds = Array.isArray(item.candidate_component_ids)
    ? item.candidate_component_ids
    : null;
  const candidateScopeValid = item.navigation_scope === 'board_only'
    ? candidateIds?.length === 0
    : Boolean(candidateIds?.length);
  return Boolean(item.case_id)
    && Array.isArray(item.symptoms)
    && item.symptoms.length > 0
    && typeof item.reported_finding === 'string'
    && Array.isArray(item.photo_sha256)
    && item.photo_sha256.every((digest) => SHA256_PATTERN.test(digest))
    && SCOPES.has(item.navigation_scope)
    && candidateScopeValid
    && item.repair_causality_claim_allowed === false
    && item.defect_label_allowed === false
    && typeof item.boundary === 'string'
    && item.boundary.length > 0;
}

function caseView(item) {
  return {
    caseId: item.case_id,
    symptoms: [...item.symptoms],
    finding: item.reported_finding,
    navigationScope: item.navigation_scope,
    candidateComponentIds: [...item.candidate_component_ids],
    boardOnly: item.navigation_scope === 'board_only',
    photoCount: item.photo_sha256.length,
    photoSha256: [...item.photo_sha256],
    boundary: item.boundary,
  };
}

export function buildCaseNavigationState(contract = {}, preferredCaseId = null) {
  if (
    contract.schema_version !== SCHEMA_VERSION
    || !Array.isArray(contract.cases)
    || !contract.cases.length
    || contract.cases.length !== contract.case_count
    || !contract.cases.every(validCase)
  ) return unavailableState('case_navigation_unavailable');

  const selected = contract.cases.find((item) => item.case_id === preferredCaseId)
    || contract.cases[0];
  const options = contract.cases.map((item) => ({
    caseId: item.case_id,
    label: `${item.case_id} · ${item.symptoms.join(' / ')}`,
  }));
  return {
    visible: true,
    reason: null,
    summary: `${contract.case_count} 条案例 · ${contract.unique_photo_count} 个独立照片`,
    options,
    activeCase: caseView(selected),
    missingFieldCount: Array.isArray(contract.missing_fields)
      ? contract.missing_fields.length
      : 0,
    boundary: contract.boundary || '',
  };
}
