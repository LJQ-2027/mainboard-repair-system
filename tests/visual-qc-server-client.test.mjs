import test from 'node:test';
import assert from 'node:assert/strict';

import {
  applyCandidateReview,
  applyDifferenceJobResult,
  applyGoldenSample,
  applyServerJobResult,
  applyFinalQcReview,
  createDifferenceJobDescriptor,
  createFinalQcReviewDescriptor,
  createGoldenSampleDescriptor,
  createRegistrationReviewDescriptor,
  createServerSyncState,
  getVisualQcCocoDataset,
  getVisualQcDatasetBundle,
  getVisualQcDatasetAudit,
  getVisualQcIdentity,
  getVisualQcAdminCase,
  getVisualQcAdminCaseImage,
  getVisualQcTrainingManifest,
  listVisualQcAdminCases,
  listRepairEvidenceLinks,
  getRepairEvidenceLinkDetail,
  normalizeServerCaptureSession,
  pollVisualQcJob,
  restoreAdminServerCase,
  transitionServerSync,
} from '../assets/visual-qc-workbench/visual-qc-server-client.js';


function visualCase() {
  return {
    schema_version: 'VISUAL-QC-CASE-V1',
    case_id: 'case-001',
    board_key: 'km4-f151',
    board_id: 'BOARD-KM4-F151-MAIN-V1.2',
    side_id: 'main_page_2',
    capture_stage: 'before_repair',
    storage_scope: 'local_only',
    capture_session: {
      schema_version: 'VISUAL-QC-CAPTURE-SESSION-V1',
      session_id: 'capture-session-001',
      setup_id: 'standard-bench',
      expected_side_ids: ['main_page_1', 'main_page_2'],
      captured_side_ids: ['main_page_2'],
      pair_status: 'pair_in_progress',
      checklist: {
        status: 'confirmed',
        items: {
          board_and_side_confirmed: true,
          focus_and_lens_confirmed: true,
          lighting_and_occlusion_confirmed: true,
        },
        confirmed_at: '2026-07-20T10:00:00.000Z',
      },
    },
    image: {
      file_name: 'board.jpg',
      mime_type: 'image/jpeg',
      sha256: 'a'.repeat(64),
      evidence_role: 'physical_capture',
    },
    quality: { status: 'usable', score: 72, metrics: {} },
    registration: {
      method: 'reviewed_manual_homography',
      status: 'draft',
      matrix: null,
      solve_anchors: [],
      check_points: [],
      error: { count: 0, rms: null, maximum: null },
    },
    annotations: [],
    qc_result: { status: 'needs_review', reviewed_at: null },
  };
}

function repairEvidenceSummary() {
  return {
    link_set_id: 'link-case005-f069-after', revision: 1, manifest_sha256: 'a'.repeat(64),
    repair_case_id: 'case-005-bg6-f069',
    board: { board_key: 'bg6h-f069', board_id: 'BOARD-F069-MAIN-V1.2' },
    server_case_ids: ['vqc-page-2'],
    counts: {
      association: { related: 0, possibly_related: 1, not_related: 0, insufficient_evidence: 0 },
      visibility: { not_assessed: 1, visible: 0, not_visible: 0, occluded: 0 },
      source_fact_superseded: 0, binding_superseded: 0,
    },
    health: { state: 'active', reasons: [] }, imported_at: '2026-07-29T00:00:00Z',
  };
}

function repairEvidenceDetail(
  repairCaseSchemaVersion = 'VISUAL-QC-REPAIR-CASE-SOURCE-V2',
) {
  const hash = (value) => value.repeat(64);
  const boundaries = {
    visual_defect_confirmed: false, qc_annotation_created: false, golden_approved: false,
    training_label_allowed: false, repair_causality_confirmed: false,
    repair_instruction_allowed: false, field_accuracy_claim_allowed: false,
  };
  return {
    schema_version: 'VISUAL-QC-REPAIR-EVIDENCE-LINK-DETAIL-V1',
    ...repairEvidenceSummary(),
    binding_states: [{
      binding_id: 'case005-emmc-u4000-page-2', source_fact_superseded: false,
      replacement_fact_id: null, binding_superseded: false, replacement_binding_id: null,
    }],
    manifest: {
      schema_version: 'VISUAL-QC-REPAIR-EVIDENCE-LINK-V1', link_set_id: 'link-case005-f069-after',
      revision: 1, previous_manifest_sha256: null, source_origin: 'codex_operator',
      repair_case_references: [{ repair_case_reference_id: 'case005-r1', repair_case_id: 'case-005-bg6-f069', revision: 1, schema_version: repairCaseSchemaVersion, manifest_sha256: hash('b'), board_key: 'bg6h-f069', board_id: 'BOARD-F069-MAIN-V1.2' }],
      board: { board_key: 'bg6h-f069', board_id: 'BOARD-F069-MAIN-V1.2', catalog_asset: { path: 'knowledge-base/repair-workbench-boards.json', sha256: hash('c'), entry_sha256: hash('d') }, compiled_sources: [{ kind: 'cross_source_dataset', path: 'knowledge-base/f069-cross-source-registration.json', sha256: hash('e') }], board_snapshot_sha256: hash('f') },
      physical_evidence: [{
        schema_version: 'VISUAL-QC-LINKABLE-PHYSICAL-EVIDENCE-V1', physical_evidence_id: 'case005-main-page-2', server_case_id: 'vqc-page-2', intake: { batch_id: 'batch-1', entry_id: 'entry-1' }, board_key: 'bg6h-f069', board_id: 'BOARD-F069-MAIN-V1.2', side_id: 'main_page_2', capture_stage: 'after_repair', evidence_role: 'physical_capture', qualified_handoff: { schema_version: 'VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1', handoff_schema_version: 'VISUAL-QC-PHYSICAL-HANDOFF-V1', source_package_manifest_sha256: hash('1'), archived_intake_manifest_sha256: hash('2'), acceptance_report_sha256: hash('3'), acceptance_action: 'manual_registration_required', registration_review_required: true, field_accuracy_claim_allowed: false }, qualified_handoff_sha256: hash('4'), image_id: 'img-page-2', image_sha256: hash('5'), job_id: 'job-page-2', registration_review_id: 'regrev-page-2', registration: { method: 'reviewed_manual_four_point', board_to_image_matrix: [1,0,0,0,1,0,0,0,1], solve_anchors: [{ board: { x: 0, y: 0 }, image: { x: 0, y: 0 } }, { board: { x: 1, y: 0 }, image: { x: 1, y: 0 } }, { board: { x: 1, y: 1 }, image: { x: 1, y: 1 } }, { board: { x: 0, y: 1 }, image: { x: 0, y: 1 } }], independent_check_points: [{ board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } }], error: { count: 1, rms: 0, maximum: 0 } }, physical_evidence_snapshot_sha256: hash('6'),
      }],
      bindings: [{
        binding_id: 'case005-emmc-u4000-page-2', repair_case_reference_id: 'case005-r1', source_fact: { kind: 'finding', fact_id: 'case005-reported-emmc-fault', display: { text: 'EMMC坏', claim_status: 'reported' }, fact_sha256: hash('7') },
        target: { kind: 'designator', side_id: 'main_page_2', engineering: { component_id: 'F069-MAIN-U4000', designator: 'U4000', technician_category: 'storage', location: { kind: 'normalized_point', point: { x: 0.542, y: 0.669 } }, evidence_descriptors: ['storage'], geometry_source_status: 'low', semantic_identity_proven: false, engineering_snapshot_sha256: hash('8') } }, physical_evidence_id: 'case005-main-page-2', association_status: 'possibly_related', visibility_status: 'not_assessed', evidence_bases: [{ kind: 'repair_case_fact' }], supersedes_binding_id: null, boundaries: { ...boundaries, model_identity_resolved: repairCaseSchemaVersion === 'VISUAL-QC-REPAIR-CASE-SOURCE-V1' },
      }],
      boundaries,
    },
  };
}

test('repair evidence detail accepts V1 V2 V3 package-linked references and rejects unknown versions', async () => {
  const originalFetch = globalThis.fetch;
  try {
    for (const version of [
      'VISUAL-QC-REPAIR-CASE-SOURCE-V1',
      'VISUAL-QC-REPAIR-CASE-SOURCE-V2',
      'VISUAL-QC-REPAIR-CASE-SOURCE-V3',
    ]) {
      globalThis.fetch = async () => ({
        ok: true,
        status: 200,
        json: async () => repairEvidenceDetail(version),
      });
      const detail = await getRepairEvidenceLinkDetail(
        '/api',
        'owner-001',
        'reviewer',
        'link-case005-f069-after',
        1,
      );
      assert.equal(
        detail.manifest.repair_case_references[0].schema_version,
        version,
      );
      assert.equal(detail.manifest.physical_evidence.length, 1);
    }

    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => repairEvidenceDetail(
        'VISUAL-QC-REPAIR-CASE-SOURCE-V999',
      ),
    });
    await assert.rejects(
      getRepairEvidenceLinkDetail(
        '/api',
        'owner-001',
        'reviewer',
        'link-case005-f069-after',
        1,
      ),
      { code: 'invalid_repair_evidence_detail' },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('repair evidence client uses reviewer-only headers and preserves list filters', async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options });
    return { ok: true, status: 200, json: async () => ({
      schema_version: 'VISUAL-QC-REPAIR-EVIDENCE-LINK-LIST-V1', links: [repairEvidenceSummary()],
    }) };
  };
  try {
    const result = await listRepairEvidenceLinks('/api/v1/visual-qc/', 'owner-001', 'reviewer', {
      serverCaseId: 'vqc/page 2', repairCaseId: 'case-005-bg6-f069',
    });
    assert.equal(result.links[0].server_case_ids[0], 'vqc-page-2');
    assert.throws(
      () => listRepairEvidenceLinks('/api', 'tech-001', 'technician'),
      { code: 'repair_evidence_reviewer_required' },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
  assert.equal(requests.length, 1);
  assert.equal(
    requests[0].url,
    '/api/v1/visual-qc/admin/repair-evidence-links?server_case_id=vqc%2Fpage+2&repair_case_id=case-005-bg6-f069',
  );
  assert.equal(requests[0].options.headers['X-Actor-Role'], 'reviewer');
});

test('repair evidence detail percent-encodes segments and rejects redacted or invalid payloads', async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options });
    return { ok: true, status: 200, json: async () => repairEvidenceDetail() };
  };
  try {
    const result = await getRepairEvidenceLinkDetail('/api/v1/visual-qc', 'owner-001', 'reviewer', 'link/set', 1);
    assert.equal(result.manifest.bindings[0].target.side_id, 'main_page_2');
    globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({
      schema_version: 'VISUAL-QC-REPAIR-EVIDENCE-LINK-LIST-V1', links: [repairEvidenceSummary()],
    }) });
    await assert.rejects(
      getRepairEvidenceLinkDetail('/api', 'owner-001', 'reviewer', 'link', 1),
      { code: 'invalid_repair_evidence_detail' },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
  assert.equal(
    requests[0].url,
    '/api/v1/visual-qc/admin/repair-evidence-links/link%2Fset/revisions/1',
  );
  assert.equal(requests[0].options.headers['X-Actor-Id'], 'owner-001');
});

test('repair evidence client rejects malformed canonical manifests before the workbench can render them', async () => {
  const originalFetch = globalThis.fetch;
  const malformed = repairEvidenceDetail();
  delete malformed.manifest.physical_evidence[0].registration.independent_check_points;
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => malformed });
  try {
    await assert.rejects(
      getRepairEvidenceLinkDetail('/api', 'owner-001', 'reviewer', 'link-case005-f069-after', 1),
      { code: 'invalid_repair_evidence_detail' },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('repair evidence client rejects malformed nested V1 variants and summary invariants', async () => {
  const originalFetch = globalThis.fetch;
  const variants = [
    (value) => { value.manifest.board.compiled_sources[0] = { kind: 'bad kind', path: 'bad path', sha256: 'x'.repeat(64) }; },
    (value) => { value.manifest.physical_evidence[0].board_id = 'OTHER-BOARD'; },
    (value) => { value.manifest.bindings[0].source_fact.display.claim_status = 'invented'; },
    (value) => { value.counts.association.extra = 1; },
    (value) => { value.health.reasons = ['invented_reason']; },
    (value) => { value.manifest.bindings[0].evidence_bases = [{}]; },
    (value) => { value.manifest.repair_case_references[0].board_id = 'OTHER-BOARD'; },
    (value) => { value.manifest.bindings[0].evidence_bases = [{ kind: 'repair_case_fact' }, { kind: 'repair_case_fact' }]; },
    (value) => { value.manifest.bindings[0].visibility_status = 'not_assessed'; value.manifest.bindings[0].evidence_bases = [{ kind: 'human_observation', observation_code: 'target_visible' }]; },
    (value) => { value.manifest.bindings[0].visibility_status = 'visible'; value.manifest.bindings[0].evidence_bases = [{ kind: 'human_observation', observation_code: 'target_visible' }, { kind: 'human_observation', observation_code: 'target_occluded' }]; },
    (value) => { value.manifest.physical_evidence.push(structuredClone(value.manifest.physical_evidence[0])); },
    (value) => { value.manifest.bindings.push(structuredClone(value.manifest.bindings[0])); },
    (value) => { value.manifest.bindings[0].repair_case_reference_id = 'missing-reference'; },
    (value) => { value.manifest.bindings[0].target.side_id = 'main_page_1'; },
    (value) => { value.binding_states[0].binding_id = 'missing-binding'; },
    (value) => { value.binding_states[0].replacement_fact_id = 'replacement-fact'; },
    (value) => { value.binding_states[0].source_fact_superseded = true; },
    (value) => { value.binding_states[0].replacement_binding_id = 'replacement-binding'; },
    (value) => { value.binding_states[0].binding_superseded = true; },
    (value) => { value.manifest.bindings[0].supersedes_binding_id = 'missing-binding'; },
    (value) => { value.counts.association.possibly_related = 0; },
    (value) => { value.server_case_ids = ['other-case']; },
  ];
  try {
    for (const mutate of variants) {
      const malformed = repairEvidenceDetail();
      mutate(malformed);
      globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => malformed });
      await assert.rejects(
        getRepairEvidenceLinkDetail('/api', 'owner-001', 'reviewer', 'link-case005-f069-after', 1),
        { code: 'invalid_repair_evidence_detail' },
      );
    }
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('repair evidence client rejects replacement state that is not backed by the manifest graph', async () => {
  const originalFetch = globalThis.fetch;
  const malformed = repairEvidenceDetail();
  malformed.binding_states[0].binding_superseded = true;
  malformed.binding_states[0].replacement_binding_id = 'does-not-exist';
  malformed.counts.binding_superseded = 1;
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => malformed });
  try {
    await assert.rejects(
      getRepairEvidenceLinkDetail('/api', 'owner-001', 'reviewer', 'link-case005-f069-after', 1),
      { code: 'invalid_repair_evidence_detail' },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('repair evidence client rejects supersession in revision one', async () => {
  const originalFetch = globalThis.fetch;
  const malformed = repairEvidenceDetail();
  const replacement = structuredClone(malformed.manifest.bindings[0]);
  replacement.binding_id = 'case005-emmc-u4000-page-2-replacement';
  replacement.supersedes_binding_id = malformed.manifest.bindings[0].binding_id;
  malformed.manifest.bindings.push(replacement);
  malformed.binding_states[0].binding_superseded = true;
  malformed.binding_states[0].replacement_binding_id = replacement.binding_id;
  malformed.binding_states.push({
    binding_id: replacement.binding_id,
    source_fact_superseded: false,
    replacement_fact_id: null,
    binding_superseded: false,
    replacement_binding_id: null,
  });
  malformed.counts.association.possibly_related = 2;
  malformed.counts.visibility.not_assessed = 2;
  malformed.counts.binding_superseded = 1;
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => malformed });
  try {
    await assert.rejects(
      getRepairEvidenceLinkDetail('/api', 'owner-001', 'reviewer', 'link-case005-f069-after', 1),
      { code: 'invalid_repair_evidence_detail' },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('related designator requires both V1 evidence bases and proven semantic identity', async () => {
  const originalFetch = globalThis.fetch;
  const variants = [
    (value) => {
      value.manifest.bindings[0].association_status = 'related';
      value.manifest.bindings[0].evidence_bases = [{ kind: 'repair_case_fact' }];
      value.manifest.bindings[0].target.engineering.semantic_identity_proven = true;
    },
    (value) => {
      value.manifest.bindings[0].association_status = 'related';
      value.manifest.bindings[0].evidence_bases = [{ kind: 'repair_case_fact' }, { kind: 'engineering_identity' }];
      value.manifest.bindings[0].target.engineering.semantic_identity_proven = false;
    },
  ];
  try {
    for (const mutate of variants) {
      const malformed = repairEvidenceDetail();
      mutate(malformed);
      globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => malformed });
      await assert.rejects(
        getRepairEvidenceLinkDetail('/api', 'owner-001', 'reviewer', 'link-case005-f069-after', 1),
        { code: 'invalid_repair_evidence_detail' },
      );
    }
    globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => repairEvidenceDetail() });
    const accepted = await getRepairEvidenceLinkDetail(
      '/api', 'owner-001', 'reviewer', 'link-case005-f069-after', 1,
    );
    assert.equal(accepted.manifest.bindings[0].association_status, 'possibly_related');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

async function sha256Hex(blob) {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, '0')).join('');
}

async function adminServerCaseFixture() {
  const imageBlob = Object.assign(new Blob(['visual-qc-image'], { type: 'image/jpeg' }), {
    width: 180,
    height: 120,
  });
  const sha256 = await sha256Hex(imageBlob);
  const registrationReview = {
    review_id: 'reg-review-2',
    case_id: 'vqc_server_case',
    job_id: 'job-server',
    decision: 'accept_manual',
    method: 'reviewed_manual_four_point',
    board_to_image_matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
    anchors: [
      { board: [0, 0], image: [0, 0] },
      { board: [1, 0], image: [1, 0] },
      { board: [1, 1], image: [1, 1] },
      { board: [0, 1], image: [0, 1] },
    ],
    check_points: [{ board: [0.5, 0.5], image: [0.5, 0.5] }],
    error: { count: 1, rms: 0, maximum: 0 },
    created_at: '2026-07-21T10:00:00.000Z',
    status: 'reviewed',
  };
  return {
    imageBlob,
    serverCase: {
      schema_version: 'VISUAL-QC-SERVER-CASE-V3',
      case_id: 'vqc_server_case',
      board_key: 'km4-f151',
      board_id: 'BOARD-KM4-F151-MAIN-V1.2',
      side_id: 'main_page_2',
      capture_stage: 'before_repair',
      evidence_role: 'physical_capture',
      intake: { batch_id: 'batch-1', entry_id: 'entry-1' },
      qualified_handoff: {
        schema_version: 'VISUAL-QC-QUALIFIED-HANDOFF-PROVENANCE-V1',
        handoff_schema_version: 'VISUAL-QC-PHYSICAL-HANDOFF-V1',
        source_package_manifest_sha256: 'a'.repeat(64),
        archived_intake_manifest_sha256: 'b'.repeat(64),
        acceptance_report_sha256: 'c'.repeat(64),
        acceptance_action: 'automatic_candidate_review_required',
        registration_review_required: true,
        field_accuracy_claim_allowed: false,
      },
      capture_session: {
        schema_version: 'VISUAL-QC-CAPTURE-SESSION-V1',
        session_id: 'session-1',
        setup_id: 'standard-bench',
        expected_side_ids: ['main_page_1', 'main_page_2'],
        captured_side_ids: ['main_page_2'],
        pair_status: 'pair_in_progress',
        checklist: {
          status: 'confirmed',
          items: {
            board_and_side_confirmed: true,
            focus_and_lens_confirmed: true,
            lighting_and_occlusion_confirmed: true,
          },
          confirmed_at: '2026-07-21T09:00:00.000Z',
        },
      },
      image: {
        image_id: 'img-server',
        original_filename: 'board.jpg',
        mime_type: 'image/jpeg',
        byte_size: imageBlob.size,
        width: 180,
        height: 120,
        sha256,
      },
      job: {
        job_id: 'job-server',
        status: 'succeeded',
        result: {
          schema_version: 'VISUAL-QC-SERVER-JOB-RESULT-V1',
          quality: { status: 'good', score: 93, metrics: {}, guidance: [] },
          registration: {
            status: 'candidate',
            method: 'automatic_feature_homography',
            board_to_image_matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
            evidence: { reprojection_rms: 0.002 },
          },
        },
      },
      server_registration_review: registrationReview,
      server_qc_review: {
        qc_review_id: 'qc-review-2',
        case_id: 'vqc_server_case',
        registration_review_id: 'reg-review-2',
        version: 2,
        qc_result: 'confirmed_anomaly',
        annotations: [{
          annotation_id: 'defect-1',
          source: 'human_annotation',
          review_status: 'confirmed',
          category: 'burn_or_heat_damage',
        }],
        notes: '',
        created_at: '2026-07-21T11:00:00.000Z',
      },
    },
  };
}

test('admin case API requests carry role, bounded filters, and binary response', async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options });
    return {
      ok: true,
      status: 200,
      json: async () => ({ schema_version: 'test' }),
      blob: async () => new Blob(['original']),
    };
  };
  try {
    await listVisualQcAdminCases('/api/v1/visual-qc/', 'owner-001', 'reviewer', {
      page: 2,
      pageSize: 10,
      boardKey: 'km4-f151',
      sideId: 'main_page_2',
      captureStage: 'before_repair',
      state: 'ready_for_human_qc',
    });
    await getVisualQcAdminCase('/api/v1/visual-qc', 'owner-001', 'reviewer', 'case/1');
    const blob = await getVisualQcAdminCaseImage(
      '/api/v1/visual-qc', 'owner-001', 'reviewer', 'case/1',
    );
    assert.equal(await blob.text(), 'original');
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(
    requests[0].url,
    '/api/v1/visual-qc/admin/cases?page=2&page_size=10&board_key=km4-f151&side_id=main_page_2&capture_stage=before_repair&state=ready_for_human_qc',
  );
  assert.equal(requests[1].url, '/api/v1/visual-qc/admin/cases/case%2F1');
  assert.equal(requests[2].url, '/api/v1/visual-qc/admin/cases/case%2F1/image');
  assert.ok(requests.every(
    ({ options }) => options.headers['X-Actor-Role'] === 'reviewer',
  ));
});

test('server case restoration preserves reviewed registration and final QC evidence', async () => {
  const { serverCase, imageBlob } = await adminServerCaseFixture();

  const restored = await restoreAdminServerCase(serverCase, imageBlob);

  assert.equal(restored.visualCase.schema_version, 'VISUAL-QC-CASE-V2');
  assert.equal(restored.visualCase.server_sync.server_case_id, 'vqc_server_case');
  assert.deepEqual(
    restored.visualCase.server_sync.qualified_handoff,
    serverCase.qualified_handoff,
  );
  assert.equal(restored.visualCase.registration.status, 'reviewed');
  assert.deepEqual(
    restored.visualCase.registration.matrix,
    [1, 0, 0, 0, 1, 0, 0, 0, 1],
  );
  assert.equal(restored.visualCase.server_qc_review.version, 2);
  assert.equal(restored.visualCase.qc_result.status, 'confirmed_anomaly');
  assert.equal(restored.visualCase.annotations[0].annotation_id, 'defect-1');
  assert.equal(restored.imageBlob, imageBlob);
});

test('qualified handoff provenance never substitutes for registration or QC review', async () => {
  const { serverCase, imageBlob } = await adminServerCaseFixture();
  delete serverCase.server_registration_review;
  delete serverCase.server_qc_review;

  const restored = await restoreAdminServerCase(serverCase, imageBlob);

  assert.equal(restored.visualCase.registration.status, 'draft');
  assert.equal(restored.visualCase.qc_result.status, 'needs_review');
  assert.equal(
    restored.visualCase.server_sync.qualified_handoff.acceptance_action,
    'automatic_candidate_review_required',
  );
});

test('server restoration rejects misleading or stale evidence with typed errors', async () => {
  const fixture = await adminServerCaseFixture();
  const cases = [
    [
      'unsupported_server_schema',
      { ...fixture.serverCase, schema_version: 'VISUAL-QC-SERVER-CASE-V2' },
      fixture.imageBlob,
    ],
    [
      'image_hash_mismatch',
      { ...fixture.serverCase, image: { ...fixture.serverCase.image, sha256: '0'.repeat(64) } },
      fixture.imageBlob,
    ],
    [
      'image_dimension_mismatch',
      { ...fixture.serverCase, image: { ...fixture.serverCase.image, width: 181 } },
      fixture.imageBlob,
    ],
    [
      'missing_server_job_result',
      { ...fixture.serverCase, job: { ...fixture.serverCase.job, result: null } },
      fixture.imageBlob,
    ],
    [
      'stale_registration_review',
      {
        ...fixture.serverCase,
        server_registration_review: {
          ...fixture.serverCase.server_registration_review,
          job_id: 'other-job',
        },
      },
      fixture.imageBlob,
    ],
    [
      'stale_qc_review',
      {
        ...fixture.serverCase,
        server_qc_review: {
          ...fixture.serverCase.server_qc_review,
          registration_review_id: 'other-review',
        },
      },
      fixture.imageBlob,
    ],
  ];

  for (const [code, serverCase, imageBlob] of cases) {
    await assert.rejects(
      restoreAdminServerCase(serverCase, imageBlob),
      (error) => error.code === code,
    );
  }
});

test('server sync keeps a stable idempotency key across retry transitions', () => {
  const initial = createServerSyncState(visualCase());
  const uploading = transitionServerSync(initial, { type: 'upload_started' });
  const failed = transitionServerSync(uploading, {
    type: 'upload_failed',
    message: 'network unavailable',
  });
  const retrying = transitionServerSync(failed, { type: 'upload_started' });

  assert.equal(initial.idempotency_key, retrying.idempotency_key);
  assert.equal(retrying.attempt_count, 2);
  assert.equal(retrying.status, 'uploading');
  assert.equal(retrying.last_error, null);
});

test('server identity replaces browser hints with the gateway assertion', async () => {
  const originalFetch = globalThis.fetch;
  let request = null;
  globalThis.fetch = async (url, options) => {
    request = { url, options };
    return {
      ok: true,
      status: 200,
      json: async () => ({
        schema_version: 'VISUAL-QC-IDENTITY-V1',
        actor_id: 'gateway-reviewer',
        role: 'reviewer',
      }),
    };
  };
  try {
    const identity = await getVisualQcIdentity(
      '/api/v1/visual-qc',
      'browser-hint',
      'technician',
    );

    assert.equal(identity.actor_id, 'gateway-reviewer');
    assert.equal(identity.role, 'reviewer');
    assert.equal(request.url, '/api/v1/visual-qc/identity');
    assert.equal(request.options.headers['X-Actor-Id'], 'browser-hint');
    assert.equal(request.options.headers['X-Actor-Role'], 'technician');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('reviewer dataset requests use all governed export and audit routes', async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options });
    return {
      ok: true,
      status: 200,
      json: async () => ({ schema_version: 'test' }),
      blob: async () => new Blob(['bundle-bytes'], { type: 'application/zip' }),
    };
  };
  try {
    await getVisualQcTrainingManifest('/api/v1/visual-qc', 'reviewer-001', 'reviewer');
    await getVisualQcCocoDataset('/api/v1/visual-qc/', 'reviewer-001', 'reviewer');
    await getVisualQcDatasetAudit('/api/v1/visual-qc/', 'reviewer-001', 'reviewer');
    const bundle = await getVisualQcDatasetBundle(
      '/api/v1/visual-qc/',
      'reviewer-001',
      'reviewer',
    );
    assert.equal(await bundle.text(), 'bundle-bytes');
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(requests.map((request) => request.url), [
    '/api/v1/visual-qc/datasets/training-manifest',
    '/api/v1/visual-qc/datasets/coco',
    '/api/v1/visual-qc/datasets/audit',
    '/api/v1/visual-qc/datasets/bundle',
  ]);
  assert.ok(requests.every(
    (request) => request.options.headers['X-Actor-Role'] === 'reviewer',
  ));
});

test('automatic result remains a draft candidate until server review succeeds', () => {
  const accepted = {
    case_id: 'vqc_server_case',
    image: { image_id: 'img_server' },
    job: { job_id: 'job_server', status: 'queued' },
    capture_session: {
      schema_version: 'VISUAL-QC-CAPTURE-SESSION-V1',
      session_id: 'capture-session-001',
      setup_id: 'standard-bench',
      expected_side_ids: ['main_page_1', 'main_page_2'],
      captured_side_ids: ['main_page_1', 'main_page_2'],
      pair_status: 'pair_complete',
      checklist: { status: 'confirmed', items: {}, confirmed_at: null },
      board_key: 'km4-f151',
      board_id: 'BOARD-KM4-F151-MAIN-V1.2',
      cases: [{ case_id: 'vqc_server_case', side_id: 'main_page_2' }],
    },
  };
  const job = {
    job_id: 'job_server',
    status: 'succeeded',
    result: {
      schema_version: 'VISUAL-QC-SERVER-JOB-RESULT-V1',
      quality: {
        schema_version: 'VISUAL-QC-IMAGE-QUALITY-V1',
        status: 'good',
        score: 91,
        metrics: { sharpness: 18 },
        guidance: [],
      },
      registration: {
        schema_version: 'VISUAL-QC-REGISTRATION-CANDIDATE-V1',
        status: 'candidate',
        method: 'automatic_feature_homography',
        review_status: 'draft',
        board_to_image_matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
        evidence: { reprojection_rms: 0.003 },
      },
    },
  };

  const updated = applyServerJobResult(visualCase(), accepted, job);

  assert.equal(updated.schema_version, 'VISUAL-QC-CASE-V2');
  assert.equal(updated.storage_scope, 'server_authoritative_with_local_draft');
  assert.equal(updated.server_sync.status, 'candidate_ready');
  assert.equal(updated.registration.method, 'automatic_feature_homography');
  assert.equal(updated.registration.status, 'draft');
  assert.deepEqual(updated.registration.matrix, job.result.registration.board_to_image_matrix);
  assert.equal(updated.quality.score, 91);
  assert.equal(updated.capture_session.pair_status, 'pair_complete');
  assert.equal('board_key' in updated.capture_session, false);
  assert.equal('cases' in updated.capture_session, false);
});

test('server capture session is reduced to the exported case contract', () => {
  const normalized = normalizeServerCaptureSession({
    schema_version: 'VISUAL-QC-CAPTURE-SESSION-V1',
    session_id: 'capture-session-001',
    setup_id: 'standard-bench',
    expected_side_ids: ['main_page_1', 'main_page_2'],
    captured_side_ids: ['main_page_1', 'main_page_2'],
    pair_status: 'pair_complete',
    checklist: visualCase().capture_session.checklist,
    board_key: 'km4-f151',
    cases: [{ case_id: 'server-only' }],
  });

  assert.deepEqual(Object.keys(normalized), [
    'schema_version',
    'session_id',
    'setup_id',
    'expected_side_ids',
    'captured_side_ids',
    'pair_status',
    'checklist',
  ]);
});

test('manual-required result preserves the local four-point fallback', () => {
  const job = {
    job_id: 'job_server',
    status: 'succeeded',
    result: {
      schema_version: 'VISUAL-QC-SERVER-JOB-RESULT-V1',
      quality: { status: 'usable', score: 70, metrics: {}, guidance: [] },
      registration: {
        status: 'manual_required',
        method: null,
        board_to_image_matrix: null,
        failure: { code: 'insufficient_matches' },
        fallback: { method: 'reviewed_manual_four_point' },
      },
    },
  };

  const updated = applyServerJobResult(
    visualCase(),
    {
      case_id: 'vqc_server_case',
      image: { image_id: 'img_server' },
      job: { job_id: 'job_server' },
    },
    job,
  );

  assert.equal(updated.server_sync.status, 'manual_required');
  assert.equal(updated.registration.method, 'reviewed_manual_four_point');
  assert.equal(updated.registration.matrix, null);
  assert.equal(updated.registration.fallback_reason, 'insufficient_matches');
});

test('job polling stops on a persisted terminal state', async () => {
  const snapshots = [
    { job_id: 'job-1', status: 'queued' },
    { job_id: 'job-1', status: 'running' },
    { job_id: 'job-1', status: 'succeeded', result: {} },
  ];
  const seen = [];

  const terminal = await pollVisualQcJob({
    jobId: 'job-1',
    getJob: async () => snapshots.shift(),
    wait: async () => {},
    onSnapshot: (snapshot) => seen.push(snapshot.status),
    maximumAttempts: 5,
  });

  assert.equal(terminal.status, 'succeeded');
  assert.deepEqual(seen, ['queued', 'running', 'succeeded']);
});

test('registration review descriptor keeps automatic and manual evidence distinct', () => {
  const automatic = createRegistrationReviewDescriptor({
    method: 'automatic_feature_homography',
    matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
    solve_anchors: [],
  });
  const manual = createRegistrationReviewDescriptor({
    method: 'reviewed_manual_homography',
    matrix: [1, 0, 0, 0, 1, 0, 0, 0, 1],
    solve_anchors: [
      { board: { x: 0, y: 0 }, image: { x: 0, y: 0 } },
      { board: { x: 1, y: 0 }, image: { x: 1, y: 0 } },
      { board: { x: 1, y: 1 }, image: { x: 1, y: 1 } },
      { board: { x: 0, y: 1 }, image: { x: 0, y: 1 } },
    ],
    check_points: [
      { board: { x: 0.5, y: 0.5 }, image: { x: 0.5, y: 0.5 } },
    ],
    error: { count: 1, rms: 0, maximum: 0 },
  });

  assert.deepEqual(automatic, { decision: 'accept_automatic', notes: '' });
  assert.equal(manual.decision, 'accept_manual');
  assert.deepEqual(manual.anchors[2], { board: [1, 1], image: [1, 1] });
  assert.deepEqual(manual.check_points[0], {
    board: [0.5, 0.5],
    image: [0.5, 0.5],
  });
  assert.deepEqual(manual.error, { count: 1, rms: 0, maximum: 0 });
  assert.equal(manual.board_to_image_matrix.length, 9);
});

test('final QC review descriptor contains only resolved human evidence', () => {
  const reviewedCase = visualCase();
  reviewedCase.qc_result = {
    status: 'confirmed_anomaly',
    reviewed_at: '2026-07-20T12:00:00.000Z',
  };
  reviewedCase.annotations = [{
    annotation_id: 'annotation-001',
    category: 'burn_or_heat_damage',
    source: 'human_annotation',
    review_status: 'confirmed',
    image_geometry: {
      type: 'polygon',
      points: [{ x: 0.2, y: 0.2 }, { x: 0.3, y: 0.2 }, { x: 0.3, y: 0.3 }],
    },
    board_geometry: {
      type: 'polygon',
      points: [{ x: 0.2, y: 0.2 }, { x: 0.3, y: 0.2 }, { x: 0.3, y: 0.3 }],
    },
    component: null,
    note: '',
  }];

  const descriptor = createFinalQcReviewDescriptor(reviewedCase);
  const synchronized = applyFinalQcReview(reviewedCase, {
    qc_review_id: 'qcrev-001',
    version: 1,
    training_status: 'eligible',
    created_at: '2026-07-20T12:01:00.000Z',
  });

  assert.equal(descriptor.qc_result, 'confirmed_anomaly');
  assert.equal(descriptor.annotations.length, 1);
  assert.equal(synchronized.server_qc_review.version, 1);
  assert.equal(synchronized.server_qc_review.training_status, 'eligible');
});

test('Golden approval descriptor requires an explicit normal-board confirmation', () => {
  assert.throws(
    () => createGoldenSampleDescriptor(visualCase(), 'bench-a', false),
    /explicit normal-board confirmation/i,
  );

  const descriptor = createGoldenSampleDescriptor(visualCase(), 'bench-a', true);

  assert.deepEqual(descriptor, {
    case_id: 'case-001',
    capture_setup_id: 'bench-a',
    confirmed_normal: true,
  });
});

test('Golden state preserves the active version and capture setup', () => {
  const updated = applyGoldenSample(visualCase(), {
    golden_sample_id: 'gold-002',
    capture_setup_id: 'bench-a',
    status: 'active',
    version: 2,
    source_sha256: 'b'.repeat(64),
  });

  assert.equal(updated.visual_comparison.capture_setup_id, 'bench-a');
  assert.equal(updated.visual_comparison.golden_sample.version, 2);
  assert.equal(updated.visual_comparison.golden_sample.status, 'active');
});

test('difference result remains a review queue and never confirms a defect', () => {
  const descriptor = createDifferenceJobDescriptor('bench-a');
  assert.deepEqual(descriptor, { capture_setup_id: 'bench-a' });

  const updated = applyDifferenceJobResult(visualCase(), {
    job_id: 'job-difference',
    status: 'succeeded',
    result: {
      schema_version: 'VISUAL-QC-DIFFERENCE-CANDIDATES-V1',
      status: 'candidate_review_required',
      source: 'model_candidate',
      requires_human_review: true,
      heatmap: { artifact_id: 'artifact-001', mime_type: 'image/png' },
      candidates: [{
        candidate_id: 'candidate_001',
        source: 'model_candidate',
        review_status: 'pending',
        board_bbox: [0.2, 0.3, 0.4, 0.5],
        area_fraction: 0.04,
        mean_difference: 52,
        maximum_difference: 180,
      }],
    },
  });

  assert.equal(updated.visual_comparison.difference.status, 'candidate_review_required');
  assert.equal(updated.visual_comparison.difference.candidates[0].review_status, 'pending');
  assert.equal(updated.visual_comparison.difference.candidates[0].source, 'model_candidate');
  assert.equal(updated.qc_result.status, 'needs_review');
});

test('candidate review records human decision without overwriting model evidence', () => {
  const withDifference = applyDifferenceJobResult(visualCase(), {
    job_id: 'job-difference',
    status: 'succeeded',
    result: {
      schema_version: 'VISUAL-QC-DIFFERENCE-CANDIDATES-V1',
      status: 'candidate_review_required',
      candidates: [{
        candidate_id: 'candidate_001',
        source: 'model_candidate',
        review_status: 'pending',
        board_bbox: [0.2, 0.3, 0.4, 0.5],
      }],
      heatmap: { artifact_id: 'artifact-001' },
    },
  });
  const reviewed = applyCandidateReview(withDifference, {
    candidate_review_id: 'review-001',
    candidate_id: 'candidate_001',
    decision: 'confirmed',
    defect_category: 'burn_or_thermal_damage',
    label_source: 'human_annotation',
  });

  const candidate = reviewed.visual_comparison.difference.candidates[0];
  assert.equal(candidate.source, 'model_candidate');
  assert.equal(candidate.review_status, 'confirmed');
  assert.equal(candidate.human_review.label_source, 'human_annotation');
  assert.equal(reviewed.qc_result.status, 'confirmed_anomaly');
});
