import assert from 'node:assert/strict';
import test from 'node:test';

import {
  resolveBoardAssets,
  resolveBoardKey,
} from '../assets/cross-source-registration/board-catalog-state.js';


const catalog = {
  default_board_key: 'km4-f151',
  boards: {
    'km4-f151': {
      title: 'KM4 · F151_MAIN_PCB_V1.2',
      data: 'km4-data.json',
      schematic: 'km4-schematic.json',
      side_manifest: 'km4-sides.json',
      geometry_by_side: { main_page_1: 'km4-p1.json', main_page_2: 'km4-p2.json' },
    },
    'kl4-f201': {
      title: 'KL4 · F201_MAIN_V1.2',
      data: 'kl4-data.json',
      schematic: 'kl4-schematic.json',
      side_manifest: 'kl4-sides.json',
      geometry_by_side: { main_page_1: 'kl4-p1.json', main_page_2: 'kl4-p2.json' },
      shield: null,
      atlas: null,
    },
    'cm6-h8918': {
      title: 'CM6 / CM5 · H8918_MAIN_PCB_V1.2',
      model: 'CM6',
      compatible_models: ['CM6', 'CM5'],
      data: 'h8918-data.json',
      schematic: 'h8918-schematic.json',
      side_manifest: 'h8918-sides.json',
      geometry_by_side: { main_page_1: 'h8918-p1.json', main_page_2: 'h8918-p2.json' },
      shield: null,
      atlas: null,
    },
    'ck6n-h6929': {
      title: 'CK6N · H6929_MAIN_PCB_V1.1',
      model: 'CK6N',
      data: 'h6929-data.json',
      schematic: 'h6929-schematic.json',
      side_manifest: 'h6929-sides.json',
      geometry_by_side: { main_top: 'h6929-top.json', main_bot: 'h6929-bot.json' },
      shield: null,
      atlas: null,
    },
  },
};


test('board key defaults only when the query parameter is absent', () => {
  assert.equal(resolveBoardKey(new URL('http://local/workbench'), catalog), 'km4-f151');
  assert.equal(resolveBoardKey(new URL('http://local/workbench?board=kl4-f201'), catalog), 'kl4-f201');
  assert.equal(resolveBoardKey(new URL('http://local/workbench?board='), catalog), 'km4-f151');
});

test('board assets retain an ordered side map without model conditionals', () => {
  const assets = resolveBoardAssets(catalog, 'kl4-f201');
  assert.equal(assets.title, 'KL4 · F201_MAIN_V1.2');
  assert.deepEqual(Object.keys(assets.geometry_by_side), ['main_page_1', 'main_page_2']);
  assert.equal(assets.shield, null);
  assert.equal(assets.atlas, null);
});

test('one board platform can declare multiple compatible sales models', () => {
  const assets = resolveBoardAssets(catalog, 'cm6-h8918');
  assert.equal(assets.model, 'CM6');
  assert.deepEqual(assets.compatible_models, ['CM6', 'CM5']);
  assert.deepEqual(Object.keys(assets.geometry_by_side), ['main_page_1', 'main_page_2']);
});

test('source-named board sides do not depend on legacy page identities', () => {
  const assets = resolveBoardAssets(catalog, 'ck6n-h6929');
  assert.deepEqual(Object.keys(assets.geometry_by_side), ['main_top', 'main_bot']);
});

test('unknown board keys fail instead of silently opening another board', () => {
  assert.throws(() => resolveBoardAssets(catalog, 'missing'), /Unknown board key: missing/);
});

test('catalog entries require all source-driven board assets', () => {
  const broken = structuredClone(catalog);
  delete broken.boards['kl4-f201'].schematic;
  assert.throws(() => resolveBoardAssets(broken, 'kl4-f201'), /schematic/);
});
