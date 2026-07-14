import assert from 'node:assert/strict';
import test from 'node:test';

import {
  answerRepairFlow,
  backRepairFlow,
  createRepairFlowState,
  currentRepairFlowStep,
  recordRepairFlowPostActionCheck,
  recordRepairFlowMeasurement,
  repairFlowMeasurementsComplete,
  repairFlowProgress,
  repairFlowTargetComponentId,
  repairFlowTrail,
  resetRepairFlow,
  setRepairFlowActionExecuted,
} from '../assets/cross-source-registration/repair-flow-state.js';

const profile = {
  flow_id: 'charging-page-14',
  entry_step_id: 'charger',
  steps: [
    {
      step_id: 'charger',
      prompt: '充电器是否正常工作？',
      choices: [
        { value: 'yes', label: '是', outcome: { kind: 'next', step_id: 'usb' } },
        { value: 'no', label: '否', outcome: { kind: 'action', label: '更换充电器' } },
      ],
    },
    {
      step_id: 'usb',
      prompt: 'USB 接口是否虚焊？',
      choices: [
        { value: 'yes', label: '是', outcome: { kind: 'action', label: '补焊 USB 接口' } },
        { value: 'no', label: '否', outcome: { kind: 'next', step_id: 'fpc' } },
      ],
    },
    {
      step_id: 'fpc',
      prompt: 'FPC 排线是否扣好？',
      choices: [
        { value: 'yes', label: '是', outcome: { kind: 'action', label: '继续下一来源检查' } },
        { value: 'no', label: '否', outcome: { kind: 'action', label: '重扣 FPC 排线' } },
      ],
    },
  ],
};

test('flow starts at its explicit source entry step', () => {
  const state = createRepairFlowState(profile);
  assert.equal(currentRepairFlowStep(profile, state).step_id, 'charger');
  assert.deepEqual(repairFlowProgress(profile, state), { current: 1, total: 3 });
  assert.deepEqual(state.history, []);
  assert.equal(state.terminal, null);
});

test('a next outcome advances and back restores the prior source question', () => {
  const initial = createRepairFlowState(profile);
  const advanced = answerRepairFlow(profile, initial, 'yes');
  assert.equal(currentRepairFlowStep(profile, advanced).step_id, 'usb');
  assert.deepEqual(repairFlowProgress(profile, advanced), { current: 2, total: 3 });
  const restored = backRepairFlow(profile, advanced);
  assert.equal(currentRepairFlowStep(profile, restored).step_id, 'charger');
  assert.deepEqual(restored.history, []);
});

test('flow trail exposes completed, current, and pending source steps', () => {
  const initial = createRepairFlowState(profile);
  assert.deepEqual(repairFlowTrail(profile, initial).map((item) => item.status), ['current', 'pending', 'pending']);
  const advanced = answerRepairFlow(profile, initial, 'yes');
  assert.deepEqual(repairFlowTrail(profile, advanced).map((item) => item.status), ['completed', 'current', 'pending']);
  const terminal = answerRepairFlow(profile, advanced, 'yes');
  assert.deepEqual(repairFlowTrail(profile, terminal).map((item) => item.status), ['completed', 'completed', 'pending']);
  assert.deepEqual(repairFlowTrail(profile, backRepairFlow(profile, terminal)).map((item) => item.status), ['completed', 'current', 'pending']);
});

test('flow target follows the current step and explicit terminal action', () => {
  const targeted = {
    ...profile,
    entry_component_id: 'U4000',
    steps: profile.steps.map((step, index) => ({
      ...step,
      target_component_id: index === 0 ? 'U4000' : 'X2100',
      choices: index === 0
        ? [
          { value: 'yes', label: '是', outcome: { kind: 'next', step_id: 'usb' } },
          { value: 'no', label: '否', outcome: { kind: 'action', label: '处理电源', target_component_id: 'U2001' } },
        ]
        : step.choices,
    })),
  };
  const initial = createRepairFlowState(targeted);
  assert.equal(repairFlowTargetComponentId(targeted, initial), 'U4000');
  assert.equal(repairFlowTargetComponentId(targeted, answerRepairFlow(targeted, initial, 'yes')), 'X2100');
  assert.equal(repairFlowTargetComponentId(targeted, answerRepairFlow(targeted, initial, 'no')), 'U2001');
});

test('an action outcome terminates with the exact source action', () => {
  const terminal = answerRepairFlow(profile, createRepairFlowState(profile), 'no');
  assert.equal(currentRepairFlowStep(profile, terminal), null);
  assert.deepEqual(terminal.terminal, { kind: 'action', label: '更换充电器' });
  assert.equal(repairFlowProgress(profile, terminal).current, 1);
  const reopened = backRepairFlow(profile, terminal);
  assert.equal(currentRepairFlowStep(profile, reopened).step_id, 'charger');
  assert.equal(reopened.terminal, null);
  assert.equal(reopened.actionExecution, null);
});

test('action execution is recordable without claiming a repair result', () => {
  const terminal = answerRepairFlow(profile, createRepairFlowState(profile), 'no');
  assert.equal(terminal.actionExecution, 'pending');
  const executed = setRepairFlowActionExecuted(terminal, true);
  assert.equal(executed.actionExecution, 'executed');
  assert.equal(executed.postActionCheck, 'pending');
  const rechecked = recordRepairFlowPostActionCheck(executed, 'symptom_persists');
  assert.equal(rechecked.postActionCheck, 'symptom_persists');
  assert.equal(setRepairFlowActionExecuted(rechecked, false).actionExecution, 'pending');
  assert.equal(setRepairFlowActionExecuted(rechecked, false).postActionCheck, null);
  assert.throws(() => recordRepairFlowPostActionCheck(terminal, 'symptom_cleared'));
  assert.throws(() => recordRepairFlowPostActionCheck(executed, 'fixed'));
  const boundaryProfile = {
    ...profile,
    steps: [{
      step_id: 'charger',
      prompt: '资料是否明确？',
      choices: [{ value: 'no', label: '否', outcome: { kind: 'boundary', label: '待资料复核' } }],
    }],
  };
  const boundary = answerRepairFlow(boundaryProfile, createRepairFlowState(boundaryProfile), 'no');
  assert.throws(() => setRepairFlowActionExecuted(boundary, true));
  assert.throws(() => recordRepairFlowPostActionCheck(boundary, 'uncertain'));
});

test('reset and invalid choices cannot escape the declared flow graph', () => {
  const advanced = answerRepairFlow(profile, createRepairFlowState(profile), 'yes');
  assert.deepEqual(resetRepairFlow(profile), createRepairFlowState(profile));
  assert.throws(() => answerRepairFlow(profile, advanced, 'maybe'));
  assert.throws(() => createRepairFlowState({ ...profile, entry_step_id: 'missing' }));
});

test('an ambiguous source branch stops at an explicit boundary terminal', () => {
  const boundedProfile = {
    ...profile,
    steps: [{
      step_id: 'charger',
      prompt: '资料是否明确？',
      choices: [{ value: 'no', label: '否', outcome: { kind: 'boundary', label: '后续 Y/N 标注待复核' } }],
    }],
  };
  const terminal = answerRepairFlow(boundedProfile, createRepairFlowState(boundedProfile), 'no');
  assert.deepEqual(terminal.terminal, { kind: 'boundary', label: '后续 Y/N 标注待复核' });
});

test('a measured step cannot advance until every required source value is recorded', () => {
  const measuredProfile = {
    flow_id: 'small-current',
    entry_step_id: 'rails',
    steps: [{
      step_id: 'rails',
      prompt: '电压是否正常？',
      measurements: [
        { measurement_id: 'vddcore', label: 'VDDCORE', unit: 'V', input_step: 0.01, required: true, reference: { kind: 'nominal', value: 1.15 } },
        { measurement_id: 'vddemmccore', label: 'VDDEMMCCORE', unit: 'V', input_step: 0.01, required: true, reference: { kind: 'nominal', value: 3.3 } },
      ],
      choices: [{ value: 'normal', label: '正常', outcome: { kind: 'action', label: '下一来源动作' } }],
    }],
  };
  const initial = createRepairFlowState(measuredProfile);
  assert.equal(repairFlowMeasurementsComplete(measuredProfile, initial), false);
  assert.throws(() => answerRepairFlow(measuredProfile, initial, 'normal'));
  const first = recordRepairFlowMeasurement(measuredProfile, initial, 'vddcore', '1.14');
  assert.equal(repairFlowMeasurementsComplete(measuredProfile, first), false);
  const complete = recordRepairFlowMeasurement(measuredProfile, first, 'vddemmccore', 3.28);
  assert.equal(repairFlowMeasurementsComplete(measuredProfile, complete), true);
  assert.deepEqual(complete.measurements.rails, { vddcore: 1.14, vddemmccore: 3.28 });
  assert.equal(answerRepairFlow(measuredProfile, complete, 'normal').terminal.label, '下一来源动作');
  assert.throws(() => recordRepairFlowMeasurement(measuredProfile, initial, 'unknown', 1));
  assert.throws(() => recordRepairFlowMeasurement(measuredProfile, initial, 'vddcore', 'bad'));
});
