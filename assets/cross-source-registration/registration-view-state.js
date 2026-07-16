export function buildRegistrationViewState(registration = {}) {
  const pointMapOnly = registration.reference_mode === 'point_map_only';
  return {
    photoAvailable: !pointMapOnly
      && Boolean(registration.proxy_image)
      && (registration.anchors?.length || 0) >= 4,
    initialView: pointMapOnly ? 'pointmap' : 'photo',
  };
}
