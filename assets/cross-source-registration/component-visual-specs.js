export const COMPONENT_VISUAL_MATERIALS = Object.freeze({
  'engineering-plastic': Object.freeze({
    color: 0x2c3632,
    roughness: 0.64,
    metalness: 0.12,
  }),
  'recessed-polymer': Object.freeze({
    color: 0x0d1412,
    roughness: 0.74,
    metalness: 0.04,
  }),
  'plated-metal': Object.freeze({
    color: 0xbfc6c2,
    roughness: 0.27,
    metalness: 0.8,
  }),
  'contact-metal': Object.freeze({
    color: 0xc79a4b,
    roughness: 0.3,
    metalness: 0.74,
  }),
  'edge-line': Object.freeze({
    color: 0x66736d,
    opacity: 0.72,
  }),
  'ic-substrate': Object.freeze({
    color: 0x31443d,
    roughness: 0.66,
    metalness: 0.08,
  }),
  'molded-package': Object.freeze({
    color: 0x171d1b,
    roughness: 0.58,
    metalness: 0.12,
  }),
  'inset-top': Object.freeze({
    color: 0x232a27,
    roughness: 0.52,
    metalness: 0.16,
  }),
  'orientation-marker': Object.freeze({
    color: 0xaab3ad,
    roughness: 0.45,
    metalness: 0.2,
  }),
});

export const J6101_CONNECTOR_VISUAL_SPEC = Object.freeze({
  spec_id: 'connector-j6101-repair-visual-v1',
  version: 1,
  asset_type: 'procedural',
  family: 'connector',
  inspection_profiles: Object.freeze(['j6101-connector-v1']),
  source_status: 'category_based',
  fidelity: 'repair_visual',
  boundary_note: '连接器结构为维修识别示意，不代表准确针脚、间距、卡扣或工程尺寸。',
  claims: Object.freeze([
    'connector_silhouette',
    'recessed_opening',
    'generic_contact_region',
  ]),
  materials: Object.freeze({
    base: 'engineering-plastic',
    opening: 'recessed-polymer',
    frame: 'plated-metal',
    contact: 'contact-metal',
    edge: 'edge-line',
  }),
  structure: Object.freeze({
    base: Object.freeze({
      width: 1,
      depth: 1,
      height: 0.24,
      radius: 0.055,
    }),
    frame: Object.freeze({
      width: 0.94,
      depth: 0.88,
      height: 0.62,
      wall: 0.14,
      radius: 0.045,
      lift: 0.2,
    }),
    opening: Object.freeze({
      width: 0.64,
      depth: 0.34,
      height: 0.14,
      radius: 0.035,
      lift: 0.25,
    }),
    contact: Object.freeze({
      width: 0.56,
      depth: 0.075,
      height: 0.055,
      offset_y: 0.075,
      lift: 0.34,
    }),
    retention: Object.freeze({
      width: 0.075,
      depth: 0.68,
      height: 0.68,
      inset_x: 0.42,
      lift: 0.2,
    }),
    inner_lip: Object.freeze({
      width: 0.72,
      depth: 0.48,
      height: 0.08,
      wall: 0.055,
      lift: 0.48,
    }),
  }),
  detail_levels: Object.freeze({
    board: Object.freeze([
      'base',
      'frame-north',
      'frame-south',
      'frame-west',
      'frame-east',
      'opening',
      'contact',
    ]),
    isolated: Object.freeze([
      'base',
      'frame-north',
      'frame-south',
      'frame-west',
      'frame-east',
      'opening',
      'contact',
      'retention-west',
      'retention-east',
      'inner-lip-north',
      'inner-lip-south',
      'inner-lip-west',
      'inner-lip-east',
      'frame-edges',
    ]),
  }),
  stages: Object.freeze(['blockout', 'structure', 'material', 'polish']),
  acceptance: Object.freeze({
    ratio_min: 0.02,
    ratio_max: 1,
    prohibited_claims: Object.freeze([
      'exact_pin_count',
      'exact_pin_pitch',
      'vendor_latch',
      'solder_foot_array',
      'internal_spring_geometry',
      'millimeter_dimensions',
    ]),
  }),
});

export const U2001_PMIC_VISUAL_SPEC = Object.freeze({
  spec_id: 'ic-bga-u2001-repair-visual-v1',
  version: 1,
  asset_type: 'procedural',
  family: 'ic_bga',
  inspection_profiles: Object.freeze(['u2001-pmic-v1']),
  source_status: 'category_based',
  fidelity: 'repair_visual',
  boundary_note: '电源管理 IC 结构为维修识别示意，不代表准确封装、球数、球距、焊盘、丝印、内部结构或工程尺寸。',
  claims: Object.freeze([
    'ic_package_silhouette',
    'substrate_body_hierarchy',
    'generic_orientation_cue',
  ]),
  materials: Object.freeze({
    substrate: 'ic-substrate',
    body: 'molded-package',
    top: 'inset-top',
    marker: 'orientation-marker',
    edge: 'edge-line',
  }),
  structure: Object.freeze({
    substrate: Object.freeze({
      width: 1,
      depth: 1,
      height: 0.12,
      radius: 0.045,
    }),
    body: Object.freeze({
      width: 0.88,
      depth: 0.88,
      height: 0.62,
      radius: 0.065,
      lift: 0.12,
    }),
    top: Object.freeze({
      width: 0.74,
      depth: 0.74,
      height: 0.055,
      radius: 0.05,
      lift: 0.72,
    }),
    marker: Object.freeze({
      radius: 0.045,
      offset_x: 0.31,
      offset_y: 0.31,
      height: 0.025,
      lift: 0.775,
    }),
  }),
  detail_levels: Object.freeze({
    board: Object.freeze([
      'substrate',
      'body',
      'top',
      'orientation-marker',
    ]),
    isolated: Object.freeze([
      'substrate',
      'body',
      'top',
      'orientation-marker',
      'substrate-edges',
      'body-edges',
      'top-seam',
    ]),
  }),
  stages: Object.freeze(['blockout', 'structure', 'material', 'polish']),
  acceptance: Object.freeze({
    ratio_min: 0.02,
    ratio_max: 1,
    prohibited_claims: Object.freeze([
      'exact_pin_count',
      'exact_pin_pitch',
      'vendor_latch',
      'solder_foot_array',
      'internal_spring_geometry',
      'millimeter_dimensions',
      'exact_ball_count',
      'exact_ball_pitch',
      'exact_pad_layout',
      'vendor_package',
      'die_or_internal_structure',
      'package_marking',
    ]),
  }),
});

export function buildComponentVisualSpecCatalog(specs) {
  const catalog = new Map();
  specs.forEach((spec) => {
    spec.inspection_profiles.forEach((profileId) => {
      if (catalog.has(profileId)) {
        throw new Error(`Duplicate inspection profile: ${profileId}`);
      }
      catalog.set(profileId, spec);
    });
  });
  return catalog;
}

const SPEC_BY_INSPECTION_PROFILE = buildComponentVisualSpecCatalog([
  J6101_CONNECTOR_VISUAL_SPEC,
  U2001_PMIC_VISUAL_SPEC,
]);

export function resolveComponentVisualSpec(inspectionProfileId) {
  return SPEC_BY_INSPECTION_PROFILE.get(inspectionProfileId) || null;
}
