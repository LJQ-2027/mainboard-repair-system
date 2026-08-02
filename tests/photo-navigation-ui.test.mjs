import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const markup = await readFile(new URL('../assets/cross-source-registration/index.html', import.meta.url), 'utf8');
const appSource = await readFile(new URL('../assets/cross-source-registration/app.js', import.meta.url), 'utf8');
const styles = await readFile(new URL('../assets/cross-source-registration/styles.css', import.meta.url), 'utf8');
const pointMapStyles = await readFile(new URL('../assets/cross-source-registration/point-map.css', import.meta.url), 'utf8');

test('workbench exposes one shared board-side selector above all three views', () => {
  assert.equal((markup.match(/class="side-panel"/g) || []).length, 1);
  const viewHead = markup.slice(markup.indexOf('<div class="view-head">'), markup.indexOf('<div class="stage">'));
  assert.match(viewHead, /class="side-panel"/);
  assert.equal((viewHead.match(/data-side-id="[^"]+"[^>]*disabled/g) || []).length, 2);
  assert.match(markup, /data-view="photo">实物图<\/button>/);
  assert.match(markup, /data-view="pointmap">点位图<\/button>/);
  assert.match(markup, /data-view="model">2\.5D 模型<\/button>/);
});

test('physical-photo view has a compact selector and matching navigation controls', () => {
  assert.match(markup, /id="photoTools" hidden/);
  assert.match(markup, /id="photoSelector"[^>]*aria-label="选择实拍图"/);
  assert.match(markup, /id="zoomOutPhoto"/);
  assert.match(markup, /id="zoomInPhoto"/);
  assert.match(markup, /id="resetPhoto"/);
  assert.match(markup, /id="photoLoadStatus"[^>]*role="status"/);
  assert.match(pointMapStyles, /\.photo-view\.active/);
  assert.match(pointMapStyles, /touch-action: none/);
});

test('app resolves reviewed photos and refreshes all board views from one side transition', () => {
  assert.match(appSource, /buildPhotoNavigationState/);
  assert.match(appSource, /failPhotoNavigation/);
  assert.match(appSource, /import \{ ImageViewport \} from '\.\/image-viewport\.js'/);
  assert.match(appSource, /function syncBoardViews\(/);
  assert.match(appSource, /buildPhotoNavigationState\(\{/);
  assert.match(appSource, /sideData\.engineeringTextureUrl/);
  assert.match(appSource, /photoViewport\.replaceImage\(photoState\.activePhoto\.photo_id\)/);
  assert.match(appSource, /#photoSelector/);
  assert.match(appSource, /function failPhotoViewClosed\(/);
  assert.doesNotMatch(appSource, /data\.registration\.proxy_image/);
});

test('starting a hash-bound repair flow selects its reviewed evidence photo before its component', () => {
  const startSource = appSource.slice(
    appSource.indexOf('async function startRepairEntry'),
    appSource.indexOf('function applyRepairFlowState'),
  );

  assert.match(appSource, /resolveReviewedPhotoIdBySourceHash/);
  assert.match(startSource, /const targetEntity = data\.entities\.find/);
  assert.match(startSource, /flow\.source_photo_sha256/);
  assert.match(startSource, /resolveReviewedPhotoIdBySourceHash\(/);
  assert.match(startSource, /if \(flow\.source_photo_sha256 && !evidencePhotoId\)/);
  assert.match(startSource, /来源实拍与当前审核资料不一致/);
  assert.match(startSource, /return false/);
  assert.match(startSource, /preferredPhotoBySide\.set\(targetEntity\.side_id, evidencePhotoId\)/);
  assert.ok(
    startSource.indexOf('preferredPhotoBySide.set') < startSource.indexOf('await selectEntity'),
    'the exact evidence photo must be preferred before side/entity synchronization',
  );
});

test('boundary-only repair results never expose action recording controls', () => {
  const flowSource = appSource.slice(
    appSource.indexOf('function renderRepairFlow'),
    appSource.indexOf('function updateInspectionUi'),
  );

  assert.match(flowSource, /state\.terminal\.kind === 'boundary' \? '资料边界' : '维修处理'/);
  assert.match(flowSource, /const actionRecordVisible = state\.terminal\?\.kind === 'action'/);
  assert.match(flowSource, /actionRecord\.hidden = !actionRecordVisible/);
  assert.match(flowSource, /flow\.source\.label\s*\|\|/);
});

test('photo and point-map markers are rebuilt from the active-side entity set', () => {
  const syncSource = appSource.slice(
    appSource.indexOf('function syncBoardViews'),
    appSource.indexOf('function evidenceCard'),
  );
  assert.match(syncSource, /sideData\.entities/);
  assert.match(syncSource, /photoMarkers\.replaceChildren\(\)/);
  assert.match(syncSource, /pointMapMarkers\.replaceChildren\(\)/);
  assert.match(syncSource, /buildSelectionState\(entity, matrix\)\.photoPoint/);
});

test('initial data selection keeps the full image until the technician requests focus', () => {
  const selectionSource = appSource.slice(
    appSource.indexOf('async function selectEntity'),
    appSource.indexOf('async function handleModelComponentActivation'),
  );
  const helperSource = appSource.slice(
    appSource.indexOf('function focusSelectedImageEntity'),
    appSource.indexOf('function syncBoardViews'),
  );
  assert.match(selectionSource, /const shouldFocusImage = options\.focus !== false && options\.explicit !== false/);
  assert.match(selectionSource, /technicianSelectionActive = options\.explicit !== false/);
  assert.doesNotMatch(helperSource, /\boptions\b|shouldFocusImage/);
  assert.match(helperSource, /if \(!technicianSelectionActive\) return/);
  assert.match(appSource, /selectEntity\(initialEntity\.component_id, \{ explicit: false, focus: false \}\)/);
});

test('mobile header controls wrap without forcing horizontal overflow', () => {
  const narrow = styles.slice(styles.indexOf('@media (max-width: 480px)'));
  assert.match(narrow, /\.view-head \{[^}]*flex-wrap: wrap;/s);
  assert.match(narrow, /\.side-panel \{[^}]*position: static;/s);
  assert.match(narrow, /\.photo-selector/);
});
