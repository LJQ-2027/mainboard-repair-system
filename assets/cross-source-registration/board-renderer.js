import * as THREE from '../vendor/three/three.module.min.js';
import {
  BOARD_WORLD_SIZE,
  buildCameraFrame,
  buildFocusFrame,
  buildRenderDescriptor,
  buildSelectionRadius,
} from './model-profiles.js';
import {
  getShieldPresentation,
  isPointCovered,
  shouldShowLabels,
} from './anatomy-state.js';
import { isPointInFocus } from './repair-focus-state.js';
import { buildInspectionTransform, inspectionOpacity } from './component-inspection-state.js';

const COLORS = {
  board: 0x17473e,
  boardEdge: 0xb4823a,
  copper: 0xc99149,
  dark: 0x202927,
  ink: 0x111816,
  metal: 0xaeb6b1,
  outline: 0x73827b,
  selected: 0xff5a3d,
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
  const marker = new THREE.Mesh(
    new THREE.RingGeometry(radius * 0.68, radius, 32),
    new THREE.MeshBasicMaterial({ color: COLORS.selected, transparent: true, opacity: 0.9, side: THREE.DoubleSide }),
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
  canvas.width = 256;
  canvas.height = 72;
  const context = canvas.getContext('2d');
  context.fillStyle = 'rgba(248,249,246,0.94)';
  context.fillRect(2, 2, 252, 68);
  context.strokeStyle = '#ef5b3f';
  context.lineWidth = 4;
  context.strokeRect(2, 2, 252, 68);
  context.fillStyle = '#17221e';
  context.font = '700 34px Segoe UI, Arial';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text, 128, 38);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false }));
  sprite.scale.set(0.13, 0.037, 1);
  sprite.renderOrder = 9;
  sprite.visible = false;
  return sprite;
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
    this.contextObjects = [];
    this.shieldMode = 'removed';
    this.activeModuleId = null;
    this.activeFocusRegion = null;
    this.selectedComponentId = null;
    this.cameraAnimation = null;
    this.inspectionAnimation = null;
    this.inspectionComponentId = null;
    this.inspectionSnapshot = null;
    this.sideTransitioning = false;
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
    this.inspectionAngle = false;
    this.selectionHalo = null;
    this.build();
    this.buildLights();
    this.renderer.compile(this.scene, this.camera);
    this.bind();
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
      sprite.position.set(descriptor.center.x, descriptor.center.y + descriptor.dimensions.y * 0.72 + 0.025, 0.12);
      this.group.add(sprite);
      this.labelSprites.set(entity.component_id, sprite);
    });
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
    this.contextObjects = [];
    this.activeModuleId = null;
    this.activeFocusRegion = null;
    this.selectionHalo = null;
    this.inspectionComponentId = null;
    this.inspectionSnapshot = null;
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
      this.cancelCameraAnimation();
      const inspected = this.inspectionComponentId ? this.renderObjects.get(this.inspectionComponentId) : null;
      this.drag = inspected
        ? { mode: 'component', x: event.clientX, y: event.clientY, rx: inspected.rotation.x, ry: inspected.rotation.y }
        : { mode: 'board', x: event.clientX, y: event.clientY, rx: this.group.rotation.x, rz: this.group.rotation.z };
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', (event) => {
      if (!this.drag) return;
      if (this.drag.mode === 'component') {
        const inspected = this.renderObjects.get(this.inspectionComponentId);
        if (!inspected) return;
        inspected.rotation.y = this.drag.ry + (event.clientX - this.drag.x) * 0.012;
        inspected.rotation.x = Math.max(-1.15, Math.min(0.75, this.drag.rx + (event.clientY - this.drag.y) * 0.009));
      } else {
        this.group.rotation.z = this.drag.rz + (event.clientX - this.drag.x) * 0.006;
        this.group.rotation.x = Math.max(-0.58, Math.min(0.08, this.drag.rx + (event.clientY - this.drag.y) * 0.004));
        this.inspectionAngle = Math.abs(this.group.rotation.x) > 0.08;
      }
      this.render();
    });
    canvas.addEventListener('pointerup', (event) => {
      const dragMode = this.drag?.mode;
      const moved = this.drag && Math.hypot(event.clientX - this.drag.x, event.clientY - this.drag.y) > 5;
      this.drag = null;
      if (!moved && dragMode !== 'component') this.pick(event);
    });
    canvas.addEventListener('pointercancel', () => { this.drag = null; });
    canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      this.cancelCameraAnimation();
      const zoomBounds = this.inspectionComponentId ? [1.8, 6] : [0.72, 4.2];
      this.camera.zoom = Math.max(zoomBounds[0], Math.min(zoomBounds[1], this.camera.zoom * (event.deltaY > 0 ? 0.9 : 1.1)));
      this.camera.updateProjectionMatrix();
      this.updateLabelVisibility(false);
      this.render();
    }, { passive: false });
  }

  pick(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObjects([...this.meshes.values()], true)[0];
    if (hit?.object.userData.componentId) this.onSelect(hit.object.userData.componentId);
  }

  clearSelectionStyle() {
    this.meshes.forEach((object) => object.traverse((child) => {
      if (!child.isMesh || !child.material?.emissive) return;
      child.material.emissive.setHex(0x000000);
      child.material.emissiveIntensity = 0;
    }));
    if (this.selectionHalo) {
      this.selectionHalo.removeFromParent();
      this.selectionHalo.geometry.dispose();
      this.selectionHalo.material.dispose();
      this.selectionHalo = null;
    }
  }

  select(componentId) {
    if (this.inspectionComponentId && this.inspectionComponentId !== componentId) void this.clearComponentInspection(false);
    this.clearSelectionStyle();
    this.selectedComponentId = componentId;
    const object = this.meshes.get(componentId);
    const descriptor = this.descriptors.get(componentId);
    if (!object || !descriptor) return this.render();
    object.traverse((child) => {
      if (!child.isMesh || !child.material?.emissive) return;
      child.material.emissive.setHex(COLORS.selected);
      child.material.emissiveIntensity = 0.2;
    });
    const radius = buildSelectionRadius(descriptor.dimensions);
    this.selectionHalo = new THREE.Mesh(
      new THREE.RingGeometry(radius * 0.82, radius, 40),
      new THREE.MeshBasicMaterial({ color: COLORS.selected, transparent: true, opacity: 0.92, side: THREE.DoubleSide, depthTest: false }),
    );
    this.selectionHalo.position.set(descriptor.center.x, descriptor.center.y, 0.07);
    this.selectionHalo.renderOrder = 8;
    this.group.add(this.selectionHalo);
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
  }

  setInspectionContextOpacity(activeComponentId) {
    this.contextObjects.forEach((object) => this.setObjectEmphasis(object, activeComponentId ? 0.16 : 1));
    this.renderObjects.forEach((object, componentId) => {
      this.setObjectEmphasis(object, inspectionOpacity(activeComponentId, componentId));
      object.visible = true;
    });
    this.shieldObjects.forEach((object) => { object.visible = false; });
    this.moduleObjects.forEach((object) => { object.visible = false; });
    this.labelSprites.forEach((sprite) => { sprite.visible = false; });
    if (this.selectionHalo) this.selectionHalo.visible = !activeComponentId;
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
    if (this.selectionHalo) this.selectionHalo.visible = true;
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
          resolve();
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
    const target = {
      scale: transform.scale,
      z: this.inspectionSnapshot.positionZ + transform.lift,
      rx: -0.42,
      ry: 0.18,
      cameraX: descriptor.center.x,
      cameraY: descriptor.center.y,
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
    this.restoreInspectionContext();
    this.inspectionComponentId = null;
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
    this.applyRepairEmphasis(region);
    if (animate) this.animateCamera(frame.center, frame.zoom);
    else {
      this.camera.position.set(frame.center.x, frame.center.y, 4);
      this.camera.lookAt(frame.center.x, frame.center.y, 0);
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
    const visible = shouldShowLabels(this.camera.zoom);
    this.labelSprites.forEach((sprite, componentId) => {
      const descriptor = this.descriptors.get(componentId);
      const locallyRelevant = componentId === this.selectedComponentId
        || isPointInFocus(descriptor.normalizedCenter, this.activeFocusRegion);
      sprite.visible = visible && locallyRelevant;
    });
    if (shouldRender) this.render();
  }

  setInspectionAngle(enabled) {
    if (this.inspectionComponentId) return;
    this.inspectionAngle = enabled;
    this.group.rotation.x = enabled ? -0.46 : TOP_VIEW_TILT;
    this.render();
  }

  reset() {
    this.cancelCameraAnimation();
    if (this.inspectionComponentId) void this.clearComponentInspection(false);
    this.group.rotation.set(TOP_VIEW_TILT, 0, 0);
    this.inspectionAngle = false;
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
      this.camera.position.set(descriptor?.center.x || 0, descriptor?.center.y || 0, frame.position.z);
      this.camera.lookAt(descriptor?.center.x || 0, descriptor?.center.y || 0, 0);
      this.camera.zoom = transform?.zoom || 2.55;
    } else if (this.activeFocusRegion) {
      const focusFrame = buildFocusFrame(this.activeFocusRegion, width / height);
      this.camera.position.set(focusFrame.center.x, focusFrame.center.y, frame.position.z);
      this.camera.lookAt(focusFrame.center.x, focusFrame.center.y, 0);
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
    this.group.updateMatrixWorld(true);
    this.renderer.render(this.scene, this.camera);
  }
}
