export function buildSourceNote({
  view,
  registration,
  side,
  inspectionEntity = null,
  repairCoverage = null,
}) {
  if (view === 'model' && inspectionEntity) {
    const coverage = repairCoverage?.status === 'source_unavailable' ? '点位与原理图' : '点位与维修资料';
    return `${inspectionEntity.designator} 单体检视 · ${side.label} · 已关联${coverage}`;
  }
  if (view === 'model') {
    return `${side.label} · 2.5D维修视图 · ${side.audit.accepted_designators} 个点位已关联`;
  }
  if (view === 'pointmap') return registration.point_map_note;
  return registration.proxy_note || registration.point_map_note;
}
