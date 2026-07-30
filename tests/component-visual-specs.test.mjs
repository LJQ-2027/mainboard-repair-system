import assert from 'node:assert/strict';
import test from 'node:test';

import {
  COMPONENT_VISUAL_MATERIALS,
  J6101_CONNECTOR_VISUAL_SPEC,
  resolveComponentVisualSpec,
} from '../assets/cross-source-registration/component-visual-specs.js';
import {
  COMPONENT_VISUAL_STAGE_ORDER,
  validateComponentVisualSpec,
} from '../assets/cross-source-registration/component-visual-validator.js';

const MATERIAL_TOKENS = [
  'engineering-plastic',
  'recessed-polymer',
  'plated-metal',
  'contact-metal',
  'edge-line',
];

const PROHIBITED_CLAIMS = [
  'exact_pin_count',
  'exact_pin_pitch',
  'vendor_latch',
  'solder_foot_array',
  'internal_spring_geometry',
  'millimeter_dimensions',
];

function validate(spec) {
  return validateComponentVisualSpec(spec, COMPONENT_VISUAL_MATERIALS);
}

function assertError(result, code, path) {
  assert.equal(result.valid, false);
  assert.ok(
    result.errors.some((item) => item.code === code && item.path === path),
    `Expected ${code} at ${path}: ${JSON.stringify(result.errors)}`,
  );
}

test('the material catalog exposes only immutable semantic tokens', () => {
  assert.deepEqual(Object.keys(COMPONENT_VISUAL_MATERIALS), MATERIAL_TOKENS);
  assert.equal(Object.isFrozen(COMPONENT_VISUAL_MATERIALS), true);
  MATERIAL_TOKENS.forEach((token) => {
    assert.equal(Object.isFrozen(COMPONENT_VISUAL_MATERIALS[token]), true);
  });
  assert.throws(() => {
    COMPONENT_VISUAL_MATERIALS['engineering-plastic'].roughness = 0;
  }, TypeError);
});

test('J6101 resolves through its reviewed inspection profile', () => {
  const spec = resolveComponentVisualSpec('j6101-connector-v1');
  assert.equal(spec, J6101_CONNECTOR_VISUAL_SPEC);
  assert.equal(spec.spec_id, 'connector-j6101-repair-visual-v1');
  assert.equal(resolveComponentVisualSpec('unknown-profile'), null);
  assert.equal(resolveComponentVisualSpec(), null);
});

test('the approved J6101 identity and evidence boundary remain explicit', () => {
  assert.deepEqual({
    spec_id: J6101_CONNECTOR_VISUAL_SPEC.spec_id,
    version: J6101_CONNECTOR_VISUAL_SPEC.version,
    asset_type: J6101_CONNECTOR_VISUAL_SPEC.asset_type,
    family: J6101_CONNECTOR_VISUAL_SPEC.family,
    inspection_profiles: J6101_CONNECTOR_VISUAL_SPEC.inspection_profiles,
    source_status: J6101_CONNECTOR_VISUAL_SPEC.source_status,
    fidelity: J6101_CONNECTOR_VISUAL_SPEC.fidelity,
    boundary_note: J6101_CONNECTOR_VISUAL_SPEC.boundary_note,
  }, {
    spec_id: 'connector-j6101-repair-visual-v1',
    version: 1,
    asset_type: 'procedural',
    family: 'connector',
    inspection_profiles: ['j6101-connector-v1'],
    source_status: 'category_based',
    fidelity: 'repair_visual',
    boundary_note: '连接器结构为维修识别示意，不代表准确针脚、间距、卡扣或工程尺寸。',
  });
  assert.deepEqual(J6101_CONNECTOR_VISUAL_SPEC.acceptance.prohibited_claims, PROHIBITED_CLAIMS);
});

test('the approved J6101 spec declares normalized structure and named detail parts', () => {
  assert.deepEqual(J6101_CONNECTOR_VISUAL_SPEC.materials, {
    base: 'engineering-plastic',
    opening: 'recessed-polymer',
    frame: 'plated-metal',
    contact: 'contact-metal',
    edge: 'edge-line',
  });
  assert.deepEqual(J6101_CONNECTOR_VISUAL_SPEC.structure, {
    base: { width: 1, depth: 1, height: 0.24, radius: 0.055 },
    frame: {
      width: 0.94, depth: 0.88, height: 0.62, wall: 0.14, radius: 0.045, lift: 0.2,
    },
    opening: {
      width: 0.64, depth: 0.34, height: 0.14, radius: 0.035, lift: 0.25,
    },
    contact: {
      width: 0.56, depth: 0.075, height: 0.055, offset_y: 0.075, lift: 0.34,
    },
    retention: {
      width: 0.075, depth: 0.68, height: 0.68, inset_x: 0.42, lift: 0.2,
    },
    inner_lip: {
      width: 0.72, depth: 0.48, height: 0.08, wall: 0.055, lift: 0.48,
    },
  });
  assert.deepEqual(J6101_CONNECTOR_VISUAL_SPEC.detail_levels, {
    board: [
      'base', 'frame-north', 'frame-south', 'frame-west', 'frame-east',
      'opening', 'contact',
    ],
    isolated: [
      'base', 'frame-north', 'frame-south', 'frame-west', 'frame-east',
      'opening', 'contact', 'retention-west', 'retention-east',
      'inner-lip-north', 'inner-lip-south', 'inner-lip-west', 'inner-lip-east',
      'frame-edges',
    ],
  });
});

test('the approved J6101 spec passes every source-bound validation rule', () => {
  const result = validate(J6101_CONNECTOR_VISUAL_SPEC);
  assert.deepEqual(result, { valid: true, errors: [] });
  assert.deepEqual(Object.keys(result), ['valid', 'errors']);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.errors), true);
});

test('canonical stages and the approved spec are deeply immutable where consumed', () => {
  assert.deepEqual(COMPONENT_VISUAL_STAGE_ORDER, ['blockout', 'structure', 'material', 'polish']);
  assert.equal(Object.isFrozen(COMPONENT_VISUAL_STAGE_ORDER), true);
  [
    J6101_CONNECTOR_VISUAL_SPEC,
    J6101_CONNECTOR_VISUAL_SPEC.inspection_profiles,
    J6101_CONNECTOR_VISUAL_SPEC.claims,
    J6101_CONNECTOR_VISUAL_SPEC.materials,
    J6101_CONNECTOR_VISUAL_SPEC.structure,
    J6101_CONNECTOR_VISUAL_SPEC.structure.frame,
    J6101_CONNECTOR_VISUAL_SPEC.detail_levels,
    J6101_CONNECTOR_VISUAL_SPEC.detail_levels.board,
    J6101_CONNECTOR_VISUAL_SPEC.detail_levels.isolated,
    J6101_CONNECTOR_VISUAL_SPEC.stages,
    J6101_CONNECTOR_VISUAL_SPEC.acceptance,
    J6101_CONNECTOR_VISUAL_SPEC.acceptance.prohibited_claims,
  ].forEach((value) => assert.equal(Object.isFrozen(value), true));
  assert.throws(() => J6101_CONNECTOR_VISUAL_SPEC.stages.push('extra'), TypeError);
  assert.throws(() => {
    J6101_CONNECTOR_VISUAL_SPEC.structure.frame.width = 0.5;
  }, TypeError);
});

test('invalid identity and version produce stable errors', () => {
  const missingIdentity = validate({ ...J6101_CONNECTOR_VISUAL_SPEC, spec_id: '' });
  assert.deepEqual(missingIdentity.errors[0], {
    code: 'invalid_identity',
    path: 'spec_id',
    message: 'A stable specification ID is required.',
  });

  [0, -1, 1.5, Number.NaN].forEach((version) => {
    assertError(
      validate({ ...J6101_CONNECTOR_VISUAL_SPEC, version }),
      'invalid_version',
      'version',
    );
  });
});

test('unsupported asset types are rejected', () => {
  assertError(
    validate({ ...J6101_CONNECTOR_VISUAL_SPEC, asset_type: 'glb' }),
    'unsupported_asset_type',
    'asset_type',
  );
});

test('missing, reordered, and extended build stages are rejected', () => {
  [
    ['blockout', 'structure', 'material'],
    ['structure', 'blockout', 'material', 'polish'],
    ['blockout', 'structure', 'material', 'polish', 'publish'],
  ].forEach((stages) => {
    assertError(
      validate({ ...J6101_CONNECTOR_VISUAL_SPEC, stages }),
      'invalid_stage_order',
      'stages',
    );
  });
});

test('unknown material tokens are rejected at their role path', () => {
  const spec = {
    ...J6101_CONNECTOR_VISUAL_SPEC,
    materials: { ...J6101_CONNECTOR_VISUAL_SPEC.materials, frame: 'unknown-metal' },
  };
  assert.deepEqual(validate(spec).errors[0], {
    code: 'unknown_material',
    path: 'materials.frame',
    message: 'Unknown material token: unknown-metal',
  });
});

test('nonfinite and out-of-range normalized structure ratios are rejected', () => {
  [
    ['width', 1.4],
    ['width', 0.01],
    ['height', Number.POSITIVE_INFINITY],
    ['radius', Number.NaN],
  ].forEach(([key, value]) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    spec.structure.frame[key] = value;
    assertError(validate(spec), 'ratio_out_of_range', `structure.frame.${key}`);
  });
});

test('every prohibited engineering claim is rejected', () => {
  PROHIBITED_CLAIMS.forEach((claim) => {
    const spec = {
      ...J6101_CONNECTOR_VISUAL_SPEC,
      claims: [...J6101_CONNECTOR_VISUAL_SPEC.claims, claim],
    };
    assert.deepEqual(validate(spec).errors[0], {
      code: 'prohibited_claim',
      path: 'claims',
      message: `Unsupported engineering claim: ${claim}`,
    });
  });
});

test('duplicate part names are rejected independently in each detail level', () => {
  ['board', 'isolated'].forEach((level) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    spec.detail_levels[level].push(spec.detail_levels[level][0]);
    assertError(validate(spec), 'duplicate_part_name', `detail_levels.${level}`);
  });
});

test('detail-level part names must be backed by declared structural parts', () => {
  const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  spec.detail_levels.board.push('individual-pin-1');
  assert.deepEqual(validate(spec).errors[0], {
    code: 'undeclared_detail_part',
    path: 'detail_levels.board[7]',
    message: 'Detail part is not backed by declared structure: individual-pin-1',
  });
});

test('all schema sections are required and fail with stable section errors', () => {
  ['materials', 'structure', 'claims', 'detail_levels', 'acceptance'].forEach((section) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    delete spec[section];
    assert.deepEqual(validate(spec).errors[0], {
      code: 'missing_section',
      path: section,
      message: `Required specification section is missing: ${section}`,
    });
  });
});

test('schema sections require exact object and array container types', () => {
  const malformedSections = [
    ['materials', [], 'object'],
    ['structure', [], 'object'],
    ['claims', 'connector_silhouette', 'array'],
    ['detail_levels', null, 'object'],
    ['acceptance', [], 'object'],
  ];

  malformedSections.forEach(([section, value, expectedType]) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    spec[section] = value;
    assert.deepEqual(validate(spec).errors[0], {
      code: 'invalid_section_type',
      path: section,
      message: `Specification section must be an ${expectedType}: ${section}`,
    });
  });
});

test('material roles must be complete, known, and backed by catalog tokens', () => {
  const missing = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  delete missing.materials.contact;
  assertError(validate(missing), 'missing_material_role', 'materials.contact');

  const extra = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  extra.materials.decorative = 'plated-metal';
  assertError(validate(extra), 'unknown_material_role', 'materials.decorative');

  const invalidTokenType = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  invalidTokenType.materials.frame = null;
  assertError(validate(invalidTokenType), 'unknown_material', 'materials.frame');
});

test('structure requires every supported role and rejects unknown roles', () => {
  const missing = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  delete missing.structure.retention;
  const missingResult = validate(missing);
  assertError(missingResult, 'missing_structure_role', 'structure.retention');
  assertError(missingResult, 'undeclared_detail_part', 'detail_levels.isolated[7]');

  const extra = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  extra.structure.vendor_latch = { width: 0.2 };
  assertError(validate(extra), 'unknown_structure_role', 'structure.vendor_latch');
});

test('each structure role requires its supported finite numeric shape', () => {
  const missingDimension = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  delete missingDimension.structure.frame.wall;
  const missingDimensionResult = validate(missingDimension);
  assertError(
    missingDimensionResult,
    'missing_structure_dimension',
    'structure.frame.wall',
  );
  assertError(
    missingDimensionResult,
    'undeclared_detail_part',
    'detail_levels.board[1]',
  );

  const extraDimension = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  extraDimension.structure.base.vendor_radius = 0.1;
  assertError(
    validate(extraDimension),
    'unknown_structure_dimension',
    'structure.base.vendor_radius',
  );

  const invalidSection = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  invalidSection.structure.opening = null;
  assertError(
    validate(invalidSection),
    'invalid_structure_role',
    'structure.opening',
  );

  const invalidDimension = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  invalidDimension.structure.contact.width = '0.56';
  assertError(
    validate(invalidDimension),
    'invalid_structure_dimension',
    'structure.contact.width',
  );
});

test('board and isolated detail levels are required arrays of part names', () => {
  const missingBoard = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  delete missingBoard.detail_levels.board;
  assertError(validate(missingBoard), 'missing_detail_level', 'detail_levels.board');

  const invalidIsolated = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  invalidIsolated.detail_levels.isolated = 'base';
  assertError(validate(invalidIsolated), 'invalid_detail_level', 'detail_levels.isolated');

  const invalidName = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  invalidName.detail_levels.board[0] = null;
  assertError(validate(invalidName), 'invalid_part_name', 'detail_levels.board[0]');

  const extraLevel = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  extraLevel.detail_levels.preview = ['base'];
  assertError(validate(extraLevel), 'unknown_detail_level', 'detail_levels.preview');
});

test('acceptance requires finite ordered normalized ratio bounds', () => {
  const cases = [
    ['ratio_min', Number.NaN],
    ['ratio_max', Number.POSITIVE_INFINITY],
    ['ratio_min', -0.1],
    ['ratio_max', 1.1],
  ];
  cases.forEach(([field, value]) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    spec.acceptance[field] = value;
    assertError(validate(spec), 'invalid_ratio_bounds', `acceptance.${field}`);
  });

  const reversed = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  reversed.acceptance.ratio_min = 0.8;
  reversed.acceptance.ratio_max = 0.2;
  assertError(validate(reversed), 'invalid_ratio_bounds', 'acceptance');
});

test('acceptance requires the complete prohibited claim policy', () => {
  const missingArray = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  delete missingArray.acceptance.prohibited_claims;
  assertError(
    validate(missingArray),
    'missing_prohibited_claims',
    'acceptance.prohibited_claims',
  );

  const wrongType = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  wrongType.acceptance.prohibited_claims = 'exact_pin_count';
  assertError(
    validate(wrongType),
    'invalid_prohibited_claims',
    'acceptance.prohibited_claims',
  );

  PROHIBITED_CLAIMS.forEach((claim) => {
    const incomplete = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    incomplete.acceptance.prohibited_claims = PROHIBITED_CLAIMS.filter(
      (candidate) => candidate !== claim,
    );
    assertError(
      validate(incomplete),
      'incomplete_prohibited_claims',
      'acceptance.prohibited_claims',
    );
  });
});

test('malformed input never throws and always returns the validation result shape', () => {
  [null, undefined, true, 42, 'invalid', [], new Date()].forEach((spec) => {
    let result;
    assert.doesNotThrow(() => {
      result = validate(spec);
    });
    assert.deepEqual(Object.keys(result), ['valid', 'errors']);
    assert.equal(result.valid, false);
    assert.ok(result.errors.length > 0);
    result.errors.forEach((item) => {
      assert.deepEqual(Object.keys(item), ['code', 'path', 'message']);
      assert.equal(Object.isFrozen(item), true);
    });
  });
});
