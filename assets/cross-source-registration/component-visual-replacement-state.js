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
  if (
    !descriptor?.componentVisualSpecId
    || descriptor.layer !== 'body'
    || !previous
  ) {
    return { object: previous, replaced: false, fallbackReason: null };
  }

  const built = buildVisual(descriptor, detailLevel);
  if (!built.group) {
    previous.userData.visualFallbackReason = built.fallbackReason;
    return {
      object: previous,
      replaced: false,
      fallbackReason: built.fallbackReason,
    };
  }

  const next = built.group;
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
  return { object: next, replaced: true, fallbackReason: null };
}
