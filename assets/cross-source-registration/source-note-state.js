export function buildSourceNote({
  view,
  registration,
  side,
  inspectionEntity = null,
}) {
  if (view === 'model' && inspectionEntity) {
    return `${inspectionEntity.designator} 单体检视 · ${side.label}注册坐标 · 维修视觉封装`;
  }
  if (view === 'model') {
    return `${side.label}点位图 · ${side.audit.accepted_designators} 个已编译位号 · 几何按来源置信度分层`;
  }
  if (view === 'pointmap') return registration.point_map_note;
  return registration.proxy_note;
}
