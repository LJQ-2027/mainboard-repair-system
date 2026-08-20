import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildRepairEntryOptions,
  resolveRepairEntryIntent,
} from '../assets/cross-source-registration/repair-entry-state.js';

const flows = [
  { flow_id: 'charge', entry_label: '不充电', entry_order: 2, entry_type: 'known_fault', entry_component_id: 'J6101' },
  { flow_id: 'unknown', entry_label: '还不确定，先做初步主板排查', entry_order: 3, entry_type: 'precheck', entry_component_id: 'U2001' },
  { flow_id: 'power', entry_label: '不开机', entry_order: 1, entry_type: 'known_fault', entry_component_id: 'U4000' },
];

test('entry options are source ordered and expose one active path', () => {
  assert.deepEqual(buildRepairEntryOptions(flows, 'charge'), [
    { flowId: 'power', label: '不开机', type: 'known_fault', active: false },
    { flowId: 'charge', label: '不充电', type: 'known_fault', active: true },
    { flowId: 'unknown', label: '还不确定，先做初步主板排查', type: 'precheck', active: false },
  ]);
});

test('entry intent routes directly to the source-defined component', () => {
  assert.deepEqual(resolveRepairEntryIntent(flows, 'unknown'), {
    flowId: 'unknown',
    targetComponentId: 'U2001',
  });
  assert.throws(() => resolveRepairEntryIntent(flows, 'missing'));
});
