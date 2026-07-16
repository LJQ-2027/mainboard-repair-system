import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { buildSourceNote } from '../assets/cross-source-registration/source-note-state.js';

const styles = await readFile(new URL('../assets/cross-source-registration/styles.css', import.meta.url), 'utf8');
const appSource = await readFile(new URL('../assets/cross-source-registration/app.js', import.meta.url), 'utf8');

const registration = {
  proxy_note: '主板实物参考 · 维修手册第10页 · 屏蔽罩下器件不可直接观察',
  point_map_note: '点位图 · F151_MAIN_PCB_V1.2 · 第2面',
};
const side = {
  label: '第2面',
  audit: { accepted_designators: 820 },
};

test('source note follows the active photo or point-map view', () => {
  assert.equal(buildSourceNote({ view: 'photo', registration, side }), registration.proxy_note);
  assert.equal(buildSourceNote({ view: 'pointmap', registration, side }), registration.point_map_note);
});

test('a board without a photo proxy falls back to its point-map source note', () => {
  const pointMapOnly = { reference_mode: 'point_map_only', point_map_note: 'H6929 TOP/BOT 点位图' };
  assert.equal(buildSourceNote({ view: 'photo', registration: pointMapOnly, side }), pointMapOnly.point_map_note);
});

test('model source note identifies the repair view and linked point coverage', () => {
  assert.equal(
    buildSourceNote({ view: 'model', registration, side }),
    '第2面 · 2.5D维修视图 · 820 个点位已关联',
  );
});

test('component inspection source note takes precedence over the board model note', () => {
  assert.equal(buildSourceNote({
    view: 'model',
    registration,
    side,
    inspectionEntity: { designator: 'U4000' },
  }), 'U4000 单体检视 · 第2面 · 已关联点位与维修资料');
});

test('narrow source note wraps completely instead of using an ellipsis', () => {
  const narrowStyles = styles.slice(styles.indexOf('@media (max-width: 480px)'));
  const noteStyles = narrowStyles.slice(
    narrowStyles.indexOf('.source-note {'),
    narrowStyles.indexOf('}', narrowStyles.indexOf('.source-note {')),
  );

  assert.match(narrowStyles, /\.workspace \{ height: 540px; grid-template-rows: auto minmax\(0, 1fr\) auto; \}/);
  assert.match(noteStyles, /white-space: normal;/);
  assert.match(noteStyles, /overflow: visible;/);
  assert.match(noteStyles, /text-overflow: clip;/);
});

test('app renders every source note through the view-aware state helper', () => {
  const assignments = appSource.match(/querySelector\('#sourceNote'\)\.textContent/g) || [];

  assert.match(appSource, /import \{ buildSourceNote \} from '\.\/source-note-state\.js'/);
  assert.equal(assignments.length, 1, 'only the centralized source-note renderer may assign text');
  assert.match(appSource, /function updateSourceNote\(inspectionEntity = null\)/);
});
