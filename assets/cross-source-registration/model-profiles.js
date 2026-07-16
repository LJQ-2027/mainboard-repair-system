const BOARD_WIDTH = 2;
const BOARD_HEIGHT = 1.25;

const FAMILY_BY_CATEGORY = {
  antenna: 'antenna',
  bga_ic: 'ic',
  capacitor: 'passive',
  connector: 'connector',
  crystal: 'crystal',
  diode: 'diode',
  ic: 'ic',
  inductor: 'inductor',
  led: 'led',
  resistor: 'passive',
  test_point: 'test-point',
  transistor: 'transistor',
};

const PACKAGE_PROFILES = {
  antenna: { min: [0.018, 0.012], max: [0.22, 0.12], height: 0.006 },
  connector: { min: [0.04, 0.025], max: [0.36, 0.24], height: 0.045 },
  crystal: { min: [0.025, 0.018], max: [0.13, 0.10], height: 0.028 },
  diode: { min: [0.015, 0.01], max: [0.11, 0.07], height: 0.014 },
  generic: { min: [0.012, 0.01], max: [0.10, 0.08], height: 0.012 },
  ic: { min: [0.022, 0.018], max: [0.26, 0.22], height: 0.032 },
  inductor: { min: [0.018, 0.016], max: [0.12, 0.10], height: 0.024 },
  led: { min: [0.014, 0.01], max: [0.08, 0.06], height: 0.016 },
  passive: { min: [0.01, 0.008], max: [0.09, 0.055], height: 0.011 },
  'test-point': { min: [0.018, 0.018], max: [0.055, 0.055], height: 0.006 },
  transistor: { min: [0.018, 0.014], max: [0.11, 0.09], height: 0.018 },
};

const INSPECTION_VISUAL_ASSETS = {
  'u2001-pmic-v1': 'reviewed-pmic',
  'u4000-emmc-v1': 'reviewed-bga',
  'u0600-rf-device-v1': 'reviewed-bga',
};

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

export function buildEngineeringSurfacePresentation() {
  return {
    boardColor: 0x285e51,
    boardEdgeColor: 0xb4823a,
    surfaceOpacity: 0.76,
  };
}

export function resolvePackageFamily(category) {
  return FAMILY_BY_CATEGORY[category] || 'generic';
}

export function buildRenderProfile(category) {
  const family = resolvePackageFamily(category);
  return { family, ...PACKAGE_PROFILES[family] };
}

export function resolveInspectionVisualAsset(inspectionProfile) {
  return INSPECTION_VISUAL_ASSETS[inspectionProfile?.profile_id] || 'standard';
}

export function buildRenderDescriptor(component, options = {}) {
  const source = component.footprint || component.geometry;
  if (!source?.center || !source?.size) return null;

  const confidence = source.confidence || source.source_status || (options.reviewed ? 'reviewed' : 'medium');
  if (confidence === 'low' && !options.reviewed) return null;

  const profile = buildRenderProfile(component.category);
  const layer = confidence === 'high' || confidence === 'reviewed'
    ? 'body'
    : (confidence === 'low' ? 'marker' : 'outline');
  const width = clamp(source.size.x * BOARD_WIDTH, profile.min[0], profile.max[0]);
  const depth = clamp(source.size.y * BOARD_HEIGHT, profile.min[1], profile.max[1]);

  return {
    componentId: component.component_id,
    designator: component.designator,
    category: component.category,
    family: profile.family,
    confidence,
    layer,
    selectable: Boolean(options.reviewed),
    inspectionProfile: component.inspection_profile || null,
    visualAsset: resolveInspectionVisualAsset(component.inspection_profile),
    normalizedCenter: { ...source.center },
    center: {
      x: source.center.x * BOARD_WIDTH - BOARD_WIDTH / 2,
      y: (1 - source.center.y) * BOARD_HEIGHT - BOARD_HEIGHT / 2,
    },
    dimensions: {
      x: width,
      y: depth,
      z: layer === 'body' ? profile.height : 0,
    },
  };
}

function rotatedBounds(width, height, rotationZ = 0) {
  const cosine = Math.abs(Math.cos(rotationZ));
  const sine = Math.abs(Math.sin(rotationZ));
  return {
    width: width * cosine + height * sine,
    height: width * sine + height * cosine,
  };
}

export function buildDefaultBoardRotation(aspect = 1) {
  return aspect < 0.9 ? Math.PI / 2 : 0;
}

export function buildCameraFrame(aspect = 1, rotationZ = 0) {
  const safeAspect = Math.max(aspect, 0.25);
  const bounds = rotatedBounds(BOARD_WIDTH, BOARD_HEIGHT, rotationZ);
  const portraitBoard = Math.abs(Math.sin(rotationZ)) > 0.7;
  const minimumWidth = bounds.width + 0.2;
  const minimumHeight = bounds.height + (portraitBoard ? 0.58 : 0.15);
  const height = Math.max(minimumHeight, minimumWidth / safeAspect);
  const width = height * safeAspect;
  return {
    left: -width / 2,
    right: width / 2,
    top: height / 2,
    bottom: -height / 2,
    near: 0.1,
    far: 20,
    position: { x: 0, y: 0, z: 4 },
  };
}

export function buildFocusFrame(region, aspect = 1, rotationZ = 0) {
  const frame = buildCameraFrame(aspect, rotationZ);
  const frameWidth = frame.right - frame.left;
  const frameHeight = frame.top - frame.bottom;
  const paddedWidth = (region.size.x * 2 + 0.22) * BOARD_WIDTH;
  const paddedHeight = (region.size.y * 1.25 + 0.18) * BOARD_HEIGHT;
  const paddedBounds = rotatedBounds(paddedWidth, paddedHeight, rotationZ);
  const maximumZoom = aspect >= 1.2 ? 1.9 : 2.2;
  const zoom = clamp(Math.min(frameWidth / paddedBounds.width, frameHeight / paddedBounds.height) * 0.86, 1.35, maximumZoom);
  return {
    center: {
      x: Math.round((region.center.x * BOARD_WIDTH - BOARD_WIDTH / 2) * 1_000_000) / 1_000_000,
      y: Math.round(((1 - region.center.y) * BOARD_HEIGHT - BOARD_HEIGHT / 2) * 1_000_000) / 1_000_000,
    },
    zoom: Math.round(zoom * 1_000_000) / 1_000_000,
  };
}

export function buildSelectionRadius(dimensions) {
  return Math.round(clamp(Math.max(dimensions.x, dimensions.y) * 0.44 + 0.006, 0.022, 0.09) * 1_000_000) / 1_000_000;
}

export function buildUnresolvedMarkerPresentation() {
  return { color: 0x73827b, opacity: 0.56 };
}

export const BOARD_WORLD_SIZE = Object.freeze({ width: BOARD_WIDTH, height: BOARD_HEIGHT });
