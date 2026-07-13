import {
  analyzeImageQuality,
  extractFeatureVector,
  rankModelCandidates,
} from './vision-core.js';

const GALLERY_URL = '../../knowledge-base/vision-reference-gallery.json';
const PROJECT_ROOT = '../../';
const ANALYSIS_MAX_EDGE = 640;

const elements = {
  libraryStatus: document.getElementById('libraryStatus'),
  sampleCount: document.getElementById('sampleCount'),
  sampleList: document.getElementById('sampleList'),
  imageInput: document.getElementById('imageInput'),
  clearButton: document.getElementById('clearButton'),
  dropZone: document.getElementById('dropZone'),
  emptyState: document.getElementById('emptyState'),
  loadingState: document.getElementById('loadingState'),
  previewCanvas: document.getElementById('previewCanvas'),
  imageMeta: document.getElementById('imageMeta'),
  captureNotice: document.getElementById('captureNotice'),
  qualityBadge: document.getElementById('qualityBadge'),
  qualitySection: document.getElementById('qualitySection'),
  qualityScore: document.getElementById('qualityScore'),
  scoreFill: document.getElementById('scoreFill'),
  metricResolution: document.getElementById('metricResolution'),
  metricBrightness: document.getElementById('metricBrightness'),
  metricContrast: document.getElementById('metricContrast'),
  metricSharpness: document.getElementById('metricSharpness'),
  guidanceList: document.getElementById('guidanceList'),
  matchesSection: document.getElementById('matchesSection'),
  matchList: document.getElementById('matchList'),
  resultEmpty: document.getElementById('resultEmpty'),
  sampleTemplate: document.getElementById('sampleTemplate'),
  matchTemplate: document.getElementById('matchTemplate'),
};

const state = {
  references: [],
  samples: [],
  activeSample: null,
  ready: false,
};

function assetUrl(path) {
  return `${PROJECT_ROOT}${path}`;
}

function boardVersionLabel(model, asset) {
  const versions = model.board_versions || {};
  if (asset.board_scope === 'main') return (versions.main || []).join(' + ');
  if (asset.board_scope === 'sub') return (versions.sub || []).join(' + ');
  return [...(versions.main || []), ...(versions.sub || [])].join(' + ');
}

function roleLabel(role) {
  return {
    exploded_structure: 'Exploded structure',
    installed_mainboard: 'Installed main board',
    installed_subboard: 'Installed sub board',
  }[role] || 'Reference image';
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.decoding = 'async';
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Unable to load image: ${url}`));
    image.src = url;
  });
}

function imagePixels(image, maxEdge = ANALYSIS_MAX_EDGE) {
  const scale = Math.min(1, maxEdge / Math.max(image.naturalWidth, image.naturalHeight));
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

function flattenApprovedReferences(manifest) {
  const references = [];
  for (const model of manifest.models || []) {
    for (const page of model.candidate_pages || []) {
      for (const asset of page.embedded_images || []) {
        if (asset.review_status !== 'approved') continue;
        references.push({
          model: model.model,
          aliases: model.aliases || [],
          role: asset.reference_role,
          boardScope: asset.board_scope,
          boardSide: asset.board_side,
          boardVersion: boardVersionLabel(model, asset) || 'Board version unresolved',
          sourcePage: asset.source_page,
          strength: asset.reference_strength,
          url: assetUrl(asset.asset_path),
        });
      }
    }
  }
  return references;
}

async function prepareReference(reference) {
  const image = await loadImage(reference.url);
  return { ...reference, vector: extractFeatureVector(imagePixels(image, 320)) };
}

function renderSamples() {
  elements.sampleList.replaceChildren();
  for (const sample of state.samples) {
    const fragment = elements.sampleTemplate.content.cloneNode(true);
    const button = fragment.querySelector('button');
    const image = fragment.querySelector('img');
    image.src = sample.url;
    image.alt = `${sample.model} main board sample`;
    fragment.querySelector('strong').textContent = sample.model;
    fragment.querySelector('small').textContent = sample.boardVersion;
    button.dataset.model = sample.model;
    button.disabled = !state.ready;
    button.setAttribute('aria-pressed', String(state.activeSample === sample.model));
    button.addEventListener('click', () => analyzeUrl(sample.url, `${sample.model} reviewed sample`, sample.model));
    elements.sampleList.append(fragment);
  }
}

async function loadReferenceLibrary() {
  try {
    const response = await fetch(GALLERY_URL, { cache: 'no-store' });
    if (!response.ok) throw new Error(`Reference manifest returned ${response.status}`);
    const manifest = await response.json();
    const metadata = flattenApprovedReferences(manifest);
    state.references = await Promise.all(metadata.map(prepareReference));
    const byModel = new Map();
    for (const reference of state.references) {
      if (reference.role === 'installed_mainboard' || !byModel.has(reference.model)) {
        byModel.set(reference.model, reference);
      }
    }
    state.samples = [...byModel.values()].sort((a, b) => a.model.localeCompare(b.model));
    state.ready = true;
    elements.libraryStatus.textContent = `${state.references.length} references ready`;
    elements.libraryStatus.className = 'library-status ready';
    elements.sampleCount.textContent = `${state.samples.length} / 7`;
    renderSamples();
  } catch (error) {
    elements.libraryStatus.textContent = 'Reference load failed';
    elements.libraryStatus.className = 'library-status error';
    elements.resultEmpty.innerHTML = `<strong>Reference library unavailable</strong><p>${error.message}</p>`;
  }
}

function setProcessing(processing) {
  elements.emptyState.hidden = true;
  elements.loadingState.hidden = !processing;
  elements.previewCanvas.hidden = processing;
}

function drawPreview(image, status) {
  const canvas = elements.previewCanvas;
  const maxWidth = 1400;
  const scale = Math.min(1, maxWidth / image.naturalWidth);
  canvas.width = Math.round(image.naturalWidth * scale);
  canvas.height = Math.round(image.naturalHeight * scale);
  const context = canvas.getContext('2d');
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  const colors = { good: '#2ec08b', usable: '#f0a84a', retake: '#e45656' };
  context.strokeStyle = colors[status] || '#ffffff';
  context.lineWidth = Math.max(4, Math.round(canvas.width / 220));
  context.strokeRect(context.lineWidth / 2, context.lineWidth / 2, canvas.width - context.lineWidth, canvas.height - context.lineWidth);
  canvas.hidden = false;
}

function renderQuality(result) {
  const { metrics } = result;
  elements.qualityBadge.textContent = result.status;
  elements.qualityBadge.className = `quality-badge ${result.status}`;
  elements.qualityScore.textContent = result.score;
  elements.scoreFill.style.width = `${result.score}%`;
  elements.scoreFill.style.background = result.status === 'good' ? '#155b4b' : result.status === 'usable' ? '#be6b23' : '#a93838';
  elements.metricResolution.textContent = `${metrics.width} x ${metrics.height}`;
  elements.metricBrightness.textContent = `${Math.round(metrics.meanLuminance)} / 255`;
  elements.metricContrast.textContent = metrics.contrast.toFixed(1);
  elements.metricSharpness.textContent = metrics.sharpness.toFixed(1);
  elements.guidanceList.replaceChildren(...result.guidance.map((item) => {
    const li = document.createElement('li');
    li.textContent = item.message;
    return li;
  }));
  elements.qualitySection.hidden = false;
}

function renderMatches(matches) {
  elements.matchList.replaceChildren();
  matches.forEach((match, index) => {
    const fragment = elements.matchTemplate.content.cloneNode(true);
    fragment.querySelector('.rank').textContent = index + 1;
    const image = fragment.querySelector('img');
    image.src = match.url;
    image.alt = `${match.model} matched reference`;
    fragment.querySelector('strong').textContent = match.model;
    fragment.querySelector('.similarity').textContent = `${Math.round(Math.max(0, match.similarity) * 100)}%`;
    fragment.querySelector('.match-role').textContent = `${roleLabel(match.role)} · page ${match.sourcePage} · ${match.strength} reference`;
    fragment.querySelector('code').textContent = match.boardVersion;
    elements.matchList.append(fragment);
  });
  elements.matchesSection.hidden = false;
}

async function analyzeImage(image, label, selectedModel = null) {
  if (!state.ready) return;
  setProcessing(true);
  elements.clearButton.disabled = false;
  elements.imageMeta.textContent = `${label} · ${image.naturalWidth} x ${image.naturalHeight}`;
  state.activeSample = selectedModel;
  renderSamples();
  await new Promise((resolve) => requestAnimationFrame(resolve));

  const pixels = imagePixels(image);
  const quality = analyzeImageQuality(pixels);
  const queryVector = extractFeatureVector(pixels);
  const matches = rankModelCandidates(queryVector, state.references, 3);
  drawPreview(image, quality.status);
  renderQuality(quality);
  renderMatches(matches);
  elements.resultEmpty.hidden = true;
  elements.captureNotice.hidden = quality.status !== 'retake';
  elements.captureNotice.textContent = quality.status === 'retake'
    ? 'Quality gate failed. Similarity results remain visible for internal testing but should not be treated as reliable.'
    : '';
  setProcessing(false);
  if (selectedModel && window.matchMedia('(max-width: 820px)').matches) {
    document.querySelector('.inspection-panel').scrollIntoView({ block: 'start', behavior: 'auto' });
  }
}

async function analyzeUrl(url, label, selectedModel = null) {
  try {
    const image = await loadImage(url);
    await analyzeImage(image, label, selectedModel);
  } catch (error) {
    showImageError(error.message);
  }
}

async function analyzeFile(file) {
  if (!file || !file.type.startsWith('image/')) {
    showImageError('Choose a JPEG, PNG or WebP image.');
    return;
  }
  const url = URL.createObjectURL(file);
  try {
    const image = await loadImage(url);
    await analyzeImage(image, file.name);
  } catch (error) {
    showImageError(error.message);
  } finally {
    URL.revokeObjectURL(url);
  }
}

function showImageError(message) {
  elements.captureNotice.hidden = false;
  elements.captureNotice.textContent = message;
  elements.loadingState.hidden = true;
  elements.emptyState.hidden = false;
}

function clearInspection() {
  state.activeSample = null;
  renderSamples();
  elements.imageInput.value = '';
  elements.emptyState.hidden = false;
  elements.loadingState.hidden = true;
  elements.previewCanvas.hidden = true;
  elements.captureNotice.hidden = true;
  elements.qualitySection.hidden = true;
  elements.matchesSection.hidden = true;
  elements.resultEmpty.hidden = false;
  elements.qualityBadge.textContent = 'Waiting';
  elements.qualityBadge.className = 'quality-badge neutral';
  elements.imageMeta.textContent = 'No image selected';
  elements.clearButton.disabled = true;
}

elements.imageInput.addEventListener('change', (event) => analyzeFile(event.target.files[0]));
elements.clearButton.addEventListener('click', clearInspection);
elements.dropZone.addEventListener('click', (event) => {
  if (event.target.closest('canvas')) return;
  elements.imageInput.click();
});
elements.dropZone.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    elements.imageInput.click();
  }
});
for (const eventName of ['dragenter', 'dragover']) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add('dragover');
  });
}
for (const eventName of ['dragleave', 'drop']) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove('dragover');
  });
}
elements.dropZone.addEventListener('drop', (event) => analyzeFile(event.dataTransfer.files[0]));

loadReferenceLibrary();
