import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const styles = await readFile(new URL('../assets/cross-source-registration/styles.css', import.meta.url), 'utf8');
const appSource = await readFile(new URL('../assets/cross-source-registration/app.js', import.meta.url), 'utf8');

function rule(selector) {
  const start = styles.indexOf(`${selector} {`);
  assert.notEqual(start, -1, `missing ${selector} rule`);
  return styles.slice(start, styles.indexOf('}', start) + 1);
}

test('cross-view marker separates a touch-size target from its compact visible dot', () => {
  const target = rule('.marker');
  const dot = rule('.marker-dot');

  assert.match(target, /width: 36px;/);
  assert.match(target, /height: 36px;/);
  assert.match(target, /background: transparent;/);
  assert.doesNotMatch(target, /var\(--accent\)/);
  assert.match(dot, /width: 12px;/);
  assert.match(dot, /height: 12px;/);
  assert.match(dot, /background: #2d3b35;/);
});

test('marker label exposes full identity only for hover, focus, or selection', () => {
  const label = rule('.marker-label');
  const visibleLabel = rule('.marker:is(:hover, :focus-visible, .selected) .marker-label');

  assert.match(label, /opacity: 0;/);
  assert.match(visibleLabel, /opacity: 1;/);
  assert.match(styles, /\.marker\.selected \.marker-dot \{[^}]*background: var\(--selected\);/s);
  assert.match(styles, /\.marker:hover:not\(\.selected\) \.marker-dot \{[^}]*background: #f6dc83;/s);
});

test('keyboard focus adds a visible ring without enlarging the marker target', () => {
  const focusTarget = rule('.marker:focus-visible');
  const focusDot = rule('.marker:focus-visible .marker-dot');

  assert.match(focusTarget, /outline: none;/);
  assert.match(focusDot, /#65a9ff/);
});

test('marker DOM carries a compact dot and the complete designator label', () => {
  const markerSource = appSource.slice(
    appSource.indexOf('function addMarkers'),
    appSource.indexOf('function evidenceCard'),
  );

  assert.match(markerSource, /dot\.className = 'marker-dot'/);
  assert.match(markerSource, /label\.className = 'marker-label'/);
  assert.match(markerSource, /label\.textContent = entity\.designator/);
  assert.doesNotMatch(markerSource, /entity\.designator\.replace/);
});
