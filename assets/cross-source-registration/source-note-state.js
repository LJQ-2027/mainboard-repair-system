export function buildSourceNote({
  view,
  registration,
  side,
  inspectionEntity = null,
}) {
  if (view === 'model' && inspectionEntity) {
    return `${inspectionEntity.designator} 单体检视 · ${side.label} · 已关联点位与维修资料`;
  }
  if (view === 'model') {
    return `${side.label} · 2.5D维修视图 · ${side.audit.accepted_designators} 个点位已关联`;
  }
  if (view === 'pointmap') return registration.point_map_note;
  return registration.proxy_note;
}
