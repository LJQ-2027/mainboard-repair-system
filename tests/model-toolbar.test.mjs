import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const toolbarMarkup = await readFile(new URL('../assets/cross-source-registration/index.html', import.meta.url), 'utf8');
const appSource = await readFile(new URL('../assets/cross-source-registration/app.js', import.meta.url), 'utf8');
const rendererSource = await readFile(new URL('../assets/cross-source-registration/board-renderer.js', import.meta.url), 'utf8');
const stylesSource = await readFile(new URL('../assets/cross-source-registration/styles.css', import.meta.url), 'utf8');

test('model toolbar keeps source-driven focus without a manual module overlay selector', () => {
  assert.doesNotMatch(toolbarMarkup, /id="moduleFocus"/);
  assert.doesNotMatch(appSource, /moduleFocusMode|populateModuleMenu|#moduleFocus/);
  assert.match(appSource, /moduleOverlayId\(currentRepairTarget\)/);
});

test('view labels use technician language instead of registration internals', () => {
  assert.match(toolbarMarkup, /data-view="photo">主板实物参考<\/button>/);
  assert.match(toolbarMarkup, /已选机型 · 工程资料已关联/);
  assert.match(toolbarMarkup, /2\.5D 维修视图/);
  assert.doesNotMatch(toolbarMarkup, /实体代理图/);
  assert.doesNotMatch(toolbarMarkup, /KNOWN BOARD|SOURCE-LINKED|维修级 2\.5D V2/);
});

test('entity facts expose the board side instead of normalized registration coordinates', () => {
  assert.match(toolbarMarkup, /<dt>所在板面<\/dt><dd id="entitySide"><\/dd>/);
  assert.doesNotMatch(toolbarMarkup, /统一坐标|entityCoordinate/);
  assert.match(appSource, /#entitySide'\)\.textContent = sideDataById\.get\(entity\.side_id\)\?\.label \|\| entity\.side_id/);
  assert.doesNotMatch(appSource, /#entityCoordinate/);
});

test('repair workflow copy separates technician actions from collapsed source evidence', () => {
  assert.match(toolbarMarkup, /<section class="repair-entry" id="repairEntry"/);
  assert.match(toolbarMarkup, /<div class="repair-entry-options" id="repairEntryOptions"/);
  assert.match(appSource, /buildRepairEntryOptions\(data\.repair_flows, activeRepairFlowId\)/);
  assert.match(toolbarMarkup, /<span id="guidanceContextLabel">器件资料<\/span>/);
  assert.match(toolbarMarkup, /<h3 id="guidanceTitle">检测参考<\/h3>/);
  assert.match(toolbarMarkup, /<h4>关联故障资料<\/h4>/);
  assert.match(appSource, /faultGroup\.hidden = repairFlowActive/);
  assert.doesNotMatch(appSource, /const entry = data\?\.repair_flows\?\.find/);
  assert.match(toolbarMarkup, /<span>当前任务<\/span>/);
  assert.match(toolbarMarkup, /<strong>检测指导<\/strong>/);
  assert.match(toolbarMarkup, /<summary>资料依据<\/summary>/);
  assert.doesNotMatch(toolbarMarkup, /来源分支|来源检测指导/);
  assert.doesNotMatch(appSource, /来源摘要|来源处理|来源步骤|来源资料/);
});

test('active repair entry collapses to the current route with an explicit change action', () => {
  assert.match(toolbarMarkup, /id="repairEntryEyebrow">维修入口<\/span>/);
  assert.match(toolbarMarkup, /id="changeRepairEntry"[^>]*hidden[^>]*>更换故障<\/button>/);
  assert.match(appSource, /let repairEntryExpanded = false/);
  assert.match(appSource, /entryRoot\.dataset\.active = String\(Boolean\(activeFlow\)\)/);
  assert.match(appSource, /options\.hidden = Boolean\(activeFlow && !repairEntryExpanded\)/);
  assert.match(appSource, /changeButton\.setAttribute\('aria-expanded', String\(repairEntryExpanded\)\)/);
  assert.match(appSource, /repairEntryExpanded = false;[\s\S]*activeRepairFlowId = flow\.flow_id/);
});

test('active repair flow presents one current-task hierarchy without duplicate headings', () => {
  assert.match(toolbarMarkup, /<span>当前任务<\/span>/);
  assert.doesNotMatch(toolbarMarkup, /<span>排查路径<\/span>/);
  assert.match(appSource, /guidanceRoot\.dataset\.repairFlowActive = String\(repairFlowActive\)/);
  assert.match(stylesSource, /\.component-guidance\[data-repair-flow-active="true"\] > \.guidance-heading \{ display: none; \}/);
  assert.match(stylesSource, /\.component-guidance\[data-repair-flow-active="true"\] \.repair-flow-control \{[^}]*margin-top:\s*0;[^}]*padding-top:\s*0;[^}]*border-top:\s*0;/);
});

test('source evidence stays available without occupying the default repair path', () => {
  assert.match(toolbarMarkup, /<details class="source-evidence-details" id="schematicEvidenceDetails">/);
  assert.match(toolbarMarkup, /<summary><span>原理图依据<\/span><small id="schematicEvidenceCount"><\/small><\/summary>/);
  assert.match(toolbarMarkup, /<details class="source-evidence-details" id="repairEvidenceDetails">/);
  assert.match(toolbarMarkup, /<summary><span>维修手册原文<\/span><small id="repairEvidenceCount"><\/small><\/summary>/);
  assert.doesNotMatch(toolbarMarkup, /<details class="source-evidence-details"[^>]*\sopen/);
  assert.match(appSource, /#schematicEvidenceCount'\)\.textContent = evidenceCountCopy\(entity\.schematic_links\.length\)/);
  assert.match(appSource, /#repairEvidenceCount'\)\.textContent = evidenceCountCopy\(entity\.repair_links\.length\)/);
  assert.match(stylesSource, /\.source-evidence-details summary::after \{[^}]*content:\s*'\+'/);
  assert.match(stylesSource, /\.source-evidence-details\[open\] summary::after \{[^}]*content:\s*'−'/);
});

test('repair workflow uses one framed work surface with readable execution states', () => {
  const flowSurface = stylesSource.match(/\.repair-flow-control \{([^}]*)\}/)?.[1] || '';
  const terminalSurface = stylesSource.match(/\.repair-flow-terminal \{([^}]*)\}/)?.[1] || '';
  assert.match(flowSurface, /border:\s*0/);
  assert.match(flowSurface, /border-top:/);
  assert.match(flowSurface, /background:\s*transparent/);
  assert.match(terminalSurface, /border:\s*0/);
  assert.match(terminalSurface, /border-top:/);
  assert.match(terminalSurface, /background:\s*transparent/);
  assert.match(stylesSource, /\.repair-flow-action-record p \{[^}]*font-size:\s*10px/);
  assert.match(stylesSource, /\.repair-flow-completion p \{[^}]*font-size:\s*10px/);
  assert.match(stylesSource, /\.repair-flow-source-details \{[^}]*font-size:\s*10px/);
});

test('desktop evidence column expands only when the workspace can afford it', () => {
  assert.match(stylesSource, /main \{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) clamp\(360px, 27vw, 420px\)/);
  assert.match(stylesSource, /@media \(max-width: 1100px\)[\s\S]*main \{ display: block; height: auto; \}/);
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
  assert.match(stylesSource, /\.model-view\[data-model-busy="true"\] #modelCanvas canvas \{ cursor: wait; \}/);
});

test('model surface loading has a canvas-local status and stale-request guard', () => {
  assert.match(toolbarMarkup, /id="modelLoadStatus"[^>]*role="status"[^>]*>正在准备主板模型<\/div>/);
  assert.match(rendererSource, /beginSurfaceLoad\(this\.surfaceLoadState, this\.sideId\)/);
  assert.match(rendererSource, /finishSurfaceLoad\(this\.surfaceLoadState, requestId, false\)/);
  assert.match(appSource, /modelAssetStatus === 'loading'/);
  assert.match(appSource, /\[role=tab\][\s\S]*control\.disabled = transitionLocked/);
  assert.match(stylesSource, /\.model-load-status \{/);
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

test('inspection Escape key uses the same application-owned return path', () => {
  assert.match(rendererSource, /if \(action\.exit\) \{[\s\S]*this\.onInspectionExitRequest\(\)/);
  assert.match(appSource, /\(\) => \{ void toggleComponentInspection\(\); \}/);
});

test('reviewed BGA profiles use a layered inspection package without invented ball geometry', () => {
  assert.match(rendererSource, /function addInspectionBgaPackage\(group, descriptor\)/);
  assert.match(rendererSource, /descriptor\.visualAsset === 'reviewed-bga'/);
  assert.doesNotMatch(rendererSource, /addInspectionBgaPackage[\s\S]*BallGeometry/);
});

test('reviewed connector profiles use a recessed package without invented pin geometry', () => {
  assert.match(rendererSource, /function addInspectionConnectorPackage\(group, descriptor\)/);
  assert.match(rendererSource, /descriptor\.visualAsset === 'reviewed-connector'/);
  assert.doesNotMatch(rendererSource, /addInspectionConnectorPackage[\s\S]*PinGeometry/);
});

test('reviewed crystal profiles use a layered can without invented internal geometry', () => {
  assert.match(rendererSource, /function addInspectionCrystalPackage\(group, descriptor\)/);
  assert.match(rendererSource, /descriptor\.visualAsset === 'reviewed-crystal'/);
  assert.doesNotMatch(rendererSource, /addInspectionCrystalPackage[\s\S]*CrystalResonatorGeometry/);
});

test('component inspection exposes and clears the active visual asset for browser QA', () => {
  assert.match(rendererSource, /this\.container\.dataset\.inspectionVisualAsset = descriptor\.visualAsset/);
  assert.match(rendererSource, /delete this\.container\.dataset\.inspectionVisualAsset/);
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
