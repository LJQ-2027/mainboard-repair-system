import { hasValidReviewedPhotoNavigation } from './photo-navigation-state.js';

export function buildRegistrationViewState(registration = {}) {
  const pointMapOnly = registration.reference_mode === 'point_map_only';
  const reviewedPhotos = hasValidReviewedPhotoNavigation(registration);
  const legacyPhoto = !registration.reference_mode || registration.reference_mode === 'photo_proxy';
  const photoAvailable = reviewedPhotos || (legacyPhoto
    && Boolean(registration.proxy_image)
    && (registration.anchors?.length || 0) >= 4);
  return {
    photoAvailable: !pointMapOnly && photoAvailable,
    initialView: !pointMapOnly && photoAvailable ? 'photo' : 'pointmap',
  };
}
