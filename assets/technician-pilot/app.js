import { buildPilotCatalog } from './pilot-catalog-state.js';
import {
  buildPilotIntentOptions,
  encodePilotIntent,
} from '../cross-source-registration/pilot-intent-state.js';

const CATALOG_URL = '../../knowledge-base/repair-workbench-boards.json';
const capabilityLabels = {
  reviewed_flow: '有来源引导路径',
  case_navigation: '有来源案例导航',
  reference_only: '结构资料可查',
};

const modelSelect = document.querySelector('#modelSelect');
const boardVersion = document.querySelector('#boardVersion');
const capabilityStatus = document.querySelector('#capabilityStatus');
const intentSelect = document.querySelector('#intentSelect');
const openWorkbench = document.querySelector('#openWorkbench');
const pilotLoadStatus = document.querySelector('#pilotLoadStatus');

let catalog;
let entries = [];
let datasetsByBoard = {};
let selectedEntry = null;
let intentOptions = [];

function setStatus(message, isError = false) {
  pilotLoadStatus.textContent = message;
  pilotLoadStatus.classList.toggle('is-error', isError);
}

function resetIntent() {
  intentOptions = [];
  intentSelect.innerHTML = '<option value="">请先选择机型</option>';
  intentSelect.disabled = true;
  openWorkbench.disabled = true;
}

function renderIntentOptions() {
  const dataset = datasetsByBoard[selectedEntry.boardKey];
  intentOptions = buildPilotIntentOptions(dataset);
  intentSelect.innerHTML = '<option value="">请选择当前问题</option>';
  intentOptions.forEach((option) => {
    const element = document.createElement('option');
    element.value = option.id;
    element.textContent = option.kind === 'case_symptom'
      ? `${option.label}（${option.caseCount} 个来源案例）`
      : option.label;
    intentSelect.append(element);
  });
  intentSelect.disabled = false;
  openWorkbench.disabled = true;
}

function handleModelChange() {
  selectedEntry = entries.find((entry) => `${entry.boardKey}::${entry.model}` === modelSelect.value) || null;
  if (!selectedEntry) {
    boardVersion.textContent = '—';
    capabilityStatus.textContent = '等待选择机型';
    resetIntent();
    setStatus('请选择维修员已确认的手机机型。');
    return;
  }
  boardVersion.textContent = selectedEntry.boardVersion || '资料未声明';
  capabilityStatus.textContent = capabilityLabels[selectedEntry.capabilityTier] || '资料状态未知';
  renderIntentOptions();
  setStatus('机型与主板已锁定，请选择当前问题。');
}

function handleIntentChange() {
  openWorkbench.disabled = !intentOptions.some((option) => option.id === intentSelect.value);
  setStatus(openWorkbench.disabled ? '请选择当前问题。' : '入口已就绪。');
}

function openSelectedWorkbench() {
  const option = intentOptions.find((item) => item.id === intentSelect.value);
  if (!selectedEntry || !option) return;
  const query = encodePilotIntent(selectedEntry, option);
  window.location.href = `../cross-source-registration/?${query.toString()}`;
}

async function loadPilot() {
  openWorkbench.disabled = true;
  try {
    const catalogResponse = await fetch(CATALOG_URL);
    if (!catalogResponse.ok) throw new Error(`目录请求失败 (${catalogResponse.status})`);
    catalog = await catalogResponse.json();
    const loadedDatasets = await Promise.all(Object.entries(catalog.boards || {}).map(async ([boardKey, board]) => {
      const response = await fetch(board.data);
      if (!response.ok) throw new Error(`${board.title || boardKey} 资料请求失败 (${response.status})`);
      return [boardKey, await response.json()];
    }));
    datasetsByBoard = Object.fromEntries(loadedDatasets);
    entries = buildPilotCatalog(catalog, datasetsByBoard);
    if (!entries.length) throw new Error('目录中没有可用主板资料');

    modelSelect.innerHTML = '<option value="">请选择机型</option>';
    entries.forEach((entry) => {
      const option = document.createElement('option');
      option.value = `${entry.boardKey}::${entry.model}`;
      option.textContent = entry.model;
      modelSelect.append(option);
    });
    modelSelect.disabled = false;
    setStatus(`已读取 ${entries.length} 个机型入口。`);
  } catch (error) {
    modelSelect.innerHTML = '<option value="">资料目录加载失败</option>';
    modelSelect.disabled = true;
    resetIntent();
    setStatus(`无法开启维修入口：${error.message}`, true);
  }
}

modelSelect.addEventListener('change', handleModelChange);
intentSelect.addEventListener('change', handleIntentChange);
openWorkbench.addEventListener('click', openSelectedWorkbench);
loadPilot();
