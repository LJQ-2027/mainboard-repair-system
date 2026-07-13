import * as THREE from '../vendor/three/three.module.min.js';

const COLORS = { board: 0x163c35, copper: 0xc78b45, component: 0x26342f, selected: 0xf2c94c, point: 0xef5b3f };

export class BoardRenderer {
  constructor(container, entities, boardOutline, onSelect) {
    this.container = container;
    this.entities = entities;
    this.boardOutline = boardOutline;
    this.onSelect = onSelect;
    this.meshes = new Map();
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xf2f3ef);
    this.camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
    this.camera.position.set(0, -2.3, 2.4);
    this.camera.lookAt(0, 0, 0);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.append(this.renderer.domElement);
    this.group = new THREE.Group();
    this.group.rotation.x = -0.08;
    this.scene.add(this.group);
    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.drag = null;
    this.build();
    this.bind();
    this.resize();
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(container);
  }

  build() {
    const shape = new THREE.Shape();
    this.boardOutline.forEach((point, index) => {
      const x = point.x * 2 - 1;
      const y = (1 - point.y) * 1.25 - 0.625;
      if (index === 0) shape.moveTo(x, y); else shape.lineTo(x, y);
    });
    shape.closePath();
    const board = new THREE.Mesh(
      new THREE.ExtrudeGeometry(shape, { depth: 0.055, bevelEnabled: false }),
      new THREE.MeshStandardMaterial({ color: COLORS.board, roughness: 0.68, metalness: 0.12 }),
    );
    board.position.z = -0.055;
    this.group.add(board);
    const rim = new THREE.LineSegments(
      new THREE.EdgesGeometry(board.geometry),
      new THREE.LineBasicMaterial({ color: COLORS.copper }),
    );
    board.add(rim);

    this.entities.forEach((entity) => {
      const { center, size } = entity.geometry;
      const height = Math.max(entity.visual_profile.height * 2.8, 0.035);
      const geometry = entity.category === 'test_point'
        ? new THREE.CylinderGeometry(0.025, 0.025, height, 20)
        : new THREE.BoxGeometry(Math.max(size.x * 2, 0.045), Math.max(size.y * 1.25, 0.045), height);
      if (entity.category === 'test_point') geometry.rotateX(Math.PI / 2);
      const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
        color: entity.category === 'test_point' ? COLORS.point : COLORS.component,
        roughness: 0.58,
        metalness: entity.category === 'connector' ? 0.5 : 0.18,
      }));
      mesh.position.set(center.x * 2 - 1, (1 - center.y) * 1.25 - 0.625, 0.03 + height / 2);
      mesh.userData.componentId = entity.component_id;
      this.group.add(mesh);
      this.meshes.set(entity.component_id, mesh);
    });

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x4a5b54, 2.2));
    const key = new THREE.DirectionalLight(0xffffff, 2.8);
    key.position.set(-2, -3, 5);
    this.scene.add(key);
  }

  bind() {
    const canvas = this.renderer.domElement;
    canvas.addEventListener('pointerdown', (event) => {
      this.drag = { x: event.clientX, y: event.clientY, rx: this.group.rotation.x, rz: this.group.rotation.z };
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', (event) => {
      if (!this.drag) return;
      this.group.rotation.z = this.drag.rz + (event.clientX - this.drag.x) * 0.008;
      this.group.rotation.x = Math.max(-0.75, Math.min(0.45, this.drag.rx + (event.clientY - this.drag.y) * 0.006));
      this.render();
    });
    canvas.addEventListener('pointerup', (event) => {
      const moved = this.drag && Math.hypot(event.clientX - this.drag.x, event.clientY - this.drag.y) > 5;
      this.drag = null;
      if (!moved) this.pick(event);
    });
    canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      this.camera.position.multiplyScalar(event.deltaY > 0 ? 1.08 : 0.92);
      this.camera.position.clampLength(2.1, 5.2);
      this.render();
    }, { passive: false });
  }

  pick(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObjects([...this.meshes.values()], false)[0];
    if (hit) this.onSelect(hit.object.userData.componentId);
  }

  select(componentId) {
    this.meshes.forEach((mesh, id) => mesh.material.color.setHex(id === componentId ? COLORS.selected : (mesh.geometry.type === 'CylinderGeometry' ? COLORS.point : COLORS.component)));
    this.render();
  }

  reset() {
    this.group.rotation.set(-0.08, 0, 0);
    this.camera.position.set(0, -2.3, 2.4);
    this.camera.lookAt(0, 0, 0);
    this.render();
  }

  resize() {
    const width = Math.max(this.container.clientWidth, 320);
    const height = Math.max(this.container.clientHeight, 320);
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.render();
  }

  render() { this.renderer.render(this.scene, this.camera); }
}
