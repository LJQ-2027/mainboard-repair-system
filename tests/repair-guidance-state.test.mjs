import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createRepairGuidance,
  guidanceProgress,
  recordGuidanceMeasurement,
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

test('a source range can classify a recorded value without generating a diagnosis', () => {
  const state = createRepairGuidance({
    ...entity,
    measurement_profile: {
      measurement_id: 'vbat1-voltage',
      label: 'VBAT1 voltage',
      quantity: 'voltage',
      unit: 'V',
      input_step: 0.01,
      reference: { kind: 'range', min: 3.4, max: 4.35 },
      source_link_index: 0,
    },
  });
  const within = recordGuidanceMeasurement(state, '3.85');
  assert.deepEqual(within.measurement, { value: 3.85, evaluation: 'within_range' });
  assert.equal(within.result, 'normal');
  assert.equal(within.resultSource, 'source_range');
  const below = recordGuidanceMeasurement(state, 3.2);
  assert.deepEqual(below.measurement, { value: 3.2, evaluation: 'below_range' });
  assert.equal(below.result, 'abnormal');
  assert.equal('diagnosis' in below, false);
});

test('nominal and record-only references never infer tolerance', () => {
  const nominal = createRepairGuidance({
    ...entity,
    measurement_profile: {
      measurement_id: 'x2100-frequency',
      label: 'X2100 frequency',
      quantity: 'frequency',
      unit: 'MHz',
      reference: { kind: 'nominal', value: 26 },
      source_link_index: 0,
    },
  });
  const recordedNominal = recordGuidanceMeasurement(nominal, 25.9);
  assert.deepEqual(recordedNominal.measurement, { value: 25.9, evaluation: 'recorded' });
  assert.equal(recordedNominal.result, 'pending');
  assert.equal(recordedNominal.resultSource, null);

  const recordOnly = createRepairGuidance({
    ...entity,
    measurement_profile: {
      measurement_id: 'vddemmccore-voltage',
      label: 'VDDEMMCCORE voltage',
      quantity: 'voltage',
      unit: 'V',
      reference: { kind: 'record_only' },
      source_link_index: 0,
    },
  });
  assert.equal(recordGuidanceMeasurement(recordOnly, 1.8).measurement.evaluation, 'recorded');
  assert.throws(() => recordGuidanceMeasurement(recordOnly, 'not-a-number'));
});

test('changing the fault clears observations from the previous path', () => {
  const initial = createRepairGuidance({
    ...entity,
    measurement_profile: {
      measurement_id: 'vbat1-voltage',
      label: 'VBAT1 voltage',
      quantity: 'voltage',
      unit: 'V',
      reference: { kind: 'range', min: 3.4, max: 4.35 },
      source_link_index: 0,
    },
  });
  const recorded = recordGuidanceMeasurement(initial, 3.9);
  const switched = selectGuidanceFault(recorded, 'Leakage current');
  assert.deepEqual(switched.measurement, { value: null, evaluation: 'unrecorded' });
  assert.equal(switched.result, 'pending');
});
