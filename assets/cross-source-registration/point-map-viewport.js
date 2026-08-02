import {
  ImageViewport,
  canStartImagePan,
} from './image-viewport.js';

export {
  centerPoint,
  clampZoom,
  zoomAt,
} from './image-viewport.js';

export function canStartPointMapPan(options) {
  return canStartImagePan(options);
}

export class PointMapViewport extends ImageViewport {}
