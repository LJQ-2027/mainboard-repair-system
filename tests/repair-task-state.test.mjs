import assert from 'node:assert/strict';
import test from 'node:test';

import { buildRepairTaskCue } from '../assets/cross-source-registration/repair-task-state.js';

test('measurement step tells the technician where to work and what to record', () => {
  assert.deepEqual(buildRepairTaskCue({
    step: { measurements: [{}, {}] },
    targetDesignator: 'U4000',
    targetSideLabel: '第2面',
  }), {
    phase: 'measure',
    title: '定位 U4000，并记录 2 项测量',
    detail: '目标位于第2面。先用左侧主板图确认位置，再完成下方测量并保存。',
  });
});

test('inspection, action, boundary and closed states expose one next action', () => {
  assert.equal(buildRepairTaskCue({
    step: { measurements: [] }, targetDesignator: 'J6101', targetSideLabel: '第1面',
  }).phase, 'inspect');
  assert.equal(buildRepairTaskCue({ terminal: { kind: 'action' } }).phase, 'repair');
  assert.equal(buildRepairTaskCue({ terminal: { kind: 'boundary' } }).phase, 'boundary');
  assert.equal(buildRepairTaskCue({ closed: true }).phase, 'closed');
});
