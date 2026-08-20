import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildPilotCatalog,
  resolvePilotModel,
} from '../assets/technician-pilot/pilot-catalog-state.js';


const catalog = {
  boards: {
    'km4-f151': {
      title: 'KM4 · F151',
      model: 'KM4',
      board_version: 'F151_MAIN_PCB_V1.2',
    },
    'xk67j-shared': {
      title: 'KM4n / KM5 · XK67J',
      model: 'KM5',
      compatible_models: ['KM4n', 'KM5'],
      board_version: 'XK67J_MAIN_PCB_V1.0B',
    },
    'kj6-h897': {
      title: 'KJ6 · H897',
      model: 'KJ6',
      compatible_models: ['KJ6'],
      board_version: 'H897_MAIN_PCB_V1.2',
    },
    'bg6m-f069m': {
      title: 'BG6M · F069M',
      model: 'BG6M',
      board_version: 'F069M_MAIN_PCB_V1.0',
    },
  },
};

const datasets = {
  'km4-f151': { repair_flows: [{ flow_id: 'known' }, { flow_id: 'initial' }] },
  'xk67j-shared': { repair_flows: [{ flow_id: 'source-boundary' }] },
  'kj6-h897': {
    repair_flows: [],
    case_navigation: {
      schema_version: 'H897-CASE-NAVIGATION-V1',
      case_count: 2,
      cases: ['CASE-1', 'CASE-2'].map((caseId, index) => ({
        case_id: caseId,
        symptoms: ['不开机'],
        reported_finding: 'Source finding',
        photo_sha256: [String(index + 1).repeat(64)],
        navigation_scope: 'board_only',
        candidate_component_ids: [],
        repair_causality_claim_allowed: false,
        defect_label_allowed: false,
        boundary: 'Navigation only.',
      })),
    },
  },
  'bg6m-f069m': {
    repair_flows: [],
    repair_coverage: { status: 'source_unavailable' },
  },
};

test('flattens compatible sales models while retaining the canonical board key', () => {
  const entries = buildPilotCatalog(catalog, datasets);

  assert.deepEqual(entries.map((item) => item.model), ['BG6M', 'KJ6', 'KM4', 'KM4n', 'KM5']);
  assert.equal(entries.find((item) => item.model === 'KM4n').boardKey, 'xk67j-shared');
  assert.equal(entries.find((item) => item.model === 'KM5').boardVersion, 'XK67J_MAIN_PCB_V1.0B');
});

test('unsafe H897 contracts do not advertise case navigation at the entry', () => {
  const unsafe = structuredClone(datasets);
  unsafe['kj6-h897'].case_navigation.cases[0].repair_causality_claim_allowed = true;

  const entry = buildPilotCatalog(catalog, unsafe).find((item) => item.model === 'KJ6');

  assert.equal(entry.capabilityTier, 'reference_only');
  assert.equal(entry.caseCount, 0);
});

test('derives capability tiers only from declared flow and H897 case contracts', () => {
  const entries = buildPilotCatalog(catalog, datasets);

  assert.equal(entries.find((item) => item.model === 'KM4').capabilityTier, 'reviewed_flow');
  assert.equal(entries.find((item) => item.model === 'KJ6').capabilityTier, 'case_navigation');
  assert.equal(entries.find((item) => item.model === 'BG6M').capabilityTier, 'reference_only');
  assert.equal(entries.find((item) => item.model === 'KJ6').caseCount, 2);
});

test('fails closed for missing board datasets instead of presenting a model', () => {
  const incomplete = structuredClone(datasets);
  delete incomplete['xk67j-shared'];

  const entries = buildPilotCatalog(catalog, incomplete);

  assert.equal(entries.some((item) => item.boardKey === 'xk67j-shared'), false);
});

test('resolves only an exact unambiguous model and optional board identity', () => {
  const entries = buildPilotCatalog(catalog, datasets);

  assert.equal(resolvePilotModel(entries, 'KM4n').boardKey, 'xk67j-shared');
  assert.equal(resolvePilotModel(entries, 'KM4n', 'xk67j-shared').model, 'KM4n');
  assert.equal(resolvePilotModel(entries, 'missing'), null);
  assert.equal(resolvePilotModel(entries, 'KM4n', 'km4-f151'), null);

  const ambiguous = [...entries, { ...entries[0], boardKey: 'duplicate-board' }];
  assert.equal(resolvePilotModel(ambiguous, entries[0].model), null);
});
