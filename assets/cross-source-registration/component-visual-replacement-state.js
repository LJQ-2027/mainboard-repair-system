function mergeDefined(target, source) {
  Object.entries(source || {}).forEach(([key, value]) => {
    if (value !== undefined) target[key] = value;
  });
}

function setFallbackReason(object, fallbackReason) {
  try {
    object.userData.visualFallbackReason = fallbackReason;
  } catch {
    // The replacement result remains authoritative when metadata is immutable.
  }
}

function failureResult(previous, currentDetailLevel, fallbackReason) {
  setFallbackReason(previous, fallbackReason);
  return {
    object: previous,
    replaced: false,
    detailCommitted: false,
    currentDetailLevel,
    fallbackReason,
    cleanupWarning: null,
  };
}

function safelyRemoveObject(object, removeObject) {
  try {
    if (removeObject) removeObject(object);
    else object?.removeFromParent?.();
  } catch {
    try {
      object?.removeFromParent?.();
    } catch {
      // Rollback is best effort for foreign scene implementations.
    }
  }
}

function safelyDisposeObject(object, disposeObject) {
  try {
    const result = disposeObject(object);
    return {
      cleanupWarning: result?.cleanupWarning || null,
    };
  } catch {
    return {
      cleanupWarning: 'previous_visual_cleanup_failed',
    };
  }
}

function restoreMapEntry(map, key, hadEntry, value) {
  try {
    if (hadEntry) map.set(key, value);
    else map.delete(key);
  } catch {
    if (!(map instanceof Map)) return;
    try {
      if (hadEntry) Map.prototype.set.call(map, key, value);
      else Map.prototype.delete.call(map, key);
    } catch {
      // Foreign map implementations may make rollback impossible.
    }
  }
}

export function replaceComponentVisualState({
  componentId,
  detailLevel,
  descriptor,
  previous,
  buildVisual,
  addObject,
  removeObject,
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
      cleanupWarning: null,
    };
  }
  if (!descriptor?.componentVisualSpecId) {
    return {
      object: previous,
      replaced: false,
      detailCommitted: true,
      currentDetailLevel,
      fallbackReason: null,
      cleanupWarning: null,
    };
  }
  if (descriptor.layer !== 'body') {
    return {
      object: previous,
      replaced: false,
      detailCommitted: currentDetailLevel === detailLevel,
      currentDetailLevel,
      fallbackReason: null,
      cleanupWarning: null,
    };
  }

  let built;
  try {
    built = buildVisual(descriptor, detailLevel);
  } catch {
    return failureResult(previous, currentDetailLevel, 'visual_replacement_build_failed');
  }
  if (!built.group) {
    setFallbackReason(previous, built.fallbackReason);
    return {
      object: previous,
      replaced: false,
      detailCommitted: currentDetailLevel === detailLevel,
      currentDetailLevel,
      fallbackReason: built.fallbackReason,
      cleanupWarning: null,
    };
  }

  const next = built.group;
  const nextDetailLevel = next.userData.visualDetailLevel;
  if (nextDetailLevel !== detailLevel) {
    safelyDisposeObject(next, disposeObject);
    setFallbackReason(previous, 'visual_detail_mismatch');
    return {
      object: previous,
      replaced: false,
      detailCommitted: currentDetailLevel === detailLevel,
      currentDetailLevel,
      fallbackReason: 'visual_detail_mismatch',
      cleanupWarning: null,
    };
  }
  try {
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
  } catch {
    safelyDisposeObject(next, disposeObject);
    return failureResult(previous, currentDetailLevel, 'visual_replacement_prepare_failed');
  }

  try {
    captureMaterialState(next);
  } catch {
    safelyDisposeObject(next, disposeObject);
    return failureResult(previous, currentDetailLevel, 'visual_replacement_capture_failed');
  }

  try {
    addObject(next);
  } catch {
    safelyRemoveObject(next, removeObject);
    safelyDisposeObject(next, disposeObject);
    return failureResult(previous, currentDetailLevel, 'visual_replacement_add_failed');
  }

  const renderHadPrevious = renderObjects.has(componentId);
  const renderPrevious = renderObjects.get(componentId);
  const meshesHadPrevious = meshes.has(componentId);
  const meshesPrevious = meshes.get(componentId);
  try {
    renderObjects.set(componentId, next);
    if (descriptor.selectable) meshes.set(componentId, next);
  } catch {
    restoreMapEntry(renderObjects, componentId, renderHadPrevious, renderPrevious);
    restoreMapEntry(meshes, componentId, meshesHadPrevious, meshesPrevious);
    safelyRemoveObject(next, removeObject);
    safelyDisposeObject(next, disposeObject);
    return failureResult(previous, currentDetailLevel, 'visual_replacement_commit_failed');
  }

  const { cleanupWarning } = safelyDisposeObject(previous, disposeObject);
  next.userData.visualCleanupWarning = cleanupWarning || '';
  return {
    object: next,
    replaced: true,
    detailCommitted: true,
    currentDetailLevel: nextDetailLevel,
    fallbackReason: null,
    cleanupWarning,
  };
}
