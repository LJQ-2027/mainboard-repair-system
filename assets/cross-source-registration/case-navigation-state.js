import {
  caseSymptomKey,
  isValidH897CaseNavigationContract,
} from './pilot-intent-state.js';

function unavailableState(reason) {
  return {
    visible: false,
    reason,
    summary: '',
    groups: [],
    activeGroup: null,
    options: [],
    activeCase: null,
    missingFieldCount: 0,
    boundary: '',
  };
}

function caseView(item) {
  return {
    caseId: item.case_id,
    symptoms: [...item.symptoms],
    symptomKey: caseSymptomKey(item.symptoms),
    finding: item.reported_finding,
    navigationScope: item.navigation_scope,
    candidateComponentIds: [...item.candidate_component_ids],
    boardOnly: item.navigation_scope === 'board_only',
    photoCount: item.photo_sha256.length,
    photoSha256: [...item.photo_sha256],
    boundary: item.boundary,
  };
}

export function buildCaseSymptomGroups(contract = {}) {
  if (!isValidH897CaseNavigationContract(contract)) return [];
  const groups = new Map();
  contract.cases.forEach((item) => {
    const key = caseSymptomKey(item.symptoms);
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        label: key.split('::').join(' / '),
        caseIds: [],
        photoHashes: new Set(),
      });
    }
    const group = groups.get(key);
    group.caseIds.push(item.case_id);
    item.photo_sha256.forEach((digest) => group.photoHashes.add(digest));
  });
  return [...groups.values()].map((group) => ({
    key: group.key,
    label: group.label,
    caseCount: group.caseIds.length,
    uniquePhotoCount: group.photoHashes.size,
  }));
}

export function buildCaseNavigationState(
  contract = {},
  preferredCaseId = null,
  preferredSymptomKey = null,
) {
  if (!isValidH897CaseNavigationContract(contract)) {
    return unavailableState('case_navigation_unavailable');
  }

  const groups = buildCaseSymptomGroups(contract);
  const preferredCase = contract.cases.find((item) => item.case_id === preferredCaseId);
  const requestedGroupKey = preferredSymptomKey || caseSymptomKey(preferredCase?.symptoms || []);
  const activeGroup = groups.find((group) => group.key === requestedGroupKey) || groups[0];
  const groupCases = contract.cases.filter(
    (item) => caseSymptomKey(item.symptoms) === activeGroup.key,
  );
  const selected = groupCases.find((item) => item.case_id === preferredCaseId) || groupCases[0];
  const options = groupCases.map((item) => ({
    caseId: item.case_id,
    label: item.case_id,
  }));
  return {
    visible: true,
    reason: null,
    summary: `${contract.case_count} 条案例 · ${contract.unique_photo_count} 个独立照片`,
    groups,
    activeGroup,
    options,
    activeCase: caseView(selected),
    missingFieldCount: Array.isArray(contract.missing_fields)
      ? contract.missing_fields.length
      : 0,
    boundary: contract.boundary || '',
  };
}
