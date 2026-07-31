const CLEANUP_WARNING = 'previous_visual_cleanup_failed';

function attemptDispose(resource) {
  try {
    resource?.dispose?.();
    return 0;
  } catch {
    return 1;
  }
}

function attemptDetach(object) {
  try {
    object?.removeFromParent?.();
    return 0;
  } catch {
    return 1;
  }
}

export function disposeGenericObjectResources(object) {
  const geometries = new Set();
  const materials = new Set();
  const textures = new Set();
  let failureCount = 0;

  try {
    object?.traverse?.((child) => {
      if (child.geometry) geometries.add(child.geometry);
      const childMaterials = Array.isArray(child.material) ? child.material : [child.material];
      childMaterials.filter(Boolean).forEach((material) => {
        materials.add(material);
        if (material.map) textures.add(material.map);
      });
      Object.values(child.userData?.labelTextures || {}).forEach((texture) => {
        if (texture) textures.add(texture);
      });
    });
  } catch {
    failureCount += 1;
  }

  geometries.forEach((geometry) => {
    failureCount += attemptDispose(geometry);
  });
  textures.forEach((texture) => {
    failureCount += attemptDispose(texture);
  });
  materials.forEach((material) => {
    failureCount += attemptDispose(material);
  });
  failureCount += attemptDetach(object);

  return {
    geometries: geometries.size,
    textures: textures.size,
    materials: materials.size,
    failureCount,
    cleanupWarning: failureCount ? CLEANUP_WARNING : null,
  };
}

export function detachObjectAfterOwnedDisposal(object, cleanupWarning = null) {
  const failureCount = attemptDetach(object);
  return {
    failureCount,
    cleanupWarning: cleanupWarning || (failureCount ? CLEANUP_WARNING : null),
  };
}
