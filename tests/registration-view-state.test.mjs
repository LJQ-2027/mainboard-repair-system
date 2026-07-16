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
