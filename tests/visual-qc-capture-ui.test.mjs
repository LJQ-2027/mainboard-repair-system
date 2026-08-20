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
  assert.match(html, /id="trainingGateCasesDisclosure"/);
  assert.match(html, /id="trainingGateCaseList"/);
  assert.match(html, /id="refreshTrainingDatasetButton"/);
  assert.match(html, /id="downloadTrainingManifestButton"/);
  assert.match(html, /id="downloadTrainingCocoButton"/);
  assert.match(html, /id="downloadTrainingBundleButton"/);
  assert.match(
    css,
    /\.training-dataset-actions\s*\{[^}]*display:\s*grid[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/s,
  );
});

test('workbench uses data-management terminology instead of a reviewer workflow', () => {
  assert.match(html, /主板视觉数据工作台/);
  assert.match(html, /数据管理/);
  assert.doesNotMatch(html, /审核员工具/);
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
