import { solveHomography } from './registration-core.js';
import { buildSelectionState } from './selection-state.js';
import { BoardRenderer } from './board-renderer.js';
import { PointMapViewport } from './point-map-viewport.js';
import { mergeCompiledSchematicLinks } from './source-links.js';

const DATA_URL = '../../knowledge-base/km4-cross-source-registration.json';
const GEOMETRY_URL = '../../knowledge-base/km4-board-compiled.json';
const SCHEMATIC_URL = '../../knowledge-base/km4-schematic-compiled.json';
const views = { photo: document.querySelector('#photoView'), pointmap: document.querySelector('#pointmapView'), model: document.querySelector('#modelView') };
let data;
let matrix;
let renderer;
let geometryData;
let selectedId;
let pointMapViewport;
let activeView = 'photo';

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

function selectEntity(componentId) {
  const entity = data.entities.find((item) => item.component_id === componentId);
  if (!entity) return;
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
  renderer.select(componentId);
  if (activeView === 'pointmap' && pointMapViewport) pointMapViewport.focus(state.boardPoint);
}

function setView(name) {
  activeView = name;
  document.querySelectorAll('[role=tab]').forEach((button) => button.setAttribute('aria-selected', String(button.dataset.view === name)));
  Object.entries(views).forEach(([key, view]) => view.classList.toggle('active', key === name));
  document.querySelector('#pointMapTools').hidden = name !== 'pointmap';
  document.querySelector('#modelTools').hidden = name !== 'model';
  if (name === 'model') {
    renderer.setInspectionAngle(true);
    document.querySelector('#toggleInspection').setAttribute('aria-pressed', 'false');
    requestAnimationFrame(() => {
      renderer.reset();
      renderer.resize();
    });
  }
  if (name === 'pointmap') requestAnimationFrame(() => pointMapViewport?.reset());
}

async function init() {
  const [response, geometryResponse, schematicResponse] = await Promise.all([fetch(DATA_URL), fetch(GEOMETRY_URL), fetch(SCHEMATIC_URL)]);
  if (!response.ok || !geometryResponse.ok || !schematicResponse.ok) throw new Error(`Dataset failed to load: ${response.status}/${geometryResponse.status}/${schematicResponse.status}`);
  data = await response.json();
  geometryData = await geometryResponse.json();
  const schematicData = await schematicResponse.json();
  const compiledByDesignator = new Map(geometryData.components.map((component) => [component.designator, component]));
  data.entities = data.entities.map((originalEntity) => {
    const entity = mergeCompiledSchematicLinks(originalEntity, schematicData);
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
    data.entities,
    geometryData.board_outline,
    geometryData.components,
    `../../${data.registration.point_map_image}`,
    selectEntity,
  );
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
  selectEntity(data.entities[0].component_id);
}

document.querySelectorAll('[role=tab]').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
document.querySelector('#resetModel').addEventListener('click', () => {
  renderer?.reset();
  document.querySelector('#toggleInspection').setAttribute('aria-pressed', 'false');
});
document.querySelector('#toggleInspection').addEventListener('click', (event) => {
  const enabled = event.currentTarget.getAttribute('aria-pressed') !== 'true';
  event.currentTarget.setAttribute('aria-pressed', String(enabled));
  renderer?.setInspectionAngle(enabled);
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
