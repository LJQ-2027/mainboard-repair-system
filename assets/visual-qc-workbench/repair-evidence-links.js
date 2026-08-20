const ASSOCIATION = Object.freeze({
  related: '工程资料关联',
  possibly_related: '候选工程关联',
  not_related: '工程资料未关联',
  insufficient_evidence: '工程资料不足',
});

const VISIBILITY = Object.freeze({
  not_assessed: '可见性未评估',
  visible: '目标可见',
  not_visible: '目标不可见',
  occluded: '目标被遮挡',
});

const HEALTH = Object.freeze({
  active: '证据有效',
  stale: '证据需要复核',
  unavailable: '证据暂不可用',
});

const NEUTRAL_TONE = 'evidence-neutral';

function stateFor(binding, detail) {
  return (detail?.binding_states || []).find((state) => state.binding_id === binding?.binding_id) || {
    source_fact_superseded: false,
    replacement_fact_id: null,
    binding_superseded: false,
    replacement_binding_id: null,
  };
}

function point(value) {
  if (Array.isArray(value) && value.length === 2) return { x: value[0], y: value[1] };
  if (value && Number.isFinite(value.x) && Number.isFinite(value.y)) return { x: value.x, y: value.y };
  return null;
}

function locationFromTarget(target, detail) {
  if (!target?.side_id || detail?.health?.state !== 'active') return null;
  if (detail?.manifest?.board && (
    detail.manifest.board.board_key !== detail.board?.board_key
    || detail.manifest.board.board_id !== detail.board?.board_id
  )) return null;
  const common = {
    boardKey: detail?.board?.board_key,
    boardId: detail?.board?.board_id,
    sideId: target.side_id,
  };
  if (!common.boardKey || !common.boardId) return null;
  if (target.kind === 'whole_board') return { ...common, mode: 'whole_board' };
  if (target.kind === 'board_region' && target.region) {
    return { ...common, mode: 'region', region: structuredClone(target.region) };
  }
  const engineering = target.engineering || target;
  const status = engineering.geometry_source_status || target.geometry?.precision;
  const lowPoint = point(engineering.location?.point || target.geometry?.point);
  if (target.kind === 'designator' && status === 'low' && lowPoint) {
    return { ...common, mode: 'conservative_point', point: lowPoint };
  }
  const rectangle = engineering.location?.rectangle || target.geometry?.rectangle;
  if (target.kind === 'designator' && rectangle) {
    return { ...common, mode: 'region', region: { kind: 'normalized_rectangle', ...structuredClone(rectangle) } };
  }
  return null;
}

export function repairEvidenceLocation(binding, detail) {
  const state = stateFor(binding, detail);
  if (state.source_fact_superseded || state.binding_superseded) return null;
  return locationFromTarget(binding?.target, detail);
}

function polygonCentroid(points) {
  let twiceArea = 0;
  let centerX = 0;
  let centerY = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    const cross = current.x * next.y - next.x * current.y;
    twiceArea += cross;
    centerX += (current.x + next.x) * cross;
    centerY += (current.y + next.y) * cross;
  }
  if (Math.abs(twiceArea) < 1e-12) return null;
  return {
    x: Number((centerX / (3 * twiceArea)).toFixed(9)),
    y: Number((centerY / (3 * twiceArea)).toFixed(9)),
  };
}

export function repairEvidenceLocationCenter(location) {
  if (location?.mode === 'conservative_point') return structuredClone(location.point);
  if (location?.mode === 'region' && location.region?.kind === 'normalized_rectangle') {
    return {
      x: location.region.x + location.region.width / 2,
      y: location.region.y + location.region.height / 2,
    };
  }
  if (location?.mode === 'region' && location.region?.kind === 'normalized_polygon') {
    const points = location.region.points;
    const center = Array.isArray(points) && points.length >= 3 ? polygonCentroid(points) : null;
    if (center) return center;
  }
  return { x: 0.5, y: 0.5 };
}

export function repairEvidenceMarker(location) {
  if (location?.mode === 'conservative_point') {
    return { shape: 'point', tone: 'neutral', point: structuredClone(location.point) };
  }
  if (location?.mode !== 'region') return null;
  if (location.region?.kind === 'normalized_rectangle') {
    return {
      shape: 'rectangle', tone: 'neutral',
      rectangle: structuredClone(location.region),
    };
  }
  if (location.region?.kind === 'normalized_polygon') {
    return {
      shape: 'polygon', tone: 'neutral', points: structuredClone(location.region.points),
    };
  }
  return null;
}

export function canProjectRepairEvidenceToPhoto(location, physicalSideId) {
  return Boolean(location?.sideId && physicalSideId && location.sideId === physicalSideId);
}

export function repairEvidenceBindingView(binding, detail) {
  const state = stateFor(binding, detail);
  const location = repairEvidenceLocation(binding, detail);
  const health = detail?.health?.state;
  const association = binding?.association_status;
  const visibility = binding?.visibility_status;
  return Object.freeze({
    bindingId: binding?.binding_id || null,
    sourceLabel: '来源报告',
    sourceFactLabel: binding?.source_fact?.display?.text || '来源事实',
    associationLabel: ASSOCIATION[association] || '工程资料状态未知',
    visibilityLabel: VISIBILITY[visibility] || '可见性未知',
    healthLabel: HEALTH[health] || '证据状态未知',
    conclusionLabel: '未形成视觉缺陷结论',
    sourceFactSupersededLabel: state.source_fact_superseded ? '来源事实已被修正' : null,
    replacementFactId: state.replacement_fact_id || null,
    bindingSupersededLabel: state.binding_superseded ? '关联已被替代' : null,
    replacementBindingId: state.replacement_binding_id || null,
    canLocate: Boolean(location),
    markerMode: location?.mode || 'none',
    tone: NEUTRAL_TONE,
    colorToken: 'neutral',
  });
}

export function activeRepairEvidenceBindings(detail) {
  return (detail?.manifest?.bindings || []).filter((binding) => {
    const state = stateFor(binding, detail);
    return !state.source_fact_superseded && !state.binding_superseded;
  });
}

export function repairEvidenceBindingsForServerCase(detail, serverCaseId, { includeSuperseded = false } = {}) {
  const physicalEvidenceIds = new Set(
    (detail?.manifest?.physical_evidence || [])
      .filter((item) => item.server_case_id === serverCaseId)
      .map((item) => item.physical_evidence_id),
  );
  const bindings = includeSuperseded ? (detail?.manifest?.bindings || []) : activeRepairEvidenceBindings(detail);
  return bindings.filter(
    (binding) => physicalEvidenceIds.has(binding.physical_evidence_id),
  );
}
