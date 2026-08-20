import test from 'node:test';
import assert from 'node:assert/strict';

import { buildPhysicalRegistrationState } from '../assets/cross-source-registration/physical-registration-state.js';

const evidence = {
  status: 'reviewed_board_coordinate_registration',
  threshold_policy: 'no_industrial_pass_threshold_declared',
  board_revision: 'XK67J_MAIN V1.0',
  engineering_board_revision: 'XK67J_MAIN_PCB V1.0B',
  downstream_admission: {
    golden_sample: false,
    defect_label: false,
    training_data: false,
    repair_causality: false,
  },
  images: [
    {
      sha256: 'a'.repeat(64),
      side_id: 'main_page_1',
      registration_status: 'reviewed_manual_registration',
      source_annotation_present: false,
      registration_review: { error: { rms: 0.013, maximum: 0.019 } },
    },
    {
      sha256: 'b'.repeat(64),
      side_id: 'main_page_2',
      registration_status: 'reviewed_manual_registration',
      source_annotation_present: true,
      registration_review: { error: { rms: 0.025, maximum: 0.037 } },
    },
    {
      sha256: 'c'.repeat(64),
      side_id: 'main_page_2',
      registration_status: 'reviewed_manual_registration',
      source_annotation_present: true,
      registration_review: { error: { rms: 0.025, maximum: 0.037 } },
    },
  ],
};

test('physical registration state is hidden when the board has no physical evidence', () => {
  assert.deepEqual(buildPhysicalRegistrationState(null, 'main_page_2'), { visible: false });
});

test('physical registration state summarizes only the active board side', () => {
  const state = buildPhysicalRegistrationState(evidence, 'main_page_2');
  assert.equal(state.visible, true);
  assert.equal(state.title, '第2面实拍配准');
  assert.equal(state.summary, '已审核 2 张');
  assert.equal(state.items.length, 2);
  assert.equal(state.items[0].error, 'RMS 0.025 · 最大 0.037');
  assert.equal(state.items[0].annotation, '含来源标注');
  assert.equal(
    state.boundary,
    '仅用于板级坐标关联；实拍 V1.0 与工程 V1.0B 仍有版本边界；不是 Golden、缺陷或训练标签，不生成维修因果；未声明工业合格阈值',
  );
});

test('physical registration state keeps missing-side evidence explicit', () => {
  const state = buildPhysicalRegistrationState(evidence, 'main_page_3');
  assert.equal(state.visible, true);
  assert.equal(state.summary, '暂无该板面审核记录');
  assert.deepEqual(state.items, []);
});
