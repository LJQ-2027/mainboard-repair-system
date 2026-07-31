import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildComponentVisualSpecCatalog,
  COMPONENT_VISUAL_MATERIALS,
  J6101_CONNECTOR_VISUAL_SPEC,
  resolveComponentVisualSpec,
  SHARED_BGA_VISUAL_SPEC,
  U2001_PMIC_VISUAL_SPEC,
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
  'ic-substrate',
  'molded-package',
  'inset-top',
  'orientation-marker',
];

const PROHIBITED_CLAIMS = [
  'exact_pin_count',
  'exact_pin_pitch',
  'vendor_latch',
  'solder_foot_array',
  'internal_spring_geometry',
  'millimeter_dimensions',
];

const U2001_PROHIBITED_CLAIMS = [
  ...PROHIBITED_CLAIMS,
  'exact_ball_count',
  'exact_ball_pitch',
  'exact_pad_layout',
  'vendor_package',
  'die_or_internal_structure',
  'package_marking',
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

test('U2001 resolves through the approved category-based PMIC profile', () => {
  const spec = resolveComponentVisualSpec('u2001-pmic-v1');
  assert.equal(spec, U2001_PMIC_VISUAL_SPEC);
  assert.deepEqual({
    spec_id: spec.spec_id,
    version: spec.version,
    asset_type: spec.asset_type,
    family: spec.family,
    inspection_profiles: spec.inspection_profiles,
    source_status: spec.source_status,
    fidelity: spec.fidelity,
    boundary_note: spec.boundary_note,
  }, {
    spec_id: 'ic-bga-u2001-repair-visual-v1',
    version: 1,
    asset_type: 'procedural',
    family: 'ic_bga',
    inspection_profiles: ['u2001-pmic-v1'],
    source_status: 'category_based',
    fidelity: 'repair_visual',
    boundary_note: '电源管理 IC 结构为维修识别示意，不代表准确封装、球数、球距、焊盘、丝印、内部结构或工程尺寸。',
  });
});

test('shared BGA profiles resolve to one production spec distinct from U2001', () => {
  [
    'u4000-emmc-v1',
    'u0600-rf-device-v1',
    'connectivity-bga-v1',
  ].forEach((profileId) => {
    assert.equal(resolveComponentVisualSpec(profileId), SHARED_BGA_VISUAL_SPEC);
  });
  assert.notEqual(SHARED_BGA_VISUAL_SPEC, U2001_PMIC_VISUAL_SPEC);
});

test('the shared BGA identity and evidence boundary remain explicit', () => {
  assert.deepEqual({
    spec_id: SHARED_BGA_VISUAL_SPEC.spec_id,
    version: SHARED_BGA_VISUAL_SPEC.version,
    asset_type: SHARED_BGA_VISUAL_SPEC.asset_type,
    family: SHARED_BGA_VISUAL_SPEC.family,
    inspection_profiles: SHARED_BGA_VISUAL_SPEC.inspection_profiles,
    source_status: SHARED_BGA_VISUAL_SPEC.source_status,
    fidelity: SHARED_BGA_VISUAL_SPEC.fidelity,
    boundary_note: SHARED_BGA_VISUAL_SPEC.boundary_note,
  }, {
    spec_id: 'ic-bga-shared-package-repair-visual-v1',
    version: 1,
    asset_type: 'procedural',
    family: 'ic_bga',
    inspection_profiles: [
      'u4000-emmc-v1',
      'u0600-rf-device-v1',
      'connectivity-bga-v1',
    ],
    source_status: 'category_based',
    fidelity: 'repair_visual',
    boundary_note: '共享 BGA IC 结构为维修识别示意，不代表准确封装、球数、球距、焊盘、丝印、内部结构、方向点或工程尺寸。',
  });
  assert.deepEqual(SHARED_BGA_VISUAL_SPEC.claims, [
    'ic_package_silhouette',
    'substrate_body_hierarchy',
    'generic_orientation_cue',
  ]);
  assert.deepEqual(
    SHARED_BGA_VISUAL_SPEC.acceptance.prohibited_claims,
    U2001_PROHIBITED_CLAIMS,
  );
});

test('the shared BGA spec declares normalized structure and U2001 detail part names', () => {
  assert.deepEqual(SHARED_BGA_VISUAL_SPEC.materials, U2001_PMIC_VISUAL_SPEC.materials);
  assert.deepEqual(SHARED_BGA_VISUAL_SPEC.structure, {
    substrate: { width: 1, depth: 1, height: 0.18, radius: 0.045 },
    body: { width: 0.92, depth: 0.92, height: 0.66, radius: 0.065, lift: 0.18 },
    top: { width: 0.72, depth: 0.68, height: 0.045, radius: 0.05, lift: 0.84 },
    marker: {
      radius: 0.04,
      offset_x: -0.31,
      offset_y: 0.31,
      height: 0.02,
      lift: 0.89,
    },
  });
  assert.deepEqual(
    SHARED_BGA_VISUAL_SPEC.detail_levels,
    U2001_PMIC_VISUAL_SPEC.detail_levels,
  );
  assert.deepEqual(SHARED_BGA_VISUAL_SPEC.detail_levels.isolated.slice(-3), [
    'substrate-edges',
    'body-edges',
    'top-seam',
  ]);
});

test('the U2001 evidence boundary rejects package engineering claims', () => {
  assert.deepEqual(U2001_PMIC_VISUAL_SPEC.claims, [
    'ic_package_silhouette',
    'substrate_body_hierarchy',
    'generic_orientation_cue',
  ]);
  assert.deepEqual(
    U2001_PMIC_VISUAL_SPEC.acceptance.prohibited_claims,
    U2001_PROHIBITED_CLAIMS,
  );
});

test('the approved U2001 spec declares normalized structure and named detail parts', () => {
  assert.deepEqual(U2001_PMIC_VISUAL_SPEC.materials, {
    substrate: 'ic-substrate',
    body: 'molded-package',
    top: 'inset-top',
    marker: 'orientation-marker',
    edge: 'edge-line',
  });
  assert.deepEqual(U2001_PMIC_VISUAL_SPEC.structure, {
    substrate: { width: 1, depth: 1, height: 0.12, radius: 0.045 },
    body: { width: 0.88, depth: 0.88, height: 0.62, radius: 0.065, lift: 0.12 },
    top: { width: 0.74, depth: 0.74, height: 0.055, radius: 0.05, lift: 0.72 },
    marker: {
      radius: 0.045,
      offset_x: 0.31,
      offset_y: 0.31,
      height: 0.025,
      lift: 0.775,
    },
  });
  assert.deepEqual(U2001_PMIC_VISUAL_SPEC.detail_levels, {
    board: ['substrate', 'body', 'top', 'orientation-marker'],
    isolated: [
      'substrate',
      'body',
      'top',
      'orientation-marker',
      'substrate-edges',
      'body-edges',
      'top-seam',
    ],
  });
});

test('catalog construction rejects duplicate inspection profiles', () => {
  assert.throws(
    () => buildComponentVisualSpecCatalog([
      J6101_CONNECTOR_VISUAL_SPEC,
      { ...U2001_PMIC_VISUAL_SPEC, inspection_profiles: ['j6101-connector-v1'] },
    ]),
    /Duplicate inspection profile: j6101-connector-v1/,
  );
});

test('catalog construction rejects a duplicate shared BGA inspection profile', () => {
  assert.throws(
    () => buildComponentVisualSpecCatalog([
      SHARED_BGA_VISUAL_SPEC,
      { ...U2001_PMIC_VISUAL_SPEC, inspection_profiles: ['u4000-emmc-v1'] },
    ]),
    /Duplicate inspection profile: u4000-emmc-v1/,
  );
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

test('the approved U2001 spec passes every IC BGA family validation rule', () => {
  const result = validate(U2001_PMIC_VISUAL_SPEC);
  assert.deepEqual(result, { valid: true, errors: [] });
  assert.deepEqual(Object.keys(result), ['valid', 'errors']);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.errors), true);
});

test('family contracts reject unknown families and cross-family roles', () => {
  const unknownFamily = {
    ...U2001_PMIC_VISUAL_SPEC,
    family: 'unknown',
  };
  assertError(validate(unknownFamily), 'unsupported_family', 'family');

  const unknownMaterial = structuredClone(U2001_PMIC_VISUAL_SPEC);
  unknownMaterial.materials.pins = 'plated-metal';
  assertError(validate(unknownMaterial), 'unknown_material_role', 'materials.pins');

  const unknownStructure = structuredClone(U2001_PMIC_VISUAL_SPEC);
  unknownStructure.structure.balls = {};
  assertError(validate(unknownStructure), 'unknown_structure_role', 'structure.balls');

  const unknownDetailPart = structuredClone(U2001_PMIC_VISUAL_SPEC);
  unknownDetailPart.detail_levels.board.push('ball-grid');
  assertError(
    validate(unknownDetailPart),
    'undeclared_detail_part',
    'detail_levels.board[4]',
  );
});

test('prototype-key family names fail soft as unsupported families', () => {
  ['__proto__', 'constructor', 'toString'].forEach((family) => {
    const spec = { ...U2001_PMIC_VISUAL_SPEC, family };
    let result;
    assert.doesNotThrow(() => {
      result = validate(spec);
    });
    assertError(result, 'unsupported_family', 'family');
  });
});

test('required identity, stage, and ratio fields cannot be inherited', () => {
  const inheritedTopLevel = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  const inheritedValues = {};
  ['spec_id', 'version', 'asset_type', 'stages'].forEach((field) => {
    inheritedValues[field] = inheritedTopLevel[field];
    delete inheritedTopLevel[field];
  });
  Object.setPrototypeOf(inheritedTopLevel, inheritedValues);
  const topLevelResult = validate(inheritedTopLevel);
  assertError(topLevelResult, 'invalid_identity', 'spec_id');
  assertError(topLevelResult, 'invalid_version', 'version');
  assertError(topLevelResult, 'unsupported_asset_type', 'asset_type');
  assertError(topLevelResult, 'invalid_stage_order', 'stages');

  const inheritedRatios = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  const inheritedMinimum = inheritedRatios.acceptance.ratio_min;
  const inheritedMaximum = inheritedRatios.acceptance.ratio_max;
  delete inheritedRatios.acceptance.ratio_min;
  delete inheritedRatios.acceptance.ratio_max;
  Object.defineProperties(Object.prototype, {
    ratio_min: { configurable: true, value: inheritedMinimum },
    ratio_max: { configurable: true, value: inheritedMaximum },
  });
  let ratioResult;
  try {
    ratioResult = validate(inheritedRatios);
  } finally {
    delete Object.prototype.ratio_min;
    delete Object.prototype.ratio_max;
  }
  assertError(ratioResult, 'invalid_ratio_bounds', 'acceptance.ratio_min');
  assertError(ratioResult, 'invalid_ratio_bounds', 'acceptance.ratio_max');
});

test('every prohibited U2001 package claim is rejected', () => {
  U2001_PROHIBITED_CLAIMS.forEach((claim) => {
    const spec = {
      ...U2001_PMIC_VISUAL_SPEC,
      claims: [...U2001_PMIC_VISUAL_SPEC.claims, claim],
    };
    assertError(validate(spec), 'prohibited_claim', 'claims');
  });
});

test('each family accepts only its explicit source-backed claims', () => {
  [
    [J6101_CONNECTOR_VISUAL_SPEC, 'engineering_digital_twin'],
    [J6101_CONNECTOR_VISUAL_SPEC, 'ic_package_silhouette'],
    [U2001_PMIC_VISUAL_SPEC, 'engineering_digital_twin'],
    [U2001_PMIC_VISUAL_SPEC, 'exact_vendor_top_text'],
    [U2001_PMIC_VISUAL_SPEC, 'connector_silhouette'],
  ].forEach(([approvedSpec, unsupportedClaim]) => {
    const spec = {
      ...approvedSpec,
      claims: [...approvedSpec.claims, unsupportedClaim],
    };
    assertError(
      validate(spec),
      'unsupported_claim',
      `claims[${approvedSpec.claims.length}]`,
    );
  });
});

test('U2001 family validation remains fail-soft for malformed nested values', () => {
  const cases = [
    ['materials.body', (spec) => { spec.materials.body = null; }, 'invalid_material_token'],
    ['structure.marker.radius', (spec) => { spec.structure.marker.radius = Number.NaN; }, 'ratio_out_of_range'],
    ['structure.body.lift', (spec) => { spec.structure.body.lift = Number.POSITIVE_INFINITY; }, 'ratio_out_of_range'],
    ['detail_levels.isolated', (spec) => { spec.detail_levels.isolated = {}; }, 'invalid_detail_level'],
    ['claims[0]', (spec) => { spec.claims[0] = Symbol('claim'); }, 'invalid_claim'],
  ];
  cases.forEach(([path, mutate, code]) => {
    const spec = structuredClone(U2001_PMIC_VISUAL_SPEC);
    mutate(spec);
    let result;
    assert.doesNotThrow(() => {
      result = validate(spec);
    });
    assertError(result, code, path);
  });
});

test('throwing accessors and proxies return a stable malformed-spec result', () => {
  const throwingGetter = structuredClone(U2001_PMIC_VISUAL_SPEC);
  Object.defineProperty(throwingGetter.materials, 'body', {
    enumerable: true,
    get() {
      throw new Error('boom');
    },
  });
  const throwingProxy = new Proxy(U2001_PMIC_VISUAL_SPEC, {
    get() {
      throw new Error('blocked');
    },
  });

  [throwingGetter, throwingProxy].forEach((spec) => {
    let result;
    assert.doesNotThrow(() => {
      result = validate(spec);
    });
    assert.deepEqual(result, {
      valid: false,
      errors: [{
        code: 'malformed_spec',
        path: '',
        message: 'Component visual specification could not be inspected safely.',
      }],
    });
    assert.equal(Object.isFrozen(result), true);
    assert.equal(Object.isFrozen(result.errors), true);
    assert.equal(Object.isFrozen(result.errors[0]), true);
  });
});

test('sparse arrays cannot bypass required item validation', () => {
  const sparseStages = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  sparseStages.stages = new Array(4);
  assertError(validate(sparseStages), 'invalid_stage_order', 'stages');

  const sparseProfiles = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  sparseProfiles.inspection_profiles = new Array(1);
  assertError(
    validate(sparseProfiles),
    'invalid_inspection_profile',
    'inspection_profiles[0]',
  );

  const sparseClaims = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  sparseClaims.claims = new Array(1);
  assertError(validate(sparseClaims), 'invalid_claim', 'claims[0]');

  ['board', 'isolated'].forEach((level) => {
    const sparseDetails = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    sparseDetails.detail_levels[level] = new Array(1);
    assertError(
      validate(sparseDetails),
      'invalid_part_name',
      `detail_levels.${level}[0]`,
    );
  });
});

test('prototype-backed sparse arrays cannot supply inherited items', () => {
  const inheritedArray = (value) => {
    const array = new Array(1);
    const prototype = Object.create(Array.prototype);
    prototype[0] = value;
    Object.setPrototypeOf(array, prototype);
    return array;
  };

  const inheritedProfiles = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  inheritedProfiles.inspection_profiles = inheritedArray('j6101-connector-v1');
  assertError(
    validate(inheritedProfiles),
    'invalid_inspection_profile',
    'inspection_profiles[0]',
  );

  const inheritedClaims = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  inheritedClaims.claims = inheritedArray('connector_silhouette');
  assertError(validate(inheritedClaims), 'invalid_claim', 'claims[0]');

  const inheritedDetails = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  inheritedDetails.detail_levels.board = inheritedArray('base');
  assertError(
    validate(inheritedDetails),
    'invalid_part_name',
    'detail_levels.board[0]',
  );
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

test('the U2001 visual specification is deeply immutable where consumed', () => {
  [
    U2001_PMIC_VISUAL_SPEC,
    U2001_PMIC_VISUAL_SPEC.inspection_profiles,
    U2001_PMIC_VISUAL_SPEC.claims,
    U2001_PMIC_VISUAL_SPEC.materials,
    U2001_PMIC_VISUAL_SPEC.structure,
    U2001_PMIC_VISUAL_SPEC.structure.substrate,
    U2001_PMIC_VISUAL_SPEC.structure.body,
    U2001_PMIC_VISUAL_SPEC.structure.top,
    U2001_PMIC_VISUAL_SPEC.structure.marker,
    U2001_PMIC_VISUAL_SPEC.detail_levels,
    U2001_PMIC_VISUAL_SPEC.detail_levels.board,
    U2001_PMIC_VISUAL_SPEC.detail_levels.isolated,
    U2001_PMIC_VISUAL_SPEC.stages,
    U2001_PMIC_VISUAL_SPEC.acceptance,
    U2001_PMIC_VISUAL_SPEC.acceptance.prohibited_claims,
  ].forEach((value) => assert.equal(Object.isFrozen(value), true));
  assert.throws(() => U2001_PMIC_VISUAL_SPEC.claims.push('extra'), TypeError);
  assert.throws(() => {
    U2001_PMIC_VISUAL_SPEC.structure.marker.radius = 0.2;
  }, TypeError);
});

test('the shared BGA visual specification is deeply immutable where consumed', () => {
  [
    SHARED_BGA_VISUAL_SPEC,
    SHARED_BGA_VISUAL_SPEC.inspection_profiles,
    SHARED_BGA_VISUAL_SPEC.claims,
    SHARED_BGA_VISUAL_SPEC.materials,
    SHARED_BGA_VISUAL_SPEC.structure,
    SHARED_BGA_VISUAL_SPEC.structure.substrate,
    SHARED_BGA_VISUAL_SPEC.structure.body,
    SHARED_BGA_VISUAL_SPEC.structure.top,
    SHARED_BGA_VISUAL_SPEC.structure.marker,
    SHARED_BGA_VISUAL_SPEC.detail_levels,
    SHARED_BGA_VISUAL_SPEC.detail_levels.board,
    SHARED_BGA_VISUAL_SPEC.detail_levels.isolated,
    SHARED_BGA_VISUAL_SPEC.stages,
    SHARED_BGA_VISUAL_SPEC.acceptance,
    SHARED_BGA_VISUAL_SPEC.acceptance.prohibited_claims,
  ].forEach((value) => assert.equal(Object.isFrozen(value), true));
  assert.throws(() => SHARED_BGA_VISUAL_SPEC.inspection_profiles.push('extra'), TypeError);
  assert.throws(() => {
    SHARED_BGA_VISUAL_SPEC.structure.marker.offset_x = 0.31;
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
    ['depth', 0],
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
  assertError(validate(invalidTokenType), 'invalid_material_token', 'materials.frame');
});

test('malformed material tokens return stable errors without throwing', () => {
  [Symbol('metal'), {}, () => 'metal', null, []].forEach((token) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    spec.materials.frame = token;
    let result;
    assert.doesNotThrow(() => {
      result = validate(spec);
    });
    assert.deepEqual(result.errors[0], {
      code: 'invalid_material_token',
      path: 'materials.frame',
      message: 'Material tokens must be non-empty strings.',
    });
    assert.equal(result.valid, false);
  });
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

  ['board', 'isolated'].forEach((level) => {
    const empty = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    empty.detail_levels[level] = [];
    assertError(validate(empty), 'empty_detail_level', `detail_levels.${level}`);
  });

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
    ['ratio_min', 0],
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

test('required visual metadata fields cannot be omitted', () => {
  [
    'family',
    'inspection_profiles',
    'source_status',
    'fidelity',
    'boundary_note',
  ].forEach((field) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    delete spec[field];
    assert.deepEqual(validate(spec).errors[0], {
      code: 'missing_required_field',
      path: field,
      message: `Required specification field is missing: ${field}`,
    });
  });
});

test('string visual metadata fields require nonempty strings', () => {
  ['family', 'source_status', 'fidelity', 'boundary_note'].forEach((field) => {
    [null, 42, [], '', '   '].forEach((value) => {
      const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
      spec[field] = value;
      assertError(validate(spec), 'invalid_required_field', field);
    });
  });
});

test('inspection profiles require a nonempty array of unique nonempty strings', () => {
  [null, 'j6101-connector-v1', {}, []].forEach((value) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    spec.inspection_profiles = value;
    assertError(validate(spec), 'invalid_inspection_profiles', 'inspection_profiles');
  });

  [null, '', '   ', Symbol('profile')].forEach((profileId) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    spec.inspection_profiles = [profileId];
    assertError(validate(spec), 'invalid_inspection_profile', 'inspection_profiles[0]');
  });

  const duplicate = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  duplicate.inspection_profiles = ['j6101-connector-v1', 'j6101-connector-v1'];
  assertError(
    validate(duplicate),
    'duplicate_inspection_profile',
    'inspection_profiles',
  );
});

test('claims require a nonempty array of unique nonempty strings', () => {
  const empty = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  empty.claims = [];
  assertError(validate(empty), 'invalid_claims', 'claims');

  [null, '', '   ', Symbol('claim')].forEach((claim) => {
    const spec = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
    spec.claims = [claim];
    assertError(validate(spec), 'invalid_claim', 'claims[0]');
  });

  const duplicate = structuredClone(J6101_CONNECTOR_VISUAL_SPEC);
  duplicate.claims = ['connector_silhouette', 'connector_silhouette'];
  assertError(validate(duplicate), 'duplicate_claim', 'claims');
});
