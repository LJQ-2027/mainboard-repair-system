const MIN_ZOOM = 1;
const MAX_ZOOM = 8;

export function clampZoom(value) {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));
}

export function zoomAt(state, nextScale, pointer) {
  const scale = clampZoom(nextScale);
  const ratio = scale / state.scale;
  return {
    scale,
    x: pointer.x - (pointer.x - state.x) * ratio,
    y: pointer.y - (pointer.y - state.y) * ratio,
  };
}

export function centerPoint(point, layerSize, viewportSize, scale) {
  return {
    scale: clampZoom(scale),
    x: viewportSize.width / 2 - point.x * layerSize.width * scale,
    y: viewportSize.height / 2 - point.y * layerSize.height * scale,
  };
}

export class PointMapViewport {
  constructor(view, layer) {
    this.view = view;
    this.layer = layer;
    this.state = { scale: 1, x: 0, y: 0 };
    this.drag = null;
    this.bind();
  }

  bind() {
    this.view.addEventListener('wheel', (event) => {
      event.preventDefault();
      const rect = this.view.getBoundingClientRect();
      const pointer = { x: event.clientX - rect.left, y: event.clientY - rect.top };
      const layerOrigin = this.layerOrigin();
      const localState = { ...this.state, x: layerOrigin.x + this.state.x, y: layerOrigin.y + this.state.y };
      const zoomed = zoomAt(localState, this.state.scale * (event.deltaY < 0 ? 1.25 : 0.8), pointer);
      this.state = { ...zoomed, x: zoomed.x - layerOrigin.x, y: zoomed.y - layerOrigin.y };
      this.render();
    }, { passive: false });
    this.view.addEventListener('pointerdown', (event) => {
      this.drag = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, originX: this.state.x, originY: this.state.y };
      this.view.setPointerCapture(event.pointerId);
      this.view.classList.add('dragging');
    });
    this.view.addEventListener('pointermove', (event) => {
      if (!this.drag || event.pointerId !== this.drag.pointerId) return;
      this.state.x = this.drag.originX + event.clientX - this.drag.x;
      this.state.y = this.drag.originY + event.clientY - this.drag.y;
      this.render();
    });
    const stop = () => { this.drag = null; this.view.classList.remove('dragging'); };
    this.view.addEventListener('pointerup', stop);
    this.view.addEventListener('pointercancel', stop);
  }

  layerOrigin() {
    return {
      x: (this.view.clientWidth - this.layer.offsetWidth) / 2,
      y: (this.view.clientHeight - this.layer.offsetHeight) / 2,
    };
  }

  render() {
    const origin = this.layerOrigin();
    this.layer.style.transform = `translate(${origin.x + this.state.x}px, ${origin.y + this.state.y}px) scale(${this.state.scale})`;
    this.view.dataset.zoom = `${Math.round(this.state.scale * 100)}%`;
  }

  reset() {
    this.state = { scale: 1, x: 0, y: 0 };
    this.render();
  }

  zoomBy(factor) {
    const center = { x: this.view.clientWidth / 2, y: this.view.clientHeight / 2 };
    const origin = this.layerOrigin();
    const zoomed = zoomAt({ ...this.state, x: origin.x + this.state.x, y: origin.y + this.state.y }, this.state.scale * factor, center);
    this.state = { ...zoomed, x: zoomed.x - origin.x, y: zoomed.y - origin.y };
    this.render();
  }

  focus(point, scale = 4) {
    const size = { width: this.layer.offsetWidth, height: this.layer.offsetHeight };
    const viewport = { width: this.view.clientWidth, height: this.view.clientHeight };
    const absolute = centerPoint(point, size, viewport, scale);
    const origin = this.layerOrigin();
    this.state = { ...absolute, x: absolute.x - origin.x, y: absolute.y - origin.y };
    this.render();
  }
}
