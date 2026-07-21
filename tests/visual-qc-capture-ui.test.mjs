import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const html = await readFile(
  new URL('../assets/visual-qc-workbench/index.html', import.meta.url),
  'utf8',
);
const css = await readFile(
  new URL('../assets/visual-qc-workbench/styles.css', import.meta.url),
  'utf8',
);

test('visual QC workbench exposes one compact capture intake section', () => {
  assert.match(html, /id="captureSessionTitle"/);
  assert.match(html, /id="captureSessionBadge"/);
  assert.match(html, /data-capture-check="board_and_side_confirmed"/);
  assert.match(html, /data-capture-check="focus_and_lens_confirmed"/);
  assert.match(html, /data-capture-check="lighting_and_occlusion_confirmed"/);
  assert.match(html, /id="captureOtherSideButton"/);
});

test('reviewer training export has one compact governed dataset section', () => {
  assert.match(html, /id="trainingDatasetSection"/);
  assert.match(html, /id="trainingCaseCount"/);
  assert.match(html, /id="trainingAnnotationCount"/);
  assert.match(html, /id="trainingExcludedCount"/);
  assert.match(html, /id="trainingGateSummary"/);
  assert.match(html, /id="refreshTrainingDatasetButton"/);
  assert.match(html, /id="downloadTrainingManifestButton"/);
  assert.match(html, /id="downloadTrainingCocoButton"/);
});

test('canvas elements cannot feed their intrinsic bitmap height back into layout', () => {
  assert.match(
    css,
    /\.workbench\s*\{[^}]*height:\s*calc\(100vh - 122px\)/s,
  );
  assert.match(css, /\.canvas-grid\s*\{[^}]*overflow:\s*hidden/s);
  assert.match(
    css,
    /\.canvas-wrap canvas\s*\{[^}]*position:\s*absolute[^}]*inset:\s*0/s,
  );
  assert.match(
    css,
    /@media \(max-width: 1100px\)[\s\S]*?\.workbench\s*\{[^}]*height:\s*auto/s,
  );
});
