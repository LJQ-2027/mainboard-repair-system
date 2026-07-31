function errorCopy(error) {
  if (!error || !Number.isFinite(error.rms) || !Number.isFinite(error.maximum)) return '误差不可用';
  return `RMS ${error.rms.toFixed(3)} · 最大 ${error.maximum.toFixed(3)}`;
}

function revisionLabel(value) {
  return typeof value === 'string' ? value.match(/V\d+(?:\.\d+)+(?:[A-Z])?/i)?.[0] : null;
}

export function buildPhysicalRegistrationState(evidence, activeSideId) {
  if (!evidence || !Array.isArray(evidence.images)) return { visible: false };
  const items = evidence.images
    .filter((item) => item.side_id === activeSideId && item.registration_status === 'reviewed_manual_registration')
    .map((item, index) => ({
      id: item.sha256,
      label: `审核图 ${index + 1}`,
      hash: item.sha256.slice(0, 8),
      error: errorCopy(item.registration_review?.error),
      annotation: item.source_annotation_present ? '含来源标注' : '无来源标注',
    }));
  const sideNumber = activeSideId?.match(/(\d+)$/)?.[1];
  const physicalRevision = revisionLabel(evidence.physical_board_revision || evidence.board_revision);
  const engineeringRevision = revisionLabel(evidence.engineering_board_revision);
  const variantBoundary = physicalRevision && engineeringRevision
    ? `实拍 ${physicalRevision} 与工程 ${engineeringRevision} 仍有版本边界；`
    : '';
  return {
    visible: true,
    title: sideNumber ? `第${sideNumber}面实拍配准` : '当前板面实拍配准',
    summary: items.length ? `已审核 ${items.length} 张` : '暂无该板面审核记录',
    items,
    boundary: `仅用于板级坐标关联；${variantBoundary}不是 Golden、缺陷或训练标签，不生成维修因果；未声明工业合格阈值`,
  };
}
