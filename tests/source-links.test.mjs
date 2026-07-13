import test from 'node:test';
import assert from 'node:assert/strict';

import { mergeCompiledSchematicLinks } from '../assets/cross-source-registration/source-links.js';

test('compiled schematic occurrences replace a vague page label with exact pages', () => {
  const entity = {
    designator: 'U2001',
    schematic_links: [{ source: 'schematic.pdf', page: 'power sheets', facts: ['Designator U2001'] }],
  };
  const compiled = { components: { U2001: [{ page: 7 }, { page: 6 }, { page: 7 }] } };
  const result = mergeCompiledSchematicLinks(entity, compiled);
  assert.equal(result.schematic_links[0].page, '第 6、7 页');
  assert.equal(result.schematic_links[0].source_status, 'compiled_pdf_text');
  assert.deepEqual(result.schematic_links[0].facts, ['Designator U2001']);
});

test('an entity absent from the compiled schematic keeps reviewed evidence', () => {
  const entity = { designator: 'U9999', schematic_links: [{ source: 'manual', page: 'reviewed', facts: [] }] };
  assert.deepEqual(mergeCompiledSchematicLinks(entity, { components: {} }), entity);
});
