import assert from 'node:assert/strict';
import test from 'node:test';

import { buildRepairCoverageState } from '../assets/cross-source-registration/repair-coverage-state.js';


test('reviewed flows keep the normal technician repair entry', () => {
  assert.deepEqual(buildRepairCoverageState({ repair_flows: [{ flow_id: 'power' }] }), {
    available: true,
    eyebrow: '维修入口',
    title: '选择故障现象',
    note: '',
  });
});

test('missing repair guide becomes an explicit source boundary instead of an empty entry', () => {
  const state = buildRepairCoverageState({
    repair_flows: [],
    repair_coverage: {
      status: 'source_unavailable',
      title: '暂无可执行维修流程',
      note: '当前资料只有点位图和原理图。',
    },
  });
  assert.deepEqual(state, {
    available: false,
    eyebrow: '资料状态',
    title: '暂无可执行维修流程',
    note: '当前资料只有点位图和原理图。',
  });
});

test('missing coverage declaration is rejected by the UI state boundary', () => {
  assert.throws(() => buildRepairCoverageState({ repair_flows: [] }), /repair coverage/i);
});
