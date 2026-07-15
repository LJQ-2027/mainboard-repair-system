import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const toolbarMarkup = await readFile(new URL('../assets/cross-source-registration/index.html', import.meta.url), 'utf8');
const appSource = await readFile(new URL('../assets/cross-source-registration/app.js', import.meta.url), 'utf8');
const rendererSource = await readFile(new URL('../assets/cross-source-registration/board-renderer.js', import.meta.url), 'utf8');

test('model toolbar keeps source-driven focus without a manual module overlay selector', () => {
  assert.doesNotMatch(toolbarMarkup, /id="moduleFocus"/);
  assert.doesNotMatch(appSource, /moduleFocusMode|populateModuleMenu|#moduleFocus/);
  assert.match(appSource, /moduleOverlayId\(currentRepairTarget\)/);
});

test('model interaction tools belong to the model canvas instead of the global view header', () => {
  const viewHead = toolbarMarkup.slice(
    toolbarMarkup.indexOf('<div class="view-head">'),
    toolbarMarkup.indexOf('<div class="stage">'),
  );
  const modelViewIndex = toolbarMarkup.indexOf('id="modelView"');
  const modelToolsIndex = toolbarMarkup.indexOf('id="modelTools"');

  assert.doesNotMatch(viewHead, /id="modelTools"/);
  assert.ok(modelToolsIndex > modelViewIndex);
});

test('model view controls use explicit repair-facing labels and synchronized angle feedback', () => {
  const modelTools = toolbarMarkup.slice(
    toolbarMarkup.indexOf('id="modelTools"'),
    toolbarMarkup.indexOf('class="anatomy-panel"'),
  );

  assert.match(modelTools, /id="toggleInspection"[^>]*>斜视<\/button>/);
  assert.match(modelTools, /id="resetModel"[^>]*>↻<\/button>/);
  assert.doesNotMatch(modelTools, />◩<|>⌖</);
  assert.match(appSource, /function syncInspectionAngleControl\(enabled\)/);
  assert.match(appSource, /button\.setAttribute\('aria-pressed', String\(enabled\)\)/);
  assert.match(appSource, /enabled \? '恢复俯视' : '切换为斜视'/);
  assert.match(appSource, /new BoardRenderer\([\s\S]*selectEntity,[\s\S]*syncInspectionAngleControl/);
});

test('button and drag angle changes share renderer-owned state and cancellable animation', () => {
  assert.match(rendererSource, /this\.onInspectionAngleChange = onInspectionAngleChange/);
  assert.match(rendererSource, /setInspectionAngleState\(enabled/);
  assert.match(rendererSource, /this\.setInspectionAngleState\(isBoardAngled\(this\.group\.rotation\.x\)\)/);
  assert.match(rendererSource, /cancelAngleAnimation\(\)/);
  assert.match(rendererSource, /prefers-reduced-motion: reduce/);
  assert.match(appSource, /startModelTransition\('angle'\)/);
  assert.match(appSource, /await renderer\?\.setInspectionAngle\(enabled\)/);
});

test('model reset preserves active component inspection and resets its view', () => {
  const resetHandler = appSource.slice(
    appSource.indexOf("document.querySelector('#resetModel').addEventListener"),
    appSource.indexOf("document.querySelector('#inspectComponent').addEventListener"),
  );

  assert.match(resetHandler, /resetComponentInspectionView/);
  assert.doesNotMatch(resetHandler, /leaveComponentInspection/);
});

test('inspection status is a canvas-local return action using the shared exit path', () => {
  const statusMarkup = toolbarMarkup.slice(
    toolbarMarkup.indexOf('class="inspection-status"'),
    toolbarMarkup.indexOf('</main>'),
  );

  assert.match(statusMarkup, /^class="inspection-status" id="inspectionStatus" type="button"/);
  assert.match(statusMarkup, /inspection-return-icon/);
  assert.match(appSource, /#inspectionStatus'\)\.addEventListener\('click', \(\) => \{ void toggleComponentInspection\(\); \}\)/);
});

test('inspection mode hides board-only controls and keeps direct manipulation tools', () => {
  assert.match(appSource, /querySelector\('\.anatomy-panel'\)\.hidden = toolbar\.boardControlsHidden/);
  assert.match(appSource, /querySelector\('\.side-panel'\)\.hidden = toolbar\.boardControlsHidden/);
  assert.match(appSource, /querySelector\('\[data-model-drag-mode="pan"\]'\)\.hidden = toolbar\.panHidden/);
  assert.match(appSource, /querySelector\('#toggleInspection'\)\.hidden = toolbar\.inspectionAngleHidden/);
});

test('mobile model reveal belongs only to explicit entity list selection', () => {
  const selectEntitySource = appSource.slice(
    appSource.indexOf('async function selectEntity'),
    appSource.indexOf('async function setView'),
  );
  const markerSource = appSource.slice(
    appSource.indexOf('function addMarkers'),
    appSource.indexOf('function evidenceCard'),
  );
  const entityListSource = appSource.slice(
    appSource.indexOf("const list = document.querySelector('#entityList')"),
    appSource.indexOf("selectEntity(data.entities[0].component_id"),
  );
  const revealCalls = appSource.match(/revealModelAfterEntityListSelection\(\)/g) || [];

  assert.equal(revealCalls.length, 2, 'one helper definition and one entity-list call are expected');
  assert.doesNotMatch(selectEntitySource, /revealModelAfterEntityListSelection/);
  assert.doesNotMatch(markerSource, /revealModelAfterEntityListSelection/);
  assert.match(entityListSource, /await selectEntity\(entity\.component_id\);\s*revealModelAfterEntityListSelection\(\);/);
});

test('cross-view inspection serializes model view, target side, isolation, and reveal', () => {
  const entrySource = appSource.slice(
    appSource.indexOf('async function enterSelectedComponentInspection'),
    appSource.indexOf('async function toggleComponentInspection'),
  );

  assert.match(entrySource, /await setView\('model'\)/);
  assert.match(entrySource, /await switchModelSide\(intent\.sideId\)/);
  assert.match(entrySource, /await enterCurrentComponentInspection\(entity\)/);
  assert.match(entrySource, /revealModelWorkspace\(\)/);
  assert.ok(entrySource.indexOf("await setView('model')") < entrySource.indexOf('await switchModelSide(intent.sideId)'));
  assert.ok(entrySource.indexOf('await switchModelSide(intent.sideId)') < entrySource.indexOf('await enterCurrentComponentInspection(entity)'));
});

test('responsive board orientation survives reset and side replacement', () => {
  assert.match(rendererSource, /this\.defaultBoardRotationZ = buildDefaultBoardRotation\(width \/ height\)/);
  assert.match(rendererSource, /this\.group\.rotation\.set\(TOP_VIEW_TILT, 0, this\.defaultBoardRotationZ\)/);
  assert.match(rendererSource, /buildFocusFrame\(region, aspect, this\.group\.rotation\.z\)/);
  assert.match(rendererSource, /const rotationX = this\.group\.rotation\.x/);
  assert.match(rendererSource, /replaceSideData\(sideData, -Math\.PI \/ 2, rotationZ, rotationX\)/);
});

test('board reset recomputes label slots only after the camera settles', () => {
  const resetStart = rendererSource.indexOf('reset(resetInteractionMode = true)');
  const resetSource = rendererSource.slice(
    resetStart,
    rendererSource.indexOf('\n  resize()', resetStart),
  );
  assert.match(rendererSource, /animateCamera\(center, zoom, duration = 420, onComplete = null\)/);
  assert.match(resetSource, /clearRepairFocus\(true, true\)/);
  assert.doesNotMatch(resetSource, /this\.labelPlacementSlots = new Map\(\)/);
});
