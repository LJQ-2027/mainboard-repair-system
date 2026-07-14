import { solveHomography } from './registration-core.js';
import { buildSelectionState } from './selection-state.js';
import { BoardRenderer } from './board-renderer.js';
import { PointMapViewport } from './point-map-viewport.js';
import { mergeCompiledSchematicLinks } from './source-links.js';
import { extractModuleRegions, extractShieldRegions } from './anatomy-state.js';
import {
  buildEntityTarget,
  buildModuleTarget,
  moduleOverlayId,
  nextSideId,
} from './repair-focus-state.js';
import {
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
let moduleFocusMode = 'auto';
let anatomy;
let currentRepairTarget;
let sideDataById = new Map();
let sideIds = [];
let activeSideId = 'main_page_2';
let componentInspection = exitComponentInspection();
let modelInteraction = createModelInteractionState();
let modelDragMode = 'pan';

const FAULT_LABELS = {
  no_power: '无法开机',
  leakage_current: '漏电',
  pmu_failure: '电源管理异常',
  'No power': '无法开机',
  'Leakage current': '漏电',
};

function updateInspectionUi() {
  const entity = data?.entities.find((candidate) => candidate.component_id === selectedId);
  const active = componentInspection.mode === 'isolated';
  const available = canInspectComponent(entity)
    && entity.side_id === activeSideId
    && activeView === 'model';
  const button = document.querySelector('#inspectComponent');
  button.disabled = !canAcceptModelInteraction(modelInteraction) || (!active && !available);
  button.textContent = active ? '返回主板' : '单体查看';
  button.setAttribute('aria-pressed', String(active));
  button.title = available || active ? '' : '当前单体样板仅支持 U2001 第2面';
  document.querySelector('#inspectionStatus').hidden = !active;
  document.querySelector('#inspectionDesignator').textContent = entity?.designator || '—';
  document.querySelector('#modelView').classList.toggle('inspection-active', active);
  document.querySelector('#toggleInspection').disabled = active || !canAcceptModelInteraction(modelInteraction);
  document.querySelector('#moduleFocus').disabled = active || !canAcceptModelInteraction(modelInteraction);
  document.querySelectorAll('[data-model-drag-mode]').forEach((control) => {
    control.disabled = active || !canAcceptModelInteraction(modelInteraction);
  });
  document.querySelectorAll('[data-shield-mode]').forEach((control) => {
    const sideHasShields = Boolean(sideDataById.get(activeSideId)?.anatomy.shields.length);
    control.disabled = active || !sideHasShields || !canAcceptModelInteraction(modelInteraction);
  });
  if (active) document.querySelector('#sourceNote').textContent = `${entity.designator} 单体检视 · ${sideDataById.get(activeSideId)?.label}注册坐标 · 维修视觉封装`;
}

function setModelDragMode(mode) {
  if (!canAcceptModelInteraction(modelInteraction) || componentInspection.mode === 'isolated') return modelDragMode;
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

function populateModuleMenu(modules) {
  const moduleMenu = document.querySelector('#moduleFocus');
  moduleMenu.replaceChildren();
  [['auto', '器件定位'], ['none', '全板视图']].forEach(([value, label]) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    moduleMenu.append(option);
  });
  modules.forEach((module) => {
    const option = document.createElement('option');
    option.value = module.moduleId;
    option.textContent = module.name;
    moduleMenu.append(option);
  });
  moduleFocusMode = 'auto';
  moduleMenu.value = 'auto';
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
    anatomy = sideDataById.get(sideId).anatomy;
    populateModuleMenu(anatomy.modules);
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
  section.hidden = !canInspectComponent(entity);
  const faultList = document.querySelector('#commonFaults');
  faultList.replaceChildren();
  const faults = [...new Set(entity.repair_links.flatMap((link) => link.faults || []))];
  faults.forEach((fault) => {
    const item = document.createElement('span');
    item.textContent = FAULT_LABELS[fault] || fault;
    faultList.append(item);
  });
  document.querySelector('#inspectionMethod').textContent = entity.repair_links
    .map((link) => link.instruction)
    .filter(Boolean)
    .join(' ');
  document.querySelector('#modelBoundary').textContent = entity.inspection_profile?.visual_note || '';
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
  renderer.select(componentId);
  moduleFocusMode = 'auto';
  document.querySelector('#moduleFocus').value = 'auto';
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
  anatomy = sideDataById.get(activeSideId).anatomy;
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
  populateModuleMenu(anatomy.modules);
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
  if (componentInspection.mode === 'isolated') await leaveComponentInspection(false);
  modelInteraction = consumePendingFocus(modelInteraction);
  setModelDragMode('pan');
  renderer?.reset();
  document.querySelector('#toggleInspection').setAttribute('aria-pressed', 'false');
  updateInspectionUi();
});
document.querySelector('#inspectComponent').addEventListener('click', () => { void toggleComponentInspection(); });
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
document.querySelector('#moduleFocus').addEventListener('change', (event) => {
  moduleFocusMode = event.currentTarget.value;
  if (moduleFocusMode === 'auto') {
    const entity = data?.entities.find((candidate) => candidate.component_id === selectedId);
    const targetModules = entity ? sideDataById.get(entity.side_id)?.anatomy.modules || [] : [];
    currentRepairTarget = entity ? buildEntityTarget(data.board_id, entity, targetModules) : null;
    activateRepairTarget();
  } else if (moduleFocusMode === 'none') {
    currentRepairTarget = null;
    renderer?.setModuleFocus(null);
    renderer?.clearRepairFocus();
  } else {
    const module = anatomy.modules.find((candidate) => candidate.moduleId === moduleFocusMode);
    currentRepairTarget = module ? buildModuleTarget(data.board_id, module) : null;
    if (activeView === 'model') applyRepairTarget();
  }
});
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
