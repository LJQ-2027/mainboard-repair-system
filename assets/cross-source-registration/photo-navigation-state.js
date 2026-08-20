const PHOTO_MODE = 'reviewed_physical_photo_navigation';
const SHA256_PATTERN = /^[a-f0-9]{64}$/i;
const SUPPORTED_SCHEMAS = new Set([
  'XK67J-PHOTO-NAVIGATION-V1',
  'H897-PHOTO-NAVIGATION-V1',
]);

function isReviewedPhoto(photo = {}) {
  return Boolean(photo.photo_id)
    && Boolean(photo.side_id)
    && Boolean(photo.label)
    && Boolean(photo.asset_path)
    && SHA256_PATTERN.test(photo.source_sha256 || '')
    && SHA256_PATTERN.test(photo.derivative_sha256 || '')
    && photo.registration_review_status === 'reviewed'
    && Array.isArray(photo.board_to_image_matrix)
    && photo.board_to_image_matrix.length === 9
    && photo.board_to_image_matrix.every(Number.isFinite);
}

export function hasValidReviewedPhotoNavigation(registration = {}) {
  if (!hasPhotoNavigationContract(registration)) return false;
  const navigation = registration.photo_navigation || {};
  return navigation.photos.some(isReviewedPhoto);
}

function hasPhotoNavigationContract(registration = {}) {
  const navigation = registration.photo_navigation || {};
  return registration.reference_mode === PHOTO_MODE
    && SUPPORTED_SCHEMAS.has(navigation.schema_version)
    && Array.isArray(navigation.photos);
}

export function resolveReviewedPhotoIdBySourceHash(registration = {}, sideId, sourceSha256) {
  if (!hasPhotoNavigationContract(registration) || !SHA256_PATTERN.test(sourceSha256 || '')) return null;
  const normalizedHash = sourceSha256.toLowerCase();
  const match = registration.photo_navigation.photos.find((photo) => (
    photo.side_id === sideId
    && isReviewedPhoto(photo)
    && photo.source_sha256.toLowerCase() === normalizedHash
  ));
  return match?.photo_id || null;
}

function unavailableState(sideId, reason) {
  return {
    available: false,
    reason,
    sideId,
    items: [],
    selectorVisible: false,
    activePhoto: null,
    assetPath: null,
    matrix: null,
    sourceAnnotationPresent: false,
    boundaryCopy: '当前板面暂无可用实拍，仍可查看点位图与2.5D模型。',
  };
}

export function buildPhotoNavigationState({
  registration = {},
  sideId,
  preferredPhotoId = null,
} = {}) {
  if (!hasPhotoNavigationContract(registration)) {
    return unavailableState(sideId, 'photo_navigation_unavailable');
  }
  const photos = registration.photo_navigation.photos.filter(
    (photo) => photo.side_id === sideId && isReviewedPhoto(photo),
  );
  if (!photos.length) return unavailableState(sideId, 'no_reviewed_photo_for_side');
  const activePhoto = photos.find((photo) => photo.photo_id === preferredPhotoId) || photos[0];
  const sourceAnnotationPresent = activePhoto.source_annotation_present === true;
  return {
    available: true,
    reason: null,
    sideId,
    items: photos.map((photo) => ({ photoId: photo.photo_id, label: photo.label })),
    selectorVisible: photos.length > 1,
    activePhoto,
    assetPath: activePhoto.asset_path,
    matrix: [...activePhoto.board_to_image_matrix],
    sourceAnnotationPresent,
    boundaryCopy: sourceAnnotationPresent
      ? '照片中的红框或标识来自原始维修案例，不是系统识别结果。'
      : '实拍图仅用于板级坐标导航，不代表正常板或故障结论。',
  };
}

export function failPhotoNavigation(state = {}) {
  const failed = unavailableState(state.sideId || null, 'photo_asset_load_failed');
  return {
    ...failed,
    boundaryCopy: '实拍图载入失败；点位图与2.5D模型仍可继续使用。',
  };
}
