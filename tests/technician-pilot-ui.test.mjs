import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';


const htmlPath = new URL('../assets/technician-pilot/index.html', import.meta.url);
const cssPath = new URL('../assets/technician-pilot/styles.css', import.meta.url);
const appPath = new URL('../assets/technician-pilot/app.js', import.meta.url);

test('technician pilot is an operational model and intent selector', () => {
  const html = fs.readFileSync(htmlPath, 'utf8');

  assert.match(html, /id="modelSelect"/);
  assert.match(html, /id="boardVersion"/);
  assert.match(html, /id="capabilityStatus"/);
  assert.match(html, /id="intentSelect"/);
  assert.match(html, /id="openWorkbench"[^>]*disabled/);
  assert.match(html, /id="pilotLoadStatus"[^>]*role="status"/);
  assert.match(html, /src="\.\/app\.js(?:\?[^\"]+)?"/);
  assert.doesNotMatch(html, /class="[^"]*hero/);
  assert.doesNotMatch(html, /knownFaultEntry|unknownFaultEntry/);
});

test('entry application loads catalog datasets and navigates only through the shared intent contract', () => {
  const source = fs.readFileSync(appPath, 'utf8');

  assert.match(source, /buildPilotCatalog/);
  assert.match(source, /buildPilotIntentOptions/);
  assert.match(source, /encodePilotIntent/);
  assert.match(source, /repair-workbench-boards\.json/);
  assert.match(source, /Promise\.all/);
  assert.match(source, /openWorkbench\.disabled/);
  assert.match(source, /\.\.\/cross-source-registration\/\?\$\{query\.toString\(\)\}/);
});

test('entry styling is dense, responsive, touch-safe, and overflow-safe', () => {
  const css = fs.readFileSync(cssPath, 'utf8');

  assert.match(css, /grid-template-columns:\s*minmax\(220px,\s*300px\)\s+minmax\(0,\s*1fr\)/);
  assert.match(css, /@media\s*\(max-width:\s*760px\)/);
  assert.match(css, /min-height:\s*40px/);
  assert.match(css, /overflow-x:\s*hidden/);
  assert.match(css, /:focus-visible/);
  assert.doesNotMatch(css, /linear-gradient|radial-gradient|border-radius:\s*(?:[1-9]\d|[2-9])px/);
});
