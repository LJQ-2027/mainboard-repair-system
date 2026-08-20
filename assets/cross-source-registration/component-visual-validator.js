export const COMPONENT_VISUAL_STAGE_ORDER = Object.freeze([
  'blockout',
  'structure',
  'material',
  'polish',
]);

const SUPPORTED_ASSET_TYPES = new Set(['procedural']);
const CONNECTOR_PROHIBITED_CLAIMS = Object.freeze([
  'exact_pin_count',
  'exact_pin_pitch',
  'vendor_latch',
  'solder_foot_array',
  'internal_spring_geometry',
  'millimeter_dimensions',
]);
const IC_BGA_PROHIBITED_CLAIMS = Object.freeze([
  ...CONNECTOR_PROHIBITED_CLAIMS,
  'exact_ball_count',
  'exact_ball_pitch',
  'exact_pad_layout',
  'vendor_package',
  'die_or_internal_structure',
  'package_marking',
]);

const REQUIRED_SECTIONS = Object.freeze({
  materials: 'object',
  structure: 'object',
  claims: 'array',
  detail_levels: 'object',
  acceptance: 'object',
});

const REQUIRED_STRING_FIELDS = Object.freeze([
  'family',
  'source_status',
  'fidelity',
  'boundary_note',
]);

const CONNECTOR_STRUCTURE_SHAPES = Object.freeze({
  base: Object.freeze(['width', 'depth', 'height', 'radius']),
  frame: Object.freeze(['width', 'depth', 'height', 'wall', 'radius', 'lift']),
  opening: Object.freeze(['width', 'depth', 'height', 'radius', 'lift']),
  contact: Object.freeze(['width', 'depth', 'height', 'offset_y', 'lift']),
  retention: Object.freeze(['width', 'depth', 'height', 'inset_x', 'lift']),
  inner_lip: Object.freeze(['width', 'depth', 'height', 'wall', 'lift']),
});

const DETAIL_LEVELS = Object.freeze(['board', 'isolated']);

const CONNECTOR_DETAIL_PARTS = Object.freeze({
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

const FAMILY_CONTRACTS = Object.freeze({
  connector: Object.freeze({
    materialRoles: Object.freeze(['base', 'opening', 'frame', 'contact', 'edge']),
    structureShapes: CONNECTOR_STRUCTURE_SHAPES,
    detailPartsByStructure: CONNECTOR_DETAIL_PARTS,
    allowedClaims: Object.freeze([
      'connector_silhouette',
      'recessed_opening',
      'generic_contact_region',
    ]),
    prohibitedClaims: CONNECTOR_PROHIBITED_CLAIMS,
  }),
  ic_bga: Object.freeze({
    materialRoles: Object.freeze(['substrate', 'body', 'top', 'marker', 'edge']),
    structureShapes: Object.freeze({
      substrate: Object.freeze(['width', 'depth', 'height', 'radius']),
      body: Object.freeze(['width', 'depth', 'height', 'radius', 'lift']),
      top: Object.freeze(['width', 'depth', 'height', 'radius', 'lift']),
      marker: Object.freeze(['radius', 'offset_x', 'offset_y', 'height', 'lift']),
    }),
    detailPartsByStructure: Object.freeze({
      substrate: Object.freeze(['substrate', 'substrate-edges']),
      body: Object.freeze(['body', 'body-edges']),
      top: Object.freeze(['top', 'top-seam']),
      marker: Object.freeze(['orientation-marker']),
    }),
    allowedClaims: Object.freeze([
      'ic_package_silhouette',
      'substrate_body_hierarchy',
      'generic_orientation_cue',
    ]),
    prohibitedClaims: IC_BGA_PROHIBITED_CLAIMS,
  }),
});

function validationError(code, path, message) {
  return Object.freeze({ code, path, message });
}

function hasOwn(value, key) {
  return value !== null
    && value !== undefined
    && Object.prototype.hasOwnProperty.call(value, key);
}

function isPlainObject(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function hasExpectedSectionType(value, type) {
  return type === 'array' ? Array.isArray(value) : isPlainObject(value);
}

function hasDenseItems(value) {
  if (!Array.isArray(value)) return false;
  for (let index = 0; index < value.length; index += 1) {
    if (!hasOwn(value, index)) return false;
  }
  return true;
}

function hasCanonicalStages(stages) {
  return Array.isArray(stages)
    && hasDenseItems(stages)
    && stages.length === COMPONENT_VISUAL_STAGE_ORDER.length
    && stages.every((stage, index) => stage === COMPONENT_VISUAL_STAGE_ORDER[index]);
}

function validateRequiredSections(spec, errors) {
  const validSections = new Set();
  Object.entries(REQUIRED_SECTIONS).forEach(([section, type]) => {
    if (!hasOwn(spec, section) || spec[section] === undefined) {
      errors.push(validationError(
        'missing_section',
        section,
        `Required specification section is missing: ${section}`,
      ));
      return;
    }
    if (!hasExpectedSectionType(spec[section], type)) {
      errors.push(validationError(
        'invalid_section_type',
        section,
        `Specification section must be an ${type}: ${section}`,
      ));
      return;
    }
    validSections.add(section);
  });
  return validSections;
}

function validateRequiredMetadata(spec, errors) {
  REQUIRED_STRING_FIELDS.forEach((field) => {
    if (!hasOwn(spec, field)) {
      errors.push(validationError(
        'missing_required_field',
        field,
        `Required specification field is missing: ${field}`,
      ));
    } else if (typeof spec[field] !== 'string' || spec[field].trim() === '') {
      errors.push(validationError(
        'invalid_required_field',
        field,
        `Required specification field must be a non-empty string: ${field}`,
      ));
    }
  });

  if (!hasOwn(spec, 'inspection_profiles')) {
    errors.push(validationError(
      'missing_required_field',
      'inspection_profiles',
      'Required specification field is missing: inspection_profiles',
    ));
    return;
  }
  const profiles = spec.inspection_profiles;
  if (!Array.isArray(profiles) || profiles.length === 0) {
    errors.push(validationError(
      'invalid_inspection_profiles',
      'inspection_profiles',
      'Inspection profiles must be a non-empty array.',
    ));
    return;
  }
  for (let index = 0; index < profiles.length; index += 1) {
    const profileId = hasOwn(profiles, index) ? profiles[index] : undefined;
    if (typeof profileId !== 'string' || profileId.trim() === '') {
      errors.push(validationError(
        'invalid_inspection_profile',
        `inspection_profiles[${index}]`,
        'Inspection profile IDs must be non-empty strings.',
      ));
    }
  }
  if (new Set(profiles).size !== profiles.length) {
    errors.push(validationError(
      'duplicate_inspection_profile',
      'inspection_profiles',
      'Inspection profile IDs must be unique.',
    ));
  }
}

function validateAcceptance(acceptance, contract, errors) {
  const ratioMinimum = hasOwn(acceptance, 'ratio_min')
    ? acceptance.ratio_min
    : undefined;
  const ratioMaximum = hasOwn(acceptance, 'ratio_max')
    ? acceptance.ratio_max
    : undefined;
  let validBounds = true;

  if (!Number.isFinite(ratioMinimum) || ratioMinimum <= 0 || ratioMinimum > 1) {
    errors.push(validationError(
      'invalid_ratio_bounds',
      'acceptance.ratio_min',
      'Minimum ratio must be finite and normalized.',
    ));
    validBounds = false;
  }
  if (!Number.isFinite(ratioMaximum) || ratioMaximum < 0 || ratioMaximum > 1) {
    errors.push(validationError(
      'invalid_ratio_bounds',
      'acceptance.ratio_max',
      'Maximum ratio must be finite and normalized.',
    ));
    validBounds = false;
  }
  if (
    Number.isFinite(ratioMinimum)
    && Number.isFinite(ratioMaximum)
    && ratioMinimum > ratioMaximum
  ) {
    errors.push(validationError(
      'invalid_ratio_bounds',
      'acceptance',
      'Minimum ratio must not exceed maximum ratio.',
    ));
    validBounds = false;
  }

  if (!hasOwn(acceptance, 'prohibited_claims')) {
    errors.push(validationError(
      'missing_prohibited_claims',
      'acceptance.prohibited_claims',
      'The prohibited claim policy is required.',
    ));
  } else if (
    !Array.isArray(acceptance.prohibited_claims)
    || !hasDenseItems(acceptance.prohibited_claims)
    || acceptance.prohibited_claims.some((claim) => typeof claim !== 'string')
  ) {
    errors.push(validationError(
      'invalid_prohibited_claims',
      'acceptance.prohibited_claims',
      'Prohibited claims must be an array of claim names.',
    ));
  } else {
    const policy = new Set(acceptance.prohibited_claims);
    if (contract?.prohibitedClaims.some((claim) => !policy.has(claim))) {
      errors.push(validationError(
        'incomplete_prohibited_claims',
        'acceptance.prohibited_claims',
        'The prohibited claim policy is incomplete.',
      ));
    }
  }

  return validBounds ? { ratioMinimum, ratioMaximum } : null;
}

function validateMaterials(materials, materialCatalog, materialRoles, errors) {
  materialRoles.forEach((role) => {
    if (!hasOwn(materials, role)) {
      errors.push(validationError(
        'missing_material_role',
        `materials.${role}`,
        `Required material role is missing: ${role}`,
      ));
    }
  });
  Object.keys(materials).forEach((role) => {
    if (!materialRoles.includes(role)) {
      errors.push(validationError(
        'unknown_material_role',
        `materials.${role}`,
        `Unsupported material role: ${role}`,
      ));
      return;
    }
    const token = materials[role];
    if (typeof token !== 'string' || token.trim() === '') {
      errors.push(validationError(
        'invalid_material_token',
        `materials.${role}`,
        'Material tokens must be non-empty strings.',
      ));
    } else if (!hasOwn(materialCatalog, token)) {
      errors.push(validationError(
        'unknown_material',
        `materials.${role}`,
        `Unknown material token: ${token}`,
      ));
    }
  });
}

function validateStructure(structure, bounds, structureShapes, errors) {
  const validRoles = new Set();
  Object.keys(structureShapes).forEach((role) => {
    if (!hasOwn(structure, role)) {
      errors.push(validationError(
        'missing_structure_role',
        `structure.${role}`,
        `Required structure role is missing: ${role}`,
      ));
      return;
    }
    if (!isPlainObject(structure[role])) {
      errors.push(validationError(
        'invalid_structure_role',
        `structure.${role}`,
        `Structure role must be an object: ${role}`,
      ));
      return;
    }

    const shape = structure[role];
    const dimensions = structureShapes[role];
    let buildable = true;
    dimensions.forEach((dimension) => {
      const path = `structure.${role}.${dimension}`;
      if (!hasOwn(shape, dimension)) {
        buildable = false;
        errors.push(validationError(
          'missing_structure_dimension',
          path,
          `Required structure dimension is missing: ${dimension}`,
        ));
        return;
      }
      const value = shape[dimension];
      if (typeof value !== 'number') {
        buildable = false;
        errors.push(validationError(
          'invalid_structure_dimension',
          path,
          'Structure dimensions must be numeric.',
        ));
      } else if (
        !Number.isFinite(value)
        || (bounds && (value < bounds.ratioMinimum || value > bounds.ratioMaximum))
      ) {
        buildable = false;
        errors.push(validationError(
          'ratio_out_of_range',
          path,
          'Structure ratios must remain inside acceptance bounds.',
        ));
      }
    });
    Object.keys(shape).forEach((dimension) => {
      if (!dimensions.includes(dimension)) {
        buildable = false;
        errors.push(validationError(
          'unknown_structure_dimension',
          `structure.${role}.${dimension}`,
          `Unsupported structure dimension: ${dimension}`,
        ));
      }
    });
    if (buildable) validRoles.add(role);
  });

  Object.keys(structure).forEach((role) => {
    if (!hasOwn(structureShapes, role)) {
      errors.push(validationError(
        'unknown_structure_role',
        `structure.${role}`,
        `Unsupported structure role: ${role}`,
      ));
    }
  });
  return validRoles;
}

function declaredDetailParts(validStructureRoles, detailPartsByStructure) {
  const names = new Set();
  validStructureRoles.forEach((structureName) => {
    (detailPartsByStructure[structureName] || []).forEach((name) => names.add(name));
  });
  return names;
}

function resolveFamilyContract(spec, errors) {
  if (typeof spec?.family !== 'string' || spec.family.trim() === '') return null;
  if (!hasOwn(FAMILY_CONTRACTS, spec.family)) {
    errors.push(validationError(
      'unsupported_family',
      'family',
      `Unsupported component visual family: ${spec.family}`,
    ));
    return null;
  }
  return FAMILY_CONTRACTS[spec.family];
}

function validateDetailLevels(detailLevels, declaredParts, errors) {
  DETAIL_LEVELS.forEach((level) => {
    if (!hasOwn(detailLevels, level)) {
      errors.push(validationError(
        'missing_detail_level',
        `detail_levels.${level}`,
        `Required detail level is missing: ${level}`,
      ));
      return;
    }
    const names = detailLevels[level];
    if (!Array.isArray(names)) {
      errors.push(validationError(
        'invalid_detail_level',
        `detail_levels.${level}`,
        `Detail level must be an array: ${level}`,
      ));
      return;
    }
    if (names.length === 0) {
      errors.push(validationError(
        'empty_detail_level',
        `detail_levels.${level}`,
        `Detail level must not be empty: ${level}`,
      ));
    }
    if (new Set(names).size !== names.length) {
      errors.push(validationError(
        'duplicate_part_name',
        `detail_levels.${level}`,
        'Part names must be unique.',
      ));
    }
    for (let index = 0; index < names.length; index += 1) {
      const name = hasOwn(names, index) ? names[index] : undefined;
      const path = `detail_levels.${level}[${index}]`;
      if (typeof name !== 'string' || name.trim() === '') {
        errors.push(validationError(
          'invalid_part_name',
          path,
          'Detail part names must be non-empty strings.',
        ));
      } else if (!declaredParts.has(name)) {
        errors.push(validationError(
          'undeclared_detail_part',
          path,
          `Detail part is not backed by declared structure: ${name}`,
        ));
      }
    }
  });
  Object.keys(detailLevels).forEach((level) => {
    if (!DETAIL_LEVELS.includes(level)) {
      errors.push(validationError(
        'unknown_detail_level',
        `detail_levels.${level}`,
        `Unsupported detail level: ${level}`,
      ));
    }
  });
}

function validateComponentVisualSpecUnsafe(spec, materialCatalog) {
  const errors = [];

  if (
    !hasOwn(spec, 'spec_id')
    || typeof spec.spec_id !== 'string'
    || spec.spec_id.trim() === ''
  ) {
    errors.push(validationError(
      'invalid_identity',
      'spec_id',
      'A stable specification ID is required.',
    ));
  }
  if (!hasOwn(spec, 'version') || !Number.isInteger(spec.version) || spec.version < 1) {
    errors.push(validationError(
      'invalid_version',
      'version',
      'A positive integer specification version is required.',
    ));
  }
  if (!hasOwn(spec, 'asset_type') || !SUPPORTED_ASSET_TYPES.has(spec.asset_type)) {
    errors.push(validationError(
      'unsupported_asset_type',
      'asset_type',
      'Only procedural assets are supported.',
    ));
  }
  if (!hasOwn(spec, 'stages') || !hasCanonicalStages(spec.stages)) {
    errors.push(validationError(
      'invalid_stage_order',
      'stages',
      'Build stages must use the canonical order.',
    ));
  }

  validateRequiredMetadata(spec, errors);
  const familyContract = resolveFamilyContract(spec, errors);
  const validSections = validateRequiredSections(spec, errors);
  const bounds = validSections.has('acceptance')
    ? validateAcceptance(spec.acceptance, familyContract, errors)
    : null;
  if (validSections.has('materials') && familyContract) {
    validateMaterials(
      spec.materials,
      isPlainObject(materialCatalog) ? materialCatalog : {},
      familyContract.materialRoles,
      errors,
    );
  }
  const validStructureRoles = validSections.has('structure') && familyContract
    ? validateStructure(
      spec.structure,
      bounds,
      familyContract.structureShapes,
      errors,
    )
    : new Set();
  if (validSections.has('claims')) {
    if (spec.claims.length === 0) {
      errors.push(validationError(
        'invalid_claims',
        'claims',
        'Claims must be a non-empty array.',
      ));
    }
    if (new Set(spec.claims).size !== spec.claims.length) {
      errors.push(validationError(
        'duplicate_claim',
        'claims',
        'Claims must be unique.',
      ));
    }
    for (let index = 0; index < spec.claims.length; index += 1) {
      const claim = hasOwn(spec.claims, index) ? spec.claims[index] : undefined;
      if (typeof claim !== 'string' || claim.trim() === '') {
        errors.push(validationError(
          'invalid_claim',
          `claims[${index}]`,
          'Claims must be non-empty strings.',
        ));
      } else if (familyContract?.prohibitedClaims.includes(claim)) {
        errors.push(validationError(
          'prohibited_claim',
          'claims',
          `Unsupported engineering claim: ${claim}`,
        ));
      } else if (familyContract && !familyContract.allowedClaims.includes(claim)) {
        errors.push(validationError(
          'unsupported_claim',
          `claims[${index}]`,
          `Claim is not supported by the selected family: ${claim}`,
        ));
      }
    }
  }
  if (validSections.has('detail_levels') && familyContract) {
    validateDetailLevels(
      spec.detail_levels,
      declaredDetailParts(
        validStructureRoles,
        familyContract.detailPartsByStructure,
      ),
      errors,
    );
  }

  return Object.freeze({
    valid: errors.length === 0,
    errors: Object.freeze(errors),
  });
}

export function validateComponentVisualSpec(spec, materialCatalog = {}) {
  try {
    return validateComponentVisualSpecUnsafe(spec, materialCatalog);
  } catch {
    return Object.freeze({
      valid: false,
      errors: Object.freeze([
        validationError(
          'malformed_spec',
          '',
          'Component visual specification could not be inspected safely.',
        ),
      ]),
    });
  }
}
