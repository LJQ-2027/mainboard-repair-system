import test from 'node:test';
import assert from 'node:assert/strict';

import {
  activeRepairEvidenceBindings,
  repairEvidenceBindingView,
  repairEvidenceLocation,
  repairEvidenceLocationCenter,
  repairEvidenceMarker,
  canProjectRepairEvidenceToPhoto,
  repairEvidenceBindingsForServerCase,
} from '../assets/visual-qc-workbench/repair-evidence-links.js';
import { readFile } from 'node:fs/promises';

const app = await readFile(
  new URL('../assets/visual-qc-workbench/app.js', import.meta.url),
  'utf8',
);
const styles = await readFile(
  new URL('../assets/visual-qc-workbench/styles.css', import.meta.url),
  'utf8',
);

function binding(overrides = {}) {
  return {
    binding_id: 'case005-emmc-u4000-page-2',
    source_fact: {
      kind: 'finding',
      fact_id: 'case005-reported-emmc-fault',
      display: { text: 'EMMC坏' },
    },
    target: {
      kind: 'designator',
      side_id: 'main_page_2',
      designator: 'U4000',
      geometry: { precision: 'low', point: [0.542, 0.669] },
    },
    association_status: 'possibly_related',
    visibility_status: 'not_assessed',
    ...overrides,
  };
}

function detail(overrides = {}) {
  return {
    schema_version: 'VISUAL-QC-REPAIR-EVIDENCE-LINK-DETAIL-V1',
    health: { state: 'active', reasons: [] },
    board: { board_key: 'bg6h-f069', board_id: 'BOARD-F069-MAIN-V1.2' },
    manifest: {
      board: { board_key: 'bg6h-f069', board_id: 'BOARD-F069-MAIN-V1.2' },
      bindings: [],
    },
    binding_states: [],
    ...overrides,
  };
}

test('candidate engineering binding uses neutral copy and a conservative point', () => {
  const view = repairEvidenceBindingView(binding(), detail());

  assert.equal(view.associationLabel, '候选工程关联');
  assert.equal(view.sourceLabel, '来源报告');
  assert.equal(view.conclusionLabel, '未形成视觉缺陷结论');
  assert.equal(view.canLocate, true);
  assert.equal(view.markerMode, 'conservative_point');
  assert.notEqual(view.tone, 'confirmed-anomaly');
  assert.notEqual(view.colorToken, 'coral');
  assert.deepEqual(repairEvidenceLocation(binding(), detail()), {
    boardKey: 'bg6h-f069',
    boardId: 'BOARD-F069-MAIN-V1.2',
    sideId: 'main_page_2',
    mode: 'conservative_point',
    point: { x: 0.542, y: 0.669 },
  });
});

test('related binding uses engineering label and whole board selector', () => {
  const item = binding({
    target: { kind: 'whole_board', side_id: 'main_page_1' },
    association_status: 'related',
  });
  const view = repairEvidenceBindingView(item, detail());

  assert.equal(view.associationLabel, '工程资料关联');
  assert.equal(view.markerMode, 'whole_board');
  assert.deepEqual(repairEvidenceLocation(item, detail()), {
    boardKey: 'bg6h-f069',
    boardId: 'BOARD-F069-MAIN-V1.2',
    sideId: 'main_page_1',
    mode: 'whole_board',
  });
});

test('stale or unavailable evidence disables location', () => {
  for (const state of ['stale', 'unavailable']) {
    const view = repairEvidenceBindingView(binding(), detail({ health: { state, reasons: ['image_missing'] } }));
    assert.equal(view.canLocate, false);
    assert.equal(repairEvidenceLocation(binding(), detail({ health: { state, reasons: [] } })), null);
  }
});

test('board identity mismatch disables location before any canvas operation', () => {
  const mismatched = detail({
    manifest: {
      board: { board_key: 'km4-f151', board_id: 'BOARD-KM4-F151-MAIN-V1.2' },
      bindings: [],
    },
  });
  assert.equal(repairEvidenceBindingView(binding(), mismatched).canLocate, false);
  assert.equal(repairEvidenceLocation(binding(), mismatched), null);
});

test('polygon board region keeps its true centroid for workbench focus', () => {
  const polygon = binding({
    target: {
      kind: 'board_region',
      side_id: 'main_page_2',
      region: {
        kind: 'normalized_polygon',
        points: [{ x: 0.2, y: 0.2 }, { x: 0.8, y: 0.2 }, { x: 0.5, y: 0.8 }],
      },
    },
  });
  const location = repairEvidenceLocation(polygon, detail());

  assert.deepEqual(repairEvidenceLocationCenter(location), { x: 0.5, y: 0.4 });
  assert.notDeepEqual(repairEvidenceLocationCenter(location), { x: 0.5, y: 0.5 });
});

test('board-region marker preserves the exact neutral polygon without manufacturing a footprint', () => {
  const location = {
    boardKey: 'bg6h-f069', boardId: 'BOARD-F069-MAIN-V1.2', sideId: 'main_page_2', mode: 'region',
    region: {
      kind: 'normalized_polygon',
      points: [{ x: 0.2, y: 0.2 }, { x: 0.8, y: 0.2 }, { x: 0.5, y: 0.8 }],
    },
  };
  assert.deepEqual(repairEvidenceMarker(location), {
    shape: 'polygon', tone: 'neutral',
    points: [{ x: 0.2, y: 0.2 }, { x: 0.8, y: 0.2 }, { x: 0.5, y: 0.8 }],
  });
});

test('cross-side evidence cannot be projected onto the restored physical photo', () => {
  const location = repairEvidenceLocation(binding(), detail());
  assert.equal(canProjectRepairEvidenceToPhoto(location, 'main_page_1'), false);
  assert.equal(canProjectRepairEvidenceToPhoto(location, 'main_page_2'), true);
  assert.match(app, /canProjectRepairEvidenceToPhoto\(evidenceLocation, currentCase\(\)\?\.side_id\)/);
  assert.match(app, /跨板面关联：仅在工程点位图显示/);
  assert.match(app, /drawRepairEvidenceMarker\(context, evidenceLocation, frame\)/);
  assert.match(app, /!state\.repairEvidence\.crossSidePhoto/);
  assert.match(app, /item\.link_set_id !== list\.links\[index\]\.link_set_id/);
  assert.match(app, /evidenceItem\.server_case_id === serverCaseId/);
});

test('current server case only exposes active bindings tied to its exact physical evidence', () => {
  const pageOne = binding({ binding_id: 'page-one', physical_evidence_id: 'photo-one' });
  const pageTwo = binding({ binding_id: 'page-two', physical_evidence_id: 'photo-two' });
  const state = detail({
    manifest: {
      board: detail().manifest.board,
      physical_evidence: [
        { physical_evidence_id: 'photo-one', server_case_id: 'case-page-1' },
        { physical_evidence_id: 'photo-two', server_case_id: 'case-page-2' },
      ],
      bindings: [pageOne, pageTwo],
    },
  });
  assert.deepEqual(
    repairEvidenceBindingsForServerCase(state, 'case-page-1').map((item) => item.binding_id),
    ['page-one'],
  );
  assert.deepEqual(
    repairEvidenceBindingsForServerCase(state, 'unknown').map((item) => item.binding_id),
    [],
  );
  assert.match(app, /repairEvidenceBindingsForServerCase\(detail, evidence\.caseId\)/);
  assert.match(app, /includeSuperseded: true/);
  assert.match(app, /state\.repairEvidence\.location = null/);
});

test('active bindings exclude independent source-fact and binding replacements', () => {
  const sourceSuperseded = binding({ binding_id: 'source-old' });
  const bindingSuperseded = binding({ binding_id: 'binding-old' });
  const active = binding({ binding_id: 'active' });
  const state = detail({
    manifest: { bindings: [sourceSuperseded, bindingSuperseded, active] },
    binding_states: [
      {
        binding_id: 'source-old', source_fact_superseded: true,
        replacement_fact_id: 'case005-finding-new', binding_superseded: false,
        replacement_binding_id: null,
      },
      {
        binding_id: 'binding-old', source_fact_superseded: false,
        replacement_fact_id: null, binding_superseded: true,
        replacement_binding_id: 'active',
      },
      {
        binding_id: 'active', source_fact_superseded: false,
        replacement_fact_id: null, binding_superseded: false,
        replacement_binding_id: null,
      },
    ],
  });

  assert.deepEqual(activeRepairEvidenceBindings(state).map((item) => item.binding_id), ['active']);
  const sourceView = repairEvidenceBindingView(sourceSuperseded, state);
  const bindingView = repairEvidenceBindingView(bindingSuperseded, state);
  assert.equal(sourceView.sourceFactSupersededLabel, '来源事实已被修正');
  assert.equal(sourceView.replacementFactId, 'case005-finding-new');
  assert.equal(bindingView.bindingSupersededLabel, '关联已被替代');
  assert.equal(bindingView.replacementBindingId, 'active');
});

test('a doubly superseded binding preserves both independent replacement identifiers', () => {
  const item = binding({ binding_id: 'replaced-twice' });
  const state = detail({
    manifest: { board: detail().manifest.board, bindings: [item] },
    binding_states: [{
      binding_id: 'replaced-twice', source_fact_superseded: true,
      replacement_fact_id: 'corrected-fact', binding_superseded: true,
      replacement_binding_id: 'corrected-binding',
    }],
  });
  const view = repairEvidenceBindingView(item, state);

  assert.equal(view.sourceFactSupersededLabel, '来源事实已被修正');
  assert.equal(view.replacementFactId, 'corrected-fact');
  assert.equal(view.bindingSupersededLabel, '关联已被替代');
  assert.equal(view.replacementBindingId, 'corrected-binding');
  assert.equal(activeRepairEvidenceBindings(state).length, 0);
});

test('presentation helpers never mutate QC, annotations, Golden, or registration', () => {
  const item = binding();
  const state = detail({
    manifest: { bindings: [item] },
    qc_result: { status: 'needs_review' },
    annotations: [],
    golden_sample: { version: 1 },
    registration: { status: 'reviewed' },
  });
  const before = structuredClone(state);

  repairEvidenceBindingView(item, state);
  activeRepairEvidenceBindings(state);
  repairEvidenceLocation(item, state);

  assert.deepEqual(state, before);
});

test('workbench renders only active bindings and separates history from current evidence', () => {
  assert.match(app, /for \(const binding of repairEvidenceBindingsForServerCase\(detail, evidence\.caseId\)\)/);
  assert.match(app, /view\.sourceLabel/);
  assert.match(app, /view\.sourceFactSupersededLabel/);
  assert.match(app, /view\.bindingSupersededLabel/);
  assert.match(app, /repairEvidenceLocationCenter\(location\)/);
});

test('server case restore clears old evidence location and allows same-case retry', () => {
  assert.match(
    app,
    /state\.repairEvidence\s*=\s*\{\s*caseId:\s*null,\s*status:\s*'idle',\s*details:\s*\[\],\s*error:\s*null,\s*location:\s*null,\s*crossSidePhoto:\s*false,\s*\};\s*syncRegistrationState\(\)/s,
  );
  assert.match(
    app,
    /state\.repairEvidence\s*=\s*\{\s*caseId:\s*serverCaseId,\s*status:\s*'loading',[\s\S]*?renderRepairEvidence\(\);\s*renderCanvases\(\);/,
  );
});

test('repair evidence card separates its fact label from revision metadata', () => {
  assert.match(
    styles,
    /\.repair-evidence-item\s*>\s*div:first-child\s*\{[^}]*display:\s*grid;[^}]*gap:\s*2px;/s,
  );
});
