import { analyzeImageQuality } from '../vision-recognition-demo/vision-core.js';
import {
  annotationCentroid,
  createVisualQcCase,
  DEFECT_CATEGORIES,
  suggestEntityAtPoint,
  updateCaptureChecklist,
} from './visual-qc-core.js';
import {
  addAnnotation,
  applyRegistration,
  commitHistory,
  createHistory,
  finalizeQc,
  redoHistory,
  removeAnnotation,
  reviewRegistration,
  undoHistory,
  updateAnnotation,
  updateDraftRegistration,
} from './visual-qc-state.js';
import {
  createViewport,
  drawFittedImage,
  drawWarpedImage,
  imageFrame,
  normalizedToScreen,
  panViewport,
  screenToNormalized,
  zoomViewportAt,
} from './canvas-stage.js';
import { invertHomography, projectPoint } from '../cross-source-registration/registration-core.js';
import {
  deleteVisualQcCase,
  listVisualQcCases,
  loadVisualQcCase,
  saveVisualQcCase,
} from './visual-qc-storage.js';
import {
  applyCandidateReview,
  applyDifferenceJobResult,
  applyFinalQcReview,
  applyGoldenSample,
  applyServerJobResult,
  approveGoldenSample,
  createDifferenceJob,
  createServerSyncState,
  getActiveGoldenSample,
  getVisualQcCaptureSession,
  getVisualQcCocoDataset,
  getVisualQcDatasetAudit,
  getVisualQcIdentity,
  getVisualQcTrainingManifest,
  getVisualQcArtifact,
  getVisualQcJob,
  normalizeServerCaptureSession,
  pollVisualQcJob,
  reviewDifferenceCandidate,
  retryVisualQcJob,
  reviewVisualQcCase,
  reviewVisualQcRegistration,
  transitionServerSync,
  uploadVisualQcCase,
} from './visual-qc-server-client.js';

const CATALOG_URL = '../../knowledge-base/repair-workbench-boards.json';
const QUERY = new URLSearchParams(window.location.search);
const VISUAL_QC_API = QUERY.get('qcApi') || '../../api/v1/visual-qc';
let VISUAL_QC_ACTOR_ID = QUERY.get('qcActor')
  || globalThis.VISUAL_QC_ACTOR_ID
  || 'local-technician';
let VISUAL_QC_ACTOR_ROLE = QUERY.get('qcRole')
  || globalThis.VISUAL_QC_ACTOR_ROLE
  || 'technician';
const ANALYSIS_MAX_EDGE = 720;
const CATEGORY_LABELS = {
  burn_or_heat_damage: '烧焦或热损伤',
  corrosion_or_oxidation: '腐蚀或氧化',
  missing_component: '元器件缺失',
  displaced_component: '元器件移位',
  connector_damage: '连接器损伤',
  shield_or_structure_damage: '屏蔽罩或结构破损',
  solder_anomaly: '焊接外观异常',
  foreign_material: '异物或污染',
  unknown_visible_anomaly: '未分类可见异常',
};
const QC_LABELS = {
  image_invalid: '图片不可用',
  needs_review: '待人工审核',
  no_visible_anomaly: '未见可见异常',
  confirmed_anomaly: '已确认可见异常',
};
const SERVER_CATEGORY_LABELS = {
  burn_or_thermal_damage: '烧焦或热损伤',
  corrosion_or_oxidation: '腐蚀或氧化',
  missing_component: '元器件缺失',
  displaced_component: '元器件移位',
  connector_damage: '连接器损伤',
  shield_or_structural_damage: '屏蔽罩或结构破损',
  solder_appearance_anomaly: '焊接外观异常',
  foreign_material_or_contamination: '异物或污染',
  unclassified_visible_anomaly: '未分类可见异常',
};

const byId = (id) => document.getElementById(id);
const elements = {
  saveStatus: byId('saveStatus'),
  savedCasesButton: byId('savedCasesButton'),
  boardSelect: byId('boardSelect'),
  sideSelector: byId('sideSelector'),
  captureStage: byId('captureStage'),
  imageInput: byId('imageInput'),
  chooseImageButton: byId('chooseImageButton'),
  proxyButton: byId('proxyButton'),
  caseImportInput: byId('caseImportInput'),
  importCaseButton: byId('importCaseButton'),
  registrationModeButton: byId('registrationModeButton'),
  annotationModeButton: byId('annotationModeButton'),
  registrationTools: byId('registrationTools'),
  annotationTools: byId('annotationTools'),
  finishPolygonButton: byId('finishPolygonButton'),
  zoomOutButton: byId('zoomOutButton'),
  zoomInButton: byId('zoomInButton'),
  resetViewButton: byId('resetViewButton'),
  undoButton: byId('undoButton'),
  redoButton: byId('redoButton'),
  boardCanvas: byId('boardCanvas'),
  photoCanvas: byId('photoCanvas'),
  boardEmpty: byId('boardEmpty'),
  photoEmpty: byId('photoEmpty'),
  photoDropZone: byId('photoDropZone'),
  boardCanvasMeta: byId('boardCanvasMeta'),
  photoCanvasMeta: byId('photoCanvasMeta'),
  interactionPrompt: byId('interactionPrompt'),
  overlayOpacity: byId('overlayOpacity'),
  captureSessionTitle: byId('captureSessionTitle'),
  captureSessionBadge: byId('captureSessionBadge'),
  captureSessionSummary: byId('captureSessionSummary'),
  captureChecklist: byId('captureChecklist'),
  refreshCaptureSessionButton: byId('refreshCaptureSessionButton'),
  captureOtherSideButton: byId('captureOtherSideButton'),
  qualityTitle: byId('qualityTitle'),
  qualityBadge: byId('qualityBadge'),
  qualityScore: byId('qualityScore'),
  qualityResolution: byId('qualityResolution'),
  qualitySharpness: byId('qualitySharpness'),
  qualityGuidance: byId('qualityGuidance'),
  serverSyncTitle: byId('serverSyncTitle'),
  serverSyncBadge: byId('serverSyncBadge'),
  serverSyncProgress: byId('serverSyncProgress'),
  serverSyncDetail: byId('serverSyncDetail'),
  serverSyncButton: byId('serverSyncButton'),
  registrationTitle: byId('registrationTitle'),
  registrationBadge: byId('registrationBadge'),
  anchorCount: byId('anchorCount'),
  checkCountLabel: byId('checkCountLabel'),
  checkCount: byId('checkCount'),
  registrationError: byId('registrationError'),
  removeLastPairButton: byId('removeLastPairButton'),
  clearRegistrationButton: byId('clearRegistrationButton'),
  reviewRegistrationButton: byId('reviewRegistrationButton'),
  comparisonSection: byId('comparisonSection'),
  comparisonTitle: byId('comparisonTitle'),
  comparisonBadge: byId('comparisonBadge'),
  captureSetupId: byId('captureSetupId'),
  goldenSummary: byId('goldenSummary'),
  normalConfirmationField: byId('normalConfirmationField'),
  normalConfirmation: byId('normalConfirmation'),
  refreshGoldenButton: byId('refreshGoldenButton'),
  approveGoldenButton: byId('approveGoldenButton'),
  runDifferenceButton: byId('runDifferenceButton'),
  heatmapFigure: byId('heatmapFigure'),
  heatmapImage: byId('heatmapImage'),
  heatmapMeta: byId('heatmapMeta'),
  heatmapOverlay: byId('heatmapOverlay'),
  candidateList: byId('candidateList'),
  annotationSection: byId('annotationSection'),
  annotationCount: byId('annotationCount'),
  defectCategory: byId('defectCategory'),
  annotationList: byId('annotationList'),
  finalizeQcButton: byId('finalizeQcButton'),
  trainingDatasetSection: byId('trainingDatasetSection'),
  trainingCaseCount: byId('trainingCaseCount'),
  trainingAnnotationCount: byId('trainingAnnotationCount'),
  trainingCategoryCount: byId('trainingCategoryCount'),
  trainingExcludedCount: byId('trainingExcludedCount'),
  trainingDatasetSummary: byId('trainingDatasetSummary'),
  trainingGateSummary: byId('trainingGateSummary'),
  trainingGateCasesDisclosure: byId('trainingGateCasesDisclosure'),
  trainingGateCaseCount: byId('trainingGateCaseCount'),
  trainingGateCaseList: byId('trainingGateCaseList'),
  refreshTrainingDatasetButton: byId('refreshTrainingDatasetButton'),
  downloadTrainingManifestButton: byId('downloadTrainingManifestButton'),
  downloadTrainingCocoButton: byId('downloadTrainingCocoButton'),
  qcResultTitle: byId('qcResultTitle'),
  qcResultBadge: byId('qcResultBadge'),
  exportJsonButton: byId('exportJsonButton'),
  exportPngButton: byId('exportPngButton'),
  savedCasesDialog: byId('savedCasesDialog'),
  closeSavedCasesButton: byId('closeSavedCasesButton'),
  savedCasesList: byId('savedCasesList'),
  annotationTemplate: byId('annotationTemplate'),
};

const state = {
  catalog: null,
  boardKey: null,
  boardEntry: null,
  dataset: null,
  manifest: null,
  sideId: null,
  geometry: null,
  entities: [],
  pointMapImage: null,
  photoImage: null,
  photoBlob: null,
  isProxy: false,
  history: null,
  mode: 'registration',
  registrationTool: 'anchor',
  annotationTool: 'rectangle',
  boardAnchors: [],
  imageAnchors: [],
  checkPoints: [],
  pendingBoardPoint: null,
  selectedAnnotationId: null,
  polygonPoints: [],
  rectanglePreview: null,
  boardViewport: createViewport(),
  photoViewport: createViewport(),
  activeCanvas: 'photo',
  drag: null,
  saveTimer: null,
  awaitingImportedImage: false,
  loadRevision: 0,
  serverBusy: false,
  comparisonBusy: false,
  heatmapUrl: null,
  heatmapArtifactId: null,
  heatmapLoadingArtifactId: null,
  captureSessionDraft: null,
  trainingManifest: null,
  trainingAudit: null,
  trainingDatasetBusy: false,
  trainingDatasetError: null,
};

const QUALITY_GUIDANCE_COPY = Object.freeze({
  low_resolution: '请靠近拍摄，并让完整主板保持在画面内。',
  overexposed: '请减弱直射光或调整角度，避免反光过曝。',
  underexposed: '请补充柔和光线，让深色区域保持可见。',
  low_contrast: '请使用对比明显的纯色背景，并改善照明均匀度。',
  blurred: '请稳定相机，并点击主板区域完成对焦。',
  soft_focus: '请靠近并重新对焦后拍摄。',
  ready: '图像质量可用于内部参考配准。',
});

const TRAINING_GATE_LABELS = Object.freeze({
  non_physical_evidence: '代理或非实拍',
  capture_checklist_required: '拍摄确认未完成',
  processing_incomplete: '服务器处理未完成',
  image_retake_required: '图片需要重拍',
  registration_review_required: '配准尚未审核',
  final_qc_review_required: '最终 QC 未审核',
});

const BOARD_SIDE_LABELS = Object.freeze({
  main_page_1: '第1面',
  main_page_2: '第2面',
  main_top: 'TOP',
  main_bot: 'BOT',
});

function currentCase() {
  return state.history?.current || null;
}

function reportUserError(error) {
  elements.interactionPrompt.textContent = error instanceof Error
    ? error.message
    : '操作失败，请重试。';
}

function captureSetupId() {
  return elements.captureSetupId.value.trim() || 'standard-bench';
}

function expectedSideIds() {
  return (state.manifest?.sides || []).map((side) => side.side_id);
}

function captureSessionForNewCase(isProxy) {
  const draft = state.captureSessionDraft;
  const expected = expectedSideIds();
  const reusable = !isProxy
    && draft?.boardKey === state.boardKey
    && draft?.captureStage === elements.captureStage.value
    && draft?.setupId === captureSetupId();
  const session = {
    sessionId: reusable ? draft.sessionId : `${isProxy ? 'proxy' : 'capture'}-${crypto.randomUUID()}`,
    setupId: captureSetupId(),
    expectedSideIds: expected,
    capturedSideIds: reusable ? draft.capturedSideIds : [],
    checklist: {},
  };
  state.captureSessionDraft = null;
  return session;
}

function clearHeatmap() {
  if (state.heatmapUrl) URL.revokeObjectURL(state.heatmapUrl);
  state.heatmapUrl = null;
  state.heatmapArtifactId = null;
  state.heatmapLoadingArtifactId = null;
  elements.heatmapImage.removeAttribute('src');
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${url} returned ${response.status}`);
  return response.json();
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.decoding = 'async';
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`无法载入图片：${url}`));
    image.src = url;
  });
}

async function imageFromBlob(blob) {
  const url = URL.createObjectURL(blob);
  try {
    return await loadImage(url);
  } finally {
    URL.revokeObjectURL(url);
  }
}

function imagePixels(image) {
  const scale = Math.min(1, ANALYSIS_MAX_EDGE / Math.max(image.naturalWidth, image.naturalHeight));
  const width = Math.max(1, Math.round(image.naturalWidth * scale));
  const height = Math.max(1, Math.round(image.naturalHeight * scale));
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d', { willReadFrequently: true });
  context.drawImage(image, 0, 0, width, height);
  const pixels = context.getImageData(0, 0, width, height);
  return {
    data: pixels.data,
    width,
    height,
    sourceWidth: image.naturalWidth,
    sourceHeight: image.naturalHeight,
  };
}

async function sha256(blob) {
  const digest = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, '0'))
    .join('');
}

function rootAsset(path) {
  return `../../${path}`;
}

function caseImageMetadata(blob, image, fileName, isProxy) {
  return {
    file_name: fileName,
    mime_type: blob.type || 'image/jpeg',
    width: image.naturalWidth,
    height: image.naturalHeight,
    evidence_role: isProxy ? 'proxy_sample' : 'physical_capture',
  };
}

function normalizedGeometryEntities(geometry, sideId) {
  return (geometry?.components || [])
    .filter((component) => component.footprint && component.footprint.confidence !== 'low')
    .map((component) => ({
      component_id: component.component_id,
      designator: component.designator,
      side_id: sideId,
      geometry: {
        center: component.footprint.center,
        size: component.footprint.size,
      },
    }));
}

async function loadBoard(boardKey, requestedSide = null, resetCase = true) {
  const loadRevision = ++state.loadRevision;
  if (resetCase) await flushPendingSave();
  if (loadRevision !== state.loadRevision) return false;
  const boardEntry = state.catalog.boards[boardKey];
  const [dataset, manifest] = await Promise.all([
    fetchJson(boardEntry.data),
    fetchJson(boardEntry.side_manifest),
  ]);
  const sideId = requestedSide && manifest.sides.some((side) => side.side_id === requestedSide)
    ? requestedSide
    : manifest.default_side_id;
  const side = manifest.sides.find((item) => item.side_id === sideId);
  const [geometry, pointMapImage] = await Promise.all([
    fetchJson(boardEntry.geometry_by_side[sideId]),
    loadImage(rootAsset(side.engineering_texture)),
  ]);
  if (loadRevision !== state.loadRevision) return false;
  state.boardKey = boardKey;
  state.boardEntry = boardEntry;
  state.dataset = dataset;
  state.manifest = manifest;
  state.sideId = sideId;
  state.geometry = geometry;
  state.entities = normalizedGeometryEntities(geometry, sideId);
  state.pointMapImage = pointMapImage;
  state.boardViewport = createViewport();
  if (resetCase) resetVisualCase();
  renderSideSelector();
  elements.boardEmpty.hidden = true;
  elements.boardCanvasMeta.textContent = `${side.label} · ${geometry.components.length} 个位号`;
  elements.proxyButton.hidden = !dataset.registration?.proxy_image;
  resizeCanvases();
  render();
  return true;
}

async function loadSide(sideId, resetCase = true) {
  const loadRevision = ++state.loadRevision;
  if (resetCase) await flushPendingSave();
  if (loadRevision !== state.loadRevision) return false;
  const boardEntry = state.boardEntry;
  const manifest = state.manifest;
  const side = manifest.sides.find((item) => item.side_id === sideId);
  const [geometry, pointMapImage] = await Promise.all([
    fetchJson(boardEntry.geometry_by_side[sideId]),
    loadImage(rootAsset(side.engineering_texture)),
  ]);
  if (loadRevision !== state.loadRevision) return false;
  state.sideId = sideId;
  state.geometry = geometry;
  state.entities = normalizedGeometryEntities(geometry, sideId);
  state.pointMapImage = pointMapImage;
  state.boardViewport = createViewport();
  if (resetCase) resetVisualCase();
  renderSideSelector();
  elements.boardEmpty.hidden = true;
  elements.boardCanvasMeta.textContent = `${side.label} · ${geometry.components.length} 个位号`;
  resizeCanvases();
  render();
  return true;
}

function renderBoardSelector() {
  elements.boardSelect.replaceChildren();
  for (const [key, entry] of Object.entries(state.catalog.boards)) {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = entry.title;
    elements.boardSelect.append(option);
  }
  elements.boardSelect.value = state.boardKey;
}

function renderSideSelector() {
  elements.sideSelector.replaceChildren();
  const legend = document.createElement('legend');
  legend.textContent = '板面';
  elements.sideSelector.append(legend);
  for (const side of state.manifest?.sides || []) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = side.label;
    button.dataset.sideId = side.side_id;
    button.setAttribute('aria-pressed', String(side.side_id === state.sideId));
    button.addEventListener('click', () => {
      if (side.side_id !== state.sideId) {
        state.captureSessionDraft = null;
        loadSide(side.side_id, true);
      }
    });
    elements.sideSelector.append(button);
  }
}

function resetVisualCase() {
  clearTimeout(state.saveTimer);
  state.saveTimer = null;
  clearHeatmap();
  state.photoImage = null;
  state.photoBlob = null;
  state.isProxy = false;
  state.awaitingImportedImage = false;
  state.history = null;
  state.boardAnchors = [];
  state.imageAnchors = [];
  state.checkPoints = [];
  state.pendingBoardPoint = null;
  state.selectedAnnotationId = null;
  state.polygonPoints = [];
  state.rectanglePreview = null;
  state.photoViewport = createViewport();
  elements.imageInput.value = '';
  render();
}

function syncRegistrationState() {
  const registration = currentCase()?.registration;
  state.boardAnchors = (registration?.solve_anchors || []).map((pair) => pair.board);
  state.imageAnchors = (registration?.solve_anchors || []).map((pair) => pair.image);
  state.checkPoints = structuredClone(registration?.check_points || []);
  state.pendingBoardPoint = null;
}

function commitCase(nextCase) {
  state.history = state.history ? commitHistory(state.history, nextCase) : createHistory(nextCase);
  syncRegistrationState();
  scheduleSave();
  render();
}

function replaceCurrentCase(nextCase, persist = false) {
  if (!state.history) return;
  state.history = {
    ...state.history,
    current: structuredClone(nextCase),
  };
  syncRegistrationState();
  if (persist) scheduleSave();
  render();
}

function scheduleSave() {
  clearTimeout(state.saveTimer);
  const visualCase = currentCase();
  if (!visualCase) return;
  const imageBlob = state.photoBlob;
  elements.saveStatus.textContent = '正在保存到本机';
  state.saveTimer = setTimeout(async () => {
    state.saveTimer = null;
    try {
      await saveVisualQcCase(visualCase, imageBlob);
      elements.saveStatus.textContent = '已保存到本机';
    } catch (error) {
      elements.saveStatus.textContent = '本机保存不可用';
      console.warn(error);
    }
  }, 250);
}

async function flushPendingSave() {
  if (!state.saveTimer) return;
  clearTimeout(state.saveTimer);
  state.saveTimer = null;
  const visualCase = currentCase();
  if (!visualCase) return;
  try {
    await saveVisualQcCase(visualCase, state.photoBlob);
    elements.saveStatus.textContent = '已保存到本机';
  } catch (error) {
    elements.saveStatus.textContent = '本机保存不可用';
    console.warn(error);
  }
}

function acceptedCaseFromSync(sync) {
  return {
    case_id: sync.server_case_id,
    image: { image_id: sync.server_image_id },
    job: { job_id: sync.job_id, status: sync.job_status },
  };
}

async function pollCurrentServerJob(acceptedCase) {
  const sync = currentCase()?.server_sync;
  if (!sync?.job_id) throw new Error('服务器任务编号不存在。');
  const terminal = await pollVisualQcJob({
    jobId: sync.job_id,
    getJob: (jobId) => getVisualQcJob(VISUAL_QC_API, VISUAL_QC_ACTOR_ID, jobId),
    onSnapshot: (snapshot) => {
      const visualCase = currentCase();
      if (!visualCase) return;
      const next = structuredClone(visualCase);
      next.server_sync = transitionServerSync(next.server_sync, {
        type: 'job_snapshot',
        snapshot,
      });
      replaceCurrentCase(next, snapshot.status === 'failed');
    },
  });
  if (terminal.status === 'failed') {
    throw new Error(terminal.error?.message || '服务器图像处理失败。');
  }
  const next = applyServerJobResult(
    currentCase(),
    acceptedCase || acceptedCaseFromSync(currentCase().server_sync),
    terminal,
  );
  commitCase(next);
  elements.interactionPrompt.textContent = next.server_sync.status === 'candidate_ready'
    ? '自动配准候选已返回，请检查叠图后人工确认'
    : '自动配准未通过，请使用四组锚点完成配准';
}

async function ensureDifferenceHeatmap() {
  const artifactId = currentCase()?.visual_comparison?.difference?.heatmap?.artifact_id;
  if (!artifactId
    || artifactId === state.heatmapArtifactId
    || artifactId === state.heatmapLoadingArtifactId) return;
  state.heatmapLoadingArtifactId = artifactId;
  try {
    const blob = await getVisualQcArtifact(VISUAL_QC_API, VISUAL_QC_ACTOR_ID, artifactId);
    if (currentCase()?.visual_comparison?.difference?.heatmap?.artifact_id !== artifactId) return;
    clearHeatmap();
    state.heatmapUrl = URL.createObjectURL(blob);
    state.heatmapArtifactId = artifactId;
    elements.heatmapImage.src = state.heatmapUrl;
  } catch (error) {
    reportUserError(error);
  } finally {
    if (state.heatmapLoadingArtifactId === artifactId) {
      state.heatmapLoadingArtifactId = null;
    }
  }
}

function updateComparisonDraft(patch, persist = true) {
  const visualCase = currentCase();
  if (!visualCase) return;
  const next = structuredClone(visualCase);
  next.visual_comparison = {
    capture_setup_id: captureSetupId(),
    golden_sample: null,
    difference: null,
    ...(next.visual_comparison || {}),
    ...patch,
  };
  replaceCurrentCase(next, persist);
}

async function refreshCurrentGoldenSample({ quietMissing = false } = {}) {
  const visualCase = currentCase();
  if (!visualCase || state.comparisonBusy) return;
  state.comparisonBusy = true;
  render();
  try {
    const golden = await getActiveGoldenSample(
      VISUAL_QC_API,
      VISUAL_QC_ACTOR_ID,
      {
        boardKey: visualCase.board_key,
        sideId: visualCase.side_id,
        captureSetupId: captureSetupId(),
      },
    );
    if (golden.status === 'missing') {
      updateComparisonDraft({
        capture_setup_id: captureSetupId(),
        golden_sample: null,
        golden_lookup_status: 'missing',
      });
      if (!quietMissing) elements.interactionPrompt.textContent = '当前拍摄工位还没有 Golden Sample';
    } else {
      replaceCurrentCase(applyGoldenSample(currentCase(), golden), true);
    }
  } catch (error) {
    reportUserError(error);
  } finally {
    state.comparisonBusy = false;
    render();
  }
}

async function approveCurrentGoldenSample() {
  const visualCase = currentCase();
  if (!visualCase || state.comparisonBusy) return;
  state.comparisonBusy = true;
  render();
  try {
    const golden = await approveGoldenSample({
      apiBase: VISUAL_QC_API,
      actorId: VISUAL_QC_ACTOR_ID,
      actorRole: VISUAL_QC_ACTOR_ROLE,
      visualCase,
      captureSetupId: captureSetupId(),
      confirmedNormal: elements.normalConfirmation.checked,
    });
    replaceCurrentCase(applyGoldenSample(currentCase(), golden), true);
    elements.normalConfirmation.checked = false;
    elements.interactionPrompt.textContent = `Golden Sample V${golden.version} 已生效`;
  } catch (error) {
    reportUserError(error);
  } finally {
    state.comparisonBusy = false;
    render();
  }
}

async function runDifferenceAnalysis() {
  const visualCase = currentCase();
  if (!visualCase?.server_sync?.server_case_id || state.comparisonBusy) return;
  state.comparisonBusy = true;
  clearHeatmap();
  render();
  try {
    const queued = await createDifferenceJob({
      apiBase: VISUAL_QC_API,
      actorId: VISUAL_QC_ACTOR_ID,
      serverCaseId: visualCase.server_sync.server_case_id,
      captureSetupId: captureSetupId(),
    });
    updateComparisonDraft({
      capture_setup_id: captureSetupId(),
      difference: {
        job_id: queued.job_id,
        status: queued.status,
        source: 'model_candidate',
        candidates: [],
        heatmap: null,
      },
    });
    const terminal = await pollVisualQcJob({
      jobId: queued.job_id,
      getJob: (jobId) => getVisualQcJob(VISUAL_QC_API, VISUAL_QC_ACTOR_ID, jobId),
      onSnapshot: (snapshot) => {
        const current = currentCase();
        if (!current) return;
        updateComparisonDraft({
          difference: {
            ...(current.visual_comparison?.difference || {}),
            job_id: snapshot.job_id,
            status: snapshot.status,
            last_error: snapshot.error?.message || null,
          },
        });
      },
    });
    if (terminal.status === 'failed') {
      throw new Error(terminal.error?.message || '差异分析失败。');
    }
    replaceCurrentCase(applyDifferenceJobResult(currentCase(), terminal), true);
    await ensureDifferenceHeatmap();
    elements.interactionPrompt.textContent = '差异候选已生成，请逐项确认、驳回或暂缓';
  } catch (error) {
    reportUserError(error);
  } finally {
    state.comparisonBusy = false;
    render();
  }
}

async function submitCandidateReview(candidate, decision, defectCategory) {
  const difference = currentCase()?.visual_comparison?.difference;
  if (!difference?.job_id || state.comparisonBusy) return;
  state.comparisonBusy = true;
  render();
  try {
    const review = await reviewDifferenceCandidate({
      apiBase: VISUAL_QC_API,
      actorId: VISUAL_QC_ACTOR_ID,
      jobId: difference.job_id,
      candidateId: candidate.candidate_id,
      decision,
      defectCategory,
    });
    replaceCurrentCase(applyCandidateReview(currentCase(), review), true);
  } catch (error) {
    reportUserError(error);
  } finally {
    state.comparisonBusy = false;
    render();
  }
}

async function syncCurrentCaseWithServer() {
  if (state.serverBusy) return;
  const visualCase = currentCase();
  if (!visualCase || !state.photoBlob) return;
  state.serverBusy = true;
  render();
  try {
    let sync = visualCase.server_sync || createServerSyncState(visualCase);
    if (sync.status === 'failed' && sync.job_id) {
      const queued = await retryVisualQcJob(
        VISUAL_QC_API,
        VISUAL_QC_ACTOR_ID,
        sync.job_id,
      );
      const next = structuredClone(currentCase());
      next.server_sync = transitionServerSync(sync, {
        type: 'job_snapshot',
        snapshot: queued,
      });
      replaceCurrentCase(next, true);
      await pollCurrentServerJob(acceptedCaseFromSync(next.server_sync));
      return;
    }
    if (sync.server_case_id && sync.job_id) {
      await pollCurrentServerJob(acceptedCaseFromSync(sync));
      return;
    }

    let next = structuredClone(currentCase());
    next.server_sync = transitionServerSync(sync, { type: 'upload_started' });
    replaceCurrentCase(next, true);
    const accepted = await uploadVisualQcCase({
      apiBase: VISUAL_QC_API,
      actorId: VISUAL_QC_ACTOR_ID,
      visualCase: next,
      imageBlob: state.photoBlob,
      syncState: next.server_sync,
      onProgress: (progress) => {
        const active = currentCase();
        if (!active) return;
        const progressed = structuredClone(active);
        progressed.server_sync = transitionServerSync(progressed.server_sync, {
          type: 'upload_progress',
          progress,
        });
        replaceCurrentCase(progressed);
      },
    });
    next = structuredClone(currentCase());
    next.server_sync = transitionServerSync(next.server_sync, {
      type: 'upload_accepted',
      caseId: accepted.case_id,
      imageId: accepted.image.image_id,
      jobId: accepted.job.job_id,
      jobStatus: accepted.job.status,
    });
    if (accepted.capture_session) {
      next.capture_session = normalizeServerCaptureSession(
        accepted.capture_session,
      );
    }
    replaceCurrentCase(next, true);
    await pollCurrentServerJob(accepted);
  } catch (error) {
    const active = currentCase();
    if (active && active.server_sync?.status !== 'failed') {
      const next = structuredClone(active);
      next.server_sync = transitionServerSync(
        next.server_sync || createServerSyncState(next),
        {
          type: next.server_sync?.server_case_id ? 'sync_interrupted' : 'upload_failed',
          message: error.message,
        },
      );
      replaceCurrentCase(next, true);
    }
    reportUserError(error);
  } finally {
    state.serverBusy = false;
    render();
  }
}

async function loadPhotoBlob(blob, fileName, isProxy = false) {
  if (!blob.type.startsWith('image/')) throw new Error('请选择 JPEG、PNG 或 WebP 图片。');
  const image = await imageFromBlob(blob);
  const imageHash = await sha256(blob);

  if (state.awaitingImportedImage && currentCase()) {
    const expected = currentCase().image;
    if (imageHash !== expected.sha256) {
      throw new Error('所选原图与案例 SHA-256 不一致。');
    }
    if (image.width !== expected.width || image.height !== expected.height) {
      throw new Error('所选原图尺寸与案例记录不一致。');
    }
    state.photoImage = image;
    state.photoBlob = blob;
    state.isProxy = expected.evidence_role === 'proxy_sample';
    state.awaitingImportedImage = false;
    state.photoViewport = createViewport();
    scheduleSave();
    resizeCanvases();
    render();
    elements.interactionPrompt.textContent = '原图哈希核验通过，案例已恢复';
    return;
  }

  const quality = analyzeImageQuality(imagePixels(image));
  clearHeatmap();
  const imageMetadata = caseImageMetadata(blob, image, fileName, isProxy);
  imageMetadata.sha256 = imageHash;
  const visualCase = createVisualQcCase({
    caseId: crypto.randomUUID(),
    boardKey: state.boardKey,
    boardId: state.dataset.board_id,
    sideId: state.sideId,
    captureStage: elements.captureStage.value,
    captureSession: captureSessionForNewCase(isProxy),
    image: imageMetadata,
    quality: {
      status: quality.status,
      score: quality.score,
      metrics: quality.metrics,
      guidance: quality.guidance,
    },
  });
  visualCase.schema_version = 'VISUAL-QC-CASE-V2';
  visualCase.server_sync = createServerSyncState(visualCase);
  if (quality.status === 'retake') {
    visualCase.qc_result = { status: 'image_invalid', reviewed_at: null };
  }
  state.photoImage = image;
  state.photoBlob = blob;
  state.isProxy = isProxy;
  state.awaitingImportedImage = false;
  state.photoViewport = createViewport();
  state.history = createHistory(visualCase);
  syncRegistrationState();

  if (isProxy && state.dataset.registration?.anchors?.length === 4) {
    const anchors = state.dataset.registration.anchors;
    const registered = applyRegistration(
      visualCase,
      anchors.map((anchor) => anchor.board),
      anchors.map((anchor) => anchor.image),
      [],
    );
    state.history = createHistory(registered);
    syncRegistrationState();
  }
  scheduleSave();
  resizeCanvases();
  render();
}

async function refreshCurrentCaptureSession() {
  const visualCase = currentCase();
  const sessionId = visualCase?.capture_session?.session_id;
  if (!sessionId || !visualCase.server_sync?.server_case_id) return;
  state.serverBusy = true;
  render();
  try {
    const serverSession = await getVisualQcCaptureSession(
      VISUAL_QC_API,
      VISUAL_QC_ACTOR_ID,
      sessionId,
    );
    const next = structuredClone(currentCase());
    next.capture_session = normalizeServerCaptureSession(
      serverSession,
      next.capture_session.checklist,
    );
    replaceCurrentCase(next, true);
  } catch (error) {
    reportUserError(error);
  } finally {
    state.serverBusy = false;
    render();
  }
}

async function startOtherSideCapture() {
  const visualCase = currentCase();
  const session = visualCase?.capture_session;
  if (!session || visualCase.image?.evidence_role !== 'physical_capture') return;
  const captured = new Set(session.captured_side_ids || [visualCase.side_id]);
  const nextSideId = (session.expected_side_ids || expectedSideIds())
    .find((sideId) => !captured.has(sideId));
  if (!nextSideId) return;
  await flushPendingSave();
  state.captureSessionDraft = {
    sessionId: session.session_id,
    setupId: session.setup_id,
    boardKey: visualCase.board_key,
    captureStage: visualCase.capture_stage,
    capturedSideIds: session.captured_side_ids || [visualCase.side_id],
  };
  await loadSide(nextSideId, true);
  elements.interactionPrompt.textContent = '采集批次已保留，请导入另一面的实拍图';
}

function recomputeRegistration() {
  if (!currentCase() || state.boardAnchors.length !== 4 || state.imageAnchors.length !== 4) return;
  try {
    const registered = applyRegistration(
      currentCase(),
      state.boardAnchors,
      state.imageAnchors,
      state.checkPoints,
    );
    commitCase(registered);
  } catch (error) {
    elements.interactionPrompt.textContent = error.message;
  }
}

function recordRegistrationPoint(role, point) {
  if (!currentCase()) return;
  if (role === 'board') {
    state.pendingBoardPoint = point;
    elements.interactionPrompt.textContent = state.registrationTool === 'anchor'
      ? '在实拍图上选择对应锚点'
      : '在实拍图上选择对应检查点';
    render();
    return;
  }
  if (!state.pendingBoardPoint) {
    elements.interactionPrompt.textContent = '请先在工程点位图上选择对应位置';
    return;
  }
  if (state.registrationTool === 'anchor') {
    if (state.boardAnchors.length >= 4) return;
    state.boardAnchors.push(state.pendingBoardPoint);
    state.imageAnchors.push(point);
  } else {
    state.checkPoints.push({ board: state.pendingBoardPoint, image: point });
  }
  state.pendingBoardPoint = null;
  if (state.boardAnchors.length === 4) {
    recomputeRegistration();
  } else {
    commitCase(updateDraftRegistration(
      currentCase(),
      state.boardAnchors,
      state.imageAnchors,
    ));
  }
  render();
}

function clearRegistration() {
  if (!currentCase()) return;
  const next = structuredClone(currentCase());
  next.registration = {
    method: 'reviewed_manual_homography',
    status: 'draft',
    matrix: null,
    solve_anchors: [],
    check_points: [],
    error: { count: 0, rms: null, maximum: null },
  };
  next.annotations = [];
  next.qc_result = {
    status: next.quality.status === 'retake' ? 'image_invalid' : 'needs_review',
    reviewed_at: null,
  };
  commitCase(next);
  setMode('registration');
}

function removeLastPair() {
  if (state.checkPoints.length) {
    state.checkPoints.pop();
  } else if (state.boardAnchors.length) {
    state.boardAnchors.pop();
    state.imageAnchors.pop();
  }
  state.pendingBoardPoint = null;
  if (state.boardAnchors.length === 4) {
    recomputeRegistration();
  } else {
    commitCase(updateDraftRegistration(
      currentCase(),
      state.boardAnchors,
      state.imageAnchors,
    ));
  }
  render();
}

async function confirmRegistration() {
  try {
    const visualCase = currentCase();
    if (!visualCase) return;
    const isAutomatic = visualCase.registration?.method === 'automatic_feature_homography';
    const next = isAutomatic
      ? structuredClone(visualCase)
      : reviewRegistration(visualCase);
    if (visualCase.server_sync?.server_case_id) {
      state.serverBusy = true;
      render();
      const reviewed = await reviewVisualQcRegistration({
        apiBase: VISUAL_QC_API,
        actorId: VISUAL_QC_ACTOR_ID,
        serverCaseId: visualCase.server_sync.server_case_id,
        registration: visualCase.registration,
      });
      next.registration.status = 'reviewed';
      next.registration.reviewed_at = reviewed.created_at;
      next.registration.server_review_id = reviewed.review_id;
      next.server_sync = {
        ...next.server_sync,
        status: 'reviewed',
        updated_at: new Date().toISOString(),
      };
    }
    commitCase(next);
    elements.interactionPrompt.textContent = '配准已人工确认，可以进入缺陷标注';
    if (next.server_sync?.server_case_id) {
      await refreshCurrentGoldenSample({ quietMissing: true });
    }
  } catch (error) {
    reportUserError(error);
  } finally {
    state.serverBusy = false;
    render();
  }
}

function setMode(mode) {
  if (mode === 'annotation' && currentCase()?.registration.status !== 'reviewed') return;
  state.mode = mode;
  elements.registrationModeButton.setAttribute('aria-selected', String(mode === 'registration'));
  elements.annotationModeButton.setAttribute('aria-selected', String(mode === 'annotation'));
  elements.registrationTools.hidden = mode !== 'registration';
  elements.annotationTools.hidden = mode !== 'annotation';
  elements.annotationSection.hidden = mode !== 'annotation';
  state.polygonPoints = [];
  state.rectanglePreview = null;
  render();
}

function selectedCategory() {
  return elements.defectCategory.value || DEFECT_CATEGORIES[0];
}

function componentSuggestion(imageGeometry) {
  const matrix = currentCase()?.registration.matrix;
  if (!matrix) return null;
  const imageCenter = annotationCentroid(imageGeometry);
  const boardPoint = projectPoint(invertHomography(matrix), imageCenter);
  const entity = suggestEntityAtPoint(state.entities, state.sideId, boardPoint);
  return entity ? { component_id: entity.component_id, designator: entity.designator } : null;
}

function createAnnotation(imageGeometry) {
  try {
    const next = addAnnotation(currentCase(), {
      annotationId: crypto.randomUUID(),
      category: selectedCategory(),
      imageGeometry,
      component: componentSuggestion(imageGeometry),
    });
    state.selectedAnnotationId = next.annotations.at(-1).annotation_id;
    commitCase(next);
  } catch (error) {
    elements.interactionPrompt.textContent = error.message;
  }
}

function finishPolygon() {
  if (state.polygonPoints.length < 3) return;
  createAnnotation({ type: 'polygon', points: state.polygonPoints });
  state.polygonPoints = [];
  render();
}

function changeAnnotation(annotationId, changes) {
  try {
    commitCase(updateAnnotation(currentCase(), annotationId, changes));
  } catch (error) {
    elements.interactionPrompt.textContent = error.message;
  }
}

function deleteAnnotation(annotationId) {
  commitCase(removeAnnotation(currentCase(), annotationId));
  if (state.selectedAnnotationId === annotationId) state.selectedAnnotationId = null;
}

async function finalizeVisualQc() {
  try {
    const finalized = finalizeQc(currentCase());
    commitCase(finalized);
    const serverCaseId = finalized.server_sync?.server_case_id;
    if (!serverCaseId) {
      elements.interactionPrompt.textContent = '人工 QC 已保存在本机草稿';
      return;
    }
    state.serverBusy = true;
    render();
    const review = await reviewVisualQcCase({
      apiBase: VISUAL_QC_API,
      actorId: VISUAL_QC_ACTOR_ID,
      serverCaseId,
      visualCase: finalized,
    });
    commitCase(applyFinalQcReview(currentCase(), review));
    elements.interactionPrompt.textContent = `人工 QC 已同步为服务器审核版本 ${review.version}`;
    if (VISUAL_QC_ACTOR_ROLE === 'reviewer') void refreshTrainingDataset({ quiet: true });
  } catch (error) {
    elements.interactionPrompt.textContent = error.message;
  } finally {
    state.serverBusy = false;
    render();
  }
}

function canvasPoint(canvas, event) {
  const bounds = canvas.getBoundingClientRect();
  return {
    x: (event.clientX - bounds.left) * (canvas.width / bounds.width),
    y: (event.clientY - bounds.top) * (canvas.height / bounds.height),
  };
}

function pointInImage(canvas, image, viewport, event) {
  const point = canvasPoint(canvas, event);
  const frame = imageFrame(canvas, {
    width: image.naturalWidth,
    height: image.naturalHeight,
  }, viewport);
  const normalized = screenToNormalized(point, frame);
  return normalized.x >= 0 && normalized.x <= 1 && normalized.y >= 0 && normalized.y <= 1
    ? normalized
    : null;
}

function onPointerDown(role, event) {
  const canvas = role === 'board' ? elements.boardCanvas : elements.photoCanvas;
  const image = role === 'board' ? state.pointMapImage : state.photoImage;
  if (!image) return;
  state.activeCanvas = role;
  const point = canvasPoint(canvas, event);
  const isPan = state.mode === 'registration'
    ? state.registrationTool === 'pan'
    : state.annotationTool === 'pan';
  state.drag = {
    role,
    pointerId: event.pointerId,
    start: point,
    last: point,
    moved: false,
    action: isPan ? 'pan' : (
      role === 'photo' && state.mode === 'annotation' && state.annotationTool === 'rectangle'
        ? 'rectangle'
        : 'click'
    ),
  };
  canvas.setPointerCapture(event.pointerId);
  if (state.drag.action === 'rectangle') {
    const normalized = pointInImage(canvas, image, state.photoViewport, event);
    state.rectanglePreview = normalized ? [normalized, normalized] : null;
  }
}

function onPointerMove(role, event) {
  if (!state.drag || state.drag.pointerId !== event.pointerId || state.drag.role !== role) return;
  const canvas = role === 'board' ? elements.boardCanvas : elements.photoCanvas;
  const point = canvasPoint(canvas, event);
  const dx = point.x - state.drag.last.x;
  const dy = point.y - state.drag.last.y;
  if (Math.hypot(point.x - state.drag.start.x, point.y - state.drag.start.y) > 4) {
    state.drag.moved = true;
  }
  if (state.drag.action === 'pan') {
    if (role === 'board') state.boardViewport = panViewport(state.boardViewport, dx, dy);
    else state.photoViewport = panViewport(state.photoViewport, dx, dy);
  } else if (state.drag.action === 'rectangle' && state.rectanglePreview) {
    const normalized = pointInImage(canvas, state.photoImage, state.photoViewport, event);
    if (normalized) state.rectanglePreview[1] = normalized;
  }
  state.drag.last = point;
  renderCanvases();
}

function onPointerUp(role, event) {
  if (!state.drag || state.drag.pointerId !== event.pointerId || state.drag.role !== role) return;
  const canvas = role === 'board' ? elements.boardCanvas : elements.photoCanvas;
  const image = role === 'board' ? state.pointMapImage : state.photoImage;
  const viewport = role === 'board' ? state.boardViewport : state.photoViewport;
  const normalized = pointInImage(canvas, image, viewport, event);
  const drag = state.drag;
  state.drag = null;
  if (drag.action === 'rectangle') {
    if (state.rectanglePreview) {
      const [first, second] = state.rectanglePreview;
      if (Math.abs(first.x - second.x) > 0.003 && Math.abs(first.y - second.y) > 0.003) {
        createAnnotation({ type: 'rectangle', points: [first, second] });
      }
    }
    state.rectanglePreview = null;
  } else if (drag.action === 'click' && !drag.moved && normalized) {
    if (state.mode === 'registration') {
      recordRegistrationPoint(role, normalized);
    } else if (role === 'photo' && state.annotationTool === 'polygon') {
      state.polygonPoints.push(normalized);
    }
  }
  render();
}

function onWheel(role, event) {
  const image = role === 'board' ? state.pointMapImage : state.photoImage;
  if (!image) return;
  event.preventDefault();
  state.activeCanvas = role;
  const canvas = role === 'board' ? elements.boardCanvas : elements.photoCanvas;
  const point = canvasPoint(canvas, event);
  const viewport = role === 'board' ? state.boardViewport : state.photoViewport;
  const next = zoomViewportAt(
    viewport,
    event.deltaY < 0 ? 1.15 : 1 / 1.15,
    point,
    canvas,
    { width: image.naturalWidth, height: image.naturalHeight },
  );
  if (role === 'board') state.boardViewport = next;
  else state.photoViewport = next;
  renderCanvases();
}

function resizeCanvas(canvas) {
  const bounds = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(bounds.width));
  const height = Math.max(1, Math.round(bounds.height));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
}

function resizeCanvases() {
  resizeCanvas(elements.boardCanvas);
  resizeCanvas(elements.photoCanvas);
  renderCanvases();
}

function drawMarker(context, point, frame, label, color, pending = false) {
  const screen = normalizedToScreen(point, frame);
  context.save();
  context.beginPath();
  context.arc(screen.x, screen.y, pending ? 8 : 6, 0, Math.PI * 2);
  context.fillStyle = pending ? '#315f78' : color;
  context.fill();
  context.lineWidth = 2;
  context.strokeStyle = '#ffffff';
  context.stroke();
  context.fillStyle = '#ffffff';
  context.font = '700 9px Segoe UI';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(label, screen.x, screen.y);
  context.restore();
}

function geometryPoints(geometry) {
  if (geometry.type === 'rectangle') {
    const [first, second] = geometry.points;
    return [
      first,
      { x: second.x, y: first.y },
      second,
      { x: first.x, y: second.y },
    ];
  }
  return geometry.points;
}

function drawGeometry(context, geometry, frame, color, selected = false, label = '') {
  const points = geometryPoints(geometry).map((point) => normalizedToScreen(point, frame));
  context.save();
  context.beginPath();
  context.moveTo(points[0].x, points[0].y);
  points.slice(1).forEach((point) => context.lineTo(point.x, point.y));
  context.closePath();
  context.fillStyle = `${color}24`;
  context.fill();
  context.strokeStyle = color;
  context.lineWidth = selected ? 3 : 2;
  context.stroke();
  if (label) {
    const x = Math.min(...points.map((point) => point.x));
    const y = Math.min(...points.map((point) => point.y));
    context.font = '700 11px Segoe UI';
    const width = context.measureText(label).width + 10;
    context.fillStyle = color;
    context.fillRect(x, Math.max(0, y - 21), width, 19);
    context.fillStyle = '#ffffff';
    context.fillText(label, x + 5, Math.max(13, y - 7));
  }
  context.restore();
}

function clearCanvas(canvas) {
  const context = canvas.getContext('2d');
  context.setTransform(1, 0, 0, 1, 0, 0);
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = '#e8ece8';
  context.fillRect(0, 0, canvas.width, canvas.height);
  return context;
}

function renderBoardCanvas() {
  const context = clearCanvas(elements.boardCanvas);
  if (!state.pointMapImage) return;
  const frame = imageFrame(elements.boardCanvas, {
    width: state.pointMapImage.naturalWidth,
    height: state.pointMapImage.naturalHeight,
  }, state.boardViewport);
  drawFittedImage(context, state.pointMapImage, frame);
  state.boardAnchors.forEach((point, index) => drawMarker(context, point, frame, index + 1, '#b87916'));
  state.checkPoints.forEach((pair, index) => drawMarker(context, pair.board, frame, `C${index + 1}`, '#2e7b62'));
  if (state.pendingBoardPoint) drawMarker(context, state.pendingBoardPoint, frame, '•', '#315f78', true);
  if (state.mode === 'annotation') {
    for (const annotation of currentCase()?.annotations || []) {
      const color = annotation.review_status === 'confirmed'
        ? '#d6533f'
        : annotation.review_status === 'not_defect' ? '#2e7b62' : '#b87916';
      drawGeometry(
        context,
        annotation.board_geometry,
        frame,
        color,
        annotation.annotation_id === state.selectedAnnotationId,
        annotation.component?.designator || '',
      );
    }
  }
}

function renderPhotoCanvas() {
  const context = clearCanvas(elements.photoCanvas);
  if (!state.photoImage) return;
  const frame = imageFrame(elements.photoCanvas, {
    width: state.photoImage.naturalWidth,
    height: state.photoImage.naturalHeight,
  }, state.photoViewport);
  drawFittedImage(context, state.photoImage, frame);
  const registration = currentCase()?.registration;
  if (registration?.matrix && Number(elements.overlayOpacity.value) > 0) {
    drawWarpedImage(
      context,
      state.pointMapImage,
      registration.matrix,
      frame,
      Number(elements.overlayOpacity.value) / 100,
    );
  }
  state.imageAnchors.forEach((point, index) => drawMarker(context, point, frame, index + 1, '#b87916'));
  state.checkPoints.forEach((pair, index) => drawMarker(context, pair.image, frame, `C${index + 1}`, '#2e7b62'));
  for (const annotation of currentCase()?.annotations || []) {
    const color = annotation.review_status === 'confirmed'
      ? '#d6533f'
      : annotation.review_status === 'not_defect' ? '#2e7b62' : '#b87916';
    drawGeometry(
      context,
      annotation.image_geometry,
      frame,
      color,
      annotation.annotation_id === state.selectedAnnotationId,
      annotation.component?.designator || CATEGORY_LABELS[annotation.category],
    );
  }
  if (state.rectanglePreview) {
    drawGeometry(context, { type: 'rectangle', points: state.rectanglePreview }, frame, '#315f78', true);
  }
  if (state.polygonPoints.length) {
    const screenPoints = state.polygonPoints.map((point) => normalizedToScreen(point, frame));
    context.save();
    context.beginPath();
    context.moveTo(screenPoints[0].x, screenPoints[0].y);
    screenPoints.slice(1).forEach((point) => context.lineTo(point.x, point.y));
    context.strokeStyle = '#315f78';
    context.lineWidth = 2;
    context.stroke();
    screenPoints.forEach((point, index) => {
      context.beginPath();
      context.arc(point.x, point.y, 4, 0, Math.PI * 2);
      context.fillStyle = index === 0 ? '#d6533f' : '#315f78';
      context.fill();
    });
    context.restore();
  }
  if (state.isProxy) {
    context.save();
    context.fillStyle = 'rgba(16, 37, 30, 0.86)';
    context.fillRect(frame.x + 8, frame.y + 8, 180, 24);
    context.fillStyle = '#ffffff';
    context.font = '700 10px Segoe UI';
    context.fillText('代理样本 · 非实物 QC 证据', frame.x + 16, frame.y + 24);
    context.restore();
  }
}

function renderCanvases() {
  renderBoardCanvas();
  renderPhotoCanvas();
}

function renderQuality() {
  const visualCase = currentCase();
  if (!visualCase) {
    elements.qualityTitle.textContent = '等待图片';
    elements.qualityBadge.textContent = '未检测';
    elements.qualityBadge.className = 'badge neutral';
    elements.qualityScore.textContent = '—';
    elements.qualityResolution.textContent = '—';
    elements.qualitySharpness.textContent = '—';
    elements.qualityGuidance.textContent = '导入后立即本机检查；服务器处理会保留独立质量证据。';
    return;
  }
  const quality = visualCase.quality;
  elements.qualityTitle.textContent = quality.status === 'retake' ? '建议重新拍摄' : '图片可进入配准';
  elements.qualityBadge.textContent = quality.status;
  elements.qualityBadge.className = `badge ${quality.status}`;
  elements.qualityScore.textContent = Math.round(quality.score);
  elements.qualityResolution.textContent = `${visualCase.image.width} × ${visualCase.image.height}`;
  elements.qualitySharpness.textContent = Number(quality.metrics.sharpness || 0).toFixed(1);
  elements.qualityGuidance.textContent = (quality.guidance || [])
    .map((item) => QUALITY_GUIDANCE_COPY[item.code] || item.message)
    .join(' ') || '图像质量检查完成。';
}

function renderCaptureSession() {
  const visualCase = currentCase();
  const session = visualCase?.capture_session;
  const isPhysical = visualCase?.image?.evidence_role === 'physical_capture';
  const synced = Boolean(visualCase?.server_sync?.server_case_id);
  const checklistInputs = elements.captureChecklist.querySelectorAll('[data-capture-check]');
  if (!visualCase || !session) {
    const draft = state.captureSessionDraft;
    const sideLabel = state.manifest?.sides
      ?.find((side) => side.side_id === state.sideId)?.label;
    elements.captureSessionTitle.textContent = draft
      ? `等待${sideLabel || '另一面'}照片`
      : '等待实拍图';
    elements.captureSessionBadge.textContent = draft ? '批次继续' : '未开始';
    elements.captureSessionBadge.className = `badge ${draft ? 'draft' : 'neutral'}`;
    elements.captureSessionSummary.textContent = draft
      ? `${draft.setupId} · 批次 ${draft.sessionId.slice(-8)}`
      : '导入后建立本块主板的正反面采集批次。';
    checklistInputs.forEach((input) => {
      input.checked = false;
      input.disabled = true;
    });
    elements.refreshCaptureSessionButton.disabled = true;
    elements.captureOtherSideButton.disabled = true;
    return;
  }

  if (!isPhysical) {
    elements.captureSessionTitle.textContent = '代理验证样本';
    elements.captureSessionBadge.textContent = '非实拍';
    elements.captureSessionBadge.className = 'badge neutral';
    elements.captureSessionSummary.textContent = '仅验证软件流程，不计入实物 QC 证据。';
  } else {
    const pairPresentations = {
      single_side: ['单面板采集', '单面'],
      pair_in_progress: ['等待另一面', '1 / 2'],
      pair_complete: ['正反面已齐', '完整'],
    };
    const [title, badge] = pairPresentations[session.pair_status]
      || pairPresentations.pair_in_progress;
    elements.captureSessionTitle.textContent = title;
    elements.captureSessionBadge.textContent = badge;
    elements.captureSessionBadge.className = `badge ${
      session.pair_status === 'pair_complete' ? 'reviewed' : 'draft'
    }`;
    const captured = session.captured_side_ids?.length || 1;
    const expected = session.expected_side_ids?.length || 1;
    elements.captureSessionSummary.textContent = `${session.setup_id} · 已采集 ${captured} / ${expected} 面 · 批次 ${session.session_id.slice(-8)}`;
  }
  checklistInputs.forEach((input) => {
    input.checked = session.checklist?.items?.[input.dataset.captureCheck] === true;
    input.disabled = !isPhysical || synced;
  });
  elements.refreshCaptureSessionButton.disabled = !synced || state.serverBusy;
  elements.captureOtherSideButton.disabled = !isPhysical
    || session.checklist?.status !== 'confirmed'
    || session.pair_status !== 'pair_in_progress'
    || state.serverBusy;
}

function renderServerSync() {
  const visualCase = currentCase();
  const sync = visualCase?.server_sync;
  const status = sync?.status || 'local_draft';
  const presentations = {
    local_draft: ['本机草稿', '本机', '图片尚未上传，原图与编辑状态保存在当前浏览器。'],
    uploading: ['正在上传', '上传中', `已上传 ${Math.round((sync?.progress || 0) * 100)}%`],
    queued: ['等待服务器处理', '排队', '案例已由服务器接受，等待 CPU 任务。'],
    running: ['正在自动配准', '处理中', '服务器正在检查质量、轮廓和特征配准。'],
    succeeded: ['处理结果已返回', '待整理', '正在载入服务器结果。'],
    candidate_ready: ['自动配准待确认', '候选', '检查半透明叠图；确认前不会成为审核配准。'],
    manual_required: ['需要人工四点配准', '人工回退', '自动配准未通过，请选择四组锚点和独立检查点。'],
    reviewed: ['配准已同步审核', '已审核', '服务器已保存本次人工审核记录。'],
    failed: ['服务器处理失败', '失败', sync?.last_error || '可保留案例并重试处理。'],
    upload_failed: ['上传未完成', '可重试', sync?.last_error || '本机草稿仍然保留。'],
    sync_interrupted: ['连接暂时中断', '待续传', sync?.last_error || '服务器任务仍可继续查询。'],
  };
  const [title, badge, detail] = presentations[status] || presentations.local_draft;
  elements.serverSyncTitle.textContent = visualCase ? title : '等待图片';
  elements.serverSyncBadge.textContent = visualCase ? badge : '本机';
  elements.serverSyncBadge.className = `badge ${status.replaceAll('_', '-')}`;
  elements.serverSyncDetail.textContent = visualCase
    ? detail
    : '图片先保存在本机草稿，服务器接受后再成为共享案例。';
  const captureReady = visualCase?.image?.evidence_role !== 'physical_capture'
    || visualCase?.capture_session?.checklist?.status === 'confirmed';
  if (visualCase && !captureReady && status === 'local_draft') {
    elements.serverSyncDetail.textContent = '完成三项拍摄确认后，才可上传实物图片。';
  }
  elements.serverSyncProgress.value = Math.round((sync?.progress || 0) * 100);
  const actionLabels = {
    upload_failed: '重新上传',
    sync_interrupted: '继续查询',
    failed: '重试处理',
    queued: '继续查询',
    running: '继续查询',
    succeeded: '正在载入结果',
    candidate_ready: '等待人工确认',
    manual_required: '请完成四点配准',
    reviewed: '服务器记录已审核',
  };
  elements.serverSyncButton.textContent = actionLabels[status] || '上传并自动配准';
  elements.serverSyncButton.disabled = !visualCase
    || !state.photoBlob
    || !captureReady
    || state.serverBusy
    || ['candidate_ready', 'manual_required', 'reviewed', 'succeeded'].includes(status);
  elements.captureStage.disabled = Boolean(visualCase);
}

function renderRegistration() {
  const registration = currentCase()?.registration;
  const reviewed = registration?.status === 'reviewed';
  const automatic = registration?.method === 'automatic_feature_homography';
  elements.registrationTitle.textContent = reviewed ? '配准已人工确认' : (
    automatic && registration?.matrix ? '自动配准等待确认' : (
      registration?.matrix ? '等待配准确认' : '尚未配准'
    )
  );
  elements.registrationBadge.textContent = reviewed ? '已审核' : '草稿';
  elements.registrationBadge.className = `badge ${reviewed ? 'reviewed' : 'draft'}`;
  elements.anchorCount.textContent = automatic ? '自动' : `${state.boardAnchors.length} / 4`;
  elements.checkCountLabel.textContent = automatic ? 'RANSAC 内点' : '独立检查点';
  elements.checkCount.textContent = automatic
    ? String(registration?.error?.count || 0)
    : String(state.checkPoints.length);
  elements.registrationError.textContent = registration?.error?.rms == null
    ? '—'
    : registration.error.rms.toFixed(5);
  elements.removeLastPairButton.disabled = !state.boardAnchors.length && !state.checkPoints.length;
  elements.clearRegistrationButton.disabled = reviewed
    || (!state.boardAnchors.length && !registration?.matrix);
  elements.reviewRegistrationButton.textContent = automatic ? '确认自动配准' : '确认配准';
  elements.reviewRegistrationButton.disabled = !registration?.matrix
    || (!automatic && !state.checkPoints.length)
    || reviewed
    || state.serverBusy;
  elements.annotationModeButton.disabled = !reviewed;
  elements.overlayOpacity.disabled = !registration?.matrix;
  elements.registrationTools.querySelector('[data-registration-tool="check"]').disabled = state.boardAnchors.length !== 4;
}

function renderComparison() {
  const visualCase = currentCase();
  const comparison = visualCase?.visual_comparison || {};
  const golden = comparison.golden_sample;
  const difference = comparison.difference;
  const isGoldenCapture = visualCase?.capture_stage === 'golden_reference';
  const serverReviewed = visualCase?.server_sync?.status === 'reviewed'
    && visualCase?.registration?.status === 'reviewed';
  const physicalCapture = visualCase?.image?.evidence_role === 'physical_capture';
  const acceptableQuality = visualCase?.quality?.status !== 'retake';
  if (comparison.capture_setup_id
    && document.activeElement !== elements.captureSetupId) {
    elements.captureSetupId.value = comparison.capture_setup_id;
  }

  elements.normalConfirmationField.hidden = !isGoldenCapture;
  elements.approveGoldenButton.hidden = !isGoldenCapture;
  elements.runDifferenceButton.hidden = isGoldenCapture;
  elements.refreshGoldenButton.disabled = !visualCase || state.comparisonBusy;
  elements.captureSetupId.disabled = !visualCase
    || state.comparisonBusy
    || Boolean(visualCase.server_sync?.server_case_id);

  if (!visualCase) {
    elements.comparisonTitle.textContent = '等待已审核案例';
    elements.comparisonBadge.textContent = '未就绪';
    elements.comparisonBadge.className = 'badge neutral';
    elements.goldenSummary.textContent = '选择固定拍摄工位后查询正常板基准。';
  } else if (isGoldenCapture) {
    const eligible = serverReviewed && physicalCapture && acceptableQuality;
    elements.comparisonTitle.textContent = golden
      ? `Golden Sample V${golden.version}`
      : eligible ? '可以提交正常板基准' : '尚不符合基准条件';
    elements.comparisonBadge.textContent = golden ? '已生效' : eligible ? '待批准' : '未就绪';
    elements.comparisonBadge.className = `badge ${golden ? 'reviewed' : eligible ? 'draft' : 'neutral'}`;
    if (golden) {
      elements.goldenSummary.textContent = `${golden.capture_setup_id} · ${golden.golden_sample_id}`;
    } else if (!physicalCapture) {
      elements.goldenSummary.textContent = '代理或合成图片不能成为 Golden Sample。';
    } else if (!acceptableQuality) {
      elements.goldenSummary.textContent = '图像质量为 retake，需重新拍摄。';
    } else if (!serverReviewed) {
      elements.goldenSummary.textContent = '需先完成服务器配准审核。';
    } else if (VISUAL_QC_ACTOR_ROLE !== 'reviewer') {
      elements.goldenSummary.textContent = '当前账号没有 Golden Sample 审核权限。';
    } else {
      elements.goldenSummary.textContent = `${captureSetupId()} · 等待正常板确认`;
    }
    elements.approveGoldenButton.disabled = !eligible
      || VISUAL_QC_ACTOR_ROLE !== 'reviewer'
      || !elements.normalConfirmation.checked
      || state.comparisonBusy;
  } else {
    const candidateCount = difference?.candidates?.length || 0;
    const pendingCount = (difference?.candidates || [])
      .filter((candidate) => !['confirmed', 'rejected'].includes(candidate.review_status))
      .length;
    if (difference?.status === 'candidate_review_required') {
      elements.comparisonTitle.textContent = `${candidateCount} 个差异候选`;
      elements.comparisonBadge.textContent = pendingCount ? `${pendingCount} 待审` : '已审核';
      elements.comparisonBadge.className = `badge ${pendingCount ? 'draft' : 'reviewed'}`;
    } else if (['queued', 'running'].includes(difference?.status)) {
      elements.comparisonTitle.textContent = '正在生成差异候选';
      elements.comparisonBadge.textContent = difference.status === 'queued' ? '排队' : '处理中';
      elements.comparisonBadge.className = 'badge running';
    } else if (golden) {
      elements.comparisonTitle.textContent = `使用 Golden V${golden.version}`;
      elements.comparisonBadge.textContent = '有基准';
      elements.comparisonBadge.className = 'badge reviewed';
    } else {
      elements.comparisonTitle.textContent = '当前工位没有 Golden';
      elements.comparisonBadge.textContent = '无基准';
      elements.comparisonBadge.className = 'badge neutral';
    }
    elements.goldenSummary.textContent = golden
      ? `${golden.capture_setup_id} · V${golden.version} · ${golden.golden_sample_id}`
      : `${captureSetupId()} · 尚未绑定正常板基准`;
    elements.runDifferenceButton.disabled = !serverReviewed || !golden || state.comparisonBusy;
  }

  const artifactId = difference?.heatmap?.artifact_id;
  elements.heatmapFigure.hidden = !artifactId;
  elements.heatmapMeta.textContent = artifactId
    ? `${difference.candidates?.length || 0} 个候选 · 需人工审核`
    : '等待结果';
  elements.heatmapOverlay.replaceChildren();
  for (const [index, candidate] of (difference?.candidates || []).entries()) {
    const [left, top, right, bottom] = candidate.board_bbox;
    const marker = document.createElement('div');
    marker.className = `heatmap-candidate ${candidate.review_status.replaceAll('_', '-')}`;
    marker.style.left = `${left * 100}%`;
    marker.style.top = `${top * 100}%`;
    marker.style.width = `${(right - left) * 100}%`;
    marker.style.height = `${(bottom - top) * 100}%`;
    const label = document.createElement('span');
    label.textContent = String(index + 1);
    marker.append(label);
    elements.heatmapOverlay.append(marker);
  }
  if (artifactId && state.heatmapArtifactId !== artifactId) {
    void ensureDifferenceHeatmap();
  }

  elements.candidateList.replaceChildren();
  for (const [index, candidate] of (difference?.candidates || []).entries()) {
    const item = document.createElement('article');
    item.className = 'candidate-item';
    const header = document.createElement('header');
    const identity = document.createElement('strong');
    identity.textContent = `候选 ${index + 1}`;
    const evidence = document.createElement('small');
    evidence.textContent = `面积 ${(candidate.area_fraction * 100).toFixed(2)}% · 差异 ${Math.round(candidate.mean_difference || 0)}`;
    header.append(identity, evidence);

    const category = document.createElement('select');
    category.setAttribute('aria-label', `候选 ${index + 1} 缺陷类别`);
    for (const [value, labelText] of Object.entries(SERVER_CATEGORY_LABELS)) {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = labelText;
      category.append(option);
    }
    category.value = candidate.human_review?.defect_category
      || 'unclassified_visible_anomaly';

    const actions = document.createElement('div');
    actions.className = 'button-row';
    for (const [decision, labelText] of [
      ['confirmed', '确认异常'],
      ['rejected', '驳回'],
      ['needs_review', '暂缓'],
    ]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = labelText;
      button.dataset.decision = decision;
      button.setAttribute('aria-pressed', String(candidate.review_status === decision));
      button.disabled = state.comparisonBusy;
      button.addEventListener('click', () => submitCandidateReview(
        candidate,
        decision,
        category.value,
      ));
      actions.append(button);
    }
    item.append(header, category, actions);
    elements.candidateList.append(item);
  }
}

function renderAnnotations() {
  const annotations = currentCase()?.annotations || [];
  elements.annotationCount.textContent = `${annotations.length} 项`;
  elements.annotationList.replaceChildren();
  for (const annotation of annotations) {
    const fragment = elements.annotationTemplate.content.cloneNode(true);
    const article = fragment.querySelector('.annotation-item');
    article.dataset.annotationId = annotation.annotation_id;
    article.classList.toggle('selected', annotation.annotation_id === state.selectedAnnotationId);
    article.classList.toggle('confirmed', annotation.review_status === 'confirmed');
    article.classList.toggle('not-defect', annotation.review_status === 'not_defect');
    fragment.querySelector('strong').textContent = CATEGORY_LABELS[annotation.category];
    fragment.querySelector('small').textContent = annotation.component?.designator
      ? `${annotation.component.designator} · ${annotation.review_status}`
      : `板级区域 · ${annotation.review_status}`;
    fragment.querySelector('.annotation-select').addEventListener('click', () => {
      state.selectedAnnotationId = annotation.annotation_id;
      render();
    });
    fragment.querySelectorAll('[data-status]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.status === annotation.review_status));
      button.addEventListener('click', () => changeAnnotation(annotation.annotation_id, {
        review_status: button.dataset.status,
      }));
    });
    fragment.querySelector('[data-action="delete"]').addEventListener(
      'click',
      () => deleteAnnotation(annotation.annotation_id),
    );
    elements.annotationList.append(fragment);
  }
  const hasUnresolved = annotations.some(
    (annotation) => annotation.review_status === 'suspected' || annotation.source !== 'human_annotation',
  );
  const serverReview = currentCase()?.server_qc_review;
  const invalidImage = currentCase()?.quality?.status === 'retake';
  elements.finalizeQcButton.textContent = invalidImage
    ? '图片质量不合格'
    : serverReview
      ? `已同步审核 v${serverReview.version}`
      : currentCase()?.server_sync?.server_case_id
        ? '完成并同步人工 QC'
        : '完成人工 QC';
  elements.finalizeQcButton.disabled = currentCase()?.registration.status !== 'reviewed'
    || hasUnresolved
    || invalidImage
    || state.serverBusy
    || Boolean(serverReview);
  elements.finishPolygonButton.disabled = state.polygonPoints.length < 3;
}

function renderQcResult() {
  const status = currentCase()?.qc_result.status || 'needs_review';
  elements.qcResultTitle.textContent = QC_LABELS[status];
  elements.qcResultBadge.textContent = status;
  elements.qcResultBadge.className = `badge ${status.replaceAll('_', '-')}`;
  elements.exportJsonButton.disabled = !currentCase();
  elements.exportPngButton.disabled = !currentCase() || !state.photoImage;
}

function renderTrainingDataset() {
  const reviewer = VISUAL_QC_ACTOR_ROLE === 'reviewer';
  elements.trainingDatasetSection.hidden = !reviewer;
  if (!reviewer) return;

  const manifest = state.trainingManifest;
  const caseCount = Number(manifest?.case_count || 0);
  const annotationCount = Number(manifest?.annotation_count || 0);
  const audit = state.trainingAudit;
  const excludedCount = Number(audit?.excluded_case_count || 0);
  const categoryCount = Object.values(manifest?.category_counts || {})
    .filter((count) => Number(count) > 0).length;
  elements.trainingCaseCount.textContent = `${caseCount} 案例`;
  elements.trainingCaseCount.className = `badge ${caseCount ? 'reviewed' : 'neutral'}`;
  elements.trainingAnnotationCount.textContent = String(annotationCount);
  elements.trainingCategoryCount.textContent = String(categoryCount);
  elements.trainingExcludedCount.textContent = String(excludedCount);
  elements.trainingGateSummary.replaceChildren();
  for (const [reason, count] of Object.entries(audit?.reason_counts || {})) {
    const item = document.createElement('span');
    item.textContent = `${TRAINING_GATE_LABELS[reason] || reason} ${count}`;
    elements.trainingGateSummary.append(item);
  }
  const excludedCases = (audit?.cases || [])
    .filter((auditCase) => auditCase.status === 'excluded');
  elements.trainingGateCasesDisclosure.hidden = excludedCases.length === 0;
  elements.trainingGateCaseCount.textContent = String(excludedCases.length);
  elements.trainingGateCaseList.replaceChildren();
  for (const auditCase of excludedCases) {
    const row = document.createElement('div');
    row.className = 'training-gate-case';
    const identity = document.createElement('span');
    const title = document.createElement('strong');
    title.textContent = state.catalog?.boards?.[auditCase.board_key]?.title
      || auditCase.board_key;
    const meta = document.createElement('small');
    meta.textContent = `${BOARD_SIDE_LABELS[auditCase.side_id] || auditCase.side_id} · ${auditCase.case_id.slice(-8)}`;
    identity.append(title, meta);
    const reason = document.createElement('span');
    reason.textContent = TRAINING_GATE_LABELS[auditCase.blocking_reason]
      || auditCase.blocking_reason;
    row.append(identity, reason);
    elements.trainingGateCaseList.append(row);
  }

  if (state.trainingDatasetBusy) {
    elements.trainingDatasetSummary.textContent = '正在读取服务器训练门禁结果。';
  } else if (state.trainingDatasetError) {
    elements.trainingDatasetSummary.textContent = `读取失败：${state.trainingDatasetError}`;
  } else if (!manifest) {
    elements.trainingDatasetSummary.textContent = '刷新后可查看服务器审核数据。';
  } else if (!caseCount) {
    elements.trainingDatasetSummary.textContent = '还没有通过训练门禁的实拍案例。';
  } else {
    elements.trainingDatasetSummary.textContent = `${caseCount} 个案例、${annotationCount} 项确认标注已通过服务器训练门禁。`;
  }

  elements.refreshTrainingDatasetButton.disabled = state.trainingDatasetBusy;
  elements.downloadTrainingManifestButton.disabled = state.trainingDatasetBusy || !manifest;
  elements.downloadTrainingCocoButton.disabled = state.trainingDatasetBusy || !manifest;
}

async function refreshTrainingDataset({ quiet = false } = {}) {
  if (VISUAL_QC_ACTOR_ROLE !== 'reviewer' || state.trainingDatasetBusy) return;
  state.trainingDatasetBusy = true;
  state.trainingDatasetError = null;
  renderTrainingDataset();
  try {
    const [manifest, audit] = await Promise.all([
      getVisualQcTrainingManifest(
        VISUAL_QC_API,
        VISUAL_QC_ACTOR_ID,
        VISUAL_QC_ACTOR_ROLE,
      ),
      getVisualQcDatasetAudit(
        VISUAL_QC_API,
        VISUAL_QC_ACTOR_ID,
        VISUAL_QC_ACTOR_ROLE,
      ),
    ]);
    if (manifest?.schema_version !== 'VISUAL-QC-TRAINING-MANIFEST-V1') {
      throw new Error('服务器训练清单版本不受支持');
    }
    if (audit?.schema_version !== 'VISUAL-QC-DATASET-AUDIT-V1') {
      throw new Error('服务器数据门禁审计版本不受支持');
    }
    state.trainingManifest = manifest;
    state.trainingAudit = audit;
  } catch (error) {
    state.trainingDatasetError = error.message || '服务器请求失败';
    if (!quiet) reportUserError(error);
  } finally {
    state.trainingDatasetBusy = false;
    renderTrainingDataset();
  }
}

function renderInteractionPrompt() {
  if (!currentCase()) {
    elements.interactionPrompt.textContent = '请先导入一张主板图片';
  } else if (currentCase()?.registration?.status === 'reviewed') {
    elements.interactionPrompt.textContent = state.mode === 'annotation'
      ? '在实拍图上标注并人工确认可见异常'
      : '配准已确认，可以进入缺陷标注';
  } else if (currentCase()?.registration?.method === 'automatic_feature_homography'
    && currentCase()?.registration?.status === 'draft') {
    elements.interactionPrompt.textContent = '检查叠图位置；确认自动配准，或清除后改用人工四点配准';
  } else if (state.mode === 'annotation') {
    elements.interactionPrompt.textContent = state.annotationTool === 'polygon'
      ? '在实拍图上逐点标注，多边形至少三个点'
      : state.annotationTool === 'rectangle'
        ? '在实拍图上拖拽缺陷区域'
        : '拖拽平移，滚轮或工具按钮缩放';
  } else if (state.pendingBoardPoint) {
    elements.interactionPrompt.textContent = '在实拍图上选择对应位置';
  } else if (state.registrationTool === 'check') {
    elements.interactionPrompt.textContent = '先点工程图，再点实拍图，添加独立检查点';
  } else if (state.registrationTool === 'anchor') {
    elements.interactionPrompt.textContent = state.boardAnchors.length < 4
      ? `先点工程图，再点实拍图，添加第 ${state.boardAnchors.length + 1} 组锚点`
      : '四组锚点已求解，请添加独立检查点';
  } else {
    elements.interactionPrompt.textContent = '拖拽平移，滚轮或工具按钮缩放';
  }
}

function render() {
  const visualCase = currentCase();
  elements.photoEmpty.hidden = Boolean(state.photoImage);
  elements.photoCanvasMeta.textContent = visualCase
    ? `${visualCase.image.file_name} · ${visualCase.image.width} × ${visualCase.image.height}`
    : '尚未导入图片';
  elements.undoButton.disabled = !state.history?.past.length;
  elements.redoButton.disabled = !state.history?.future.length;
  renderCaptureSession();
  renderServerSync();
  renderQuality();
  renderRegistration();
  renderComparison();
  renderAnnotations();
  renderQcResult();
  renderTrainingDataset();
  renderInteractionPrompt();
  renderCanvases();
}

function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function downloadJsonDocument(documentValue, fileName) {
  downloadBlob(
    new Blob([`${JSON.stringify(documentValue, null, 2)}\n`], { type: 'application/json' }),
    fileName,
  );
}

async function downloadTrainingCoco() {
  if (VISUAL_QC_ACTOR_ROLE !== 'reviewer') return;
  state.trainingDatasetBusy = true;
  state.trainingDatasetError = null;
  renderTrainingDataset();
  try {
    const dataset = await getVisualQcCocoDataset(
      VISUAL_QC_API,
      VISUAL_QC_ACTOR_ID,
      VISUAL_QC_ACTOR_ROLE,
    );
    if (dataset?.info?.version !== 'VISUAL-QC-COCO-V1') {
      throw new Error('服务器 COCO 数据版本不受支持');
    }
    downloadJsonDocument(dataset, 'visual-qc-reviewed-dataset.coco.json');
  } catch (error) {
    state.trainingDatasetError = error.message || 'COCO 下载失败';
    reportUserError(error);
  } finally {
    state.trainingDatasetBusy = false;
    renderTrainingDataset();
  }
}

function exportJson() {
  const visualCase = currentCase();
  if (!visualCase) return;
  downloadBlob(
    new Blob([`${JSON.stringify(visualCase, null, 2)}\n`], { type: 'application/json' }),
    `${visualCase.case_id}.visual-qc.json`,
  );
}

function exportAnnotatedPng() {
  const visualCase = currentCase();
  if (!visualCase || !state.photoImage) return;
  const canvas = document.createElement('canvas');
  canvas.width = state.photoImage.naturalWidth;
  canvas.height = state.photoImage.naturalHeight;
  const context = canvas.getContext('2d');
  context.drawImage(state.photoImage, 0, 0);
  const frame = { x: 0, y: 0, width: canvas.width, height: canvas.height };
  for (const annotation of visualCase.annotations) {
    const color = annotation.review_status === 'confirmed'
      ? '#d6533f'
      : annotation.review_status === 'not_defect' ? '#2e7b62' : '#b87916';
    drawGeometry(
      context,
      annotation.image_geometry,
      frame,
      color,
      annotation.annotation_id === state.selectedAnnotationId,
      annotation.component?.designator || CATEGORY_LABELS[annotation.category],
    );
  }
  if (state.isProxy) {
    context.fillStyle = 'rgba(16, 37, 30, 0.9)';
    context.fillRect(20, 20, 430, 46);
    context.fillStyle = '#ffffff';
    context.font = '700 20px Segoe UI';
    context.fillText('INTERNAL PROXY · NOT FIELD QC EVIDENCE', 34, 51);
  }
  canvas.toBlob((blob) => {
    if (blob) downloadBlob(blob, `${visualCase.case_id}.annotated.png`);
  }, 'image/png');
}

async function importCase(file) {
  const operationRevision = state.loadRevision;
  await flushPendingSave();
  const visualCase = JSON.parse(await file.text());
  if (operationRevision !== state.loadRevision) {
    throw new Error('案例导入被新的主板切换中断。');
  }
  if (!['VISUAL-QC-CASE-V1', 'VISUAL-QC-CASE-V2'].includes(visualCase.schema_version)) {
    throw new Error('案例版本不受支持。');
  }
  if (!state.catalog.boards[visualCase.board_key]) throw new Error('案例主板不在当前目录中。');
  elements.boardSelect.value = visualCase.board_key;
  const loaded = await loadBoard(visualCase.board_key, visualCase.side_id, false);
  if (!loaded) throw new Error('案例载入被新的主板切换中断。');
  elements.captureStage.value = visualCase.capture_stage;
  clearHeatmap();
  state.history = createHistory(visualCase);
  state.photoImage = null;
  state.photoBlob = null;
  state.isProxy = visualCase.image.evidence_role === 'proxy_sample';
  state.awaitingImportedImage = true;
  syncRegistrationState();
  render();
  elements.saveStatus.textContent = '案例已导入，等待原图';
  elements.interactionPrompt.textContent = '案例已导入，请重新选择原图以核对 SHA-256';
}

async function renderSavedCases() {
  const records = await listVisualQcCases();
  elements.savedCasesList.replaceChildren();
  if (!records.length) {
    const empty = document.createElement('p');
    empty.className = 'source-note';
    empty.textContent = '本机还没有视觉 QC 草稿。';
    elements.savedCasesList.append(empty);
    return;
  }
  for (const record of records) {
    const article = document.createElement('article');
    article.className = 'saved-case';
    const strong = document.createElement('strong');
    strong.textContent = `${record.board_key} · ${record.side_id}`;
    const small = document.createElement('small');
    small.textContent = `${record.image.file_name} · ${record.qc_result.status}`;
    const open = document.createElement('button');
    open.type = 'button';
    open.textContent = '打开';
    open.addEventListener('click', async () => {
      try {
        const operationRevision = state.loadRevision;
        await flushPendingSave();
        const saved = await loadVisualQcCase(record.case_id);
        if (operationRevision !== state.loadRevision) return;
        const photoImage = saved.imageBlob ? await imageFromBlob(saved.imageBlob) : null;
        if (operationRevision !== state.loadRevision) return;
        const loaded = await loadBoard(
          saved.visualCase.board_key,
          saved.visualCase.side_id,
          false,
        );
        if (!loaded) return;
        elements.boardSelect.value = saved.visualCase.board_key;
        elements.captureStage.value = saved.visualCase.capture_stage;
        clearHeatmap();
        state.history = createHistory(saved.visualCase);
        state.photoBlob = saved.imageBlob;
        state.photoImage = photoImage;
        state.isProxy = saved.visualCase.image.evidence_role === 'proxy_sample';
        syncRegistrationState();
        elements.savedCasesDialog.close();
        resizeCanvases();
        render();
        elements.saveStatus.textContent = '已从本机恢复';
      } catch (error) {
        reportUserError(error);
      }
    });
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = '删除';
    remove.addEventListener('click', async () => {
      await deleteVisualQcCase(record.case_id);
      renderSavedCases();
    });
    article.append(strong, open, small, remove);
    elements.savedCasesList.append(article);
  }
}

function bindCanvas(canvas, role) {
  canvas.addEventListener('pointerdown', (event) => onPointerDown(role, event));
  canvas.addEventListener('pointermove', (event) => onPointerMove(role, event));
  canvas.addEventListener('pointerup', (event) => onPointerUp(role, event));
  canvas.addEventListener('pointercancel', () => {
    state.drag = null;
    state.rectanglePreview = null;
    renderCanvases();
  });
  canvas.addEventListener('wheel', (event) => onWheel(role, event), { passive: false });
}

function bindEvents() {
  elements.boardSelect.addEventListener('change', () => {
    state.captureSessionDraft = null;
    loadBoard(elements.boardSelect.value);
  });
  elements.captureStage.addEventListener('change', () => {
    if (!currentCase()) return;
    const next = structuredClone(currentCase());
    next.capture_stage = elements.captureStage.value;
    commitCase(next);
  });
  elements.chooseImageButton.addEventListener('click', () => elements.imageInput.click());
  elements.photoEmpty.addEventListener('click', () => elements.imageInput.click());
  elements.imageInput.addEventListener('change', async () => {
    const file = elements.imageInput.files[0];
    if (!file) return;
    try {
      await loadPhotoBlob(file, file.name);
    } catch (error) {
      reportUserError(error);
    } finally {
      elements.imageInput.value = '';
    }
  });
  elements.proxyButton.addEventListener('click', async () => {
    try {
      const path = state.dataset.registration.proxy_image;
      const response = await fetch(rootAsset(path));
      if (!response.ok) throw new Error(`代理样本返回 ${response.status}`);
      await loadPhotoBlob(await response.blob(), path.split('/').at(-1), true);
    } catch (error) {
      reportUserError(error);
    }
  });
  elements.importCaseButton.addEventListener('click', () => elements.caseImportInput.click());
  elements.caseImportInput.addEventListener('change', async () => {
    const file = elements.caseImportInput.files[0];
    if (!file) return;
    try {
      await importCase(file);
    } catch (error) {
      reportUserError(error);
    } finally {
      elements.caseImportInput.value = '';
    }
  });
  elements.registrationModeButton.addEventListener('click', () => setMode('registration'));
  elements.annotationModeButton.addEventListener('click', () => setMode('annotation'));
  elements.registrationTools.querySelectorAll('[data-registration-tool]').forEach((button) => {
    button.addEventListener('click', () => {
      state.registrationTool = button.dataset.registrationTool;
      state.pendingBoardPoint = null;
      elements.registrationTools.querySelectorAll('[data-registration-tool]').forEach((item) => {
        item.setAttribute('aria-pressed', String(item === button));
      });
      render();
    });
  });
  elements.annotationTools.querySelectorAll('[data-annotation-tool]').forEach((button) => {
    button.addEventListener('click', () => {
      state.annotationTool = button.dataset.annotationTool;
      state.polygonPoints = [];
      state.rectanglePreview = null;
      elements.annotationTools.querySelectorAll('[data-annotation-tool]').forEach((item) => {
        item.setAttribute('aria-pressed', String(item === button));
      });
      render();
    });
  });
  elements.finishPolygonButton.addEventListener('click', finishPolygon);
  elements.overlayOpacity.addEventListener('input', renderCanvases);
  elements.removeLastPairButton.addEventListener('click', removeLastPair);
  elements.clearRegistrationButton.addEventListener('click', clearRegistration);
  elements.reviewRegistrationButton.addEventListener('click', confirmRegistration);
  elements.serverSyncButton.addEventListener('click', syncCurrentCaseWithServer);
  elements.captureChecklist.querySelectorAll('[data-capture-check]').forEach((input) => {
    input.addEventListener('change', () => {
      const visualCase = currentCase();
      if (!visualCase || visualCase.server_sync?.server_case_id) return;
      commitCase(updateCaptureChecklist(
        visualCase,
        input.dataset.captureCheck,
        input.checked,
      ));
    });
  });
  elements.refreshCaptureSessionButton.addEventListener(
    'click',
    refreshCurrentCaptureSession,
  );
  elements.captureOtherSideButton.addEventListener('click', startOtherSideCapture);
  elements.refreshGoldenButton.addEventListener('click', () => refreshCurrentGoldenSample());
  elements.approveGoldenButton.addEventListener('click', approveCurrentGoldenSample);
  elements.runDifferenceButton.addEventListener('click', runDifferenceAnalysis);
  elements.normalConfirmation.addEventListener('change', render);
  elements.captureSetupId.addEventListener('change', () => {
    if (!currentCase()) return;
    clearHeatmap();
    const next = structuredClone(currentCase());
    if (!next.server_sync?.server_case_id && next.capture_session) {
      next.capture_session.setup_id = captureSetupId();
      replaceCurrentCase(next, true);
    }
    updateComparisonDraft({
      capture_setup_id: captureSetupId(),
      golden_sample: null,
      difference: null,
      golden_lookup_status: 'unknown',
    });
    void refreshCurrentGoldenSample({ quietMissing: true });
  });
  elements.finalizeQcButton.addEventListener('click', finalizeVisualQc);
  elements.undoButton.addEventListener('click', () => {
    state.history = undoHistory(state.history);
    syncRegistrationState();
    scheduleSave();
    render();
  });
  elements.redoButton.addEventListener('click', () => {
    state.history = redoHistory(state.history);
    syncRegistrationState();
    scheduleSave();
    render();
  });
  elements.resetViewButton.addEventListener('click', () => {
    if (state.activeCanvas === 'board') state.boardViewport = createViewport();
    else state.photoViewport = createViewport();
    renderCanvases();
  });
  for (const [button, factor] of [[elements.zoomInButton, 1.2], [elements.zoomOutButton, 1 / 1.2]]) {
    button.addEventListener('click', () => {
      const role = state.activeCanvas;
      const canvas = role === 'board' ? elements.boardCanvas : elements.photoCanvas;
      const image = role === 'board' ? state.pointMapImage : state.photoImage;
      if (!image) return;
      const viewport = role === 'board' ? state.boardViewport : state.photoViewport;
      const next = zoomViewportAt(
        viewport,
        factor,
        { x: canvas.width / 2, y: canvas.height / 2 },
        canvas,
        { width: image.naturalWidth, height: image.naturalHeight },
      );
      if (role === 'board') state.boardViewport = next;
      else state.photoViewport = next;
      renderCanvases();
    });
  }
  elements.exportJsonButton.addEventListener('click', exportJson);
  elements.exportPngButton.addEventListener('click', exportAnnotatedPng);
  elements.refreshTrainingDatasetButton.addEventListener(
    'click',
    () => refreshTrainingDataset(),
  );
  elements.downloadTrainingManifestButton.addEventListener('click', () => {
    if (state.trainingManifest) {
      downloadJsonDocument(state.trainingManifest, 'visual-qc-training-manifest.json');
    }
  });
  elements.downloadTrainingCocoButton.addEventListener('click', downloadTrainingCoco);
  elements.savedCasesButton.addEventListener('click', async () => {
    await renderSavedCases();
    elements.savedCasesDialog.showModal();
  });
  elements.closeSavedCasesButton.addEventListener('click', () => elements.savedCasesDialog.close());

  for (const eventName of ['dragenter', 'dragover']) {
    elements.photoDropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.photoDropZone.classList.add('dragover');
    });
  }
  for (const eventName of ['dragleave', 'drop']) {
    elements.photoDropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.photoDropZone.classList.remove('dragover');
    });
  }
  elements.photoDropZone.addEventListener('drop', async (event) => {
    const file = event.dataTransfer.files[0];
    if (!file) return;
    try {
      await loadPhotoBlob(file, file.name);
    } catch (error) {
      reportUserError(error);
    }
  });
  bindCanvas(elements.boardCanvas, 'board');
  bindCanvas(elements.photoCanvas, 'photo');
  new ResizeObserver(resizeCanvases).observe(document.querySelector('.canvas-grid'));
}

async function initialize() {
  DEFECT_CATEGORIES.forEach((category) => {
    const option = document.createElement('option');
    option.value = category;
    option.textContent = CATEGORY_LABELS[category];
    elements.defectCategory.append(option);
  });
  try {
    const identity = await getVisualQcIdentity(
      VISUAL_QC_API,
      VISUAL_QC_ACTOR_ID,
      VISUAL_QC_ACTOR_ROLE,
    );
    if (identity?.schema_version === 'VISUAL-QC-IDENTITY-V1') {
      VISUAL_QC_ACTOR_ID = identity.actor_id;
      VISUAL_QC_ACTOR_ROLE = identity.role === 'reviewer' ? 'reviewer' : 'technician';
    }
  } catch (error) {
    VISUAL_QC_ACTOR_ROLE = 'technician';
    if (error.status !== 404) console.warn('Visual-QC identity unavailable:', error.message);
  }
  state.catalog = await fetchJson(CATALOG_URL);
  state.boardKey = state.catalog.default_board_key;
  renderBoardSelector();
  bindEvents();
  await loadBoard(state.boardKey);
  await refreshTrainingDataset({ quiet: true });
  resizeCanvases();
}

initialize().catch((error) => {
  console.error(error);
  elements.boardEmpty.hidden = false;
  elements.boardEmpty.textContent = `工作台载入失败：${error.message}`;
  elements.interactionPrompt.textContent = '工作台载入失败';
});
