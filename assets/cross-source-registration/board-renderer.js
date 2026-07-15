import * as THREE from '../vendor/three/three.module.min.js';
import {
  BOARD_WORLD_SIZE,
  buildCameraFrame,
  buildFocusFrame,
  buildRenderDescriptor,
  buildSelectionRadius,
  buildUnresolvedMarkerPresentation,
} from './model-profiles.js';
import {
  getShieldPresentation,
  isPointCovered,
} from './anatomy-state.js';
import { buildInspectionTransform, inspectionOpacity } from './component-inspection-state.js';
import { transformBoardCenter } from './model-interaction-state.js';
import {
  anchorZoomCenter,
  clampPanCenter,
  pinchZoom,
  resolveBoardInteractionMode,
  screenDeltaToPan,
} from './board-pan-state.js';
import {
  buildCornerSegments,
  buildHitArea,
  buildScreenLabelPositions,
  buildScreenAwareHitScale,
  placeHoverTooltip,
  resolveAffordancePresentation,
} from './component-affordance-state.js';

const COLORS = {
  board: 0x17473e,
  boardEdge: 0xb4823a,
  copper: 0xc99149,
  dark: 0x202927,
  ink: 0x111816,
  metal: 0xaeb6b1,
  outline: 0x73827b,
  selected: 0xf2c94c,
};
const TOP_VIEW_TILT = -0.012;

const MATERIALS = {
  dark: { color: COLORS.dark, roughness: 0.62, metalness: 0.12 },
  black: { color: COLORS.ink, roughness: 0.5, metalness: 0.16 },
  metal: { color: COLORS.metal, roughness: 0.28, metalness: 0.78 },
  copper: { color: COLORS.copper, roughness: 0.34, metalness: 0.7 },
  ceramic: { color: 0xb9b4a5, roughness: 0.72, metalness: 0.04 },
  inductor: { color: 0x343c38, roughness: 0.82, metalness: 0.06 },
};

function material(name, overrides = {}) {
  return new THREE.MeshStandardMaterial({ ...MATERIALS[name], ...overrides });
}

function box(width, depth, height, meshMaterial) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, depth, height), meshMaterial);
  mesh.position.z = height / 2;
  return mesh;
}

function roundedRectShape(width, height, radius) {
  const x = -width / 2;
  const y = -height / 2;
  const shape = new THREE.Shape();
  shape.moveTo(x + radius, y);
  shape.lineTo(x + width - radius, y);
  shape.quadraticCurveTo(x + width, y, x + width, y + radius);
  shape.lineTo(x + width, y + height - radius);
  shape.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  shape.lineTo(x + radius, y + height);
  shape.quadraticCurveTo(x, y + height, x, y + height - radius);
  shape.lineTo(x, y + radius);
  shape.quadraticCurveTo(x, y, x + radius, y);
  return shape;
}

function captureMaterialState(object) {
  object.traverse((child) => {
    if (!child.material) return;
    child.userData.baseOpacity = child.material.opacity;
    child.userData.baseTransparent = child.material.transparent;
    child.userData.baseDepthWrite = child.material.depthWrite;
  });
}

function addPassivePackage(group, descriptor) {
  const { x, y, z } = descriptor.dimensions;
  const terminalWidth = Math.max(x * 0.2, 0.004);
  const bodyMaterial = descriptor.category === 'resistor' ? material('dark') : material('ceramic');
  group.add(box(Math.max(x - terminalWidth * 2, 0.004), y, z * 0.86, bodyMaterial));
  [-1, 1].forEach((side) => {
    const terminal = box(terminalWidth, y, z, material('metal'));
    terminal.position.x = side * (x - terminalWidth) / 2;
    group.add(terminal);
  });
}

function addIcPackage(group, descriptor) {
  const { x, y, z } = descriptor.dimensions;
  group.add(box(x, y, z, material('black')));
  const dotRadius = Math.max(Math.min(x, y) * 0.055, 0.0022);
  const dot = new THREE.Mesh(
    new THREE.CylinderGeometry(dotRadius, dotRadius, 0.0018, 16),
    material('ceramic', { color: 0x858d89 }),
  );
  dot.rotation.x = Math.PI / 2;
  dot.position.set(-x * 0.3, y * 0.3, z + 0.001);
  group.add(dot);
}

function addInspectionPmicPackage(group, descriptor) {
  const { x, y, z } = descriptor.dimensions;
  const radius = Math.min(x, y) * 0.075;
  const substrateMaterial = material('copper', { color: 0x4d5948, roughness: 0.52, metalness: 0.3 });
  const substrate = new THREE.Mesh(
    new THREE.ExtrudeGeometry(roundedRectShape(x, y, radius * 0.72), {
      depth: z * 0.24,
      bevelEnabled: true,
      bevelSize: Math.min(radius * 0.24, 0.003),
      bevelThickness: 0.0015,
      bevelSegments: 2,
    }),
    substrateMaterial,
  );
  group.add(substrate);
  const substrateEdge = new THREE.LineSegments(
    new THREE.EdgesGeometry(substrate.geometry, 24),
    new THREE.LineBasicMaterial({ color: 0x9b7742, transparent: true, opacity: 0.78 }),
  );
  group.add(substrateEdge);

  const body = new THREE.Mesh(
    new THREE.ExtrudeGeometry(roundedRectShape(x * 0.94, y * 0.94, radius), {
      depth: z * 0.7,
      bevelEnabled: true,
      bevelSize: Math.min(radius * 0.55, 0.006),
      bevelThickness: Math.min(z * 0.08, 0.003),
      bevelSegments: 3,
    }),
    material('black', { color: 0x151a19, roughness: 0.38, metalness: 0.2 }),
  );
  body.position.z = z * 0.22;
  group.add(body);

  const top = new THREE.Mesh(
    new THREE.ShapeGeometry(roundedRectShape(x * 0.76, y * 0.72, radius * 0.65)),
    material('dark', { color: 0x29302e, roughness: 0.5, metalness: 0.12 }),
  );
  top.position.z = z * 0.94;
  group.add(top);

  const dotRadius = Math.max(Math.min(x, y) * 0.045, 0.003);
  const dot = new THREE.Mesh(
    new THREE.CircleGeometry(dotRadius, 24),
    material('ceramic', { color: 0xa6ada8, roughness: 0.62 }),
  );
  dot.position.set(-x * 0.31, y * 0.31, z * 0.955);
  group.add(dot);

  const edge = new THREE.LineSegments(
    new THREE.EdgesGeometry(body.geometry, 24),
    new THREE.LineBasicMaterial({ color: 0x4f5955, transparent: true, opacity: 0.72 }),
  );
  edge.position.copy(body.position);
  group.add(edge);
  group.userData.inspectionProfileId = descriptor.inspectionProfile.profile_id;
}

function addConnectorPackage(group, descriptor) {
  const { x, y, z } = descriptor.dimensions;
  group.add(box(x, y, z * 0.7, material('metal')));
  const insert = box(x * 0.72, y * 0.42, z * 0.76, material('black'));
  insert.position.y = y * 0.12;
  group.add(insert);
}

function addCrystalPackage(group, descriptor) {
  const { x, y, z } = descriptor.dimensions;
  group.add(box(x, y, z * 0.76, material('metal', { color: 0xc8cbc7 })));
  const lid = box(x * 0.86, y * 0.84, z * 0.08, material('metal', { color: 0xe0e2df }));
  lid.position.z = z * 0.8;
  group.add(lid);
}

function addInductorPackage(group, descriptor) {
  const { x, y, z } = descriptor.dimensions;
  const radius = Math.min(x, y) * 0.48;
  const core = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, z, 20),
    material('inductor'),
  );
  core.rotation.x = Math.PI / 2;
  core.position.z = z / 2;
  core.scale.x = x / Math.max(radius * 2, 0.001);
  core.scale.z = y / Math.max(radius * 2, 0.001);
  group.add(core);
}

function addTestPoint(group, descriptor) {
  const radius = Math.min(descriptor.dimensions.x, descriptor.dimensions.y) / 2;
  const height = Math.max(descriptor.dimensions.z, 0.004);
  const pad = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, height, 24),
    material('copper'),
  );
  pad.rotation.x = Math.PI / 2;
  pad.position.z = height / 2;
  group.add(pad);
}

function addFlatMetalPackage(group, descriptor) {
  const { x, y, z } = descriptor.dimensions;
  group.add(box(x, y, z, material('copper')));
}

function addGenericPackage(group, descriptor) {
  const { x, y, z } = descriptor.dimensions;
  group.add(box(x, y, z, material(descriptor.family === 'led' ? 'ceramic' : 'dark', descriptor.family === 'led' ? { color: 0x9fcbb5 } : {})));
}

function createPackageMesh(descriptor) {
  const group = new THREE.Group();
  if (descriptor.inspectionProfile?.profile_id === 'u2001-pmic-v1') addInspectionPmicPackage(group, descriptor);
  else if (descriptor.family === 'passive') addPassivePackage(group, descriptor);
  else if (descriptor.family === 'ic') addIcPackage(group, descriptor);
  else if (descriptor.family === 'connector') addConnectorPackage(group, descriptor);
  else if (descriptor.family === 'crystal') addCrystalPackage(group, descriptor);
  else if (descriptor.family === 'inductor') addInductorPackage(group, descriptor);
  else if (descriptor.family === 'test-point') addTestPoint(group, descriptor);
  else if (descriptor.family === 'antenna') addFlatMetalPackage(group, descriptor);
  else addGenericPackage(group, descriptor);
  return group;
}

function createOutline(descriptor) {
  const geometry = new THREE.BoxGeometry(descriptor.dimensions.x, descriptor.dimensions.y, 0.002);
  const outline = new THREE.LineSegments(
    new THREE.EdgesGeometry(geometry),
    new THREE.LineBasicMaterial({ color: COLORS.outline, transparent: true, opacity: 0.48 }),
  );
  outline.position.z = 0.009;
  return outline;
}

function createMarker(descriptor) {
  const radius = Math.max(descriptor.dimensions.x, descriptor.dimensions.y) * 0.72;
  const presentation = buildUnresolvedMarkerPresentation();
  const marker = new THREE.Mesh(
    new THREE.RingGeometry(radius * 0.68, radius, 32),
    new THREE.MeshBasicMaterial({
      color: presentation.color,
      transparent: true,
      opacity: presentation.opacity,
      side: THREE.DoubleSide,
    }),
  );
  marker.position.z = 0.012;
  return marker;
}

function normalizedToWorld(point) {
  return {
    x: point.x * BOARD_WORLD_SIZE.width - BOARD_WORLD_SIZE.width / 2,
    y: (1 - point.y) * BOARD_WORLD_SIZE.height - BOARD_WORLD_SIZE.height / 2,
  };
}

function createShieldMesh(region) {
  const center = normalizedToWorld(region.center);
  const polygon = region.polygon?.length >= 3
    ? region.polygon.map(([x, y]) => normalizedToWorld({ x, y }))
    : [
      { x: center.x - region.size.x * BOARD_WORLD_SIZE.width / 2, y: center.y - region.size.y * BOARD_WORLD_SIZE.height / 2 },
      { x: center.x + region.size.x * BOARD_WORLD_SIZE.width / 2, y: center.y - region.size.y * BOARD_WORLD_SIZE.height / 2 },
      { x: center.x + region.size.x * BOARD_WORLD_SIZE.width / 2, y: center.y + region.size.y * BOARD_WORLD_SIZE.height / 2 },
      { x: center.x - region.size.x * BOARD_WORLD_SIZE.width / 2, y: center.y + region.size.y * BOARD_WORLD_SIZE.height / 2 },
    ];
  const localPoints = polygon.map((point) => ({ x: point.x - center.x, y: point.y - center.y }));
  const makeShape = (scale = 1) => {
    const shape = new THREE.Shape();
    localPoints.forEach((point, index) => {
      const x = point.x * scale;
      const y = point.y * scale;
      if (index === 0) shape.moveTo(x, y); else shape.lineTo(x, y);
    });
    shape.closePath();
    return shape;
  };
  const group = new THREE.Group();
  const rimMaterial = material('metal', { color: 0x7f8a85, transparent: true });
  const lidMaterial = material('metal', { color: 0xc3c9c5, roughness: 0.32, transparent: true });
  const rim = new THREE.Mesh(
    new THREE.ExtrudeGeometry(makeShape(), { depth: 0.012, bevelEnabled: true, bevelSize: 0.004, bevelThickness: 0.003, bevelSegments: 1 }),
    rimMaterial,
  );
  const lid = new THREE.Mesh(new THREE.ShapeGeometry(makeShape(0.965)), lidMaterial);
  lid.position.z = 0.016;
  group.add(rim, lid);
  const edgePoints = [...localPoints, localPoints[0]].map((point) => new THREE.Vector3(point.x, point.y, 0.019));
  const edge = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(edgePoints),
    new THREE.LineBasicMaterial({ color: 0x4a5651, transparent: true, opacity: 0.86 }),
  );
  group.add(edge);
  group.position.set(center.x, center.y, 0.047);
  group.userData.shieldId = region.shieldId;
  group.userData.materials = [rimMaterial, lidMaterial, edge.material];
  return group;
}

function createModuleMesh(module) {
  const points = module.polygon.map(([x, y]) => normalizedToWorld({ x, y }));
  const shape = new THREE.Shape();
  points.forEach((point, index) => {
    if (index === 0) shape.moveTo(point.x, point.y); else shape.lineTo(point.x, point.y);
  });
  shape.closePath();
  const fill = new THREE.Mesh(
    new THREE.ShapeGeometry(shape),
    new THREE.MeshBasicMaterial({ color: 0x1c8f75, transparent: true, opacity: 0.16, depthTest: false }),
  );
  fill.position.z = 0.102;
  fill.renderOrder = 6;
  const linePoints = [...points, points[0]].map((point) => new THREE.Vector3(point.x, point.y, 0.104));
  const line = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(linePoints),
    new THREE.LineBasicMaterial({ color: 0xf5b544, transparent: true, opacity: 0.96, depthTest: false }),
  );
  line.renderOrder = 7;
  const group = new THREE.Group();
  group.add(fill, line);
  group.visible = false;
  group.userData.moduleId = module.moduleId;
  return group;
}

function createLabelSprite(text) {
  const canvas = document.createElement('canvas');
  canvas.width = 240;
  canvas.height = 64;
  const context = canvas.getContext('2d');
  context.fillStyle = 'rgba(19,29,25,0.94)';
  context.fillRect(0, 0, 240, 64);
  context.strokeStyle = 'rgba(196,206,200,0.82)';
  context.lineWidth = 2;
  context.strokeRect(1, 1, 238, 62);
  context.fillStyle = '#f2c94c';
  context.fillRect(12, 28, 8, 8);
  context.fillStyle = '#ffffff';
  context.font = '700 29px Segoe UI, Arial';
  context.textAlign = 'left';
  context.textBaseline = 'middle';
  context.fillText(text, 32, 33);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false }));
  sprite.scale.set(0.1, 0.028, 1);
  sprite.renderOrder = 9;
  sprite.visible = true;
  return sprite;
}

function createAffordanceFrame(descriptor) {
  const points = buildCornerSegments(descriptor.dimensions)
    .flatMap((segment) => segment.map((point) => new THREE.Vector3(point.x, point.y, 0)));
  const presentation = resolveAffordancePresentation();
  const frame = new THREE.LineSegments(
    new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineBasicMaterial({
      color: presentation.color,
      transparent: true,
      opacity: presentation.opacity,
      depthTest: false,
    }),
  );
  frame.position.set(descriptor.center.x, descriptor.center.y, 0.108);
  frame.renderOrder = 8;
  return frame;
}

function createPickTarget(descriptor) {
  const size = buildHitArea(descriptor.dimensions);
  const target = new THREE.Mesh(
    new THREE.PlaneGeometry(size.x, size.y),
    new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }),
  );
  target.position.set(descriptor.center.x, descriptor.center.y, 0.116);
  target.userData.hitArea = size;
  target.userData.componentId = descriptor.componentId;
  return target;
}

export class BoardRenderer {
  constructor(container, sideData, onSelect) {
    this.container = container;
    this.assignSideData(sideData);
    this.onSelect = onSelect;
    this.meshes = new Map();
    this.renderObjects = new Map();
    this.descriptors = new Map();
    this.shieldObjects = new Map();
    this.moduleObjects = new Map();
    this.labelSprites = new Map();
    this.affordanceObjects = new Map();
    this.pickTargets = new Map();
    this.contextObjects = [];
    this.shieldMode = 'removed';
    this.activeModuleId = null;
    this.activeFocusRegion = null;
    this.selectedComponentId = null;
    this.cameraAnimation = null;
    this.inspectionAnimation = null;
    this.inspectionAnimationResolve = null;
    this.inspectionComponentId = null;
    this.inspectionSnapshot = null;
    this.sideTransitioning = false;
    this.interactionLocked = false;
    this.interactionMode = 'pan';
    this.manualPanCenter = null;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xe7eae5);
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 20);
    this.camera.position.set(0, 0, 4);
    this.camera.lookAt(0, 0, 0);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.append(this.renderer.domElement);
    this.group = new THREE.Group();
    this.scene.add(this.group);
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.drag = null;
    this.activePointers = new Map();
    this.suppressTouchTap = false;
    this.inspectionAngle = false;
    this.hoveredComponentId = null;
    this.build();
    this.buildLights();
    this.renderer.compile(this.scene, this.camera);
    this.hoverTooltip = document.createElement('div');
    this.hoverTooltip.className = 'model-hover-tooltip';
    this.hoverTooltip.setAttribute('role', 'tooltip');
    this.hoverTooltip.hidden = true;
    container.append(this.hoverTooltip);
    this.bind();
    this.setInteractionMode(this.interactionMode);
    this.resize();
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(container);
  }

  assignSideData(sideData) {
    this.sideId = sideData.sideId;
    this.entities = sideData.entities;
    this.boardOutline = sideData.boardOutline;
    this.compiledComponents = sideData.compiledComponents;
    this.engineeringTextureUrl = sideData.engineeringTextureUrl;
    this.shieldRegions = sideData.anatomy.shields;
    this.modules = sideData.anatomy.modules;
  }

  createBoardShape() {
    const shape = new THREE.Shape();
    this.boardOutline.forEach((point, index) => {
      const x = point.x * BOARD_WORLD_SIZE.width - BOARD_WORLD_SIZE.width / 2;
      const y = (1 - point.y) * BOARD_WORLD_SIZE.height - BOARD_WORLD_SIZE.height / 2;
      if (index === 0) shape.moveTo(x, y); else shape.lineTo(x, y);
    });
    shape.closePath();
    return shape;
  }

  buildBoard() {
    const shape = this.createBoardShape();
    const substrate = new THREE.Mesh(
      new THREE.ExtrudeGeometry(shape, { depth: 0.026, bevelEnabled: false }),
      new THREE.MeshStandardMaterial({ color: COLORS.board, roughness: 0.72, metalness: 0.08 }),
    );
    substrate.position.z = -0.026;
    substrate.receiveShadow = true;
    this.group.add(substrate);
    const rim = new THREE.LineSegments(
      new THREE.EdgesGeometry(substrate.geometry),
      new THREE.LineBasicMaterial({ color: COLORS.boardEdge, transparent: true, opacity: 0.8 }),
    );
    substrate.add(rim);
    captureMaterialState(substrate);
    this.contextObjects.push(substrate);

    const surfaceGeometry = new THREE.ShapeGeometry(shape);
    const positions = surfaceGeometry.attributes.position;
    const uv = surfaceGeometry.attributes.uv;
    for (let index = 0; index < positions.count; index += 1) {
      uv.setXY(
        index,
        (positions.getX(index) + BOARD_WORLD_SIZE.width / 2) / BOARD_WORLD_SIZE.width,
        (positions.getY(index) + BOARD_WORLD_SIZE.height / 2) / BOARD_WORLD_SIZE.height,
      );
    }
    uv.needsUpdate = true;
    const surfaceMaterial = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.88,
      blending: THREE.MultiplyBlending,
      premultipliedAlpha: true,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -2,
    });
    const surface = new THREE.Mesh(surfaceGeometry, surfaceMaterial);
    surface.position.z = 0.001;
    captureMaterialState(surface);
    this.group.add(surface);
    this.contextObjects.push(surface);
    new THREE.TextureLoader().load(this.engineeringTextureUrl, (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = Math.min(this.renderer.capabilities.getMaxAnisotropy(), 8);
      surfaceMaterial.map = texture;
      surfaceMaterial.needsUpdate = true;
      this.render();
    });
  }

  addDescriptor(descriptor) {
    let object;
    if (descriptor.layer === 'body') object = createPackageMesh(descriptor);
    else if (descriptor.layer === 'outline') object = createOutline(descriptor);
    else object = createMarker(descriptor);
    object.position.x = descriptor.center.x;
    object.position.y = descriptor.center.y;
    if (descriptor.layer === 'body') object.position.z = 0.004;
    object.userData.componentId = descriptor.componentId;
    object.traverse((child) => {
      child.userData.componentId = descriptor.componentId;
      if (child.isMesh) {
        child.castShadow = descriptor.layer === 'body';
        child.receiveShadow = true;
      }
    });
    captureMaterialState(object);
    this.group.add(object);
    this.descriptors.set(descriptor.componentId, descriptor);
    this.renderObjects.set(descriptor.componentId, object);
    if (descriptor.selectable) this.meshes.set(descriptor.componentId, object);
  }

  buildShields() {
    this.shieldRegions.forEach((region) => {
      const shield = createShieldMesh(region);
      this.group.add(shield);
      this.shieldObjects.set(region.shieldId, shield);
    });
  }

  buildModules() {
    this.modules.forEach((module) => {
      const object = createModuleMesh(module);
      this.group.add(object);
      this.moduleObjects.set(module.moduleId, object);
    });
  }

  buildLabels() {
    this.entities.forEach((entity) => {
      const descriptor = this.descriptors.get(entity.component_id);
      if (!descriptor) return;
      const sprite = createLabelSprite(entity.designator);
      sprite.position.set(descriptor.center.x, descriptor.center.y, 0.12);
      this.group.add(sprite);
      this.labelSprites.set(entity.component_id, sprite);
    });
  }

  buildAffordances() {
    this.entities.forEach((entity) => {
      const descriptor = this.descriptors.get(entity.component_id);
      if (!descriptor) return;
      const frame = createAffordanceFrame(descriptor);
      const pickTarget = createPickTarget(descriptor);
      this.group.add(frame);
      this.group.add(pickTarget);
      this.affordanceObjects.set(entity.component_id, frame);
      this.pickTargets.set(entity.component_id, pickTarget);
    });
    this.container.dataset.interactiveCount = String(this.affordanceObjects.size);
    this.updateAffordanceStyles(false);
  }

  build() {
    this.buildBoard();
    const reviewedDesignators = new Set(this.entities.map((entity) => entity.designator));
    this.compiledComponents
      .filter((component) => !reviewedDesignators.has(component.designator))
      .map((component) => buildRenderDescriptor(component))
      .filter(Boolean)
      .forEach((descriptor) => this.addDescriptor(descriptor));
    this.entities
      .map((entity) => buildRenderDescriptor(entity, { reviewed: true }))
      .filter(Boolean)
      .forEach((descriptor) => this.addDescriptor(descriptor));
    this.buildModules();
    this.buildShields();
    this.buildLabels();
    this.buildAffordances();
    this.setShieldMode(this.shieldMode, false);
    this.updateLabelVisibility(false);
  }

  buildLights() {
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x3a5148, 1.7));
    const key = new THREE.DirectionalLight(0xffffff, 2.5);
    key.position.set(-1.8, -2.4, 4.2);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xdce9e2, 0.8);
    fill.position.set(2.5, 1.2, 2.5);
    this.scene.add(fill);
  }

  disposeGroup(group) {
    group.traverse((child) => {
      child.geometry?.dispose();
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      materials.filter(Boolean).forEach((item) => {
        item.map?.dispose();
        item.dispose();
      });
    });
    group.removeFromParent();
  }

  replaceSideData(sideData, rotationY = 0) {
    this.cancelInspectionAnimation();
    this.disposeGroup(this.group);
    this.assignSideData(sideData);
    this.meshes = new Map();
    this.renderObjects = new Map();
    this.descriptors = new Map();
    this.shieldObjects = new Map();
    this.moduleObjects = new Map();
    this.labelSprites = new Map();
    this.affordanceObjects = new Map();
    this.pickTargets = new Map();
    this.contextObjects = [];
    this.activeModuleId = null;
    this.activeFocusRegion = null;
    this.hoveredComponentId = null;
    this.inspectionComponentId = null;
    this.inspectionSnapshot = null;
    this.manualPanCenter = null;
    this.group = new THREE.Group();
    this.group.rotation.set(TOP_VIEW_TILT, rotationY, 0);
    this.scene.add(this.group);
    this.build();
    this.renderer.compile(this.scene, this.camera);
    this.resize();
  }

  setSideData(sideData, animate = true) {
    if (this.sideTransitioning || sideData.sideId === this.sideId) return Promise.resolve(this.sideId);
    this.cancelCameraAnimation();
    if (!animate) {
      this.replaceSideData(sideData);
      return Promise.resolve(this.sideId);
    }
    this.sideTransitioning = true;
    const started = performance.now();
    const duration = 520;
    let swapped = false;
    return new Promise((resolve) => {
      const tick = (now) => {
        const progress = Math.min(1, (now - started) / duration);
        if (progress < 0.5) {
          const local = 1 - (1 - progress * 2) ** 3;
          this.group.rotation.y = local * Math.PI / 2;
        } else {
          if (!swapped) {
            swapped = true;
            this.replaceSideData(sideData, -Math.PI / 2);
          }
          const local = (progress - 0.5) * 2;
          this.group.rotation.y = -Math.PI / 2 + (1 - (1 - local) ** 3) * Math.PI / 2;
        }
        this.render();
        if (progress < 1) requestAnimationFrame(tick);
        else {
          this.group.rotation.y = 0;
          this.sideTransitioning = false;
          this.render();
          resolve(this.sideId);
        }
      };
      requestAnimationFrame(tick);
    });
  }

  bind() {
    const canvas = this.renderer.domElement;
    canvas.addEventListener('pointerdown', (event) => {
      if (this.interactionLocked) return;
      this.cancelCameraAnimation();
      this.clearHover(false);
      canvas.setPointerCapture(event.pointerId);
      if (event.pointerType === 'touch') {
        this.activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
        if (this.activePointers.size >= 2) {
          const [first, second] = [...this.activePointers.values()];
          this.drag = {
            mode: 'pinch',
            distance: Math.hypot(second.x - first.x, second.y - first.y),
            zoom: this.camera.zoom,
            centerNdc: this.clientPointToNdc((first.x + second.x) / 2, (first.y + second.y) / 2),
            camera: { x: this.camera.position.x, y: this.camera.position.y },
            frame: {
              width: this.camera.right - this.camera.left,
              height: this.camera.top - this.camera.bottom,
            },
          };
          this.suppressTouchTap = true;
          this.container.classList.add('dragging');
          return;
        }
      }
      const inspected = this.inspectionComponentId ? this.renderObjects.get(this.inspectionComponentId) : null;
      if (inspected) {
        this.drag = { mode: 'component', x: event.clientX, y: event.clientY, rx: inspected.rotation.x, ry: inspected.rotation.y };
      } else if (this.interactionMode === 'rotate') {
        this.drag = { mode: 'board', x: event.clientX, y: event.clientY, rx: this.group.rotation.x, rz: this.group.rotation.z };
      } else {
        this.drag = { mode: 'pan', x: event.clientX, y: event.clientY, cx: this.camera.position.x, cy: this.camera.position.y };
      }
      this.container.classList.add('dragging');
    });
    canvas.addEventListener('pointermove', (event) => {
      if (this.interactionLocked) return;
      if (event.pointerType === 'touch' && this.activePointers.has(event.pointerId)) {
        this.activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      }
      if (!this.drag) {
        this.updateHover(event);
        return;
      }
      if (this.drag.mode === 'pinch') {
        const [first, second] = [...this.activePointers.values()];
        if (!first || !second) return;
        const [minimum, maximum] = this.zoomBounds();
        this.camera.zoom = pinchZoom({
          startDistance: this.drag.distance,
          currentDistance: Math.hypot(second.x - first.x, second.y - first.y),
          startZoom: this.drag.zoom,
          minimum,
          maximum,
        });
        const currentNdc = this.clientPointToNdc((first.x + second.x) / 2, (first.y + second.y) / 2);
        this.manualPanCenter = clampPanCenter(anchorZoomCenter({
          camera: this.drag.camera,
          startNdc: this.drag.centerNdc,
          currentNdc,
          frame: this.drag.frame,
          startZoom: this.drag.zoom,
          currentZoom: this.camera.zoom,
        }));
        this.camera.position.set(this.manualPanCenter.x, this.manualPanCenter.y, 4);
        this.camera.lookAt(this.manualPanCenter.x, this.manualPanCenter.y, 0);
        this.camera.updateProjectionMatrix();
        this.updateLabelVisibility(false);
      } else if (this.drag.mode === 'component') {
        const inspected = this.renderObjects.get(this.inspectionComponentId);
        if (!inspected) return;
        inspected.rotation.y = this.drag.ry + (event.clientX - this.drag.x) * 0.012;
        inspected.rotation.x = Math.max(-1.15, Math.min(0.75, this.drag.rx + (event.clientY - this.drag.y) * 0.009));
      } else if (this.drag.mode === 'board') {
        this.group.rotation.z = this.drag.rz + (event.clientX - this.drag.x) * 0.006;
        this.group.rotation.x = Math.max(-0.58, Math.min(0.08, this.drag.rx + (event.clientY - this.drag.y) * 0.004));
        this.inspectionAngle = Math.abs(this.group.rotation.x) > 0.08;
      } else {
        const delta = screenDeltaToPan({
          dx: event.clientX - this.drag.x,
          dy: event.clientY - this.drag.y,
          width: this.container.clientWidth,
          height: this.container.clientHeight,
          frameWidth: this.camera.right - this.camera.left,
          frameHeight: this.camera.top - this.camera.bottom,
          zoom: this.camera.zoom,
        });
        this.manualPanCenter = clampPanCenter({ x: this.drag.cx + delta.x, y: this.drag.cy + delta.y });
        this.camera.position.set(this.manualPanCenter.x, this.manualPanCenter.y, 4);
        this.camera.lookAt(this.manualPanCenter.x, this.manualPanCenter.y, 0);
      }
      this.render();
    });
    canvas.addEventListener('pointerup', (event) => {
      if (this.interactionLocked) return;
      if (event.pointerType === 'touch') this.activePointers.delete(event.pointerId);
      if (this.suppressTouchTap) {
        this.drag = null;
        this.container.classList.remove('dragging');
        if (!this.activePointers.size) this.suppressTouchTap = false;
        return;
      }
      const dragMode = this.drag?.mode;
      const moved = this.drag && Math.hypot(event.clientX - this.drag.x, event.clientY - this.drag.y) > 5;
      this.drag = null;
      this.container.classList.remove('dragging');
      if (!moved && dragMode !== 'component') this.pick(event);
    });
    canvas.addEventListener('pointercancel', (event) => {
      if (event.pointerType === 'touch') this.activePointers.delete(event.pointerId);
      this.drag = null;
      if (!this.activePointers.size) this.suppressTouchTap = false;
      this.container.classList.remove('dragging');
    });
    canvas.addEventListener('pointerleave', () => {
      if (!this.drag) this.clearHover();
    });
    canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      if (this.interactionLocked) return;
      this.cancelCameraAnimation();
      const zoomBounds = this.zoomBounds();
      const startZoom = this.camera.zoom;
      const currentNdc = this.clientPointToNdc(event.clientX, event.clientY);
      this.camera.zoom = Math.max(zoomBounds[0], Math.min(zoomBounds[1], startZoom * (event.deltaY > 0 ? 0.9 : 1.1)));
      this.manualPanCenter = clampPanCenter(anchorZoomCenter({
        camera: { x: this.camera.position.x, y: this.camera.position.y },
        startNdc: currentNdc,
        currentNdc,
        frame: {
          width: this.camera.right - this.camera.left,
          height: this.camera.top - this.camera.bottom,
        },
        startZoom,
        currentZoom: this.camera.zoom,
      }));
      this.camera.position.set(this.manualPanCenter.x, this.manualPanCenter.y, 4);
      this.camera.lookAt(this.manualPanCenter.x, this.manualPanCenter.y, 0);
      this.camera.updateProjectionMatrix();
      this.updateLabelVisibility(false);
      this.updateHover(event);
    }, { passive: false });
  }

  zoomBounds() {
    return this.inspectionComponentId ? [1.8, 6] : [0.72, 4.2];
  }

  clientPointToNdc(clientX, clientY) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    return {
      x: ((clientX - rect.left) / rect.width) * 2 - 1,
      y: -((clientY - rect.top) / rect.height) * 2 + 1,
    };
  }

  pick(event) {
    if (this.interactionLocked) return;
    const componentId = this.componentAtPointer(event);
    if (componentId) this.onSelect(componentId);
  }

  componentAtPointer(event) {
    const pointer = this.clientPointToNdc(event.clientX, event.clientY);
    this.pointer.set(pointer.x, pointer.y);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObjects([...this.pickTargets.values()], false);
    if (!hits.length) return null;
    let nearestComponentId = null;
    let nearestDistance = Number.POSITIVE_INFINITY;
    const position = new THREE.Vector3();
    const seen = new Set();
    hits.forEach((hit) => {
      const componentId = hit.object.userData.componentId;
      if (seen.has(componentId)) return;
      seen.add(componentId);
      hit.object.getWorldPosition(position).project(this.camera);
      const distance = (position.x - this.pointer.x) ** 2 + (position.y - this.pointer.y) ** 2;
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestComponentId = componentId;
      }
    });
    return nearestComponentId;
  }

  updateHover(event) {
    if (event.pointerType === 'touch') return this.clearHover();
    if (this.inspectionComponentId) return this.clearHover();
    const componentId = this.componentAtPointer(event);
    if (componentId !== this.hoveredComponentId) {
      this.hoveredComponentId = componentId;
      this.updateAffordanceStyles(false);
    }
    this.container.classList.toggle('component-hover', Boolean(componentId));
    if (!componentId) {
      this.hoverTooltip.hidden = true;
      return this.render();
    }
    const entity = this.entities.find((candidate) => candidate.component_id === componentId);
    const rect = this.container.getBoundingClientRect();
    const designator = document.createElement('strong');
    designator.textContent = entity.designator;
    const name = document.createElement('span');
    name.textContent = entity.name;
    this.hoverTooltip.replaceChildren(designator, name);
    this.hoverTooltip.hidden = false;
    const placement = placeHoverTooltip({
      pointer: { x: event.clientX - rect.left, y: event.clientY - rect.top },
      viewport: { width: rect.width, height: rect.height },
      tooltip: {
        width: this.hoverTooltip.offsetWidth,
        height: this.hoverTooltip.offsetHeight,
      },
    });
    this.hoverTooltip.style.left = `${placement.x}px`;
    this.hoverTooltip.style.top = `${placement.y}px`;
    this.hoverTooltip.dataset.horizontal = placement.horizontal;
    this.hoverTooltip.dataset.vertical = placement.vertical;
    this.render();
  }

  clearHover(shouldRender = true) {
    if (!this.hoveredComponentId && this.hoverTooltip.hidden) return;
    this.hoveredComponentId = null;
    this.container.classList.remove('component-hover');
    this.hoverTooltip.hidden = true;
    this.updateAffordanceStyles(false);
    if (shouldRender) this.render();
  }

  updateAffordanceStyles(shouldRender = true) {
    this.affordanceObjects.forEach((frame, componentId) => {
      const presentation = resolveAffordancePresentation({
        selected: componentId === this.selectedComponentId,
        hovered: componentId === this.hoveredComponentId,
      });
      frame.material.color.setHex(presentation.color);
      frame.material.opacity = presentation.opacity;
      frame.visible = !this.inspectionComponentId;
      const label = this.labelSprites.get(componentId);
      if (label) {
        label.material.opacity = presentation.labelOpacity;
        label.visible = !this.inspectionComponentId;
      }
      const object = this.meshes.get(componentId);
      object?.traverse((child) => {
        if (!child.isMesh || !child.material?.emissive) return;
        child.material.emissive.setHex(presentation.color);
        child.material.emissiveIntensity = presentation.emissiveIntensity;
      });
    });
    if (shouldRender) this.render();
  }

  clearSelectionStyle() {
    this.meshes.forEach((object) => object.traverse((child) => {
      if (!child.isMesh || !child.material?.emissive) return;
      child.material.emissive.setHex(0x000000);
      child.material.emissiveIntensity = 0;
    }));
  }

  select(componentId) {
    if (this.inspectionComponentId && this.inspectionComponentId !== componentId) void this.clearComponentInspection(false);
    this.clearSelectionStyle();
    this.selectedComponentId = componentId;
    const object = this.meshes.get(componentId);
    const descriptor = this.descriptors.get(componentId);
    if (!object || !descriptor) return this.render();
    this.updateAffordanceStyles(false);
    this.render();
  }

  setShieldMode(mode, shouldRender = true) {
    this.shieldMode = mode;
    const presentation = getShieldPresentation(mode);
    this.shieldObjects.forEach((shield) => {
      shield.visible = presentation.visible;
      shield.userData.materials.forEach((shieldMaterial) => {
        shieldMaterial.opacity = presentation.opacity;
        shieldMaterial.depthWrite = presentation.opacity >= 0.9;
        shieldMaterial.needsUpdate = true;
      });
    });
    this.renderObjects.forEach((object, componentId) => {
      const descriptor = this.descriptors.get(componentId);
      const covered = this.shieldRegions.some((region) => isPointCovered(descriptor.normalizedCenter, region));
      object.visible = presentation.coveredBodiesVisible || !covered;
    });
    if (shouldRender) this.render();
  }

  setModuleFocus(moduleId) {
    this.activeModuleId = moduleId || null;
    this.container.dataset.activeModule = this.activeModuleId || '';
    this.moduleObjects.forEach((object, id) => { object.visible = id === this.activeModuleId; });
    this.render();
  }

  setObjectEmphasis(object, factor) {
    object.traverse((child) => {
      if (!child.material || child.userData.baseOpacity === undefined) return;
      child.material.opacity = child.userData.baseOpacity * factor;
      child.material.transparent = factor < 1 || child.userData.baseTransparent;
      child.material.depthWrite = factor >= 1 ? child.userData.baseDepthWrite : false;
      child.material.needsUpdate = true;
    });
  }

  applyRepairEmphasis(region) {
    this.renderObjects.forEach((object, componentId) => {
      const descriptor = this.descriptors.get(componentId);
      const inFocus = !region || isPointCovered(descriptor.normalizedCenter, region, 0.015);
      const selected = componentId === this.selectedComponentId;
      this.setObjectEmphasis(object, inFocus || selected ? 1 : 0.52);
    });
  }

  cancelInspectionAnimation() {
    if (this.inspectionAnimation !== null) cancelAnimationFrame(this.inspectionAnimation);
    this.inspectionAnimation = null;
    if (this.inspectionAnimationResolve) this.inspectionAnimationResolve(false);
    this.inspectionAnimationResolve = null;
  }

  setInspectionContextOpacity(activeComponentId) {
    this.clearHover(false);
    this.contextObjects.forEach((object) => this.setObjectEmphasis(object, activeComponentId ? 0.16 : 1));
    this.renderObjects.forEach((object, componentId) => {
      this.setObjectEmphasis(object, inspectionOpacity(activeComponentId, componentId));
      object.visible = true;
    });
    this.shieldObjects.forEach((object) => { object.visible = false; });
    this.moduleObjects.forEach((object) => { object.visible = false; });
    this.labelSprites.forEach((sprite) => { sprite.visible = false; });
    this.affordanceObjects.forEach((frame) => { frame.visible = false; });
  }

  setInspectionSelectionStyle(object, active) {
    object.traverse((child) => {
      if (!child.isMesh || !child.material?.emissive) return;
      child.material.emissive.setHex(active ? 0x000000 : COLORS.selected);
      child.material.emissiveIntensity = active ? 0 : 0.2;
    });
  }

  restoreInspectionContext() {
    this.contextObjects.forEach((object) => this.setObjectEmphasis(object, 1));
    this.applyRepairEmphasis(this.activeFocusRegion);
    this.setShieldMode(this.inspectionSnapshot?.shieldMode || this.shieldMode, false);
    this.setModuleFocus(this.inspectionSnapshot?.moduleId || this.activeModuleId);
    this.updateAffordanceStyles(false);
    this.updateLabelVisibility(false);
  }

  animateInspectionObject(object, target, duration = 460) {
    this.cancelInspectionAnimation();
    const started = performance.now();
    const from = {
      scale: object.scale.x,
      z: object.position.z,
      rx: object.rotation.x,
      ry: object.rotation.y,
      cameraX: this.camera.position.x,
      cameraY: this.camera.position.y,
      zoom: this.camera.zoom,
    };
    return new Promise((resolve) => {
      this.inspectionAnimationResolve = resolve;
      const tick = (now) => {
        const progress = Math.min(1, (now - started) / duration);
        const eased = 1 - (1 - progress) ** 3;
        const scale = from.scale + (target.scale - from.scale) * eased;
        object.scale.setScalar(scale);
        object.position.z = from.z + (target.z - from.z) * eased;
        object.rotation.x = from.rx + (target.rx - from.rx) * eased;
        object.rotation.y = from.ry + (target.ry - from.ry) * eased;
        const cameraX = from.cameraX + (target.cameraX - from.cameraX) * eased;
        const cameraY = from.cameraY + (target.cameraY - from.cameraY) * eased;
        this.camera.position.set(cameraX, cameraY, 4);
        this.camera.lookAt(cameraX, cameraY, 0);
        this.camera.zoom = from.zoom + (target.zoom - from.zoom) * eased;
        this.camera.updateProjectionMatrix();
        this.render();
        if (progress < 1) this.inspectionAnimation = requestAnimationFrame(tick);
        else {
          this.inspectionAnimation = null;
          this.inspectionAnimationResolve = null;
          resolve(true);
        }
      };
      this.inspectionAnimation = requestAnimationFrame(tick);
    });
  }

  async setComponentInspection(componentId, animate = true) {
    const object = this.renderObjects.get(componentId);
    const descriptor = this.descriptors.get(componentId);
    if (!object || !descriptor?.inspectionProfile || this.inspectionComponentId === componentId) return false;
    if (this.inspectionComponentId) await this.clearComponentInspection(false);
    this.cancelCameraAnimation();
    const narrow = this.container.clientWidth < 620;
    const transform = buildInspectionTransform(descriptor.dimensions, narrow);
    this.inspectionComponentId = componentId;
    this.inspectionSnapshot = {
      positionZ: object.position.z,
      rotation: object.rotation.clone(),
      scale: object.scale.x,
      camera: { x: this.camera.position.x, y: this.camera.position.y, zoom: this.camera.zoom },
      shieldMode: this.shieldMode,
      moduleId: this.activeModuleId,
    };
    this.setInspectionContextOpacity(componentId);
    this.setInspectionSelectionStyle(object, true);
    object.traverse((child) => { child.renderOrder = 12; });
    const focusCenter = this.focusCenterFor(descriptor.center);
    const target = {
      scale: transform.scale,
      z: this.inspectionSnapshot.positionZ + transform.lift,
      rx: -0.42,
      ry: 0.18,
      cameraX: focusCenter.x,
      cameraY: focusCenter.y,
      zoom: transform.zoom,
    };
    if (animate) await this.animateInspectionObject(object, target);
    else {
      object.scale.setScalar(target.scale);
      object.position.z = target.z;
      object.rotation.set(target.rx, target.ry, 0);
      this.camera.position.set(target.cameraX, target.cameraY, 4);
      this.camera.lookAt(target.cameraX, target.cameraY, 0);
      this.camera.zoom = target.zoom;
      this.camera.updateProjectionMatrix();
      this.render();
    }
    return true;
  }

  async clearComponentInspection(animate = true) {
    if (!this.inspectionComponentId || !this.inspectionSnapshot) return false;
    const object = this.renderObjects.get(this.inspectionComponentId);
    const snapshot = this.inspectionSnapshot;
    if (object) {
      const target = {
        scale: snapshot.scale,
        z: snapshot.positionZ,
        rx: snapshot.rotation.x,
        ry: snapshot.rotation.y,
        cameraX: snapshot.camera.x,
        cameraY: snapshot.camera.y,
        zoom: snapshot.camera.zoom,
      };
      if (animate) await this.animateInspectionObject(object, target);
      else {
        object.scale.setScalar(target.scale);
        object.position.z = target.z;
        object.rotation.copy(snapshot.rotation);
        this.camera.position.set(target.cameraX, target.cameraY, 4);
        this.camera.lookAt(target.cameraX, target.cameraY, 0);
        this.camera.zoom = target.zoom;
        this.camera.updateProjectionMatrix();
      }
      object.traverse((child) => { child.renderOrder = 0; });
      this.setInspectionSelectionStyle(object, false);
    }
    this.inspectionComponentId = null;
    this.restoreInspectionContext();
    this.inspectionSnapshot = null;
    this.render();
    return true;
  }

  isComponentInspectionActive() {
    return Boolean(this.inspectionComponentId);
  }

  cancelCameraAnimation() {
    if (this.cameraAnimation !== null) cancelAnimationFrame(this.cameraAnimation);
    this.cameraAnimation = null;
  }

  animateCamera(center, zoom, duration = 420) {
    this.cancelCameraAnimation();
    const start = performance.now();
    const from = { x: this.camera.position.x, y: this.camera.position.y, zoom: this.camera.zoom };
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - progress) ** 3;
      const x = from.x + (center.x - from.x) * eased;
      const y = from.y + (center.y - from.y) * eased;
      this.camera.position.set(x, y, 4);
      this.camera.lookAt(x, y, 0);
      this.camera.zoom = from.zoom + (zoom - from.zoom) * eased;
      this.camera.updateProjectionMatrix();
      this.updateLabelVisibility(false);
      this.render();
      if (progress < 1) this.cameraAnimation = requestAnimationFrame(tick);
      else this.cameraAnimation = null;
    };
    this.cameraAnimation = requestAnimationFrame(tick);
  }

  focusRegion(region, animate = true) {
    if (!region) return this.clearRepairFocus(animate);
    this.activeFocusRegion = region;
    const aspect = Math.max(this.container.clientWidth, 320) / Math.max(this.container.clientHeight, 320);
    const frame = buildFocusFrame(region, aspect);
    const focusCenter = this.focusCenterFor(frame.center);
    this.manualPanCenter = null;
    this.applyRepairEmphasis(region);
    if (animate) this.animateCamera(focusCenter, frame.zoom);
    else {
      this.camera.position.set(focusCenter.x, focusCenter.y, 4);
      this.camera.lookAt(focusCenter.x, focusCenter.y, 0);
      this.camera.zoom = frame.zoom;
      this.camera.updateProjectionMatrix();
      this.updateLabelVisibility(false);
      this.render();
    }
  }

  setRepairFocus(moduleId, region, animate = true) {
    this.setModuleFocus(moduleId);
    this.focusRegion(region, animate);
  }

  clearRepairFocus(animate = true) {
    this.activeFocusRegion = null;
    this.manualPanCenter = null;
    this.applyRepairEmphasis(null);
    if (animate) this.animateCamera({ x: 0, y: 0 }, 1);
    else {
      this.camera.position.set(0, 0, 4);
      this.camera.lookAt(0, 0, 0);
      this.camera.zoom = 1;
      this.camera.updateProjectionMatrix();
      this.updateLabelVisibility(false);
      this.render();
    }
  }

  focusModuleForDesignator(designator) {
    const module = this.modules.find((candidate) => candidate.designators.includes(designator));
    this.setModuleFocus(module?.moduleId || null);
    return module?.moduleId || null;
  }

  updateLabelVisibility(shouldRender = true) {
    this.labelSprites.forEach((sprite, componentId) => {
      const presentation = resolveAffordancePresentation({
        selected: componentId === this.selectedComponentId,
        hovered: componentId === this.hoveredComponentId,
      });
      sprite.visible = !this.inspectionComponentId;
      sprite.material.opacity = presentation.labelOpacity;
    });
    if (shouldRender) this.render();
  }

  setInspectionAngle(enabled) {
    if (this.inspectionComponentId) return;
    this.inspectionAngle = enabled;
    this.group.rotation.x = enabled ? -0.46 : TOP_VIEW_TILT;
    this.render();
  }

  setInteractionLocked(locked) {
    this.interactionLocked = Boolean(locked);
    if (this.interactionLocked) {
      this.clearHover(false);
      this.drag = null;
      this.container.classList.remove('dragging');
    }
  }

  setInteractionMode(mode) {
    this.interactionMode = resolveBoardInteractionMode(mode);
    this.container.dataset.dragMode = this.interactionMode;
    return this.interactionMode;
  }

  focusCenterFor(center) {
    return transformBoardCenter(center, {
      x: this.group.rotation.x,
      z: this.group.rotation.z,
    });
  }

  reset(resetInteractionMode = true) {
    this.cancelCameraAnimation();
    if (this.inspectionComponentId) void this.clearComponentInspection(false);
    this.group.rotation.set(TOP_VIEW_TILT, 0, 0);
    this.inspectionAngle = false;
    if (resetInteractionMode) this.setInteractionMode('pan');
    this.clearRepairFocus(true);
  }

  resize() {
    const width = Math.max(this.container.clientWidth, 320);
    const height = Math.max(this.container.clientHeight, 320);
    this.renderer.setSize(width, height, false);
    const frame = buildCameraFrame(width / height);
    this.camera.left = frame.left;
    this.camera.right = frame.right;
    this.camera.top = frame.top;
    this.camera.bottom = frame.bottom;
    this.camera.near = frame.near;
    this.camera.far = frame.far;
    if (this.inspectionComponentId) {
      const descriptor = this.descriptors.get(this.inspectionComponentId);
      const transform = descriptor ? buildInspectionTransform(descriptor.dimensions, width < 620) : null;
      const focusCenter = this.focusCenterFor(descriptor?.center || { x: 0, y: 0 });
      this.camera.position.set(focusCenter.x, focusCenter.y, frame.position.z);
      this.camera.lookAt(focusCenter.x, focusCenter.y, 0);
      this.camera.zoom = transform?.zoom || 2.55;
    } else if (this.manualPanCenter) {
      this.camera.position.set(this.manualPanCenter.x, this.manualPanCenter.y, frame.position.z);
      this.camera.lookAt(this.manualPanCenter.x, this.manualPanCenter.y, 0);
    } else if (this.activeFocusRegion) {
      const focusFrame = buildFocusFrame(this.activeFocusRegion, width / height);
      const focusCenter = this.focusCenterFor(focusFrame.center);
      this.camera.position.set(focusCenter.x, focusCenter.y, frame.position.z);
      this.camera.lookAt(focusCenter.x, focusCenter.y, 0);
      this.camera.zoom = focusFrame.zoom;
    } else {
      this.camera.position.set(frame.position.x, frame.position.y, frame.position.z);
      this.camera.lookAt(0, 0, 0);
      this.camera.zoom = 1;
    }
    this.camera.updateProjectionMatrix();
    this.render();
  }

  render() {
    const width = Math.max(this.container.clientWidth, 1);
    const height = Math.max(this.container.clientHeight, 1);
    const worldPerPixelX = (this.camera.right - this.camera.left) / (width * this.camera.zoom);
    const worldPerPixelY = (this.camera.top - this.camera.bottom) / (height * this.camera.zoom);
    this.container.dataset.cameraZoom = this.camera.zoom.toFixed(3);
    this.group.updateMatrixWorld(true);
    const labelDepths = new Map();
    const anchor = new THREE.Vector3();
    const labelPositions = new Map(buildScreenLabelPositions(this.entities
      .map((entity) => ({ entity, descriptor: this.descriptors.get(entity.component_id) }))
      .filter(({ descriptor }) => Boolean(descriptor))
      .map(({ entity, descriptor }) => {
        anchor.set(descriptor.center.x, descriptor.center.y, 0.12)
          .applyMatrix4(this.group.matrixWorld)
          .project(this.camera);
        labelDepths.set(entity.component_id, anchor.z);
        return {
          id: entity.component_id,
          anchor: {
            x: ((anchor.x + 1) / 2) * width,
            y: ((1 - anchor.y) / 2) * height,
          },
        };
      }), {
      viewport: { width, height },
    }).map((position) => [position.id, position]));
    this.labelSprites.forEach((sprite, componentId) => {
      const presentation = resolveAffordancePresentation({
        selected: componentId === this.selectedComponentId,
        hovered: componentId === this.hoveredComponentId,
      });
      const position = labelPositions.get(componentId);
      if (position) {
        const worldPosition = new THREE.Vector3(
          (position.x / width) * 2 - 1,
          1 - (position.y / height) * 2,
          labelDepths.get(componentId),
        ).unproject(this.camera);
        sprite.position.copy(this.group.worldToLocal(worldPosition));
      }
      sprite.scale.set(
        worldPerPixelX * presentation.labelPixels.width,
        worldPerPixelY * presentation.labelPixels.height,
        1,
      );
    });
    const minimumPickPixels = width < 620 ? 36 : 24;
    this.pickTargets.forEach((target) => {
      const scale = buildScreenAwareHitScale(
        target.userData.hitArea,
        { x: worldPerPixelX, y: worldPerPixelY },
        minimumPickPixels,
      );
      target.scale.set(scale.x, scale.y, 1);
    });
    this.group.updateMatrixWorld(true);
    const screenLabels = [];
    const projected = new THREE.Vector3();
    this.labelSprites.forEach((sprite, componentId) => {
      if (!sprite.visible) return;
      const presentation = resolveAffordancePresentation({
        selected: componentId === this.selectedComponentId,
        hovered: componentId === this.hoveredComponentId,
      });
      sprite.getWorldPosition(projected).project(this.camera);
      screenLabels.push({
        left: ((projected.x + 1) / 2) * width - presentation.labelPixels.width / 2,
        top: ((1 - projected.y) / 2) * height - presentation.labelPixels.height / 2,
        width: presentation.labelPixels.width,
        height: presentation.labelPixels.height,
      });
    });
    let overlapCount = 0;
    screenLabels.forEach((label, index) => {
      screenLabels.slice(index + 1).forEach((other) => {
        if (label.left < other.left + other.width
          && label.left + label.width > other.left
          && label.top < other.top + other.height
          && label.top + label.height > other.top) overlapCount += 1;
      });
    });
    this.container.dataset.labelOverlapCount = String(overlapCount);
    this.container.dataset.labelOutsideCount = String(screenLabels.filter((label) => (
      label.left < 0 || label.top < 0
      || label.left + label.width > width
      || label.top + label.height > height
    )).length);
    this.renderer.render(this.scene, this.camera);
  }
}
