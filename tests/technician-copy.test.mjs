import assert from 'node:assert/strict';
import test from 'node:test';
import {
  technicianEntityCopy,
  technicianInstruction,
} from '../assets/cross-source-registration/technician-copy.js';

test('reviewed entity identity is translated without replacing source fields', () => {
  const source = {
    category: 'bga_ic',
    name: 'Power management IC',
    module: 'Power management',
  };
  assert.deepEqual(technicianEntityCopy(source), {
    category: 'BGA 芯片',
    name: '电源管理 IC',
    module: '电源管理',
  });
  assert.deepEqual(source, {
    category: 'bga_ic',
    name: 'Power management IC',
    module: 'Power management',
  });
});

test('all reviewed package families have technician-facing category labels', () => {
  assert.equal(technicianEntityCopy({ category: 'crystal' }).category, '晶振');
  assert.equal(technicianEntityCopy({ category: 'connector' }).category, '连接器');
  assert.equal(technicianEntityCopy({ category: 'test_point' }).category, '测试点');
});

test('unknown engineering identity remains visible instead of being guessed', () => {
  assert.deepEqual(technicianEntityCopy({
    category: 'custom_part',
    name: 'Source name',
    module: 'Source module',
  }), {
    category: 'custom part',
    name: 'Source name',
    module: 'Source module',
  });
});

test('reviewed repair instruction receives a display translation with source fallback', () => {
  assert.equal(
    technicianInstruction('Follow the power-on and PMU checks; confirm supply conditions before component action.'),
    '按开机与电源管理检测步骤排查；处理器件前先确认各路供电条件。',
  );
  assert.equal(technicianInstruction('Unreviewed source instruction'), 'Unreviewed source instruction');
});
