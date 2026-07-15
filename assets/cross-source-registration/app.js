import { solveHomography } from './registration-core.js';
import { buildSelectionState } from './selection-state.js';
import { BoardRenderer } from './board-renderer.js';
import { PointMapViewport } from './point-map-viewport.js';
import { mergeCompiledSchematicLinks } from './source-links.js';
import { extractModuleRegions, extractShieldRegions } from './anatomy-state.js';
import {
  buildEntityTarget,
  moduleOverlayId,
  nextSideId,
} from './repair-focus-state.js';
import {
  buildInspectionToolbarState,
  canInspectComponent,
  enterComponentInspection,
  exitComponentInspection,
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
  closeRepairFlow,
  createRepairFlowState,
  currentRepairFlowStep,
  recordRepairFlowPostActionCheck,
  recordRepairFlowMeasurement,
  repairFlowMeasurementsComplete,
  repairFlowProgress,
  repairFlowTargetComponentId,
  repairFlowTrail,
  resetRepairFlow,
  setRepairFlowActionExecuted,
} from './repair-flow-state.js';

const DATA_URL = '../../knowledge-base/km4-cross-source-registration.json';
const GEOMETRY_URL = '../../knowledge-base/km4-board-compiled.json';
const SCHEMATIC_URL = '../../knowledge-base/km4-schematic-compiled.json';
const SHIELD_URL = '../../knowledge-base/km4-point-map-geometry.json';
const ATLAS_URL = '../../knowledge-base/board-atlas-mvp.json';
const SIDE_MANIFEST_URL = '../../knowledge-base/km4-board-sides.json';
const PAGE_ONE_GEOMETRY_URL = '../../knowledge-base/km4-board-compiled-page-1.json';
const views = { photo: document.querySelector('#photoView'), pointmap: document.querySelector('#pointmapView'), model: document.querySelector('#modelView') };
let data;
let matrix;
let renderer;
let geometryData;
let selectedId;
let pointMapViewport;
let activeView = 'photo';
let currentRepairTarget;
let sideDataById = new Map();
let sideIds = [];
let activeSideId = 'main_page_2';
let componentInspection = exitComponentInspection();
let modelInteraction = createModelInteractionState();
let modelDragMode = 'pan';
const repairGuidanceByComponent = new Map();
const repairFlowById = new Map();
const confirmationTimers = new WeakMap();
let activeRepairFlowId = null;

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
};

const GUIDANCE_RESULT_COPY = {
  pending: '尚未返回检测结果。完成来源步骤后记录本次观察。',
  normal: '已记录正常。继续结合下方原理图与维修指导排查其他路径。',
  abnormal: '已记录异常。保留测量信息，并结合下方来源资料继续处理。',
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
      : '资料范围判断：本次测量值位于范围外；保留测量信息并继续来源步骤。';
  }
  return GUIDANCE_RESULT_COPY[guidance.result];
}

function matchingRepairFlow(entity, guidance) {
  const active = data?.repair_flows?.find((flow) => flow.flow_id === activeRepairFlowId);
  if (active && active.fault === guidance.selectedFault) {
    const state = repairFlowById.get(active.flow_id) || createRepairFlowState(active);
    const target = repairFlowTargetComponentId(active, state);
    if (target === entity.component_id) return active;
  }
  const entry = data?.repair_flows?.find((flow) => (
    flow.entry_component_id === entity.component_id && flow.fault === guidance.selectedFault
  )) || null;
  if (entry) activeRepairFlowId = entry.flow_id;
  return entry;
}

function applyRepairFlowState(flow, next, entity) {
  repairFlowById.set(flow.flow_id, next);
  activeRepairFlowId = flow.flow_id;
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
  const flow = matchingRepairFlow(entity, guidance);
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
  document.querySelector('#inspectionStepLabel').textContent = '来源摘要';
  document.querySelector('#repairFlowTitle').textContent = flow.title;
  document.querySelector('#repairFlowStep').textContent = state.closed
    ? `已结束 · ${progress.current} / ${progress.total}`
    : `步骤 ${progress.current} / ${progress.total}`;
  document.querySelector('#repairFlowSource').textContent = `${flow.source.source} · 第 ${flow.source.page} 页`;
  const targetId = repairFlowTargetComponentId(flow, state);
  const targetEntity = data.entities.find((candidate) => candidate.component_id === targetId);
  document.querySelector('#repairFlowTarget').textContent = targetEntity?.designator || '当前结果';

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
        choices.querySelectorAll('button').forEach((button) => { button.disabled = true; });
      });
      row.append(label, input, unit);
      measurementFields.append(row);
    });
    const measurementsComplete = repairFlowMeasurementsComplete(flow, state);
    const measurementStatus = document.querySelector('#repairFlowMeasurementStatus');
    measurementStatus.dataset.complete = String(measurementsComplete);
    measurementStatus.textContent = measurementsComplete
      ? '本步测量已记录。资料未提供容差，请依据来源判断正常或异常。'
      : `需记录本步 ${step.measurements?.filter((measurement) => measurement.required !== false).length || 0} 项测量后再选择结果。`;
    document.querySelector('#repairFlowRecordMeasurements').onclick = () => {
      let next = repairFlowById.get(flow.flow_id);
      const inputs = [...measurementFields.querySelectorAll('[data-flow-measurement]')];
      if (inputs.some((input) => !input.reportValidity())) return;
      inputs.forEach((input) => {
        next = recordRepairFlowMeasurement(flow, next, input.dataset.flowMeasurement, input.value);
      });
      applyRepairFlowState(flow, next, entity);
    };
    step.choices.forEach((choice) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = choice.label;
      button.disabled = !measurementsComplete;
      button.addEventListener('click', () => {
        const next = answerRepairFlow(flow, repairFlowById.get(flow.flow_id), choice.value);
        applyRepairFlowState(flow, next, entity);
      });
      choices.append(button);
    });
  }
  if (state.terminal) {
    terminal.dataset.kind = state.terminal.kind;
    document.querySelector('#repairFlowTerminalType').textContent = state.terminal.kind === 'boundary' ? '资料边界' : '来源处理';
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
    ? '已记录来源处理已执行；维修结果仍需复检确认。'
    : '尚未记录来源处理是否已执行。';
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
    readinessCopy = '先记录来源处理是否已执行。';
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
    applyRepairFlowState(flow, next, entity);
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
    applyRepairFlowState(flow, resetRepairFlow(flow), entity);
  });
  return true;
}

function updateInspectionUi() {
  const entity = data?.entities.find((candidate) => candidate.component_id === selectedId);
  const active = componentInspection.mode === 'isolated';
  const available = canInspectComponent(entity)
    && entity.side_id === activeSideId
    && activeView === 'model';
  const button = document.querySelector('#inspectComponent');
  button.disabled = !canAcceptModelInteraction(modelInteraction) || (!active && !available);
  button.hidden = !active && !available;
  button.textContent = active ? '返回主板' : '单体查看';
  button.setAttribute('aria-pressed', String(active));
  button.title = available || active ? '' : '该点位没有可单独检视的器件包体';
  document.querySelector('#inspectionStatus').hidden = !active;
  document.querySelector('#inspectionDesignator').textContent = entity?.designator || '—';
  document.querySelector('#modelView').classList.toggle('inspection-active', active);
  document.querySelector('#toggleInspection').disabled = active || !canAcceptModelInteraction(modelInteraction);
  const toolbar = buildInspectionToolbarState({
    active,
    ready: canAcceptModelInteraction(modelInteraction),
    boardMode: modelDragMode,
  });
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
  if (active) document.querySelector('#sourceNote').textContent = `${entity.designator} 单体检视 · ${sideDataById.get(activeSideId)?.label}注册坐标 · 维修视觉封装`;
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
  const locked = !canAcceptModelInteraction(modelInteraction);
  renderer?.setInteractionLocked(locked);
  document.querySelectorAll('[role=tab], [data-side-id], #flipSide, #resetModel, #entityList button').forEach((control) => {
    control.disabled = locked;
  });
  updateSideControls();
  updateInspectionUi();
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
    await renderer.clearComponentInspection(animate);
    componentInspection = exitComponentInspection(componentInspection);
    return true;
  } finally {
    finishModelTransition(transitionId);
  }
}

async function toggleComponentInspection() {
  if (!canAcceptModelInteraction(modelInteraction)) return;
  if (componentInspection.mode === 'isolated') {
    await leaveComponentInspection();
    return;
  }
  const entity = data?.entities.find((candidate) => candidate.component_id === selectedId);
  const next = enterComponentInspection(entity, activeSideId);
  if (next.mode !== 'isolated') return;
  const transitionId = startModelTransition('inspection');
  if (transitionId === null) return;
  try {
    const entered = await renderer.setComponentInspection(next.componentId);
    componentInspection = entered ? next : exitComponentInspection();
  } finally {
    finishModelTransition(transitionId);
  }
}

function updateSideControls() {
  const locked = !canAcceptModelInteraction(modelInteraction);
  document.querySelectorAll('[data-side-id]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.sideId === activeSideId));
    button.disabled = locked;
  });
  document.querySelector('#flipSide').disabled = locked;
  const sideData = sideDataById.get(activeSideId);
  document.querySelector('#activeSideLabel').textContent = sideData?.label || activeSideId;
  const shieldsAvailable = Boolean(sideData?.anatomy.shields.length);
  document.querySelectorAll('[data-shield-mode]').forEach((button) => {
    button.disabled = locked || componentInspection.mode === 'isolated' || !shieldsAvailable;
  });
  const linkedSide = sideDataById.get(data?.side_id);
  if (linkedSide) document.querySelector('#entityListHeading').textContent = `${linkedSide.label}已关联实体`;
  const selectedEntity = data?.entities.find((entity) => entity.component_id === selectedId);
  if (selectedEntity) {
    document.querySelector('#entityVisibility').textContent = selectedEntity.side_id === activeSideId
      ? (selectedEntity.proxy_visibility === 'concealed_by_shield' ? '屏蔽罩下' : '代理图可见区域')
      : `目标位于${sideDataById.get(selectedEntity.side_id)?.label || selectedEntity.side_id}`;
  }
  if (activeView === 'model' && sideData) {
    document.querySelector('#sourceNote').textContent = `${sideData.label}点位图 · ${sideData.audit.accepted_designators} 个已编译位号 · 几何按来源置信度分层`;
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
      await renderer.clearComponentInspection(false);
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
    const point = positions.get(entity.component_id);
    const button = document.createElement('button');
    button.className = 'marker';
    button.type = 'button';
    button.dataset.componentId = entity.component_id;
    button.style.left = `${point.x * 100}%`;
    button.style.top = `${point.y * 100}%`;
    button.textContent = entity.designator.replace(/[0-9]/g, '').slice(0, 2);
    button.title = `${entity.designator} · ${entity.name}`;
    button.setAttribute('aria-label', `选择 ${entity.designator} ${entity.name}`);
    button.addEventListener('click', () => selectEntity(entity.component_id));
    fragment.append(button);
  });
  layer.append(fragment);
}

function evidenceCard(link, type) {
  const details = type === 'schematic' ? (link.facts || []).join(' · ') : link.instruction;
  const previews = (link.previews || []).map((preview) => `
    <button class="schematic-preview" type="button" data-preview-src="../../${preview.source}" data-preview-label="第 ${preview.page} 页" aria-label="查看第 ${preview.page} 页原理图局部图">
      <img src="../../${preview.source}" alt="第 ${preview.page} 页原理图局部图" loading="lazy">
    </button>`).join('');
  return `<article class="evidence-card">${details}${previews}<small>${link.source} · ${link.page}</small></article>`;
}

function renderComponentGuidance(entity) {
  const section = document.querySelector('#componentGuidance');
  let guidance = repairGuidanceByComponent.get(entity.component_id);
  if (!guidance) {
    guidance = createRepairGuidance(entity);
    repairGuidanceByComponent.set(entity.component_id, guidance);
  }
  section.hidden = !guidance.steps.length;
  if (!guidance.steps.length) {
    renderActiveFlowReturn(entity, false);
    return;
  }
  const faultList = document.querySelector('#commonFaults');
  faultList.replaceChildren();
  guidance.faults.forEach((fault) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = FAULT_LABELS[fault] || fault;
    button.setAttribute('aria-pressed', String(fault === guidance.selectedFault));
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
  document.querySelector('#inspectionMethod').textContent = step.instruction;
  document.querySelector('#inspectionSource').textContent = `${step.source} · ${step.page}`;
  const repairFlowActive = renderRepairFlow(entity, guidance);
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
  if (!canAcceptModelInteraction(modelInteraction)) return;
  const entity = data.entities.find((item) => item.component_id === componentId);
  if (!entity) return;
  if (componentInspection.mode === 'isolated') await leaveComponentInspection(false);
  if (!canAcceptModelInteraction(modelInteraction)) return;
  modelInteraction = recordSelectionIntent(modelInteraction, options.explicit !== false);
  selectedId = componentId;
  const state = buildSelectionState(entity, matrix);
  document.querySelectorAll('[data-component-id]').forEach((node) => node.classList.toggle('selected', node.dataset.componentId === componentId));
  document.querySelector('#entityCategory').textContent = entity.category.replaceAll('_', ' ');
  document.querySelector('#entityDesignator').textContent = entity.designator;
  document.querySelector('#entityName').textContent = entity.name;
  document.querySelector('#entityModule').textContent = entity.module;
  document.querySelector('#entityCoordinate').textContent = `${state.boardPoint.x.toFixed(3)}, ${state.boardPoint.y.toFixed(3)}`;
  document.querySelector('#entityVisibility').textContent = entity.proxy_visibility === 'concealed_by_shield' ? '屏蔽罩下' : '代理图可见区域';
  document.querySelector('#schematicEvidence').innerHTML = entity.schematic_links.map((link) => evidenceCard(link, 'schematic')).join('');
  document.querySelector('#repairEvidence').innerHTML = entity.repair_links.map((link) => evidenceCard(link, 'repair')).join('');
  renderComponentGuidance(entity);
  if (options.explicit !== false) document.querySelector('.evidence').scrollTo({ top: 0, behavior: 'auto' });
  renderer.select(componentId);
  const targetModules = sideDataById.get(entity.side_id)?.anatomy.modules || [];
  currentRepairTarget = buildEntityTarget(data.board_id, entity, targetModules);
  updateSideControls();
  activateRepairTarget();
  if (activeView === 'model') modelInteraction = consumePendingFocus(modelInteraction);
  if (activeView === 'pointmap' && pointMapViewport) pointMapViewport.focus(state.boardPoint);
  updateInspectionUi();
}

async function setView(name) {
  if (!canAcceptModelInteraction(modelInteraction)) return;
  if (name !== 'model' && componentInspection.mode === 'isolated') await leaveComponentInspection(false);
  activeView = name;
  document.querySelectorAll('[role=tab]').forEach((button) => button.setAttribute('aria-selected', String(button.dataset.view === name)));
  Object.entries(views).forEach(([key, view]) => view.classList.toggle('active', key === name));
  document.querySelector('#pointMapTools').hidden = name !== 'pointmap';
  document.querySelector('#modelTools').hidden = name !== 'model';
  if (name !== 'model' && data) document.querySelector('#sourceNote').textContent = `${data.registration.proxy_label} · ${data.registration.proxy_limit}`;
  if (name === 'model') {
    renderer.setInspectionAngle(true);
    document.querySelector('#toggleInspection').setAttribute('aria-pressed', 'false');
    requestAnimationFrame(() => {
      renderer.reset(false);
      renderer.resize();
      if (modelInteraction.pendingFocus && currentRepairTarget?.sideId === activeSideId) {
        applyRepairTarget();
        modelInteraction = consumePendingFocus(modelInteraction);
      }
    });
  }
  if (name === 'pointmap') requestAnimationFrame(() => pointMapViewport?.reset());
  updateSideControls();
  updateInspectionUi();
}

async function init() {
  const [response, geometryResponse, schematicResponse, shieldResponse, atlasResponse, manifestResponse, pageOneResponse] = await Promise.all([
    fetch(DATA_URL),
    fetch(GEOMETRY_URL),
    fetch(SCHEMATIC_URL),
    fetch(SHIELD_URL),
    fetch(ATLAS_URL),
    fetch(SIDE_MANIFEST_URL),
    fetch(PAGE_ONE_GEOMETRY_URL),
  ]);
  const responses = [response, geometryResponse, schematicResponse, shieldResponse, atlasResponse, manifestResponse, pageOneResponse];
  if (responses.some((candidate) => !candidate.ok)) throw new Error(`Dataset failed to load: ${responses.map((candidate) => candidate.status).join('/')}`);
  data = await response.json();
  geometryData = await geometryResponse.json();
  const schematicData = await schematicResponse.json();
  const shieldData = await shieldResponse.json();
  const atlasData = await atlasResponse.json();
  const sideManifest = await manifestResponse.json();
  const pageOneGeometry = await pageOneResponse.json();
  const compiledByDesignator = new Map(geometryData.components.map((component) => [component.designator, component]));
  data.entities = data.entities.map((originalEntity) => {
    const entity = {
      ...mergeCompiledSchematicLinks(originalEntity, schematicData),
      side_id: originalEntity.side_id || data.side_id,
    };
    const compiled = compiledByDesignator.get(entity.designator);
    if (!compiled?.footprint) return entity;
    return {
      ...entity,
      geometry: {
        ...entity.geometry,
        center: compiled.footprint.center,
        size: compiled.footprint.size,
        source_status: compiled.footprint.confidence,
      },
    };
  });
  const geometryBySide = new Map([
    ['main_page_1', pageOneGeometry],
    ['main_page_2', geometryData],
  ]);
  sideIds = sideManifest.sides.map((side) => side.side_id);
  sideDataById = new Map(sideManifest.sides.map((side) => {
    const compiled = geometryBySide.get(side.side_id);
    return [side.side_id, {
      sideId: side.side_id,
      label: side.label,
      entities: side.side_id === data.side_id ? data.entities : [],
      boardOutline: compiled.board_outline,
      compiledComponents: compiled.components,
      audit: compiled.audit,
      engineeringTextureUrl: `../../${side.engineering_texture}`,
      anatomy: {
        shields: side.side_id === data.side_id ? extractShieldRegions(shieldData) : [],
        modules: extractModuleRegions(atlasData, side.side_id),
      },
    }];
  }));
  activeSideId = sideManifest.default_side_id;
  const source = data.registration.anchors.slice(0, 4).map((anchor) => anchor.board);
  const target = data.registration.anchors.slice(0, 4).map((anchor) => anchor.image);
  matrix = solveHomography(source, target);

  const photoImage = document.querySelector('#photoView img');
  const pointMapImage = document.querySelector('#pointmapView img');
  photoImage.src = `../../${data.registration.proxy_image}`;
  pointMapImage.src = `../../${data.registration.point_map_image}`;
  pointMapViewport = new PointMapViewport(document.querySelector('#pointmapView'), document.querySelector('#pointmapView .point-map'));
  pointMapImage.addEventListener('load', () => pointMapViewport.reset(), { once: true });
  const boardPositions = new Map(data.entities.map((entity) => [entity.component_id, entity.geometry.center]));
  const photoPositions = new Map(data.entities.map((entity) => [entity.component_id, buildSelectionState(entity, matrix).photoPoint]));
  addMarkers(document.querySelector('#photoView .markers'), photoPositions, data.entities);
  addMarkers(document.querySelector('#pointmapView .markers'), boardPositions, data.entities);

  renderer = new BoardRenderer(
    document.querySelector('#modelCanvas'),
    sideDataById.get(activeSideId),
    selectEntity,
  );
  updateSideControls();
  document.querySelector('#sourceNote').textContent = `${data.registration.proxy_label} · ${data.registration.proxy_limit}`;
  const list = document.querySelector('#entityList');
  data.entities.forEach((entity) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.componentId = entity.component_id;
    button.innerHTML = `<strong>${entity.designator}</strong>${entity.module}`;
    button.addEventListener('click', () => selectEntity(entity.component_id));
    list.append(button);
  });
  selectEntity(data.entities[0].component_id, { explicit: false });
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
  document.querySelector('#toggleInspection').setAttribute('aria-pressed', 'false');
  updateInspectionUi();
});
document.querySelector('#inspectComponent').addEventListener('click', () => { void toggleComponentInspection(); });
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
document.querySelector('#toggleInspection').addEventListener('click', (event) => {
  const enabled = event.currentTarget.getAttribute('aria-pressed') !== 'true';
  event.currentTarget.setAttribute('aria-pressed', String(enabled));
  renderer?.setInspectionAngle(enabled);
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
document.querySelector('#flipSide').addEventListener('click', () => {
  const targetSideId = nextSideId(sideIds, activeSideId);
  if (targetSideId) void switchModelSide(targetSideId);
});
document.querySelector('#zoomOutPointMap').addEventListener('click', () => pointMapViewport?.zoomBy(0.8));
document.querySelector('#zoomInPointMap').addEventListener('click', () => pointMapViewport?.zoomBy(1.25));
document.querySelector('#resetPointMap').addEventListener('click', () => pointMapViewport?.reset());
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
