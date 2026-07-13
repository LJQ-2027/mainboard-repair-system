import * as THREE from '../vendor/three/three.module.min.js';
import {
  BOARD_WORLD_SIZE,
  buildCameraFrame,
  buildRenderDescriptor,
} from './model-profiles.js';

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
  if (descriptor.family === 'passive') addPassivePackage(group, descriptor);
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

export class BoardRenderer {
  constructor(container, entities, boardOutline, compiledComponents, engineeringTextureUrl, onSelect) {
    this.container = container;
    this.entities = entities;
    this.boardOutline = boardOutline;
    this.compiledComponents = compiledComponents;
    this.engineeringTextureUrl = engineeringTextureUrl;
    this.onSelect = onSelect;
    this.meshes = new Map();
    this.descriptors = new Map();
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
    this.renderer.compile(this.scene, this.camera);
    this.bind();
    this.resize();
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(container);
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
    this.group.add(surface);
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
    this.group.add(object);
    this.descriptors.set(descriptor.componentId, descriptor);
    if (descriptor.selectable) this.meshes.set(descriptor.componentId, object);
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

  bind() {
    const canvas = this.renderer.domElement;
    canvas.addEventListener('pointerdown', (event) => {
      this.drag = { x: event.clientX, y: event.clientY, rx: this.group.rotation.x, rz: this.group.rotation.z };
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', (event) => {
      if (!this.drag) return;
      this.group.rotation.z = this.drag.rz + (event.clientX - this.drag.x) * 0.006;
      this.group.rotation.x = Math.max(-0.58, Math.min(0.08, this.drag.rx + (event.clientY - this.drag.y) * 0.004));
      this.inspectionAngle = Math.abs(this.group.rotation.x) > 0.08;
      this.render();
    });
    canvas.addEventListener('pointerup', (event) => {
      const moved = this.drag && Math.hypot(event.clientX - this.drag.x, event.clientY - this.drag.y) > 5;
      this.drag = null;
      if (!moved) this.pick(event);
    });
    canvas.addEventListener('pointercancel', () => { this.drag = null; });
    canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      this.camera.zoom = Math.max(0.72, Math.min(4.2, this.camera.zoom * (event.deltaY > 0 ? 0.9 : 1.1)));
      this.camera.updateProjectionMatrix();
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
    this.clearSelectionStyle();
    const object = this.meshes.get(componentId);
    const descriptor = this.descriptors.get(componentId);
    if (!object || !descriptor) return this.render();
    object.traverse((child) => {
      if (!child.isMesh || !child.material?.emissive) return;
      child.material.emissive.setHex(COLORS.selected);
      child.material.emissiveIntensity = 0.2;
    });
    const radius = Math.max(descriptor.dimensions.x, descriptor.dimensions.y) * 0.58 + 0.008;
    this.selectionHalo = new THREE.Mesh(
      new THREE.RingGeometry(radius * 0.82, radius, 40),
      new THREE.MeshBasicMaterial({ color: COLORS.selected, transparent: true, opacity: 0.92, side: THREE.DoubleSide, depthTest: false }),
    );
    this.selectionHalo.position.set(descriptor.center.x, descriptor.center.y, 0.07);
    this.selectionHalo.renderOrder = 8;
    this.group.add(this.selectionHalo);
    this.render();
  }

  setInspectionAngle(enabled) {
    this.inspectionAngle = enabled;
    this.group.rotation.x = enabled ? -0.46 : TOP_VIEW_TILT;
    this.render();
  }

  reset() {
    this.group.rotation.set(TOP_VIEW_TILT, 0, 0);
    this.camera.zoom = 1;
    this.camera.position.set(0, 0, 4);
    this.camera.lookAt(0, 0, 0);
    this.camera.updateProjectionMatrix();
    this.inspectionAngle = false;
    this.render();
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
    this.camera.position.set(frame.position.x, frame.position.y, frame.position.z);
    this.camera.lookAt(0, 0, 0);
    this.camera.updateProjectionMatrix();
    this.render();
  }

  render() {
    this.group.updateMatrixWorld(true);
    this.renderer.render(this.scene, this.camera);
  }
}
