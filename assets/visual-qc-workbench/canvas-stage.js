import { projectPoint } from '../cross-source-registration/registration-core.js';

const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));
const rounded = (value) => Number(value.toFixed(9));

export function createViewport() {
  return { zoom: 1, panX: 0, panY: 0 };
}

export function imageFrame(canvas, image, viewport = createViewport()) {
  const baseScale = Math.min(canvas.width / image.width, canvas.height / image.height);
  const width = image.width * baseScale * viewport.zoom;
  const height = image.height * baseScale * viewport.zoom;
  return {
    x: (canvas.width - width) / 2 + viewport.panX,
    y: (canvas.height - height) / 2 + viewport.panY,
    width,
    height,
  };
}

export function normalizedToScreen(point, frame) {
  return {
    x: frame.x + point.x * frame.width,
    y: frame.y + point.y * frame.height,
  };
}

export function screenToNormalized(point, frame) {
  return {
    x: rounded((point.x - frame.x) / frame.width),
    y: rounded((point.y - frame.y) / frame.height),
  };
}

export function zoomViewportAt(viewport, factor, pointer, canvas, image) {
  const before = imageFrame(canvas, image, viewport);
  const normalized = screenToNormalized(pointer, before);
  const next = {
    ...viewport,
    zoom: clamp(viewport.zoom * factor, 1, 8),
  };
  const after = imageFrame(canvas, image, next);
  const projected = normalizedToScreen(normalized, after);
  next.panX += pointer.x - projected.x;
  next.panY += pointer.y - projected.y;
  return next;
}

export function panViewport(viewport, deltaX, deltaY) {
  return {
    ...viewport,
    panX: viewport.panX + deltaX,
    panY: viewport.panY + deltaY,
  };
}

export function drawFittedImage(context, image, frame) {
  context.drawImage(image, frame.x, frame.y, frame.width, frame.height);
}

function drawTriangle(context, image, source, destination) {
  const [s0, s1, s2] = source;
  const [d0, d1, d2] = destination;
  const denominator = s0.x * (s1.y - s2.y) + s1.x * (s2.y - s0.y) + s2.x * (s0.y - s1.y);
  if (Math.abs(denominator) < 1e-9) return;
  const a = (d0.x * (s1.y - s2.y) + d1.x * (s2.y - s0.y) + d2.x * (s0.y - s1.y)) / denominator;
  const c = (d0.x * (s2.x - s1.x) + d1.x * (s0.x - s2.x) + d2.x * (s1.x - s0.x)) / denominator;
  const e = (
    d0.x * (s1.x * s2.y - s2.x * s1.y)
    + d1.x * (s2.x * s0.y - s0.x * s2.y)
    + d2.x * (s0.x * s1.y - s1.x * s0.y)
  ) / denominator;
  const b = (d0.y * (s1.y - s2.y) + d1.y * (s2.y - s0.y) + d2.y * (s0.y - s1.y)) / denominator;
  const d = (d0.y * (s2.x - s1.x) + d1.y * (s0.x - s2.x) + d2.y * (s1.x - s0.x)) / denominator;
  const f = (
    d0.y * (s1.x * s2.y - s2.x * s1.y)
    + d1.y * (s2.x * s0.y - s0.x * s2.y)
    + d2.y * (s0.x * s1.y - s1.x * s0.y)
  ) / denominator;

  context.save();
  context.beginPath();
  context.moveTo(d0.x, d0.y);
  context.lineTo(d1.x, d1.y);
  context.lineTo(d2.x, d2.y);
  context.closePath();
  context.clip();
  context.setTransform(a, b, c, d, e, f);
  context.drawImage(image, 0, 0);
  context.restore();
}

export function drawWarpedImage(context, image, matrix, targetFrame, opacity = 0.35, gridSize = 10) {
  if (!matrix || !image) return;
  context.save();
  context.globalAlpha = opacity;
  for (let row = 0; row < gridSize; row += 1) {
    for (let column = 0; column < gridSize; column += 1) {
      const normalized = [
        { x: column / gridSize, y: row / gridSize },
        { x: (column + 1) / gridSize, y: row / gridSize },
        { x: (column + 1) / gridSize, y: (row + 1) / gridSize },
        { x: column / gridSize, y: (row + 1) / gridSize },
      ];
      const source = normalized.map((point) => ({
        x: point.x * image.naturalWidth,
        y: point.y * image.naturalHeight,
      }));
      const destination = normalized.map(
        (point) => normalizedToScreen(projectPoint(matrix, point), targetFrame),
      );
      drawTriangle(context, image, [source[0], source[1], source[2]], [
        destination[0], destination[1], destination[2],
      ]);
      drawTriangle(context, image, [source[0], source[2], source[3]], [
        destination[0], destination[2], destination[3],
      ]);
    }
  }
  context.restore();
}
