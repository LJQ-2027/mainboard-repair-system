import assert from 'node:assert/strict';
import test from 'node:test';

import {
  beginSurfaceLoad,
  createSurfaceLoadState,
  finishSurfaceLoad,
} from '../assets/cross-source-registration/model-surface-state.js';

test('surface loading owns one current board texture request', () => {
  const initial = createSurfaceLoadState();
  const pageTwo = beginSurfaceLoad(initial, 'main_page_2');
  const pageOne = beginSurfaceLoad(pageTwo, 'main_page_1');

  assert.deepEqual(initial, { requestId: 0, sideId: null, status: 'idle' });
  assert.deepEqual(pageTwo, { requestId: 1, sideId: 'main_page_2', status: 'loading' });
  assert.deepEqual(pageOne, { requestId: 2, sideId: 'main_page_1', status: 'loading' });
  assert.equal(finishSurfaceLoad(pageOne, pageTwo.requestId, false), pageOne);
});

test('only the current texture request can publish ready or error', () => {
  const loading = beginSurfaceLoad(createSurfaceLoadState(), 'main_page_2');
  assert.deepEqual(finishSurfaceLoad(loading, loading.requestId, false), {
    requestId: 1,
    sideId: 'main_page_2',
    status: 'ready',
  });
  assert.deepEqual(finishSurfaceLoad(loading, loading.requestId, true), {
    requestId: 1,
    sideId: 'main_page_2',
    status: 'error',
  });
});
