function mergeDefined(target, source) {
  Object.entries(source || {}).forEach(([key, value]) => {
    if (value !== undefined) target[key] = value;
  });
}

export function replaceComponentVisualState({
  componentId,
  detailLevel,
  descriptor,
  previous,
  buildVisual,
  addObject,
  disposeObject,
  captureMaterialState,
  renderObjects,
  meshes,
}) {
  const currentDetailLevel = previous?.userData?.visualDetailLevel;
  if (!previous) {
    return {
      object: previous,
      replaced: false,
      detailCommitted: false,
      currentDetailLevel,
      fallbackReason: null,
    };
  }
  if (!descriptor?.componentVisualSpecId) {
    return {
      object: previous,
      replaced: false,
      detailCommitted: true,
      currentDetailLevel,
      fallbackReason: null,
    };
  }
  if (descriptor.layer !== 'body') {
    return {
      object: previous,
      replaced: false,
      detailCommitted: currentDetailLevel === detailLevel,
      currentDetailLevel,
      fallbackReason: null,
    };
  }

  const built = buildVisual(descriptor, detailLevel);
  if (!built.group) {
    previous.userData.visualFallbackReason = built.fallbackReason;
    return {
      object: previous,
      replaced: false,
      detailCommitted: currentDetailLevel === detailLevel,
      currentDetailLevel,
      fallbackReason: built.fallbackReason,
    };
  }

  const next = built.group;
  const nextDetailLevel = next.userData.visualDetailLevel;
  if (nextDetailLevel !== detailLevel) {
    disposeObject(next);
    previous.userData.visualFallbackReason = 'visual_detail_mismatch';
    return {
      object: previous,
      replaced: false,
      detailCommitted: currentDetailLevel === detailLevel,
      currentDetailLevel,
      fallbackReason: 'visual_detail_mismatch',
    };
  }
  const nextVisualData = { ...next.userData };
  next.position.copy(previous.position);
  next.rotation.copy(previous.rotation);
  next.scale.copy(previous.scale);
  next.visible = previous.visible;
  next.renderOrder = previous.renderOrder;
  next.userData = { ...previous.userData };
  mergeDefined(next.userData, nextVisualData);
  next.userData.componentId = componentId;
  next.userData.visualFallbackReason = built.fallbackReason || '';
  next.traverse((child) => {
    child.userData.componentId = componentId;
    child.renderOrder = previous.renderOrder;
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });
  captureMaterialState(next);
  addObject(next);
  renderObjects.set(componentId, next);
  if (descriptor.selectable) meshes.set(componentId, next);
  disposeObject(previous);
  return {
    object: next,
    replaced: true,
    detailCommitted: true,
    currentDetailLevel: nextDetailLevel,
    fallbackReason: null,
  };
}
