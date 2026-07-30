import * as THREE from '../vendor/three/three.module.min.js';
import {
  COMPONENT_VISUAL_MATERIALS,
  resolveComponentVisualSpec,
} from './component-visual-specs.js';
import { validateComponentVisualSpec } from './component-visual-validator.js';

const DETAIL_LEVELS = new Set(['board', 'isolated']);
const DIMENSION_KEYS = Object.freeze(['x', 'y', 'z']);

function hasValidDimensions(dimensions) {
  return dimensions !== null
    && typeof dimensions === 'object'
    && DIMENSION_KEYS.every(
      (key) => Number.isFinite(dimensions[key]) && dimensions[key] > 0,
    );
}

function ownResource(ownership, type, resource) {
  ownership?.[type].add(resource);
  return resource;
}

function disposeOwnedResources(ownership) {
  if (!ownership) return;
  ownership.geometries.forEach((geometry) => geometry.dispose());
  ownership.materials.forEach((material) => material.dispose());
}

function materialFor(spec, role, ownership) {
  const token = spec.materials[role];
  const values = COMPONENT_VISUAL_MATERIALS[token];
  if (role === 'edge') {
    return {
      material: ownResource(
        ownership,
        'materials',
        new THREE.LineBasicMaterial({
          color: values.color,
          transparent: true,
          opacity: values.opacity,
        }),
      ),
      token,
    };
  }
  return {
    material: ownResource(
      ownership,
      'materials',
      new THREE.MeshStandardMaterial({
        color: values.color,
        roughness: values.roughness,
        metalness: values.metalness,
      }),
    ),
    token,
  };
}

function roundedShape(width, depth, radius) {
  const halfWidth = width / 2;
  const halfDepth = depth / 2;
  const safeRadius = Math.max(0, Math.min(radius, halfWidth, halfDepth));
  const shape = new THREE.Shape();
  shape.moveTo(-halfWidth + safeRadius, -halfDepth);
  shape.lineTo(halfWidth - safeRadius, -halfDepth);
  shape.quadraticCurveTo(halfWidth, -halfDepth, halfWidth, -halfDepth + safeRadius);
  shape.lineTo(halfWidth, halfDepth - safeRadius);
  shape.quadraticCurveTo(halfWidth, halfDepth, halfWidth - safeRadius, halfDepth);
  shape.lineTo(-halfWidth + safeRadius, halfDepth);
  shape.quadraticCurveTo(-halfWidth, halfDepth, -halfWidth, halfDepth - safeRadius);
  shape.lineTo(-halfWidth, -halfDepth + safeRadius);
  shape.quadraticCurveTo(-halfWidth, -halfDepth, -halfWidth + safeRadius, -halfDepth);
  return shape;
}

function roundedPart(
  spec,
  role,
  name,
  width,
  depth,
  height,
  radius,
  lift = 0,
  ownership,
) {
  const safeRadius = Math.min(radius, width / 2, depth / 2);
  const bevelSize = Math.min(
    safeRadius * 0.28,
    width * 0.015,
    depth * 0.015,
  );
  const bevelThickness = Math.min(height * 0.08, height / 4);
  const shapeWidth = width - bevelSize * 2;
  const shapeDepth = depth - bevelSize * 2;
  const shapeRadius = Math.max(0, safeRadius - bevelSize);
  const coreHeight = height - bevelThickness * 2;
  const geometry = ownResource(
    ownership,
    'geometries',
    new THREE.ExtrudeGeometry(
      roundedShape(shapeWidth, shapeDepth, shapeRadius),
      {
        depth: coreHeight,
        bevelEnabled: true,
        bevelSize,
        bevelThickness,
        bevelSegments: 2,
        curveSegments: 6,
        steps: 1,
      },
    ),
  );
  const mesh = new THREE.Mesh(geometry, null);
  mesh.name = name;
  mesh.userData.visualPart = name;
  mesh.userData.visualMaterial = spec.materials[role];
  mesh.userData.visualMaterialRole = role;
  mesh.position.z = lift + bevelThickness;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function addPart(context, name, source, role, position = {}) {
  if (!context.allowed.has(name)) return null;
  const { dimensions, group, spec } = context;
  const part = roundedPart(
    spec,
    role,
    name,
    dimensions.x * source.width,
    dimensions.y * source.depth,
    dimensions.z * source.height,
    Math.min(dimensions.x, dimensions.y) * (source.radius || 0.02),
    dimensions.z * (source.lift || 0),
    context.ownership,
  );
  part.position.x = dimensions.x * (position.x || 0);
  part.position.y = dimensions.y * (position.y || 0);
  group.add(part);
  return part;
}

function blockout(context) {
  addPart(context, 'base', context.spec.structure.base, 'base');
}

function addFrame(context) {
  const { dimensions, spec } = context;
  const frame = spec.structure.frame;
  const width = dimensions.x * frame.width;
  const depth = dimensions.y * frame.depth;
  const wallX = dimensions.x * frame.wall;
  const wallY = dimensions.y * frame.wall;
  const sourceRadius = Math.min(dimensions.x, dimensions.y) * frame.radius;
  const parts = [
    ['frame-north', width - wallX * 2, wallY, 0, (depth - wallY) / 2],
    ['frame-south', width - wallX * 2, wallY, 0, -(depth - wallY) / 2],
    ['frame-west', wallX, depth, -(width - wallX) / 2, 0],
    ['frame-east', wallX, depth, (width - wallX) / 2, 0],
  ];
  parts.forEach(([name, partWidth, partDepth, x, y]) => {
    if (!context.allowed.has(name)) return;
    const part = roundedPart(
      spec,
      'frame',
      name,
      partWidth,
      partDepth,
      dimensions.z * frame.height,
      sourceRadius,
      dimensions.z * frame.lift,
      context.ownership,
    );
    part.position.x = x;
    part.position.y = y;
    context.group.add(part);
  });
}

function addInnerLip(context) {
  const lip = context.spec.structure.inner_lip;
  const horizontal = {
    width: lip.width,
    depth: lip.wall,
    height: lip.height,
    radius: 0.02,
    lift: lip.lift,
  };
  const vertical = {
    width: lip.wall,
    depth: lip.depth,
    height: lip.height,
    radius: 0.02,
    lift: lip.lift,
  };
  addPart(context, 'inner-lip-north', horizontal, 'frame', {
    y: (lip.depth - lip.wall) / 2,
  });
  addPart(context, 'inner-lip-south', horizontal, 'frame', {
    y: -(lip.depth - lip.wall) / 2,
  });
  addPart(context, 'inner-lip-west', vertical, 'frame', {
    x: -(lip.width - lip.wall) / 2,
  });
  addPart(context, 'inner-lip-east', vertical, 'frame', {
    x: (lip.width - lip.wall) / 2,
  });
}

function structure(context) {
  addFrame(context);
  addPart(context, 'opening', context.spec.structure.opening, 'opening');
  addPart(context, 'contact', context.spec.structure.contact, 'contact', {
    y: context.spec.structure.contact.offset_y,
  });

  const retention = context.spec.structure.retention;
  addPart(context, 'retention-west', retention, 'frame', {
    x: -retention.inset_x,
  });
  addPart(context, 'retention-east', retention, 'frame', {
    x: retention.inset_x,
  });
  addInnerLip(context);
}

function material(context) {
  context.group.traverse((child) => {
    if (!child.isMesh) return;
    child.material = materialFor(
      context.spec,
      child.userData.visualMaterialRole,
      context.ownership,
    ).material;
  });
}

function polish(context) {
  if (!context.allowed.has('frame-edges')) return;
  const edgeGroup = new THREE.Group();
  edgeGroup.name = 'frame-edges';
  edgeGroup.userData.visualPart = 'frame-edges';
  context.group.children
    .filter((child) => /^frame-(north|south|west|east)$/.test(child.name))
    .forEach((source) => {
      const { material: edgeMaterial, token } = materialFor(
        context.spec,
        'edge',
        context.ownership,
      );
      const edge = new THREE.LineSegments(
        ownResource(
          context.ownership,
          'geometries',
          new THREE.EdgesGeometry(source.geometry, 28),
        ),
        edgeMaterial,
      );
      edge.name = `${source.name}-edge`;
      edge.userData.visualPart = 'frame-edges';
      edge.userData.visualMaterial = token;
      edge.position.copy(source.position);
      edgeGroup.add(edge);
    });
  context.group.add(edgeGroup);
}

const BUILD_STAGES = Object.freeze([
  ['blockout', blockout],
  ['structure', structure],
  ['material', material],
  ['polish', polish],
]);

function finishMetadata(group, spec, detailLevel, stages) {
  const names = group.children
    .map((child) => child.userData.visualPart)
    .filter(Boolean)
    .sort();
  group.userData.visualSpecId = spec.spec_id;
  group.userData.visualSpecVersion = spec.version;
  group.userData.visualAssetType = spec.asset_type;
  group.userData.visualDetailLevel = detailLevel;
  group.userData.visualStages = stages;
  group.userData.visualPartNames = names;
  group.userData.visualBoundaryNote = spec.boundary_note;
}

export function disposeComponentVisual(group) {
  const ownership = {
    geometries: new Set(),
    materials: new Set(),
  };
  if (!group || typeof group.traverse !== 'function') {
    return { geometries: 0, materials: 0 };
  }
  group.traverse((child) => {
    if (child.geometry?.dispose) ownership.geometries.add(child.geometry);
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material];
    materials
      .filter((material) => material?.dispose)
      .forEach((material) => ownership.materials.add(material));
  });
  disposeOwnedResources(ownership);
  return {
    geometries: ownership.geometries.size,
    materials: ownership.materials.size,
  };
}

export function componentVisualBounds(group) {
  const box = new THREE.Box3().setFromObject(group);
  const size = new THREE.Vector3();
  box.getSize(size);
  return { width: size.x, depth: size.y, height: size.z };
}

export function buildComponentVisual(
  descriptor,
  detailLevel = 'board',
  dependencies = {},
) {
  let ownership = null;
  try {
    const resolveSpec = typeof dependencies.resolveSpec === 'function'
      ? dependencies.resolveSpec
      : resolveComponentVisualSpec;
    const spec = resolveSpec(descriptor?.inspectionProfile?.profile_id);
    if (!spec) return { group: null, fallbackReason: 'visual_spec_not_found' };
    if (!DETAIL_LEVELS.has(detailLevel)) {
      return { group: null, fallbackReason: 'unknown_detail_level' };
    }
    if (!hasValidDimensions(descriptor?.dimensions)) {
      return { group: null, fallbackReason: 'invalid_dimensions' };
    }

    const validation = validateComponentVisualSpec(spec, COMPONENT_VISUAL_MATERIALS);
    if (!validation.valid) {
      return { group: null, fallbackReason: validation.errors[0].code };
    }

    ownership = {
      geometries: new Set(),
      materials: new Set(),
    };
    const context = {
      allowed: new Set(spec.detail_levels[detailLevel]),
      dimensions: descriptor.dimensions,
      group: new THREE.Group(),
      ownership,
      spec,
    };
    const completedStages = [];
    BUILD_STAGES.forEach(([name, buildStage]) => {
      buildStage(context);
      completedStages.push(name);
    });
    finishMetadata(context.group, spec, detailLevel, completedStages);
    return { group: context.group, fallbackReason: null };
  } catch {
    disposeOwnedResources(ownership);
    return { group: null, fallbackReason: 'visual_build_error' };
  }
}
