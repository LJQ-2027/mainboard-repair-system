export function buildRepairCoverageState(dataset = {}) {
  if ((dataset.repair_flows || []).length) {
    return {
      available: true,
      eyebrow: '维修入口',
      title: '选择故障现象',
      note: '',
    };
  }
  const coverage = dataset.repair_coverage;
  const supportedBoundary = coverage?.status === 'source_unavailable'
    || (coverage?.status === 'source_available_pending_review' && coverage.source);
  if (!supportedBoundary || !coverage.title || !coverage.note) {
    throw new Error('Repair coverage boundary is required when no reviewed flow exists.');
  }
  return {
    available: false,
    eyebrow: '资料状态',
    title: coverage.title,
    note: coverage.note,
  };
}
