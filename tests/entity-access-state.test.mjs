import test from 'node:test';
import assert from 'node:assert/strict';

import { buildEntityAccessState } from '../assets/cross-source-registration/entity-access-state.js';

test('concealed components expose a technician action instead of a proxy-data label', () => {
  assert.deepEqual(buildEntityAccessState({
    side_id: 'main_page_2',
    proxy_visibility: 'concealed_by_shield',
  }, 'main_page_2', '第2面'), {
    tone: 'caution',
    label: '需拆屏蔽罩',
    description: '该器件位于屏蔽罩下，检测前需拆罩或使用透视定位。',
  });
});

test('visible context is expressed as direct technician access', () => {
  assert.deepEqual(buildEntityAccessState({
    side_id: 'main_page_2',
    proxy_visibility: 'visible_context',
  }, 'main_page_2', '第2面'), {
    tone: 'clear',
    label: '可直接观察',
    description: '该位置在当前板面可直接定位。',
  });
});

test('an entity on another side reports its source side without a warning color', () => {
  assert.deepEqual(buildEntityAccessState({
    side_id: 'main_page_2',
    proxy_visibility: 'concealed_by_shield',
  }, 'main_page_1', '第2面'), {
    tone: 'side',
    label: '位于第2面',
    description: '切换到第2面定位该器件。',
  });
});
