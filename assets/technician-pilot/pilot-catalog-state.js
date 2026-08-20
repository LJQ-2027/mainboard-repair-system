import { isValidH897CaseNavigationContract } from '../cross-source-registration/pilot-intent-state.js';

function compatibleModels(board = {}) {
  const models = Array.isArray(board.compatible_models) && board.compatible_models.length
    ? board.compatible_models
    : [board.model];
  return [...new Set(models.filter((model) => typeof model === 'string' && model.trim()))];
}

function caseCount(dataset = {}) {
  const navigation = dataset.case_navigation;
  if (!isValidH897CaseNavigationContract(navigation)) return 0;
  return navigation.cases.length;
}

function capability(dataset = {}) {
  const flowCount = Array.isArray(dataset.repair_flows) ? dataset.repair_flows.length : 0;
  const cases = caseCount(dataset);
  if (flowCount > 0) return { capabilityTier: 'reviewed_flow', flowCount, caseCount: cases };
  if (cases > 0) return { capabilityTier: 'case_navigation', flowCount, caseCount: cases };
  return { capabilityTier: 'reference_only', flowCount, caseCount: cases };
}

export function buildPilotCatalog(catalog = {}, datasetsByBoard = {}) {
  const entries = [];
  Object.entries(catalog.boards || {}).forEach(([boardKey, board]) => {
    const dataset = datasetsByBoard[boardKey];
    if (!dataset || typeof dataset !== 'object') return;
    const coverage = capability(dataset);
    compatibleModels(board).forEach((model) => {
      entries.push({
        boardKey,
        model,
        title: board.title,
        boardVersion: board.board_version,
        ...coverage,
        repairCoverageStatus: dataset.repair_coverage?.status || null,
      });
    });
  });
  return entries.sort((left, right) => left.model.localeCompare(right.model, 'en', { sensitivity: 'base' }));
}

export function resolvePilotModel(entries = [], model = '', boardKey = null) {
  const matches = entries.filter((entry) => (
    entry.model === model && (!boardKey || entry.boardKey === boardKey)
  ));
  return matches.length === 1 ? matches[0] : null;
}
