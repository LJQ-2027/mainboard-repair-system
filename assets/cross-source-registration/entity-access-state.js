export function buildEntityAccessState(entity, activeSideId, targetSideLabel) {
  if (entity.side_id !== activeSideId) {
    const side = targetSideLabel || entity.side_id;
    return {
      tone: 'side',
      label: `位于${side}`,
      description: `切换到${side}定位该器件。`,
    };
  }
  if (entity.proxy_visibility === 'concealed_by_shield') {
    return {
      tone: 'caution',
      label: '需拆屏蔽罩',
      description: '该器件位于屏蔽罩下，检测前需拆罩或使用透视定位。',
    };
  }
  return {
    tone: 'clear',
    label: '可直接观察',
    description: '该位置在当前板面可直接定位。',
  };
}
