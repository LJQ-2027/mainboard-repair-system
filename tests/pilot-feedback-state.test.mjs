import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createPilotFeedback,
  loadPilotFeedback,
  savePilotFeedback,
  serializePilotFeedback,
} from '../assets/cross-source-registration/pilot-feedback-state.js';

const context = {
  boardKey: 'kj6-h897',
  model: 'KJ6',
  boardVersion: 'H897 V1.2',
  intent: { kind: 'case_symptom', label: '不开机', symptomKey: '不开机' },
  selectedComponentId: 'kj6-h897-u2001',
  selectedCaseId: 'H897-CASE-001',
  photo: { name: 'must-not-leak.jpg' },
};

test('creates a privacy-reduced feedback record from allowed usability fields', () => {
  const record = createPilotFeedback(context, {
    targetStatus: 'found',
    usefulness: 'enough_to_continue',
    note: '  点位与实物位置一致。  ',
  }, '2026-08-03T12:00:00.000Z', 'feedback-1');

  assert.equal(record.schema_version, 'TECHNICIAN-PILOT-FEEDBACK-V1');
  assert.equal(record.feedback_id, 'feedback-1');
  assert.equal(record.context.board_key, 'kj6-h897');
  assert.equal(record.context.intent.kind, 'case_symptom');
  assert.equal(record.target_location, 'found');
  assert.equal(record.source_usefulness, 'enough_to_continue');
  assert.equal(record.note, '点位与实物位置一致。');
  assert.equal('photo' in record.context, false);
});

test('requires at least one controlled feedback dimension and rejects invalid values', () => {
  assert.throws(() => createPilotFeedback(context, {}, '2026-08-03T12:00:00.000Z', 'feedback-2'));
  assert.throws(() => createPilotFeedback(context, { targetStatus: 'maybe' }, '2026-08-03T12:00:00.000Z', 'feedback-3'));
  assert.throws(() => createPilotFeedback(context, { note: 'x'.repeat(501) }, '2026-08-03T12:00:00.000Z', 'feedback-4'));
});

test('persists records locally and exports deterministic ordered JSON', () => {
  const storage = new Map();
  const localStorageLike = {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
  };
  const later = createPilotFeedback(context, { usefulness: 'insufficient' }, '2026-08-03T13:00:00.000Z', 'feedback-b');
  const earlier = createPilotFeedback(context, { targetStatus: 'uncertain' }, '2026-08-03T12:00:00.000Z', 'feedback-a');

  savePilotFeedback(localStorageLike, [later, earlier]);
  assert.deepEqual(loadPilotFeedback(localStorageLike), [later, earlier]);
  const exported = JSON.parse(serializePilotFeedback([later, earlier]));
  assert.equal(exported.schema_version, 'TECHNICIAN-PILOT-FEEDBACK-EXPORT-V1');
  assert.deepEqual(exported.records.map((item) => item.feedback_id), ['feedback-a', 'feedback-b']);
  assert.doesNotMatch(JSON.stringify(exported), /must-not-leak/);
});

test('sanitizes stored records and drops malformed or privacy-bearing fields before export', () => {
  const storage = new Map();
  const localStorageLike = {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
  };
  const valid = createPilotFeedback(context, { targetStatus: 'found' }, '2026-08-03T12:00:00.000Z', 'feedback-safe');
  storage.set('technician-pilot-feedback-v1', JSON.stringify([
    { ...valid, imei: '1234567890', repair_verdict: 'replace', context: { ...valid.context, phone: 'secret' } },
    { schema_version: 'UNSAFE', imei: 'leak' },
  ]));

  const loaded = loadPilotFeedback(localStorageLike);
  assert.equal(loaded.length, 1);
  const serialized = serializePilotFeedback(loaded);
  assert.doesNotMatch(serialized, /imei|repair_verdict|phone|secret|1234567890/);
});
