import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const html = fs.readFileSync(new URL('../assets/cross-source-registration/index.html', import.meta.url), 'utf8');
const app = fs.readFileSync(new URL('../assets/cross-source-registration/app.js', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../assets/cross-source-registration/styles.css', import.meta.url), 'utf8');

test('workbench exposes pilot intent, symptom-first cases, and controlled feedback', () => {
  assert.match(html, /id="pilotIntentContext"[^>]*hidden/);
  assert.match(html, /id="caseSymptomSelector"/);
  assert.match(html, /id="pilotFeedback"[^>]*hidden/);
  assert.match(html, /href="\.\.\/technician-pilot\/">返回入口/);
  assert.match(html, /data-feedback-target="found"/);
  assert.match(html, /data-feedback-usefulness="insufficient"/);
  assert.match(html, /id="exportPilotFeedback"/);
});

test('workbench resolves entry intent before applying flow or case state', () => {
  assert.match(app, /resolvePilotIntent/);
  assert.match(app, /selectedCaseSymptomKey/);
  assert.match(app, /url\.searchParams\.set\('symptom', selectedGroup\.key\)/);
  assert.match(app, /renderPilotIntentContext\(\);/);
  assert.match(app, /pilotIntent\.flowId/);
  assert.match(app, /await startRepairEntry\(pilotIntent\.flowId, \{ syncPilotIntent: false \}\)/);
  assert.match(app, /const boundaryOnly = pilotIntent\?\.valid && pilotIntent\.boundaryOnly/);
  assert.match(app, /selectedComponentId: technicianSelectionActive \? selectedId : null/);
  assert.match(app, /url\.searchParams\.set\('intent', 'repair_flow'\)/);
  assert.match(app, /createPilotFeedback/);
  assert.match(app, /serializePilotFeedback/);
});

test('pilot context and feedback controls remain compact in the evidence rail', () => {
  assert.match(css, /\.pilot-intent-context/);
  assert.match(css, /\.pilot-feedback/);
  assert.match(css, /\.feedback-segments/);
});

test('reviewed flows create, persist, restore, and explicitly restart repair sessions', () => {
  assert.match(app, /beginRepairSession/);
  assert.match(app, /persistRepairSession/);
  assert.match(app, /restartRepairSession/);
  assert.match(app, /declaredFlows: data\.repair_flows/);
  assert.match(app, /restartSession: true/);
});

test('repair session status and export stay inside the existing reviewed-flow panel', () => {
  assert.match(html, /id="repairFlowControl"[^>]*hidden[\s\S]*id="repairSessionStrip"[^>]*hidden/);
  assert.match(html, /id="repairSessionStatus"/);
  assert.match(html, /id="repairSessionSavedAt"/);
  assert.match(html, /id="exportRepairSession"/);
  assert.match(app, /serializeRepairSessions\(\[activeRepairSession\]\)/);
  assert.match(css, /\.repair-session-strip/);
});
