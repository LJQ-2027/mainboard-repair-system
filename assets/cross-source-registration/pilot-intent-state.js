const INTENT_KINDS = new Set(['repair_flow', 'case_symptom', 'initial_check']);
const SHA256_PATTERN = /^[a-f0-9]{64}$/i;
const CASE_SCOPES = new Set(['board_only', 'component_candidate', 'component_group_candidate']);

function normalizeSymptom(value) {
  return String(value || '').normalize('NFKC').trim().replace(/\s+/g, ' ');
}

export function caseSymptomKey(symptoms = []) {
  return [...new Set(symptoms.map(normalizeSymptom).filter(Boolean))]
    .sort((left, right) => left.localeCompare(right, 'zh-CN'))
    .join('::');
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
    && CASE_SCOPES.has(item.navigation_scope)
    && candidateScopeValid
    && item.repair_causality_claim_allowed === false
    && item.defect_label_allowed === false
    && typeof item.boundary === 'string'
    && item.boundary.length > 0;
}

export function isValidH897CaseNavigationContract(contract = {}) {
  return contract.schema_version === 'H897-CASE-NAVIGATION-V1'
    && Array.isArray(contract.cases)
    && contract.cases.length > 0
    && contract.cases.length === contract.case_count
    && contract.cases.every(validCase);
}

function isInitialFlow(flow = {}) {
  return /precheck|initial|unknown/i.test(flow.entry_type || '');
}

function symptomOptions(dataset = {}) {
  const navigation = dataset.case_navigation;
  if (!isValidH897CaseNavigationContract(navigation)) return [];
  const groups = new Map();
  navigation.cases.forEach((item) => {
    const key = caseSymptomKey(item.symptoms);
    if (!key) return;
    if (!groups.has(key)) {
      groups.set(key, {
        kind: 'case_symptom',
        id: `case:${key}`,
        symptomKey: key,
        label: key.split('::').join(' / '),
        caseIds: [],
        photoHashes: new Set(),
      });
    }
    const group = groups.get(key);
    if (item.case_id) group.caseIds.push(item.case_id);
    (item.photo_sha256 || []).forEach((digest) => group.photoHashes.add(digest));
  });
  return [...groups.values()]
    .sort((left, right) => left.label.localeCompare(right.label, 'zh-CN'))
    .map((group) => ({
      kind: group.kind,
      id: group.id,
      symptomKey: group.symptomKey,
      label: group.label,
      caseCount: group.caseIds.length,
      uniquePhotoCount: group.photoHashes.size,
    }));
}

export function buildPilotIntentOptions(dataset = {}) {
  const flows = Array.isArray(dataset.repair_flows) ? dataset.repair_flows : [];
  const known = flows
    .filter((flow) => flow?.flow_id && flow?.entry_label && !isInitialFlow(flow))
    .sort((left, right) => (left.entry_order ?? 999) - (right.entry_order ?? 999))
    .map((flow) => ({
      kind: 'repair_flow',
      id: `flow:${flow.flow_id}`,
      flowId: flow.flow_id,
      label: flow.entry_label,
    }));
  const initialFlow = flows.find(isInitialFlow);
  return [
    ...known,
    ...symptomOptions(dataset),
    {
      kind: 'initial_check',
      id: 'initial_check',
      flowId: initialFlow?.flow_id || null,
      label: '不确定，先做初步排查',
    },
  ];
}

export function encodePilotIntent(boardEntry, option) {
  const query = new URLSearchParams({
    board: boardEntry.boardKey,
    model: boardEntry.model,
    intent: option.kind,
  });
  if (option.kind === 'repair_flow') query.set('flow', option.flowId);
  if (option.kind === 'case_symptom') query.set('symptom', option.symptomKey);
  return query;
}

function invalid(reason, legacy = false) {
  return { valid: false, legacy, reason };
}

function declaredModels(board = {}) {
  return Array.isArray(board.compatible_models) && board.compatible_models.length
    ? board.compatible_models
    : [board.model];
}

function resolvedIntent(kind, label, model, flowId = null, symptomKey = null, boundaryOnly = false) {
  return {
    valid: true,
    legacy: false,
    kind,
    label,
    model,
    flowId,
    symptomKey,
    boundaryOnly,
  };
}

export function resolvePilotIntent({ boardKey, board = {}, dataset = {}, query }) {
  const params = query instanceof URLSearchParams ? query : new URLSearchParams(query || '');
  const kind = params.get('intent');
  if (!kind) {
    const partialPilotContract = ['model', 'flow', 'symptom'].some((key) => params.has(key));
    return partialPilotContract
      ? invalid('incomplete_pilot_intent')
      : invalid('pilot_intent_absent', true);
  }
  if (!INTENT_KINDS.has(kind)) return invalid('unknown_intent');
  if (params.get('board') !== boardKey) return invalid('board_mismatch');
  const model = params.get('model');
  if (!declaredModels(board).includes(model)) return invalid('model_mismatch');
  const options = buildPilotIntentOptions(dataset);

  if (kind === 'repair_flow') {
    if (params.has('symptom')) return invalid('unexpected_symptom_parameter');
    const flowId = params.get('flow');
    const option = options.find((item) => item.kind === kind && item.flowId === flowId);
    return option
      ? resolvedIntent(kind, option.label, model, option.flowId)
      : invalid('unknown_repair_flow');
  }
  if (kind === 'case_symptom') {
    if (params.has('flow')) return invalid('unexpected_flow_parameter');
    const symptomKey = params.get('symptom');
    const option = options.find((item) => item.kind === kind && item.symptomKey === symptomKey);
    return option
      ? resolvedIntent(kind, option.label, model, null, option.symptomKey)
      : invalid('unknown_case_symptom');
  }

  if (params.has('flow') || params.has('symptom')) return invalid('unexpected_intent_parameter');

  const initial = options.find((item) => item.kind === 'initial_check');
  return resolvedIntent(
    kind,
    initial.label,
    model,
    initial.flowId,
    null,
    !initial.flowId,
  );
}
