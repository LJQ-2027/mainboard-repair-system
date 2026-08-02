import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildPhotoNavigationState,
  failPhotoNavigation,
  resolveReviewedPhotoIdBySourceHash,
} from '../assets/cross-source-registration/photo-navigation-state.js';


const matrix = [1, 0, 0, 0, 1, 0, 0, 0, 1];
const hash = (character) => character.repeat(64);
const photo = (photoId, sideId, label, character, overrides = {}) => ({
  photo_id: photoId,
  side_id: sideId,
  label,
  source_sha256: hash(character),
  derivative_sha256: hash(character.toUpperCase()),
  asset_path: `assets/physical/${photoId}.webp`,
  board_to_image_matrix: matrix,
  registration_review_status: 'reviewed',
  source_annotation_present: sideId === 'main_page_2',
  source_annotation_role: sideId === 'main_page_2'
    ? 'source_component_callout_not_system_label'
    : null,
  ...overrides,
});

const registration = {
  reference_mode: 'reviewed_physical_photo_navigation',
  photo_navigation: {
    schema_version: 'XK67J-PHOTO-NAVIGATION-V1',
    photos: [
      photo('side-1', 'main_page_1', '第1面实拍', 'a'),
      photo('side-2-a', 'main_page_2', '第2面实拍 A', 'b'),
      photo('side-2-b', 'main_page_2', '第2面实拍 B', 'c'),
    ],
  },
};

test('returns the reviewed photo for the requested board side', () => {
  const state = buildPhotoNavigationState({ registration, sideId: 'main_page_1' });

  assert.equal(state.available, true);
  assert.equal(state.activePhoto.photo_id, 'side-1');
  assert.equal(state.assetPath, 'assets/physical/side-1.webp');
  assert.deepEqual(state.matrix, matrix);
  assert.deepEqual(state.items, [{ photoId: 'side-1', label: '第1面实拍' }]);
  assert.equal(state.selectorVisible, false);
});

test('retains a preferred photo when it belongs to the active side', () => {
  const state = buildPhotoNavigationState({
    registration,
    sideId: 'main_page_2',
    preferredPhotoId: 'side-2-b',
  });

  assert.equal(state.activePhoto.photo_id, 'side-2-b');
  assert.equal(state.selectorVisible, true);
  assert.deepEqual(state.items, [
    { photoId: 'side-2-a', label: '第2面实拍 A' },
    { photoId: 'side-2-b', label: '第2面实拍 B' },
  ]);
});

test('uses a deterministic first-photo fallback for a stale preference', () => {
  const state = buildPhotoNavigationState({
    registration,
    sideId: 'main_page_2',
    preferredPhotoId: 'side-1',
  });

  assert.equal(state.activePhoto.photo_id, 'side-2-a');
});

test('exposes source-callout boundaries without converting them into findings', () => {
  const state = buildPhotoNavigationState({ registration, sideId: 'main_page_2' });

  assert.equal(state.sourceAnnotationPresent, true);
  assert.match(state.boundaryCopy, /原始维修案例/);
  assert.match(state.boundaryCopy, /不是系统识别结果/);
});

test('rejects malformed matrices and fails closed when no reviewed photo remains', () => {
  const malformed = structuredClone(registration);
  malformed.photo_navigation.photos = [
    photo('bad', 'main_page_1', 'bad', 'd', { board_to_image_matrix: [1, 0] }),
  ];
  const state = buildPhotoNavigationState({ registration: malformed, sideId: 'main_page_1' });

  assert.deepEqual(state, {
    available: false,
    reason: 'no_reviewed_photo_for_side',
    sideId: 'main_page_1',
    items: [],
    selectorVisible: false,
    activePhoto: null,
    assetPath: null,
    matrix: null,
    sourceAnnotationPresent: false,
    boundaryCopy: '当前板面暂无可用实拍，仍可查看点位图与2.5D模型。',
  });
});

test('does not expose photos for legacy or unsupported reference modes', () => {
  const state = buildPhotoNavigationState({
    registration: { ...registration, reference_mode: 'point_map_only' },
    sideId: 'main_page_2',
  });

  assert.equal(state.available, false);
  assert.equal(state.reason, 'photo_navigation_unavailable');
});

test('runtime image failure clears the active photo and preserves a fail-closed boundary', () => {
  const state = buildPhotoNavigationState({
    registration,
    sideId: 'main_page_2',
  });
  const failed = failPhotoNavigation(state);

  assert.equal(failed.available, false);
  assert.equal(failed.activePhoto, null);
  assert.equal(failed.assetPath, null);
  assert.equal(failed.matrix, null);
  assert.match(failed.boundaryCopy, /载入失败/);
});

test('resolves an exact reviewed source hash only on the requested side', () => {
  assert.equal(
    resolveReviewedPhotoIdBySourceHash(registration, 'main_page_2', hash('c')),
    'side-2-b',
  );
  assert.equal(
    resolveReviewedPhotoIdBySourceHash(registration, 'main_page_1', hash('c')),
    null,
  );
  assert.equal(
    resolveReviewedPhotoIdBySourceHash(registration, 'main_page_2', hash('f')),
    null,
  );
});

test('hash resolution fails closed for malformed or unreviewed photo records', () => {
  const malformed = structuredClone(registration);
  malformed.photo_navigation.photos[2].registration_review_status = 'draft';
  assert.equal(
    resolveReviewedPhotoIdBySourceHash(malformed, 'main_page_2', hash('c')),
    null,
  );
  assert.equal(resolveReviewedPhotoIdBySourceHash(registration, 'main_page_2', 'bad'), null);
});
