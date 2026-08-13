export function buildRepairTaskCue({
  step,
  terminal,
  closed = false,
  targetDesignator = '当前器件',
  targetSideLabel = '当前板面',
} = {}) {
  if (closed) {
    return {
      phase: 'closed',
      title: '本次排查已结束',
      detail: '导出维修记录，或开始新一轮排查。',
    };
  }

  if (terminal?.kind === 'boundary') {
    return {
      phase: 'boundary',
      title: '资料已到边界',
      detail: '停止继续判断，保留当前记录并结束本次排查。',
    };
  }

  if (terminal?.kind === 'action') {
    return {
      phase: 'repair',
      title: '执行资料指定的维修处理',
      detail: '完成处理后，记录执行情况和复检结果。',
    };
  }

  const measurementCount = step?.measurements?.length || 0;
  if (measurementCount) {
    return {
      phase: 'measure',
      title: `定位 ${targetDesignator}，并记录 ${measurementCount} 项测量`,
      detail: `目标位于${targetSideLabel}。先用左侧主板图确认位置，再完成下方测量并保存。`,
    };
  }

  return {
    phase: 'inspect',
    title: `定位 ${targetDesignator}，完成本步检查`,
    detail: `目标位于${targetSideLabel}。先用左侧主板图确认位置，再按下方提示选择检查结果。`,
  };
}
