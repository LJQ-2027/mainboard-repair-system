import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const toolbarMarkup = await readFile(new URL('../assets/cross-source-registration/index.html', import.meta.url), 'utf8');
const appSource = await readFile(new URL('../assets/cross-source-registration/app.js', import.meta.url), 'utf8');

test('model toolbar keeps source-driven focus without a manual module overlay selector', () => {
  assert.doesNotMatch(toolbarMarkup, /id="moduleFocus"/);
  assert.doesNotMatch(appSource, /moduleFocusMode|populateModuleMenu|#moduleFocus/);
  assert.match(appSource, /moduleOverlayId\(currentRepairTarget\)/);
});
