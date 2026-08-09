import { solveHomography } from './registration-core.js';
import { resolveBoardAssets, resolveBoardKey } from './board-catalog-state.js';
import { buildSelectionState, entityListModelRevealOptions, nearestPointerTarget } from './selection-state.js';
import { BoardRenderer } from './board-renderer.js';
import { ImageViewport } from './image-viewport.js';
import { PointMapViewport } from './point-map-viewport.js';
import {
  buildPhotoNavigationState,
  failPhotoNavigation,
  resolveReviewedPhotoIdBySourceHash,
} from './photo-navigation-state.js';
import { buildSourceNote } from './source-note-state.js';
import { buildRegistrationViewState } from './registration-view-state.js';
import { buildPhysicalRegistrationState } from './physical-registration-state.js';
import { buildRepairCoverageState } from './repair-coverage-state.js';
import { buildCaseNavigationState } from './case-navigation-state.js';
import { resolvePilotIntent } from './pilot-intent-state.js';
import {
  createPilotFeedback,
  loadPilotFeedback,
  savePilotFeedback as savePilotFeedbackRecords,
  serializePilotFeedback,
} from './pilot-feedback-state.js';
import { buildEntityAccessState } from './entity-access-state.js';
import { mergeCompiledSchematicLinks } from './source-links.js';
import { mergeCompiledFootprint } from './source-geometry-state.js';
import { technicianEntityCopy, technicianInstruction } from './technician-copy.js';
import { extractModuleRegions, extractShieldRegions } from './anatomy-state.js';
import {
  buildEntityTarget,
  moduleOverlayId,
} from './repair-focus-state.js';
import {
  buildInspectionActionState,
  buildInspectionEntryIntent,
  buildInspectionToolbarState,
  canInspectComponent,
  enterComponentInspection,
  exitComponentInspection,
  resolveModelComponentActivation,
} from './component-inspection-state.js';
import {
  beginModelTransition,
  canAcceptModelInteraction,
  completeModelTransition,
  consumePendingFocus,
  createModelInteractionState,
  recordSelectionIntent,
} from './model-interaction-state.js';
import { resolveBoardInteractionMode } from './board-pan-state.js';
import { buildRepairEntryOptions, resolveRepairEntryIntent } from './repair-entry-state.js';
import {
  createRepairGuidance,
  guidanceProgress,
  recordGuidanceMeasurement,
  recordGuidanceResult,
  selectGuidanceFault,
} from './repair-guidance-state.js';
import {
  answerRepairFlow,
  backRepairFlow,
  buildRepairFlowChoiceOptions,
  closeRepairFlow,
  createRepairFlowState,
  currentRepairFlowStep,
  recordRepairFlowPostActionCheck,
  recordRepairFlowMeasurement,
  repairFlowMeasurementsComplete,
  repairFlowMeasurementAssessment,
  repairFlowProgress,
  repairFlowTargetComponentId,
  repairFlowTrail,
  resetRepairFlow,
  setRepairFlowActionExecuted,
} from './repair-flow-state.js';
import {
  beginRepairSession,
  isRepairSessionEligible,
  persistRepairSession,
  repairSessionStartState,
  restartRepairSession,
} from './repair-session-controller.js';
import { serializeRepairSessions } from './repair-session-state.js';

const BOARD_CATALOG_URL = '../../knowledge-base/repair-workbench-boards.json';
const views = { photo: document.querySelector('#photoView'), pointmap: document.querySelector('#pointmapView'), model: document.querySelector('#modelView') };
let data;
let matrix;
let renderer;
let geometryData;
let selectedId;
let pointMapViewport;
let photoViewport;
let photoState = null;
const preferredPhotoBySide = new Map();
let technicianSelectionActive = false;
let activeView = 'photo';
let currentRepairTarget;
let sideDataById = new Map();
let activeSideId = 'main_page_2';
let componentInspection = exitComponentInspection();
let modelInteraction = createModelInteractionState();
let modelDragMode = 'pan';
let modelAssetStatus = 'loading';
const repairGuidanceByComponent = new Map();
const repairFlowById = new Map();
const confirmationTimers = new WeakMap();
let activeRepairFlowId = null;
let repairEntryExpanded = false;
let repairEntryError = '';
let selectedCaseId = null;
let selectedCaseSymptomKey = null;
let pilotIntent = null;
let activeBoardKey = null;
let pilotFeedbackTarget = null;
let pilotFeedbackUsefulness = null;
let activeRepairSession = null;
let activeRepairSessionContext = null;
let repairSessionRecovered = false;
let repairSessionPersistenceError = null;
let repairSessionPendingRecords = [];

const FAULT_LABELS = {
  no_power: '无法开机',
  leakage_current: '漏电',
  pmu_failure: '电源管理异常',
  'No power': '无法开机',
  'Leakage current': '漏电',
  'Storage failure': '存储异常',
  'Clock failure': '时钟异常',
  'No service': '无服务',
  'Weak signal': '信号弱',
  'Not charging': '无法充电',
  'USB no response': 'USB 无响应',
  'WiFi connection failure': 'Wi-Fi 无法连接',
  'Display failure': 'LCD 无显示',
};

function revealModelWorkspace() {
  const options = entityListModelRevealOptions({
    activeView,
    viewportWidth: window.innerWidth,
    reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  });
  if (options) document.querySelector('.workspace').scrollIntoView(options);
}

function revealModelAfterEntityListSelection() {
  revealModelWorkspace();
}

function updateSourceNote(inspectionEntity = null) {
  if (!data) return;
  const side = sideDataById.get(activeSideId);
  if (!side) return;
  document.querySelector('#sourceNote').textContent = buildSourceNote({
    view: activeView,
    registration: data.registration,
    side,
    photo: activeView === 'photo' && photoState ? {
      label: photoState.available ? photoState.activePhoto.label : null,
      boundaryCopy: photoState.boundaryCopy,
    } : null,
    inspectionEntity,
    repairCoverage: data.repair_coverage,
  });
}

function updateEntityAccessStatus(entity) {
  if (!entity) return;
  const targetSideLabel = sideDataById.get(entity.side_id)?.label || entity.side_id;
  const access = buildEntityAccessState(entity, activeSideId, targetSideLabel);
  const visibility = document.querySelector('#entityVisibility');
  visibility.textContent = access.label;
  visibility.dataset.tone = access.tone;
  visibility.title = access.description;
  visibility.setAttribute('aria-label', `位置状态：${access.label}。${access.description}`);
}

function renderPhysicalRegistration() {
  if (!data) return;
  const state = buildPhysicalRegistrationState(data.physical_evidence, activeSideId);
  const details = document.querySelector('#physicalRegistrationDetails');
  details.hidden = !state.visible;
  if (!state.visible) return;
  document.querySelector('#physicalRegistrationTitle').textContent = state.title;
  document.querySelector('#physicalRegistrationCount').textContent = state.summary;
  const content = document.querySelector('#physicalRegistrationEvidence');
  content.replaceChildren();
  state.items.forEach((item) => {
    const article = document.createElement('article');
    article.className = 'physical-registration-card';
    const heading = document.createElement('div');
    const label = document.createElement('strong');
    label.textContent = item.label;
    const hash = document.createElement('code');
    hash.textContent = item.hash;
    heading.append(label, hash);
    const error = document.createElement('span');
    error.textContent = item.error;
    const annotation = document.createElement('small');
    annotation.textContent = item.annotation;
    article.append(heading, error, annotation);
    content.append(article);
  });
  const boundary = document.createElement('p');
  boundary.className = 'physical-registration-boundary';
  boundary.textContent = state.boundary;
  content.append(boundary);
}

const GUIDANCE_RESULT_COPY = {
  pending: '尚未返回检测结果。完成当前检测步骤后记录本次观察。',
  normal: '已记录正常。继续结合下方原理图与维修指导排查其他路径。',
  abnormal: '已记录异常。保留测量信息，并结合下方维修资料继续处理。',
  uncertain: '已记录无法确认。复核检测条件后再次执行本步骤。',
};

function measurementReferenceCopy(profile) {
  const { reference, unit } = profile;
  if (reference.kind === 'range') return `资料范围 ${reference.min}–${reference.max} ${unit}`;
  if (reference.kind === 'nominal') return `资料参考 ${reference.value} ${unit} · 未提供容差`;
  return '资料要求记录 · 未提供参考范围';
}

function measurementFeedbackCopy(guidance) {
  const { measurement, measurementProfile: profile } = guidance;
  if (!profile || measurement.evaluation === 'unrecorded') return '尚未记录测量值。';
  const value = `${measurement.value} ${profile.unit}`;
  if (measurement.evaluation === 'within_range') return `${value} · 位于资料范围内。`;
  if (measurement.evaluation === 'below_range') return `${value} · 低于资料范围。`;
  if (measurement.evaluation === 'above_range') return `${value} · 高于资料范围。`;
  return `${value} · 已记录；资料未提供容差，未自动判定。`;
}

function guidanceResultCopy(guidance) {
  if (guidance.resultSource === 'source_range') {
    return guidance.result === 'normal'
      ? '资料范围判断：本次测量值位于范围内；这不是器件诊断。'
      : '资料范围判断：本次测量值位于范围外；保留测量信息并继续当前检测步骤。';
  }
  return GUIDANCE_RESULT_COPY[guidance.result];
}

function matchingRepairFlow(entity) {
  const active = data?.repair_flows?.find((flow) => flow.flow_id === activeRepairFlowId);
  if (active) {
    const state = repairFlowById.get(active.flow_id) || createRepairFlowState(active);
    const target = repairFlowTargetComponentId(active, state);
    if (target === entity.component_id) return active;
  }
  return null;
}

function renderRepairEntry() {
  const entryRoot = document.querySelector('#repairEntry');
  const options = document.querySelector('#repairEntryOptions');
  const changeButton = document.querySelector('#changeRepairEntry');
  if (!entryRoot || !options || !changeButton || !data) return;
  const coverage = buildRepairCoverageState(data);
  const flows = data.repair_flows || [];
  const activeFlow = flows.find((flow) => flow.flow_id === activeRepairFlowId);
  const activeState = activeFlow && repairFlowById.get(activeFlow.flow_id);
  const boundaryOnly = pilotIntent?.valid && pilotIntent.boundaryOnly;
  entryRoot.dataset.active = String(Boolean(activeFlow));
  entryRoot.dataset.closed = String(Boolean(activeState?.closed));
  entryRoot.dataset.available = String(coverage.available);
  document.querySelector('#repairEntryEyebrow').textContent = boundaryOnly
    ? '资料边界'
    : activeState?.closed
    ? '排查已结束'
    : activeFlow ? '当前排查' : coverage.eyebrow;
  document.querySelector('#repairEntryTitle').textContent = boundaryOnly
    ? '暂无可执行初步排查步骤'
    : activeFlow?.title || coverage.title;
  const coverageNote = document.querySelector('#repairCoverageNote');
  coverageNote.hidden = !boundaryOnly && coverage.available && !repairEntryError;
  coverageNote.textContent = boundaryOnly
    ? '当前资料未形成可执行初步排查步骤。可以查看板面、器件与既有依据，但系统不会建议测量、结论或维修动作。'
    : repairEntryError || coverage.note;
  options.hidden = boundaryOnly || !coverage.available || Boolean(activeFlow && !repairEntryExpanded);
  changeButton.hidden = !activeFlow;
  changeButton.textContent = repairEntryExpanded ? '收起' : '更换故障';
  changeButton.setAttribute('aria-expanded', String(repairEntryExpanded));
  changeButton.onclick = () => {
    repairEntryExpanded = !repairEntryExpanded;
    renderRepairEntry();
  };
  options.replaceChildren();
  (boundaryOnly ? [] : buildRepairEntryOptions(flows, activeRepairFlowId)).forEach((entry) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.flowId = entry.flowId;
    button.dataset.entryType = entry.type;
    button.textContent = entry.label;
    button.setAttribute('aria-pressed', String(entry.active));
    button.addEventListener('click', () => { void startRepairEntry(entry.flowId); });
    options.append(button);
  });
  renderCaseNavigation();
}

function renderPilotIntentContext() {
  const root = document.querySelector('#pilotIntentContext');
  const feedback = document.querySelector('#pilotFeedback');
  const visible = Boolean(pilotIntent?.valid);
  root.hidden = !visible;
  feedback.hidden = !visible;
  if (!visible) return;
  document.querySelector('#pilotIntentModel').textContent = `${pilotIntent.model} · ${data.board_version}`;
  document.querySelector('#pilotIntentLabel').textContent = pilotIntent.label;
  const boundaries = {
    repair_flow: '按已审核的来源流程进入；系统不会补写资料中没有的检测参数或维修动作。',
    case_symptom: '候选器件仅来自该故障现象组的原始案例关联，不代表已确认故障因果。',
    initial_check: pilotIntent.boundaryOnly
      ? '当前板型没有已审核的初步排查步骤。仅开放结构和既有依据查看，并在此边界停止。'
      : '按资料中已审核的初步排查步骤进入。',
  };
  document.querySelector('#pilotIntentBoundary').textContent = boundaries[pilotIntent.kind];
}

function renderCaseNavigation() {
  const root = document.querySelector('#caseNavigation');
  if (!root || !data) return;
  const state = buildCaseNavigationState(data.case_navigation, selectedCaseId, selectedCaseSymptomKey);
  const intentAllowsCases = !pilotIntent?.valid || pilotIntent.kind === 'case_symptom';
  root.hidden = !state.visible || !intentAllowsCases;
  if (!state.visible || !intentAllowsCases) return;
  selectedCaseSymptomKey = state.activeGroup.key;
  selectedCaseId = state.activeCase.caseId;
  document.querySelector('#caseNavigationSummary').textContent = state.summary;
  const symptomSelector = document.querySelector('#caseSymptomSelector');
  symptomSelector.replaceChildren();
  state.groups.forEach((group) => {
    const node = document.createElement('option');
    node.value = group.key;
    node.textContent = `${group.label}（${group.caseCount} 个案例）`;
    symptomSelector.append(node);
  });
  symptomSelector.value = state.activeGroup.key;
  symptomSelector.onchange = () => {
    selectedCaseSymptomKey = symptomSelector.value;
    selectedCaseId = null;
    if (pilotIntent?.valid && pilotIntent.kind === 'case_symptom') {
      const selectedGroup = state.groups.find((group) => group.key === selectedCaseSymptomKey);
      pilotIntent = {
        ...pilotIntent,
        label: selectedGroup.label,
        symptomKey: selectedGroup.key,
      };
      const url = new URL(window.location.href);
      url.searchParams.set('symptom', selectedGroup.key);
      window.history.replaceState(null, '', url);
      renderPilotIntentContext();
    }
    renderCaseNavigation();
  };
  const selector = document.querySelector('#caseSelector');
  selector.replaceChildren();
  state.options.forEach((option) => {
    const node = document.createElement('option');
    node.value = option.caseId;
    node.textContent = option.label;
    selector.append(node);
  });
  selector.value = state.activeCase.caseId;
  selector.onchange = () => {
    selectedCaseId = selector.value;
    renderCaseNavigation();
  };
  document.querySelector('#caseSymptoms').textContent = state.activeCase.symptoms.join(' / ');
  document.querySelector('#caseFinding').textContent = state.activeCase.finding;
  document.querySelector('#caseNavigationBoundary').textContent = state.activeCase.boundary;
  document.querySelector('#caseGapSummary').textContent = `缺少 ${state.missingFieldCount} 类可执行检测字段 · ${state.activeCase.photoCount} 张来源照片记录`;
  const targets = document.querySelector('#caseCandidateTargets');
  targets.replaceChildren();
  if (state.activeCase.boardOnly) {
    const boundary = document.createElement('p');
    boundary.textContent = '该案例缺少可审核的精确位号，保留为板级案例。';
    targets.append(boundary);
    return;
  }
  state.activeCase.candidateComponentIds.forEach((componentId) => {
    const entity = data.entities.find((candidate) => candidate.component_id === componentId);
    if (!entity) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.caseComponentId = componentId;
    button.innerHTML = `<strong>${entity.designator}</strong><span>${technicianEntityCopy(entity).module}</span>`;
    button.addEventListener('click', () => { void selectCaseCandidate(componentId); });
    targets.append(button);
  });
}

async function selectCaseCandidate(componentId) {
  const state = buildCaseNavigationState(data?.case_navigation, selectedCaseId, selectedCaseSymptomKey);
  if (!state.visible || !state.activeCase.candidateComponentIds.includes(componentId)) return false;
  const entity = data.entities.find((candidate) => candidate.component_id === componentId);
  if (!entity) return false;
  const evidencePhotoId = state.activeCase.photoSha256
    .map((digest) => resolveReviewedPhotoIdBySourceHash(data.registration, entity.side_id, digest))
    .find(Boolean);
  if (evidencePhotoId) preferredPhotoBySide.set(entity.side_id, evidencePhotoId);
  return selectEntity(componentId);
}

function replaceRepairFlowStates(flowById) {
  repairFlowById.clear();
  flowById.forEach((state, flowId) => repairFlowById.set(flowId, state));
}

function buildRepairSessionContext(entryFlowId, flow) {
  if (!pilotIntent?.valid || !pilotIntent.model || !isRepairSessionEligible(data, flow)) return null;
  return {
    boardKey: activeBoardKey,
    model: pilotIntent.model,
    boardVersion: data.board_version,
    intent: {
      kind: pilotIntent.kind,
      label: pilotIntent.label || flow.entry_label,
      flowId: pilotIntent.flowId || entryFlowId,
    },
    entryFlowId,
  };
}

function persistActiveRepairSession() {
  if (!activeRepairSession || !activeRepairFlowId) return;
  const result = persistRepairSession({
    storage: window.localStorage,
    session: activeRepairSession,
    activeFlowId: activeRepairFlowId,
    flowById: repairFlowById,
    pendingRecords: repairSessionPendingRecords,
  });
  activeRepairSession = result.session;
  repairSessionPersistenceError = result.persistenceError;
  repairSessionPendingRecords = result.pendingRecords;
  repairSessionRecovered = false;
}

function renderRepairSessionStatus() {
  const strip = document.querySelector('#repairSessionStrip');
  if (!strip) return;
  strip.hidden = !activeRepairSession;
  if (!activeRepairSession) return;
  const status = repairSessionPersistenceError ? 'error' : activeRepairSession.status;
  const statusCopy = repairSessionPersistenceError
    ? '保存失败'
    : activeRepairSession.status === 'completed'
      ? '已完成'
      : activeRepairSession.status === 'stopped_at_source_boundary'
        ? '已在资料边界停止'
        : repairSessionRecovered
          ? '已恢复'
          : '进行中';
  strip.dataset.status = status;
  document.querySelector('#repairSessionStatus').textContent = statusCopy;
  document.querySelector('#repairSessionSavedAt').textContent = repairSessionPersistenceError
    ? '当前流程仍可继续，但本机未能保存最新记录'
    : `本机保存 · ${new Date(activeRepairSession.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  document.querySelector('#exportRepairSession').disabled = false;
}

function exportActiveRepairSession() {
  if (!activeRepairSession) return;
  const blob = new Blob([serializeRepairSessions([activeRepairSession])], { type: 'application/json;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `technician-repair-session-${new Date().toISOString().slice(0, 10)}.json`;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

function setExclusiveFeedback(selector, value) {
  document.querySelectorAll(selector).forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.feedbackTarget === value || button.dataset.feedbackUsefulness === value));
  });
}

function feedbackContext() {
  return {
    boardKey: activeBoardKey,
    model: pilotIntent.model,
    boardVersion: data.board_version,
    intent: pilotIntent,
    selectedComponentId: technicianSelectionActive ? selectedId : null,
    selectedCaseId,
  };
}

function recordPilotFeedback() {
  const status = document.querySelector('#pilotFeedbackStatus');
  try {
    const record = createPilotFeedback(feedbackContext(), {
      targetStatus: pilotFeedbackTarget,
      usefulness: pilotFeedbackUsefulness,
      note: document.querySelector('#pilotFeedbackNote').value,
    });
    const records = loadPilotFeedback(window.localStorage);
    savePilotFeedbackRecords(window.localStorage, [...records, record]);
    status.textContent = `已保存在本机 · 共 ${records.length + 1} 条`;
  } catch (error) {
    status.textContent = error.message === 'Select at least one feedback dimension'
      ? '请至少选择一项反馈。'
      : `无法记录：${error.message}`;
  }
}

function exportPilotFeedback() {
  const records = loadPilotFeedback(window.localStorage);
  const blob = new Blob([serializePilotFeedback(records)], { type: 'application/json;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `technician-pilot-feedback-${new Date().toISOString().slice(0, 10)}.json`;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  document.querySelector('#pilotFeedbackStatus').textContent = `已导出 ${records.length} 条本机反馈。`;
}

function syncPilotFlowIntent(flow) {
  if (!pilotIntent?.valid) return;
  pilotIntent = {
    ...pilotIntent,
    kind: 'repair_flow',
    label: flow.entry_label,
    flowId: flow.flow_id,
    symptomKey: null,
    boundaryOnly: false,
  };
  const url = new URL(window.location.href);
  url.searchParams.set('intent', 'repair_flow');
  url.searchParams.set('flow', flow.flow_id);
  url.searchParams.delete('symptom');
  window.history.replaceState(null, '', url);
  renderPilotIntentContext();
}

async function startRepairEntry(flowId, options = {}) {
  const intent = resolveRepairEntryIntent(data?.repair_flows, flowId);
  const flow = data.repair_flows.find((candidate) => candidate.flow_id === intent.flowId);
  const targetEntity = data.entities.find((candidate) => candidate.component_id === intent.targetComponentId);
  const evidencePhotoId = targetEntity && resolveReviewedPhotoIdBySourceHash(
    data.registration,
    targetEntity.side_id,
    flow.source_photo_sha256,
  );
  if (flow.source_photo_sha256 && !evidencePhotoId) {
    repairEntryError = '来源实拍与当前审核资料不一致，已停止进入该排查。请复核照片哈希、板面与审核状态。';
    renderRepairEntry();
    return false;
  }
  if (options.syncPilotIntent !== false) syncPilotFlowIntent(flow);
  repairEntryError = '';
  if (evidencePhotoId) {
    preferredPhotoBySide.set(targetEntity.side_id, evidencePhotoId);
    if (targetEntity.side_id === activeSideId) syncBoardViews();
  }
  if (!repairFlowById.has(flow.flow_id)) repairFlowById.set(flow.flow_id, createRepairFlowState(flow));
  repairFlowById.set(flow.flow_id, repairSessionStartState(flow, repairFlowById.get(flow.flow_id)));
  const sessionContext = buildRepairSessionContext(flow.flow_id, flow);
  if (sessionContext) {
    const initialFlowById = new Map([[flow.flow_id, repairFlowById.get(flow.flow_id)]]);
    const session = beginRepairSession({
      storage: window.localStorage,
      context: sessionContext,
      activeFlowId: flow.flow_id,
      flowById: initialFlowById,
      declaredFlows: data.repair_flows,
      pendingRecords: repairSessionPendingRecords,
    });
    activeRepairSession = session.session;
    activeRepairSessionContext = sessionContext;
    repairSessionRecovered = session.recovered;
    repairSessionPersistenceError = session.persistenceError;
    repairSessionPendingRecords = session.pendingRecords;
    activeRepairFlowId = session.activeFlowId;
    replaceRepairFlowStates(session.flowById);
  } else {
    activeRepairSession = null;
    activeRepairSessionContext = null;
    repairSessionRecovered = false;
    repairSessionPersistenceError = null;
    repairSessionPendingRecords = [];
    activeRepairFlowId = flow.flow_id;
  }
  repairEntryExpanded = false;
  renderRepairEntry();
  const activeFlow = data.repair_flows.find((candidate) => candidate.flow_id === activeRepairFlowId);
  const activeState = activeFlow && repairFlowById.get(activeFlow.flow_id);
  const activeTarget = activeFlow && repairFlowTargetComponentId(activeFlow, activeState);
  await selectEntity(activeTarget || intent.targetComponentId);
  return true;
}

function applyRepairFlowState(flow, next, entity, options = {}) {
  if (options.restartSession && activeRepairSession && activeRepairSessionContext) {
    const replacementFlows = new Map([[flow.flow_id, next]]);
    const restarted = restartRepairSession({
      storage: window.localStorage,
      session: activeRepairSession,
      context: activeRepairSessionContext,
      activeFlowId: flow.flow_id,
      flowById: replacementFlows,
      pendingRecords: repairSessionPendingRecords,
    });
    activeRepairSession = restarted.session;
    repairSessionRecovered = false;
    repairSessionPersistenceError = restarted.persistenceError;
    repairSessionPendingRecords = restarted.pendingRecords;
    replaceRepairFlowStates(replacementFlows);
  } else {
    repairFlowById.set(flow.flow_id, next);
  }
  if (next.terminal?.kind === 'handoff') {
    const targetFlow = data.repair_flows.find((candidate) => candidate.flow_id === next.terminal.flowId);
    if (!targetFlow) throw new Error(`Unknown repair flow handoff: ${next.terminal.flowId}`);
    if (!repairFlowById.has(targetFlow.flow_id)) {
      repairFlowById.set(targetFlow.flow_id, createRepairFlowState(targetFlow));
    }
    activeRepairFlowId = targetFlow.flow_id;
    persistActiveRepairSession();
    renderRepairEntry();
    const targetState = repairFlowById.get(targetFlow.flow_id);
    const targetId = repairFlowTargetComponentId(targetFlow, targetState);
    if (targetId === entity.component_id) renderComponentGuidance(entity);
    else void selectEntity(targetId);
    return;
  }
  activeRepairFlowId = flow.flow_id;
  persistActiveRepairSession();
  renderRepairEntry();
  const target = repairFlowTargetComponentId(flow, next);
  if (target && target !== entity.component_id) {
    void selectEntity(target);
    return;
  }
  renderComponentGuidance(entity);
}

function configureResetConfirmation(button, disabled, onConfirm) {
  const priorTimer = confirmationTimers.get(button);
  if (priorTimer) window.clearTimeout(priorTimer);
  const disarm = () => {
    const timer = confirmationTimers.get(button);
    if (timer) window.clearTimeout(timer);
    confirmationTimers.delete(button);
    button.dataset.armed = 'false';
    button.textContent = '重新开始';
    button.setAttribute('aria-label', '重新开始当前排查');
  };
  disarm();
  button.disabled = disabled;
  button.onclick = () => {
    if (button.dataset.armed === 'true') {
      disarm();
      onConfirm();
      return;
    }
    button.dataset.armed = 'true';
    button.textContent = '确认重置';
    button.setAttribute('aria-label', '再次点击确认清空当前排查记录');
    confirmationTimers.set(button, window.setTimeout(disarm, 4000));
  };
  button.onkeydown = (event) => {
    if (event.key === 'Escape' && button.dataset.armed === 'true') {
      event.preventDefault();
      disarm();
    }
  };
}

function renderActiveFlowReturn(entity, flowActive) {
  const control = document.querySelector('#activeFlowReturn');
  const flow = data?.repair_flows?.find((candidate) => candidate.flow_id === activeRepairFlowId);
  const state = flow && repairFlowById.get(flow.flow_id);
  const targetId = state && repairFlowTargetComponentId(flow, state);
  const targetEntity = data?.entities.find((candidate) => candidate.component_id === targetId);
  const visible = Boolean(flow && state && targetEntity && !state.closed && !flowActive);
  control.hidden = !visible;
  if (!visible) return;
  document.querySelector('#activeFlowReturnTitle').textContent = flow.title;
  document.querySelector('#activeFlowReturnTarget').textContent = `返回 ${targetEntity.designator} · 保留当前进度`;
  document.querySelector('#resumeActiveFlow').onclick = () => {
    let targetGuidance = repairGuidanceByComponent.get(targetEntity.component_id);
    if (!targetGuidance) targetGuidance = createRepairGuidance(targetEntity);
    if (targetGuidance.faults.includes(flow.fault) && targetGuidance.selectedFault !== flow.fault) {
      targetGuidance = selectGuidanceFault(targetGuidance, flow.fault);
    }
    repairGuidanceByComponent.set(targetEntity.component_id, targetGuidance);
    if (targetEntity.component_id === entity.component_id) renderComponentGuidance(entity);
    else void selectEntity(targetEntity.component_id);
  };
}

function renderRepairFlow(entity, guidance) {
  const control = document.querySelector('#repairFlowControl');
  const flow = matchingRepairFlow(entity);
  document.querySelector('#guidanceProgress').hidden = Boolean(flow);
  control.hidden = !flow;
  document.querySelector('#resultControl').hidden = Boolean(flow);
  document.querySelector('#guidanceResultStatus').hidden = Boolean(flow);
  if (!flow) return false;

  let state = repairFlowById.get(flow.flow_id);
  if (!state) {
    state = createRepairFlowState(flow);
    repairFlowById.set(flow.flow_id, state);
  }
  const step = currentRepairFlowStep(flow, state);
  const progress = repairFlowProgress(flow, state);
  control.dataset.closed = String(state.closed);
  document.querySelector('#guidanceProgress').textContent = `${progress.current} / ${progress.total}`;
  document.querySelector('#inspectionStepLabel').textContent = '辅助资料';
  document.querySelector('#repairFlowTitle').textContent = flow.title;
  renderRepairSessionStatus();
  document.querySelector('#repairFlowStep').textContent = state.closed
    ? `已结束 · ${progress.current} / ${progress.total}`
    : `步骤 ${progress.current} / ${progress.total}`;
  document.querySelector('#repairFlowSource').textContent = flow.source.label
    || `${flow.source.source} · 第 ${flow.source.page} 页`;
  const targetId = repairFlowTargetComponentId(flow, state);
  const targetEntity = data.entities.find((candidate) => candidate.component_id === targetId);
  const targetDisplay = targetEntity && technicianEntityCopy(targetEntity);
  const targetSideLabel = targetEntity && (sideDataById.get(targetEntity.side_id)?.label || targetEntity.side_id);
  document.querySelector('#repairFlowTarget').textContent = targetEntity?.designator || '当前结果';
  document.querySelector('#repairFlowTargetMeta').textContent = targetEntity
    ? `${targetDisplay.name} · ${targetSideLabel}`
    : '';

  const trail = document.querySelector('#repairFlowTrail');
  trail.replaceChildren();
  repairFlowTrail(flow, state).forEach((item, index) => {
    const node = document.createElement('li');
    const marker = document.createElement('span');
    const label = document.createElement('strong');
    const sourceStep = flow.steps.find((candidate) => candidate.step_id === item.stepId);
    node.dataset.status = item.status;
    node.title = sourceStep?.prompt || item.label;
    if (item.status === 'current') node.setAttribute('aria-current', 'step');
    marker.textContent = String(index + 1);
    label.textContent = item.label;
    node.append(marker, label);
    trail.append(node);
  });

  const prompt = document.querySelector('#repairFlowPrompt');
  const choices = document.querySelector('#repairFlowChoices');
  const terminal = document.querySelector('#repairFlowTerminal');
  const measurementControl = document.querySelector('#repairFlowMeasurements');
  const measurementFields = document.querySelector('#repairFlowMeasurementFields');
  choices.replaceChildren();
  measurementFields.replaceChildren();
  prompt.hidden = !step;
  choices.hidden = !step;
  terminal.hidden = !state.terminal;
  measurementControl.hidden = !step?.measurements?.length;
  if (step) {
    prompt.textContent = step.prompt;
    const existingMeasurements = state.measurements?.[step.step_id] || {};
    (step.measurements || []).forEach((measurement) => {
      const row = document.createElement('div');
      row.className = 'repair-flow-measurement';
      const label = document.createElement('label');
      const reference = document.createElement('small');
      const input = document.createElement('input');
      const unit = document.createElement('span');
      input.type = 'number';
      input.inputMode = 'decimal';
      input.required = measurement.required !== false;
      input.step = String(measurement.input_step || 'any');
      input.dataset.flowMeasurement = measurement.measurement_id;
      input.id = `flow-measurement-${measurement.measurement_id}`;
      input.value = existingMeasurements[measurement.measurement_id] ?? '';
      label.htmlFor = input.id;
      label.append(document.createTextNode(measurement.label), reference);
      reference.textContent = measurementReferenceCopy(measurement);
      unit.textContent = measurement.unit;
      input.addEventListener('input', () => {
        measurementStatus.dataset.complete = 'false';
        measurementStatus.textContent = '输入已修改，请重新记录本步测量后再选择结果。';
        choices.hidden = true;
      });
      row.append(label, input, unit);
      measurementFields.append(row);
    });
    const measurementsComplete = repairFlowMeasurementsComplete(flow, state);
    const measurementAssessment = repairFlowMeasurementAssessment(flow, state);
    const choiceOptions = buildRepairFlowChoiceOptions(flow, state);
    choices.hidden = !step || !choiceOptions.length;
    choices.dataset.mode = measurementAssessment ? 'confirmed-range' : 'technician-choice';
    const measurementStatus = document.querySelector('#repairFlowMeasurementStatus');
    measurementStatus.dataset.complete = String(measurementsComplete);
    measurementStatus.dataset.assessment = measurementAssessment?.result || 'unassessed';
    measurementStatus.textContent = !measurementsComplete
      ? `需记录本步 ${step.measurements?.filter((measurement) => measurement.required !== false).length || 0} 项测量后再选择结果。`
      : measurementAssessment?.result === 'within_range'
        ? `${measurementAssessment.values.join('、')} 位于资料范围内；确认后继续。`
        : measurementAssessment?.result === 'outside_range'
          ? `${measurementAssessment.values.join('、')} 位于资料范围外；确认后继续。`
          : '本步测量已记录。资料未提供容差，请依据来源判断正常或异常。';
    document.querySelector('#repairFlowRecordMeasurements').onclick = () => {
      let next = repairFlowById.get(flow.flow_id);
      const inputs = [...measurementFields.querySelectorAll('[data-flow-measurement]')];
      if (inputs.some((input) => !input.reportValidity())) return;
      inputs.forEach((input) => {
        next = recordRepairFlowMeasurement(flow, next, input.dataset.flowMeasurement, input.value);
      });
      applyRepairFlowState(flow, next, entity);
    };
    choiceOptions.forEach((choice) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = choice.label;
      button.dataset.confirmedByRange = String(choice.confirmedByRange);
      button.addEventListener('click', () => {
        const next = answerRepairFlow(flow, repairFlowById.get(flow.flow_id), choice.value);
        applyRepairFlowState(flow, next, entity);
      });
      choices.append(button);
    });
  }
  if (state.terminal) {
    terminal.dataset.kind = state.terminal.kind;
    document.querySelector('#repairFlowTerminalType').textContent = state.terminal.kind === 'boundary' ? '资料边界' : '维修处理';
    document.querySelector('#repairFlowTerminalLabel').textContent = state.terminal.label;
    const boundary = document.querySelector('#repairFlowBoundary');
    boundary.hidden = state.terminal.kind !== 'boundary';
    boundary.textContent = state.terminal.kind === 'boundary' ? flow.boundary_note : '';
  }
  const actionRecord = document.querySelector('#repairFlowActionRecord');
  const actionRecordVisible = state.terminal?.kind === 'action';
  const actionExecuted = state.actionExecution === 'executed';
  actionRecord.hidden = !actionRecordVisible;
  actionRecord.dataset.executed = String(actionExecuted);
  const actionButton = document.querySelector('#recordRepairFlowAction');
  actionButton.setAttribute('aria-pressed', String(actionExecuted));
  actionButton.disabled = state.closed;
  actionButton.textContent = state.closed
    ? '已记录执行'
    : (actionExecuted ? '撤销执行记录' : '记录已执行');
  actionButton.title = state.closed ? '本次排查已结束，执行记录为只读' : '';
  document.querySelector('#repairFlowActionStatus').textContent = actionExecuted
    ? '已记录：维修处理已执行；维修结果仍需复检确认。'
    : '尚未记录维修处理是否已执行。';
  actionButton.onclick = () => {
    const next = setRepairFlowActionExecuted(repairFlowById.get(flow.flow_id), !actionExecuted);
    applyRepairFlowState(flow, next, entity);
  };
  const recheck = document.querySelector('#repairFlowRecheck');
  recheck.hidden = !actionExecuted;
  recheck.querySelectorAll('[data-post-action-check]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.postActionCheck === state.postActionCheck));
    button.disabled = state.closed;
    button.title = state.closed ? '本次排查已结束，复检记录为只读' : '';
    button.onclick = () => {
      const next = recordRepairFlowPostActionCheck(
        repairFlowById.get(flow.flow_id),
        button.dataset.postActionCheck,
      );
      applyRepairFlowState(flow, next, entity);
    };
  });
  const recheckStatus = document.querySelector('#repairFlowRecheckStatus');
  recheckStatus.dataset.result = state.postActionCheck || 'pending';
  recheckStatus.textContent = {
    pending: '尚未记录执行后的故障现象。',
    symptom_cleared: '已记录：故障现象消失；仍需完成最终质量确认。',
    symptom_persists: '已记录：故障现象仍存在；继续依据资料排查。',
    uncertain: '已记录：无法确认；请保留现场信息并复核。',
  }[state.postActionCheck || 'pending'];
  const completion = document.querySelector('#repairFlowCompletion');
  const completionButton = document.querySelector('#closeRepairFlow');
  const actionReady = state.actionExecution === 'executed'
    && state.postActionCheck
    && state.postActionCheck !== 'pending';
  const canClose = state.terminal?.kind === 'boundary' || actionReady;
  const completionStatus = document.querySelector('#repairFlowCompletionStatus');
  let readiness = 'blocked';
  let readinessCopy = '';
  if (state.closed) {
    readiness = 'closed';
    readinessCopy = '本次排查记录已结束；当前页面会话仍保留以上记录。';
  } else if (state.terminal?.kind === 'boundary') {
    readiness = 'ready';
    readinessCopy = '资料路径已到边界，可结束并保留当前记录。';
  } else if (state.terminal?.kind === 'action' && state.actionExecution !== 'executed') {
    readinessCopy = '先记录维修处理是否已执行。';
  } else if (state.terminal?.kind === 'action' && !actionReady) {
    readinessCopy = '记录执行后的故障现象后即可结束。';
  } else if (actionReady) {
    readiness = 'ready';
    readinessCopy = '执行与复检已记录，可结束本次排查。';
  }
  completion.hidden = !state.terminal;
  completion.dataset.closed = String(state.closed);
  completion.dataset.readiness = readiness;
  completionButton.disabled = !state.closed && !canClose;
  completionButton.textContent = state.closed ? '开始新一轮' : '结束本次排查';
  completionButton.title = !state.closed && !canClose ? '完成动作执行与复检记录后可结束本次排查' : '';
  completionStatus.textContent = readinessCopy;
  completionButton.onclick = () => {
    const next = state.closed ? resetRepairFlow(flow) : closeRepairFlow(repairFlowById.get(flow.flow_id));
    applyRepairFlowState(flow, next, entity, { restartSession: state.closed });
  };

  const history = document.querySelector('#repairFlowHistory');
  history.replaceChildren();
  state.history.forEach((entry) => {
    const historyStep = flow.steps.find((candidate) => candidate.step_id === entry.stepId);
    const historyChoice = historyStep?.choices.find((candidate) => candidate.value === entry.choice);
    const item = document.createElement('li');
    const label = document.createElement('span');
    const value = document.createElement('strong');
    label.textContent = historyStep?.prompt || entry.stepId;
    value.textContent = historyChoice?.label || entry.choice;
    item.append(label, value);
    history.append(item);
  });
  document.querySelector('#repairFlowLog').hidden = !state.history.length;
  const back = document.querySelector('#repairFlowBack');
  const reset = document.querySelector('#repairFlowReset');
  document.querySelector('#repairFlowNavigation').hidden = state.closed;
  back.disabled = !state.history.length;
  back.onclick = () => {
    applyRepairFlowState(flow, backRepairFlow(flow, repairFlowById.get(flow.flow_id)), entity);
  };
  configureResetConfirmation(reset, !state.history.length, () => {
    applyRepairFlowState(flow, resetRepairFlow(flow), entity, { restartSession: true });
  });
  return true;
}

function updateInspectionUi() {
  const entity = data?.entities.find((candidate) => candidate.component_id === selectedId);
  const active = componentInspection.mode === 'isolated';
  const action = buildInspectionActionState({
    active,
    inspectable: canInspectComponent(entity),
    ready: canAcceptModelInteraction(modelInteraction),
  });
  const button = document.querySelector('#inspectComponent');
  button.disabled = action.disabled;
  button.hidden = action.hidden;
  button.textContent = action.label;
  button.setAttribute('aria-pressed', String(active));
  button.title = action.title;
  const status = document.querySelector('#inspectionStatus');
  status.hidden = !active;
  status.disabled = !active || !canAcceptModelInteraction(modelInteraction);
  status.setAttribute('aria-label', `返回主板：${entity?.designator || '当前器件'}`);
  document.querySelector('#inspectionDesignator').textContent = entity?.designator || '—';
  document.querySelector('#modelView').classList.toggle('inspection-active', active);
  document.querySelector('#toggleInspection').disabled = active || !canAcceptModelInteraction(modelInteraction);
  const toolbar = buildInspectionToolbarState({
    active,
    ready: canAcceptModelInteraction(modelInteraction),
    boardMode: modelDragMode,
  });
  document.querySelector('.anatomy-panel').hidden = toolbar.boardControlsHidden;
  document.querySelector('.side-panel').hidden = toolbar.boardControlsHidden;
  document.querySelector('[data-model-drag-mode="pan"]').hidden = toolbar.panHidden;
  document.querySelector('#toggleInspection').hidden = toolbar.inspectionAngleHidden;
  document.querySelectorAll('[data-model-drag-mode]').forEach((control) => {
    const pan = control.dataset.modelDragMode === 'pan';
    control.disabled = pan ? toolbar.panDisabled : toolbar.rotateDisabled;
    control.setAttribute('aria-pressed', String(pan ? toolbar.panPressed : toolbar.rotatePressed));
  });
  const reset = document.querySelector('#resetModel');
  reset.title = toolbar.resetLabel;
  reset.setAttribute('aria-label', toolbar.resetLabel);
  document.querySelectorAll('[data-shield-mode]').forEach((control) => {
    const sideHasShields = Boolean(sideDataById.get(activeSideId)?.anatomy.shields.length);
    control.disabled = active || !sideHasShields || !canAcceptModelInteraction(modelInteraction);
  });
  if (active) updateSourceNote(entity);
}

function syncInspectionAngleControl(enabled) {
  const button = document.querySelector('#toggleInspection');
  const label = enabled ? '恢复俯视' : '切换为斜视';
  button.setAttribute('aria-pressed', String(enabled));
  button.setAttribute('aria-label', label);
  button.title = label;
}

function setModelDragMode(mode) {
  if (!canAcceptModelInteraction(modelInteraction)) return modelDragMode;
  if (componentInspection.mode === 'isolated') {
    if (mode === 'rotate') renderer?.focusInteractionSurface();
    return modelDragMode;
  }
  modelDragMode = resolveBoardInteractionMode(mode);
  renderer?.setInteractionMode(modelDragMode);
  document.querySelectorAll('[data-model-drag-mode]').forEach((control) => {
    control.setAttribute('aria-pressed', String(control.dataset.modelDragMode === modelDragMode));
  });
  return modelDragMode;
}

function updateModelControlState() {
  const transitionLocked = !canAcceptModelInteraction(modelInteraction);
  const locked = transitionLocked || modelAssetStatus === 'loading';
  const modelView = document.querySelector('#modelView');
  modelView.dataset.modelBusy = String(locked);
  modelView.setAttribute('aria-busy', String(locked));
  renderer?.setInteractionLocked(locked);
  document.querySelectorAll('[role=tab]').forEach((control) => {
    control.disabled = transitionLocked;
  });
  document.querySelectorAll('[data-side-id], #resetModel, #entityList button').forEach((control) => {
    control.disabled = locked;
  });
  updateSideControls();
  updateInspectionUi();
}

function updateModelAssetStatus(state) {
  modelAssetStatus = state.status;
  const status = document.querySelector('#modelLoadStatus');
  status.hidden = state.status === 'ready';
  status.dataset.tone = state.status;
  status.textContent = state.status === 'error' ? '工程底图载入失败' : '正在准备主板模型';
  updateModelControlState();
}

function startModelTransition(phase) {
  const next = beginModelTransition(modelInteraction, phase);
  if (next === modelInteraction) return null;
  modelInteraction = next;
  updateModelControlState();
  return next.transitionId;
}

function finishModelTransition(transitionId) {
  modelInteraction = completeModelTransition(modelInteraction, transitionId);
  updateModelControlState();
}

async function leaveComponentInspection(animate = true) {
  if (componentInspection.mode !== 'isolated') return false;
  const transitionId = startModelTransition('inspection');
  if (transitionId === null) return false;
  try {
    const cleared = await renderer.clearComponentInspection(animate);
    if (!cleared) return false;
    componentInspection = exitComponentInspection(componentInspection);
    return true;
  } finally {
    finishModelTransition(transitionId);
  }
}

async function enterCurrentComponentInspection(entity) {
  const next = enterComponentInspection(entity, activeSideId);
  if (next.mode !== 'isolated') return false;
  const transitionId = startModelTransition('inspection');
  if (transitionId === null) return false;
  try {
    const entered = await renderer.setComponentInspection(next.componentId);
    componentInspection = entered ? next : exitComponentInspection();
    return entered;
  } finally {
    finishModelTransition(transitionId);
  }
}

async function enterSelectedComponentInspection() {
  if (!canAcceptModelInteraction(modelInteraction)) return false;
  const entity = data?.entities.find((candidate) => candidate.component_id === selectedId);
  const intent = buildInspectionEntryIntent(entity, activeView, activeSideId);
  if (!intent) return false;
  if (intent.changeView) await setView('model');
  if (intent.changeSide) await switchModelSide(intent.sideId);
  if (!canAcceptModelInteraction(modelInteraction)) return false;
  modelInteraction = consumePendingFocus(modelInteraction);
  const entered = await enterCurrentComponentInspection(entity);
  if (entered) revealModelWorkspace();
  return entered;
}

async function toggleComponentInspection() {
  if (!canAcceptModelInteraction(modelInteraction)) return;
  if (componentInspection.mode === 'isolated') {
    await leaveComponentInspection();
    return;
  }
  await enterSelectedComponentInspection();
}

function updateSideControls() {
  const locked = !canAcceptModelInteraction(modelInteraction);
  document.querySelectorAll('[data-side-id]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.sideId === activeSideId));
    button.disabled = locked;
  });
  const sideData = sideDataById.get(activeSideId);
  document.querySelector('#activeSideLabel').textContent = sideData?.label || activeSideId;
  const shieldsAvailable = Boolean(sideData?.anatomy.shields.length);
  document.querySelectorAll('[data-shield-mode]').forEach((button) => {
    button.disabled = locked || componentInspection.mode === 'isolated' || !shieldsAvailable;
  });
  document.querySelector('#entityListHeading').textContent = '已关联维修实体';
  const selectedEntity = data?.entities.find((entity) => entity.component_id === selectedId);
  updateEntityAccessStatus(selectedEntity);
  renderPhysicalRegistration();
  if (activeView === 'model' && sideData) {
    updateSourceNote();
  }
}

function applyRepairTarget(animate = true) {
  if (!renderer || !currentRepairTarget || currentRepairTarget.sideId !== activeSideId) return;
  renderer.setRepairFocus(moduleOverlayId(currentRepairTarget), currentRepairTarget.focusRegion, animate);
}

async function switchModelSide(sideId, animate = true) {
  if (!canAcceptModelInteraction(modelInteraction) || sideId === activeSideId || !sideDataById.has(sideId)) return activeSideId;
  const transitionId = startModelTransition('side');
  if (transitionId === null) return activeSideId;
  try {
    if (componentInspection.mode === 'isolated') {
      const cleared = await renderer.clearComponentInspection(false);
      if (!cleared) return activeSideId;
      componentInspection = exitComponentInspection(componentInspection);
    }
    await renderer.setSideData(sideDataById.get(sideId), animate);
    activeSideId = sideId;
    if (currentRepairTarget?.sideId === activeSideId) {
      renderer.select(selectedId);
      applyRepairTarget();
    } else {
      renderer.setModuleFocus(null);
      renderer.clearRepairFocus(false);
    }
    syncBoardViews();
    return activeSideId;
  } finally {
    finishModelTransition(transitionId);
  }
}

function activateRepairTarget() {
  if (!currentRepairTarget || activeView !== 'model') return;
  if (currentRepairTarget.recommendedSideId !== activeSideId) {
    void switchModelSide(currentRepairTarget.recommendedSideId);
  } else {
    applyRepairTarget();
  }
}

function addMarkers(layer, positions, entities) {
  const fragment = document.createDocumentFragment();
  entities.forEach((entity) => {
    const display = technicianEntityCopy(entity);
    const point = positions.get(entity.component_id);
    if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) return;
    const button = document.createElement('button');
    button.className = 'marker';
    button.classList.toggle('selected', entity.component_id === selectedId);
    button.type = 'button';
    button.dataset.componentId = entity.component_id;
    button.style.left = `${point.x * 100}%`;
    button.style.top = `${point.y * 100}%`;
    const dot = document.createElement('span');
    dot.className = 'marker-dot';
    dot.setAttribute('aria-hidden', 'true');
    const label = document.createElement('span');
    label.className = 'marker-label';
    label.textContent = entity.designator;
    label.setAttribute('aria-hidden', 'true');
    button.append(dot, label);
    button.title = `${entity.designator} · ${display.name}`;
    button.setAttribute('aria-label', `选择 ${entity.designator} ${display.name}`);
    button.addEventListener('click', (event) => {
      let componentId = entity.component_id;
      if (event.detail > 0) {
        const targets = [...layer.querySelectorAll('.marker')].map((marker) => {
          const bounds = marker.getBoundingClientRect();
          return {
            id: marker.dataset.componentId,
            center: { x: bounds.left + bounds.width / 2, y: bounds.top + bounds.height / 2 },
          };
        });
        componentId = nearestPointerTarget(targets, { x: event.clientX, y: event.clientY });
      }
      if (componentId) void selectEntity(componentId);
    });
    fragment.append(button);
  });
  layer.append(fragment);
}

function legacyPhotoState(registration, sideId) {
  const { proxy_image: assetPath, proxy_note: boundaryCopy, anchors = [] } = registration;
  if (!assetPath || sideId !== data.side_id || anchors.length < 4) return null;
  const source = anchors.slice(0, 4).map((anchor) => anchor.board);
  const target = anchors.slice(0, 4).map((anchor) => anchor.image);
  return {
    available: true,
    items: [{ photoId: 'legacy-photo-proxy', label: '主板实物参考' }],
    selectorVisible: false,
    activePhoto: { photo_id: 'legacy-photo-proxy', label: '主板实物参考' },
    assetPath,
    matrix: solveHomography(source, target),
    sourceAnnotationPresent: false,
    boundaryCopy: boundaryCopy || registration.point_map_note,
  };
}

function renderPhotoSelector(state) {
  const control = document.querySelector('.photo-selector');
  const select = document.querySelector('#photoSelector');
  control.hidden = !state?.selectorVisible;
  select.replaceChildren();
  (state?.items || []).forEach((item) => {
    const option = document.createElement('option');
    option.value = item.photoId;
    option.textContent = item.label;
    option.selected = item.photoId === state.activePhoto?.photo_id;
    select.append(option);
  });
}

function focusSelectedImageEntity() {
  if (!technicianSelectionActive) return;
  const entity = data?.entities.find((candidate) => candidate.component_id === selectedId);
  if (!entity || entity.side_id !== activeSideId) return;
  const state = buildSelectionState(entity, matrix);
  if (activeView === 'photo' && state.photoPoint) photoViewport?.focus(state.photoPoint);
  if (activeView === 'pointmap') pointMapViewport?.focus(state.boardPoint);
}

function syncBoardViews() {
  const sideData = sideDataById.get(activeSideId);
  if (!sideData) return;
  const photoImage = document.querySelector('#photoView img');
  const pointMapImage = document.querySelector('#pointmapView img');
  const photoMarkers = document.querySelector('#photoView .markers');
  const pointMapMarkers = document.querySelector('#pointmapView .markers');
  const status = document.querySelector('#photoLoadStatus');
  const preferredPhotoId = preferredPhotoBySide.get(activeSideId) || null;
  photoState = buildPhotoNavigationState({
    registration: data.registration,
    sideId: activeSideId,
    preferredPhotoId,
  });
  if (!photoState.available) photoState = legacyPhotoState(data.registration, activeSideId) || photoState;
  matrix = photoState.available ? photoState.matrix : null;

  pointMapMarkers.replaceChildren();
  const boardPositions = new Map(
    sideData.entities.map((entity) => [entity.component_id, entity.geometry.center]),
  );
  addMarkers(pointMapMarkers, boardPositions, sideData.entities);
  pointMapImage.alt = `${data.board_version} ${sideData.label}点位图`;
  if (pointMapImage.getAttribute('src') !== sideData.engineeringTextureUrl) {
    pointMapImage.src = sideData.engineeringTextureUrl;
    pointMapViewport?.replaceImage(activeSideId);
  }

  photoMarkers.replaceChildren();
  renderPhotoSelector(photoState);
  status.hidden = photoState.available;
  if (!photoState.available) {
    photoImage.removeAttribute('src');
    photoImage.hidden = true;
    status.textContent = photoState.boundaryCopy;
  } else {
    preferredPhotoBySide.set(activeSideId, photoState.activePhoto.photo_id);
    photoImage.hidden = false;
    photoImage.alt = `${data.model} ${sideData.label}${photoState.activePhoto.label}`;
    const nextSource = `../../${photoState.assetPath}`;
    if (photoImage.getAttribute('src') !== nextSource) photoImage.src = nextSource;
    photoViewport.replaceImage(photoState.activePhoto.photo_id);
    const photoPositions = new Map(sideData.entities.map((entity) => [
      entity.component_id,
      buildSelectionState(entity, matrix).photoPoint,
    ]));
    addMarkers(photoMarkers, photoPositions, sideData.entities);
  }
  document.querySelector('#photoTools').hidden = activeView !== 'photo' || !photoState.available;
  updateSourceNote();
}

function failPhotoViewClosed() {
  photoState = failPhotoNavigation(photoState);
  matrix = null;
  const photoImage = document.querySelector('#photoView img');
  photoImage.removeAttribute('src');
  photoImage.hidden = true;
  document.querySelector('#photoView .markers').replaceChildren();
  renderPhotoSelector(photoState);
  photoViewport?.replaceImage(null);
  document.querySelector('#photoTools').hidden = true;
  const status = document.querySelector('#photoLoadStatus');
  status.hidden = false;
  status.textContent = photoState.boundaryCopy;
  updateSourceNote();
}

function evidenceCard(link, type) {
  const details = type === 'schematic' ? (link.facts || []).join(' · ') : link.instruction;
  const previews = (link.previews || []).map((preview) => `
    <button class="schematic-preview" type="button" data-preview-src="../../${preview.source}" data-preview-label="第 ${preview.page} 页" aria-label="查看第 ${preview.page} 页原理图局部图">
      <img src="../../${preview.source}" alt="第 ${preview.page} 页原理图局部图" loading="lazy">
    </button>`).join('');
  return `<article class="evidence-card">${details}${previews}<small>${link.source} · ${link.page}</small></article>`;
}

function evidenceCountCopy(count) {
  return `${count} 组资料`;
}

function renderComponentGuidance(entity) {
  const guidanceRoot = document.querySelector('#componentGuidance');
  const evidenceRoot = document.querySelector('.evidence');
  if (pilotIntent?.valid && pilotIntent.boundaryOnly) {
    guidanceRoot.hidden = true;
    guidanceRoot.dataset.repairFlowActive = 'false';
    evidenceRoot.dataset.repairFlowActive = 'false';
    renderActiveFlowReturn(entity, false);
    return;
  }
  let guidance = repairGuidanceByComponent.get(entity.component_id);
  if (!guidance) {
    guidance = createRepairGuidance(entity);
    repairGuidanceByComponent.set(entity.component_id, guidance);
  }
  guidanceRoot.hidden = !guidance.steps.length;
  guidanceRoot.dataset.repairFlowActive = 'false';
  evidenceRoot.dataset.repairFlowActive = 'false';
  if (!guidance.steps.length) {
    renderActiveFlowReturn(entity, false);
    return;
  }
  const faultList = document.querySelector('#commonFaults');
  const faultGroup = faultList.closest('.guidance-group');
  faultList.replaceChildren();
  guidance.faults.forEach((fault) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = FAULT_LABELS[fault] || fault;
    const activeFlow = data.repair_flows.find((flow) => flow.flow_id === activeRepairFlowId);
    const activeState = activeFlow && repairFlowById.get(activeFlow.flow_id);
    const activeTarget = activeFlow && repairFlowTargetComponentId(activeFlow, activeState || createRepairFlowState(activeFlow));
    const displayedFault = activeTarget === entity.component_id ? activeFlow.fault : guidance.selectedFault;
    button.setAttribute('aria-pressed', String(fault === displayedFault));
    button.addEventListener('click', () => {
      const next = selectGuidanceFault(repairGuidanceByComponent.get(entity.component_id), fault);
      repairGuidanceByComponent.set(entity.component_id, next);
      renderComponentGuidance(entity);
    });
    faultList.append(button);
  });
  const step = guidance.steps[0];
  const progress = guidanceProgress(guidance);
  document.querySelector('#guidanceProgress').textContent = `${progress.completed} / ${progress.total}`;
  document.querySelector('#inspectionStepLabel').textContent = `检测步骤 1 / ${progress.total}`;
  document.querySelector('#inspectionMethod').textContent = technicianInstruction(step.instruction);
  document.querySelector('#inspectionSource').textContent = `${step.source} · ${step.page}`;
  const repairFlowActive = renderRepairFlow(entity, guidance);
  guidanceRoot.dataset.repairFlowActive = String(repairFlowActive);
  evidenceRoot.dataset.repairFlowActive = String(repairFlowActive);
  const sourceSummary = document.querySelector('#componentSourceSummary');
  const sourceContext = repairFlowActive ? 'flow' : 'component';
  if (sourceSummary.dataset.context !== sourceContext) sourceSummary.open = !repairFlowActive;
  sourceSummary.dataset.context = repairFlowActive ? 'flow' : 'component';
  document.querySelector('#inspectionSummaryLabel').textContent = repairFlowActive ? '器件检测参考' : '检测指导';
  faultGroup.hidden = repairFlowActive;
  document.querySelector('#guidanceContextLabel').textContent = repairFlowActive ? '当前维修路径' : '器件资料';
  document.querySelector('#guidanceTitle').textContent = repairFlowActive ? '故障排查' : '检测参考';
  renderActiveFlowReturn(entity, repairFlowActive);
  const measurementControl = document.querySelector('#measurementControl');
  const profile = guidance.measurementProfile;
  measurementControl.hidden = repairFlowActive || !profile;
  if (profile) {
    document.querySelector('#measurementLabel').textContent = profile.label;
    document.querySelector('#measurementReference').textContent = measurementReferenceCopy(profile);
    document.querySelector('#measurementUnit').textContent = profile.unit;
    const measurementInput = document.querySelector('#guidanceMeasurementValue');
    measurementInput.step = String(profile.input_step || 'any');
    measurementInput.value = guidance.measurement.value ?? '';
    const measurementFeedback = document.querySelector('#measurementFeedback');
    measurementFeedback.dataset.evaluation = guidance.measurement.evaluation;
    measurementFeedback.textContent = measurementFeedbackCopy(guidance);
  }
  document.querySelectorAll('[data-guidance-result]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.guidanceResult === guidance.result));
  });
  const resultStatus = document.querySelector('#guidanceResultStatus');
  resultStatus.dataset.result = guidance.result;
  resultStatus.textContent = guidanceResultCopy(guidance);
  const boundary = entity.inspection_profile?.visual_note || '';
  document.querySelector('#modelBoundaryDetails').hidden = !boundary;
  document.querySelector('#modelBoundary').textContent = boundary;
}

async function selectEntity(componentId, options = {}) {
  if (!canAcceptModelInteraction(modelInteraction)) return false;
  const entity = data.entities.find((item) => item.component_id === componentId);
  if (!entity) return false;
  if (componentInspection.mode === 'isolated') {
    const leftInspection = await leaveComponentInspection(false);
    if (!leftInspection) return false;
  }
  if (!canAcceptModelInteraction(modelInteraction)) return false;
  if (entity.side_id !== activeSideId) {
    const switchedSide = await switchModelSide(entity.side_id, activeView === 'model');
    if (switchedSide !== entity.side_id) return false;
  }
  if (!canAcceptModelInteraction(modelInteraction)) return false;
  modelInteraction = recordSelectionIntent(modelInteraction, options.explicit !== false);
  selectedId = componentId;
  technicianSelectionActive = options.explicit !== false;
  const state = buildSelectionState(entity, matrix);
  const shouldFocusImage = options.focus !== false && options.explicit !== false;
  const display = technicianEntityCopy(entity);
  document.querySelectorAll('[data-component-id]').forEach((node) => node.classList.toggle('selected', node.dataset.componentId === componentId));
  document.querySelector('#entityCategory').textContent = display.category;
  document.querySelector('#entityDesignator').textContent = entity.designator;
  document.querySelector('#entityName').textContent = display.name;
  document.querySelector('#entityModule').textContent = display.module;
  document.querySelector('#entitySide').textContent = sideDataById.get(entity.side_id)?.label || entity.side_id;
  document.querySelector('#schematicEvidenceCount').textContent = evidenceCountCopy(entity.schematic_links.length);
  document.querySelector('#repairEvidenceCount').textContent = evidenceCountCopy(entity.repair_links.length);
  document.querySelector('#schematicEvidenceDetails').hidden = !entity.schematic_links.length;
  document.querySelector('#repairEvidenceDetails').hidden = !entity.repair_links.length;
  document.querySelector('#schematicEvidence').innerHTML = entity.schematic_links.map((link) => evidenceCard(link, 'schematic')).join('');
  document.querySelector('#repairEvidence').innerHTML = entity.repair_links.map((link) => evidenceCard(link, 'repair')).join('');
  renderComponentGuidance(entity);
  if (options.explicit !== false) document.querySelector('.evidence').scrollTo({ top: 0, behavior: 'auto' });
  renderer.select(componentId);
  const targetModules = sideDataById.get(entity.side_id)?.anatomy.modules || [];
  currentRepairTarget = buildEntityTarget(data.board_id, entity, targetModules);
  updateSideControls();
  if (options.focus === false && activeView === 'model') renderer.clearRepairEmphasis();
  else activateRepairTarget();
  if (activeView === 'model') modelInteraction = consumePendingFocus(modelInteraction);
  if (shouldFocusImage && activeView === 'pointmap' && pointMapViewport) pointMapViewport.focus(state.boardPoint);
  if (shouldFocusImage && activeView === 'photo' && photoViewport && state.photoPoint) photoViewport.focus(state.photoPoint);
  updateInspectionUi();
  return true;
}

async function handleModelComponentActivation(componentId) {
  const entity = data?.entities.find((candidate) => candidate.component_id === componentId);
  const action = resolveModelComponentActivation(
    entity,
    selectedId,
    canAcceptModelInteraction(modelInteraction),
  );
  if (action === 'inspect') {
    await enterSelectedComponentInspection();
    return;
  }
  if (action === 'select') await selectEntity(componentId, { focus: false });
}

async function setView(name) {
  if (!canAcceptModelInteraction(modelInteraction)) return false;
  if (name !== 'model' && componentInspection.mode === 'isolated') {
    const leftInspection = await leaveComponentInspection(false);
    if (!leftInspection) return false;
  }
  activeView = name;
  document.querySelectorAll('[role=tab]').forEach((button) => button.setAttribute('aria-selected', String(button.dataset.view === name)));
  Object.entries(views).forEach(([key, view]) => view.classList.toggle('active', key === name));
  document.querySelector('#pointMapTools').hidden = name !== 'pointmap';
  document.querySelector('#photoTools').hidden = name !== 'photo' || !photoState?.available;
  document.querySelector('#modelTools').hidden = name !== 'model';
  if (name === 'model') {
    syncInspectionAngleControl(false);
    await new Promise((resolve) => {
      requestAnimationFrame(() => {
        renderer.reset(false);
        renderer.resize();
        if (modelInteraction.pendingFocus && currentRepairTarget?.sideId === activeSideId) {
          applyRepairTarget();
          modelInteraction = consumePendingFocus(modelInteraction);
        }
        resolve();
      });
    });
  }
  if (name === 'pointmap') requestAnimationFrame(() => pointMapViewport?.reset());
  if (name === 'photo') requestAnimationFrame(() => photoViewport?.resize());
  updateSideControls();
  updateSourceNote();
  updateInspectionUi();
  return true;
}

async function init() {
  const catalogResponse = await fetch(BOARD_CATALOG_URL);
  if (!catalogResponse.ok) throw new Error(`主板目录载入失败 (${catalogResponse.status})`);
  const catalog = await catalogResponse.json();
  const currentUrl = new URL(window.location.href);
  const boardKey = resolveBoardKey(new URL(window.location.href), catalog);
  const boardAssets = resolveBoardAssets(catalog, boardKey);
  activeBoardKey = boardKey;
  const fetchAsset = async (label, url) => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${boardKey} ${label}载入失败 (${response.status})`);
    return response.json();
  };
  const geometryEntries = Object.entries(boardAssets.geometry_by_side);
  const [boardData, schematicData, sideManifest, geometryValues, shieldData, atlasData] = await Promise.all([
    fetchAsset('维修数据', boardAssets.data),
    fetchAsset('原理图数据', boardAssets.schematic),
    fetchAsset('板面清单', boardAssets.side_manifest),
    Promise.all(geometryEntries.map(([sideId, url]) => fetchAsset(`${sideId} 几何数据`, url))),
    boardAssets.shield ? fetchAsset('屏蔽罩数据', boardAssets.shield) : Promise.resolve({ regions: [] }),
    boardAssets.atlas ? fetchAsset('模块数据', boardAssets.atlas) : Promise.resolve({ boards: [] }),
  ]);
  data = boardData;
  pilotIntent = resolvePilotIntent({
    boardKey,
    board: boardAssets,
    dataset: data,
    query: currentUrl.searchParams,
  });
  if (!pilotIntent.valid && !pilotIntent.legacy) {
    throw new Error(`内测入口参数与资料不一致 (${pilotIntent.reason})`);
  }
  if (pilotIntent.valid && pilotIntent.kind === 'case_symptom') {
    selectedCaseSymptomKey = pilotIntent.symptomKey;
  }
  const registrationView = buildRegistrationViewState(data.registration);
  activeView = registrationView.initialView;
  const photoTab = document.querySelector('[data-view="photo"]');
  photoTab.hidden = !registrationView.photoAvailable;
  document.querySelectorAll('[role=tab]').forEach((button) => {
    button.setAttribute('aria-selected', String(button.dataset.view === activeView));
  });
  Object.entries(views).forEach(([key, view]) => view.classList.toggle('active', key === activeView));
  document.querySelector('#pointMapTools').hidden = activeView !== 'pointmap';
  document.querySelector('#modelTools').hidden = activeView !== 'model';
  const geometryBySide = new Map(geometryEntries.map(([sideId], index) => [sideId, geometryValues[index]]));
  geometryData = geometryBySide.get(sideManifest.default_side_id);
  if (!geometryData) throw new Error(`${boardKey} 缺少默认板面 ${sideManifest.default_side_id} 的几何数据`);
  const compiledBySide = new Map([...geometryBySide].map(([sideId, compiled]) => [
    sideId,
    new Map(compiled.components.map((component) => [component.designator, component])),
  ]));
  data.entities = data.entities.map((originalEntity) => {
    const entity = {
      ...mergeCompiledSchematicLinks(originalEntity, schematicData),
      side_id: originalEntity.side_id || data.side_id,
    };
    const compiled = compiledBySide.get(entity.side_id)?.get(entity.designator);
    return mergeCompiledFootprint(entity, compiled);
  });
  sideDataById = new Map(sideManifest.sides.map((side) => {
    const compiled = geometryBySide.get(side.side_id);
    if (!compiled) throw new Error(`${boardKey} 缺少 ${side.side_id} 的几何数据`);
    return [side.side_id, {
      sideId: side.side_id,
      label: side.label,
      entities: data.entities.filter((entity) => entity.side_id === side.side_id),
      boardOutline: compiled.board_outline,
      compiledComponents: compiled.components,
      audit: compiled.audit,
      engineeringTextureUrl: `../../${side.engineering_texture}`,
      pointMapNote: `${data.board_version} · ${side.label}点位图`,
      anatomy: {
        shields: side.side_id === data.side_id ? extractShieldRegions(shieldData) : [],
        modules: extractModuleRegions(atlasData, side.side_id),
      },
    }];
  }));
  activeSideId = sideManifest.default_side_id;
  const sideButtons = [...document.querySelectorAll('[data-side-id]')];
  sideButtons.forEach((button, index) => {
    const side = sideManifest.sides[index];
    button.hidden = !side;
    if (!side) return;
    button.dataset.sideId = side.side_id;
    button.setAttribute('aria-label', side.label);
    button.textContent = side.label;
  });
  document.title = `${boardAssets.title} 维修工作台`;
  document.querySelector('#boardTitle').textContent = boardAssets.title;
  renderPilotIntentContext();
  const photoImage = document.querySelector('#photoView img');
  const pointMapImage = document.querySelector('#pointmapView img');
  photoViewport = new ImageViewport(
    document.querySelector('#photoView'),
    document.querySelector('#photoView .physical-photo'),
  );
  pointMapViewport = new PointMapViewport(document.querySelector('#pointmapView'), document.querySelector('#pointmapView .point-map'));
  photoImage.addEventListener('load', () => {
    document.querySelector('#photoLoadStatus').hidden = true;
    photoViewport.render();
    focusSelectedImageEntity();
  });
  photoImage.addEventListener('error', () => {
    failPhotoViewClosed();
  });
  pointMapImage.addEventListener('load', () => pointMapViewport.render());
  syncBoardViews();

  renderer = new BoardRenderer(
    document.querySelector('#modelCanvas'),
    sideDataById.get(activeSideId),
    handleModelComponentActivation,
    syncInspectionAngleControl,
    updateModelAssetStatus,
    () => { void toggleComponentInspection(); },
  );
  updateModelControlState();
  updateSideControls();
  updateSourceNote();
  const list = document.querySelector('#entityList');
  data.entities.forEach((entity) => {
    const display = technicianEntityCopy(entity);
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.componentId = entity.component_id;
    button.innerHTML = `<strong>${entity.designator}</strong>${display.module}`;
    button.addEventListener('click', async () => {
      const selected = await selectEntity(entity.component_id);
      if (selected) revealModelAfterEntityListSelection();
    });
    list.append(button);
  });
  renderRepairEntry();
  const initialEntity = data.entities.find((entity) => entity.side_id === activeSideId) || data.entities[0];
  await selectEntity(initialEntity.component_id, { explicit: false, focus: false });
  if (pilotIntent?.valid && pilotIntent.flowId) {
    await startRepairEntry(pilotIntent.flowId, { syncPilotIntent: false });
  }
}

document.querySelectorAll('[role=tab]').forEach((button) => button.addEventListener('click', () => { void setView(button.dataset.view); }));
document.querySelector('#resetModel').addEventListener('click', async () => {
  if (!canAcceptModelInteraction(modelInteraction)) return;
  if (componentInspection.mode === 'isolated') {
    const transitionId = startModelTransition('inspection');
    if (transitionId === null) return;
    try {
      await renderer?.resetComponentInspectionView();
    } finally {
      finishModelTransition(transitionId);
    }
    return;
  }
  modelInteraction = consumePendingFocus(modelInteraction);
  setModelDragMode('pan');
  renderer?.reset();
  syncInspectionAngleControl(false);
  updateInspectionUi();
});
document.querySelector('#inspectComponent').addEventListener('click', () => { void toggleComponentInspection(); });
document.querySelector('#inspectionStatus').addEventListener('click', () => { void toggleComponentInspection(); });
document.querySelectorAll('[data-guidance-result]').forEach((button) => button.addEventListener('click', () => {
  const entity = data?.entities.find((candidate) => candidate.component_id === selectedId);
  if (!entity) return;
  const current = repairGuidanceByComponent.get(entity.component_id) || createRepairGuidance(entity);
  const next = recordGuidanceResult(current, button.dataset.guidanceResult);
  repairGuidanceByComponent.set(entity.component_id, next);
  renderComponentGuidance(entity);
}));
document.querySelector('#recordMeasurement').addEventListener('click', () => {
  const entity = data?.entities.find((candidate) => candidate.component_id === selectedId);
  const input = document.querySelector('#guidanceMeasurementValue');
  if (!entity || !input.reportValidity()) return;
  const current = repairGuidanceByComponent.get(entity.component_id) || createRepairGuidance(entity);
  const next = recordGuidanceMeasurement(current, input.value);
  repairGuidanceByComponent.set(entity.component_id, next);
  renderComponentGuidance(entity);
});
document.querySelector('#toggleInspection').addEventListener('click', async (event) => {
  if (!canAcceptModelInteraction(modelInteraction)) return;
  const enabled = event.currentTarget.getAttribute('aria-pressed') !== 'true';
  const transitionId = startModelTransition('angle');
  if (transitionId === null) return;
  try {
    await renderer?.setInspectionAngle(enabled);
  } finally {
    finishModelTransition(transitionId);
  }
});
document.querySelectorAll('[data-model-drag-mode]').forEach((button) => button.addEventListener('click', () => {
  setModelDragMode(button.dataset.modelDragMode);
}));
document.querySelectorAll('[data-shield-mode]').forEach((button) => button.addEventListener('click', () => {
  document.querySelectorAll('[data-shield-mode]').forEach((candidate) => candidate.setAttribute('aria-pressed', String(candidate === button)));
  renderer?.setShieldMode(button.dataset.shieldMode);
}));
document.querySelectorAll('[data-side-id]').forEach((button) => button.addEventListener('click', () => {
  void switchModelSide(button.dataset.sideId);
}));
document.querySelector('#zoomOutPointMap').addEventListener('click', () => pointMapViewport?.zoomBy(0.8));
document.querySelector('#zoomInPointMap').addEventListener('click', () => pointMapViewport?.zoomBy(1.25));
document.querySelector('#resetPointMap').addEventListener('click', () => pointMapViewport?.reset());
document.querySelector('#zoomOutPhoto').addEventListener('click', () => photoViewport?.zoomBy(0.8));
document.querySelector('#zoomInPhoto').addEventListener('click', () => photoViewport?.zoomBy(1.25));
document.querySelector('#resetPhoto').addEventListener('click', () => photoViewport?.reset());
document.querySelector('#photoSelector').addEventListener('change', (event) => {
  preferredPhotoBySide.set(activeSideId, event.currentTarget.value);
  syncBoardViews();
});
document.querySelectorAll('[data-feedback-target]').forEach((button) => button.addEventListener('click', () => {
  pilotFeedbackTarget = button.dataset.feedbackTarget;
  setExclusiveFeedback('[data-feedback-target]', pilotFeedbackTarget);
}));
document.querySelectorAll('[data-feedback-usefulness]').forEach((button) => button.addEventListener('click', () => {
  pilotFeedbackUsefulness = button.dataset.feedbackUsefulness;
  setExclusiveFeedback('[data-feedback-usefulness]', pilotFeedbackUsefulness);
}));
document.querySelector('#savePilotFeedback').addEventListener('click', recordPilotFeedback);
document.querySelector('#exportPilotFeedback').addEventListener('click', exportPilotFeedback);
document.querySelector('#exportRepairSession').addEventListener('click', exportActiveRepairSession);
window.addEventListener('resize', () => {
  if (activeView === 'photo') photoViewport?.resize();
  if (activeView === 'pointmap') pointMapViewport?.resize();
});
document.querySelector('#modelTools').hidden = true;
const evidenceDialog = document.querySelector('#evidenceDialog');
document.querySelector('#schematicEvidence').addEventListener('click', (event) => {
  const trigger = event.target.closest('[data-preview-src]');
  if (!trigger) return;
  evidenceDialog.querySelector('img').src = trigger.dataset.previewSrc;
  evidenceDialog.querySelector('p').textContent = trigger.dataset.previewLabel;
  evidenceDialog.showModal();
});
evidenceDialog.querySelector('.dialog-close').addEventListener('click', () => evidenceDialog.close());
evidenceDialog.addEventListener('click', (event) => {
  if (event.target === evidenceDialog) evidenceDialog.close();
});
init().catch((error) => {
  document.querySelector('.stage').innerHTML = `<p class="load-error">无法载入跨资料数据：${error.message}</p>`;
  console.error(error);
});
