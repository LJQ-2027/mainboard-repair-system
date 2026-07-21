export const ADMIN_CASE_STATE_LABELS = Object.freeze({
  processing: '处理中',
  processing_failed: '处理失败',
  manual_registration_required: '需人工配准',
  registration_review_required: '待确认配准',
  ready_for_human_qc: '待人工 QC',
  completed: '已完成',
});

const CAPTURE_STAGES = new Set(['golden_reference', 'before_repair', 'after_repair']);

export function normalizeAdminCaseFilters(filters = {}) {
  const state = String(filters.state || '').trim();
  const captureStage = String(filters.captureStage || '').trim();
  return {
    boardKey: String(filters.boardKey || '').trim(),
    sideId: String(filters.sideId || '').trim(),
    captureStage: CAPTURE_STAGES.has(captureStage) ? captureStage : '',
    state: Object.hasOwn(ADMIN_CASE_STATE_LABELS, state) ? state : '',
  };
}

export function clampAdminCasePage(page, total, pageSize) {
  const safeSize = Math.max(1, Math.min(100, Number(pageSize) || 25));
  const maximum = Math.max(1, Math.ceil(Math.max(0, Number(total) || 0) / safeSize));
  return Math.max(1, Math.min(maximum, Math.trunc(Number(page) || 1)));
}

export function buildVisualQcAccessState(role) {
  const dataAdmin = role === 'reviewer';
  return {
    roleLabel: dataAdmin ? '数据管理员' : '只读',
    imageIntake: dataAdmin,
    proxyLoading: dataAdmin,
    serverSync: dataAdmin,
    goldenManagement: dataAdmin,
    serverCatalog: dataAdmin,
    datasetExport: dataAdmin,
  };
}
