export const COMPONENT_VISUAL_STAGE_ORDER = Object.freeze([
  'blockout',
  'structure',
  'material',
  'polish',
]);

const SUPPORTED_ASSET_TYPES = new Set(['procedural']);
const PROHIBITED_CLAIMS = new Set([
  'exact_pin_count',
  'exact_pin_pitch',
  'vendor_latch',
  'solder_foot_array',
  'internal_spring_geometry',
  'millimeter_dimensions',
]);

const DETAIL_PARTS_BY_STRUCTURE = Object.freeze({
  base: Object.freeze(['base']),
  frame: Object.freeze([
    'frame-north',
    'frame-south',
    'frame-west',
    'frame-east',
    'frame-edges',
  ]),
  opening: Object.freeze(['opening']),
  contact: Object.freeze(['contact']),
  retention: Object.freeze(['retention-west', 'retention-east']),
  inner_lip: Object.freeze([
    'inner-lip-north',
    'inner-lip-south',
    'inner-lip-west',
    'inner-lip-east',
  ]),
});

function validationError(code, path, message) {
  return Object.freeze({ code, path, message });
}

function structureLeaves(value, path = 'structure') {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return [];
  return Object.entries(value).flatMap(([key, item]) => {
    const itemPath = `${path}.${key}`;
    if (item && typeof item === 'object' && !Array.isArray(item)) {
      return structureLeaves(item, itemPath);
    }
    return [[itemPath, item]];
  });
}

function hasCanonicalStages(stages) {
  return Array.isArray(stages)
    && stages.length === COMPONENT_VISUAL_STAGE_ORDER.length
    && stages.every((stage, index) => stage === COMPONENT_VISUAL_STAGE_ORDER[index]);
}

function declaredDetailParts(structure) {
  const names = new Set();
  Object.keys(structure || {}).forEach((structureName) => {
    (DETAIL_PARTS_BY_STRUCTURE[structureName] || []).forEach((name) => names.add(name));
  });
  return names;
}

export function validateComponentVisualSpec(spec, materialCatalog = {}) {
  const errors = [];

  if (typeof spec?.spec_id !== 'string' || spec.spec_id.trim() === '') {
    errors.push(validationError(
      'invalid_identity',
      'spec_id',
      'A stable specification ID is required.',
    ));
  }
  if (!Number.isInteger(spec?.version) || spec.version < 1) {
    errors.push(validationError(
      'invalid_version',
      'version',
      'A positive integer specification version is required.',
    ));
  }
  if (!SUPPORTED_ASSET_TYPES.has(spec?.asset_type)) {
    errors.push(validationError(
      'unsupported_asset_type',
      'asset_type',
      'Only procedural assets are supported.',
    ));
  }
  if (!hasCanonicalStages(spec?.stages)) {
    errors.push(validationError(
      'invalid_stage_order',
      'stages',
      'Build stages must use the canonical order.',
    ));
  }

  Object.entries(spec?.materials || {}).forEach(([role, token]) => {
    if (!Object.prototype.hasOwnProperty.call(materialCatalog, token)) {
      errors.push(validationError(
        'unknown_material',
        `materials.${role}`,
        `Unknown material token: ${token}`,
      ));
    }
  });

  const ratioMinimum = spec?.acceptance?.ratio_min;
  const ratioMaximum = spec?.acceptance?.ratio_max;
  structureLeaves(spec?.structure).forEach(([path, value]) => {
    if (
      !Number.isFinite(value)
      || !Number.isFinite(ratioMinimum)
      || !Number.isFinite(ratioMaximum)
      || value < ratioMinimum
      || value > ratioMaximum
    ) {
      errors.push(validationError(
        'ratio_out_of_range',
        path,
        'Structure ratios must remain inside acceptance bounds.',
      ));
    }
  });

  (Array.isArray(spec?.claims) ? spec.claims : []).forEach((claim) => {
    if (PROHIBITED_CLAIMS.has(claim)) {
      errors.push(validationError(
        'prohibited_claim',
        'claims',
        `Unsupported engineering claim: ${claim}`,
      ));
    }
  });

  const declaredParts = declaredDetailParts(spec?.structure);
  Object.entries(spec?.detail_levels || {}).forEach(([level, names]) => {
    if (!Array.isArray(names)) return;
    if (new Set(names).size !== names.length) {
      errors.push(validationError(
        'duplicate_part_name',
        `detail_levels.${level}`,
        'Part names must be unique.',
      ));
    }
    names.forEach((name, index) => {
      if (!declaredParts.has(name)) {
        errors.push(validationError(
          'undeclared_detail_part',
          `detail_levels.${level}[${index}]`,
          `Detail part is not backed by declared structure: ${name}`,
        ));
      }
    });
  });

  return Object.freeze({
    valid: errors.length === 0,
    errors: Object.freeze(errors),
  });
}
