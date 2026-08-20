import assert from 'node:assert/strict';
import test from 'node:test';

import { buildRegistrationViewState } from '../assets/cross-source-registration/registration-view-state.js';


test('photo proxy registration starts on the synchronized physical reference', () => {
  const state = buildRegistrationViewState({
    proxy_image: 'photo.jpg',
    anchors: [{}, {}, {}, {}],
  });
  assert.deepEqual(state, { photoAvailable: true, initialView: 'photo' });
});

test('point-map-only registration never invents a physical reference tab', () => {
  const state = buildRegistrationViewState({ reference_mode: 'point_map_only' });
  assert.deepEqual(state, { photoAvailable: false, initialView: 'pointmap' });
});

test('reviewed physical-photo navigation starts on the real photo view', () => {
  const state = buildRegistrationViewState({
    reference_mode: 'reviewed_physical_photo_navigation',
    photo_navigation: {
      schema_version: 'XK67J-PHOTO-NAVIGATION-V1',
      photos: [{
        photo_id: 'side-2-a',
        side_id: 'main_page_2',
        label: '第2面实拍 A',
        asset_path: 'assets/photo.webp',
        source_sha256: 'a'.repeat(64),
        derivative_sha256: 'b'.repeat(64),
        board_to_image_matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
        registration_review_status: 'reviewed',
      }],
    },
  });

  assert.deepEqual(state, { photoAvailable: true, initialView: 'photo' });
});

test('malformed reviewed photo navigation fails closed to the point map', () => {
  const state = buildRegistrationViewState({
    reference_mode: 'reviewed_physical_photo_navigation',
    photo_navigation: { photos: [{ asset_path: 'photo.webp', board_to_image_matrix: [1] }] },
  });

  assert.deepEqual(state, { photoAvailable: false, initialView: 'pointmap' });
});
