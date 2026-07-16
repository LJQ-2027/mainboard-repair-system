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

test('board side selection has one explicit control path without a duplicate flip action', () => {
  assert.equal((toolbarMarkup.match(/data-side-id=/g) || []).length, 2);
  assert.doesNotMatch(toolbarMarkup, /id="flipSide"|class="side-flip"|>⇄</);
  assert.doesNotMatch(appSource, /#flipSide|nextSideId/);
  assert.match(appSource, /\[data-side-id\][\s\S]*switchModelSide\(button\.dataset\.sideId\)/);
});

test('ordinary selection keeps native component materials and uses precise affordances only', () => {
  assert.doesNotMatch(rendererSource, /presentation\.emissiveIntensity/);
  assert.doesNotMatch(rendererSource, /clearSelectionStyle\(\)/);
  assert.doesNotMatch(rendererSource, /setInspectionSelectionStyle\(/);
  assert.match(rendererSource, /createAffordanceFrame/);
  assert.match(rendererSource, /labelVariant/);
});

test('external component labels share the package picking and drill-down path', () => {
  assert.match(rendererSource, /sprite\.userData\.componentId = entity\.component_id/);
  assert.match(rendererSource, /\.\.\.this\.pickTargets\.values\(\), \.\.\.this\.labelSprites\.values\(\)/);
  assert.match(rendererSource, /filter\(\(object\) => object\.visible\)/);
  assert.match(rendererSource, /dataset\.labelScreenBounds/);
});

test('pointer activation keeps the visible target stable through hover cleanup', () => {
  assert.match(rendererSource, /this\.activationTargets = new Map\(\)/);
  assert.match(rendererSource, /const activationTarget = this\.componentAtPointer\(event\);[\s\S]*this\.activationTargets\.set\(event\.pointerId, activationTarget\);[\s\S]*this\.clearHover\(false\)/);
  assert.match(rendererSource, /const activationTarget = this\.activationTargets\.get\(event\.pointerId\);/);
  assert.match(rendererSource, /this\.pick\(event, activationTarget\)/);
  assert.match(rendererSource, /this\.activationTargets\.delete\(event\.pointerId\)/);
});

test('hover and selection styling do not reorder external label placement', () => {
  const labelLayoutSource = rendererSource.slice(
    rendererSource.indexOf('const labelItems = this.entities'),
    rendererSource.indexOf('const labelLayout = buildScreenLabelPositions'),
  );
  assert.doesNotMatch(labelLayoutSource, /priority/);
  assert.doesNotMatch(labelLayoutSource, /\.sort\(/);
});

test('entity access status is rendered through one technician-facing state path', () => {
  assert.match(appSource, /function updateEntityAccessStatus\(entity\)/);
  assert.match(appSource, /buildEntityAccessState\(entity, activeSideId, targetSideLabel\)/);
  assert.match(appSource, /visibility\.dataset\.tone = access\.tone/);
  assert.doesNotMatch(appSource, /代理图可见区域/);
  assert.doesNotMatch(appSource, /textContent = entity\.proxy_visibility/);
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
  assert.match(appSource, /new BoardRenderer\([\s\S]*handleModelComponentActivation,[\s\S]*syncInspectionAngleControl/);
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

test('model transitions expose a canvas-local busy state without erasing the active control', () => {
  const controlStateSource = appSource.slice(
    appSource.indexOf('function updateModelControlState'),
    appSource.indexOf('function startModelTransition'),
  );

  assert.match(controlStateSource, /modelView\.dataset\.modelBusy = String\(locked\)/);
  assert.match(controlStateSource, /modelView\.setAttribute\('aria-busy', String\(locked\)\)/);
  assert.match(toolbarMarkup, /id="modelView"[^>]*aria-busy="false"/);
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

test('model activation uses selection first and direct inspection only for the selected package', () => {
  const activationSource = appSource.slice(
    appSource.indexOf('async function handleModelComponentActivation'),
    appSource.indexOf('async function setView'),
  );

  assert.match(activationSource, /resolveModelComponentActivation\([\s\S]*entity,[\s\S]*selectedId/);
  assert.match(activationSource, /action === 'inspect'/);
  assert.match(activationSource, /await enterSelectedComponentInspection\(\)/);
  assert.match(activationSource, /await selectEntity\(componentId, \{ focus: false \}\)/);
  assert.match(appSource, /new BoardRenderer\([\s\S]*handleModelComponentActivation/);
  assert.match(rendererSource, /action\.textContent = '单体查看'/);
});

test('canvas selection keeps the manual camera while guided selection retains repair focus', () => {
  const selectEntitySource = appSource.slice(
    appSource.indexOf('async function selectEntity'),
    appSource.indexOf('async function handleModelComponentActivation'),
  );

  assert.match(selectEntitySource, /options\.focus === false && activeView === 'model'/);
  assert.match(selectEntitySource, /renderer\.clearRepairEmphasis\(\)/);
  assert.match(selectEntitySource, /else activateRepairTarget\(\)/);
  assert.match(rendererSource, /clearRepairEmphasis\(\)/);
  assert.match(rendererSource, /this\.cancelCameraAnimation\(\)/);
  assert.match(rendererSource, /this\.applyRepairEmphasis\(null\)/);
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
