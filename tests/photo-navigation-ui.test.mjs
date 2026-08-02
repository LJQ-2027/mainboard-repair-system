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
  assert.match(appSource, /import \{ buildPhotoNavigationState, failPhotoNavigation \} from '\.\/photo-navigation-state\.js'/);
  assert.match(appSource, /import \{ ImageViewport \} from '\.\/image-viewport\.js'/);
  assert.match(appSource, /function syncBoardViews\(/);
  assert.match(appSource, /buildPhotoNavigationState\(\{/);
  assert.match(appSource, /sideData\.engineeringTextureUrl/);
  assert.match(appSource, /photoViewport\.replaceImage\(photoState\.activePhoto\.photo_id\)/);
  assert.match(appSource, /#photoSelector/);
  assert.match(appSource, /function failPhotoViewClosed\(/);
  assert.doesNotMatch(appSource, /data\.registration\.proxy_image/);
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
