import test from 'node:test';
import assert from 'node:assert/strict';

import {
  beginModelTransition,
  canAcceptModelInteraction,
  completeModelTransition,
  consumePendingFocus,
  createModelInteractionState,
  recordSelectionIntent,
  transformBoardCenter,
} from '../assets/cross-source-registration/model-interaction-state.js';

test('one transition owns the complete model interaction surface', () => {
  const ready = createModelInteractionState();
  const inspection = beginModelTransition(ready, 'inspection');
  const rejectedSide = beginModelTransition(inspection, 'side');

  assert.equal(canAcceptModelInteraction(ready), true);
  assert.equal(canAcceptModelInteraction(inspection), false);
  assert.deepEqual(rejectedSide, inspection);
  assert.equal(completeModelTransition(inspection, inspection.transitionId - 1).phase, 'inspection');
  assert.equal(completeModelTransition(inspection, inspection.transitionId).phase, 'ready');
});

test('initial data selection does not become an automatic camera request', () => {
  const initial = recordSelectionIntent(createModelInteractionState(), false);
  assert.equal(initial.pendingFocus, false);

  const explicit = recordSelectionIntent(initial, true);
  assert.equal(explicit.pendingFocus, true);
  assert.equal(consumePendingFocus(explicit).pendingFocus, false);
});

test('focus center follows the board rotation used by the renderer', () => {
  const quarterTurn = transformBoardCenter({ x: 0.2, y: 0.125 }, { x: 0, z: Math.PI / 2 });
  assert.equal(Math.abs(quarterTurn.x + 0.125) < 1e-6, true);
  assert.equal(Math.abs(quarterTurn.y - 0.2) < 1e-6, true);

  const tilted = transformBoardCenter({ x: 0.2, y: 0.125 }, { x: -0.46, z: 0 });
  assert.equal(tilted.x, 0.2);
  assert.equal(tilted.y < 0.125, true);
});
