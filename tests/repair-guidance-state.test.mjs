import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createRepairGuidance,
  guidanceProgress,
  recordGuidanceResult,
  selectGuidanceFault,
} from '../assets/cross-source-registration/repair-guidance-state.js';

const entity = {
  component_id: 'KM4-MAIN-U2001',
  repair_links: [{
    source: 'repair-guide.pdf',
    page: '7-11',
    faults: ['No power', 'Leakage current'],
    instruction: 'Confirm supply conditions before component action.',
  }],
};

test('guidance is compiled only from source-linked faults and instructions', () => {
  const state = createRepairGuidance(entity);
  assert.deepEqual(state.faults, ['No power', 'Leakage current']);
  assert.deepEqual(state.steps, [{
    stepId: 'repair-0',
    instruction: 'Confirm supply conditions before component action.',
    source: 'repair-guide.pdf',
    page: '7-11',
  }]);
  assert.equal(state.selectedFault, 'No power');
  assert.equal(state.result, 'pending');
});

test('fault selection and result recording remain scoped to the current component', () => {
  const initial = createRepairGuidance(entity);
  const selected = selectGuidanceFault(initial, 'Leakage current');
  const recorded = recordGuidanceResult(selected, 'abnormal');
  assert.equal(recorded.selectedFault, 'Leakage current');
  assert.equal(recorded.result, 'abnormal');
  assert.equal(initial.result, 'pending');
  assert.throws(() => selectGuidanceFault(initial, 'Unknown fault'));
  assert.throws(() => recordGuidanceResult(initial, 'replace-component'));
});

test('progress reports observation status without inventing a diagnosis', () => {
  const initial = createRepairGuidance(entity);
  assert.deepEqual(guidanceProgress(initial), { completed: 0, total: 1 });
  const recorded = recordGuidanceResult(initial, 'normal');
  assert.deepEqual(guidanceProgress(recorded), { completed: 1, total: 1 });
  assert.equal('diagnosis' in recorded, false);
  assert.equal('repairAction' in recorded, false);
});

test('entities without source instructions do not expose an executable path', () => {
  const state = createRepairGuidance({ component_id: 'KM4-MAIN-X', repair_links: [] });
  assert.deepEqual(state.faults, []);
  assert.deepEqual(state.steps, []);
  assert.equal(state.selectedFault, null);
});
