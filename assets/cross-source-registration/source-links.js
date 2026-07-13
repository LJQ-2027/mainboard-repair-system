export function mergeCompiledSchematicLinks(entity, compiled) {
  const occurrences = compiled.components?.[entity.designator];
  if (!occurrences?.length || !entity.schematic_links?.length) return entity;
  const pages = [...new Set(occurrences.map((occurrence) => occurrence.page))].sort((left, right) => left - right);
  return {
    ...entity,
    schematic_links: entity.schematic_links.map((link, index) => index === 0 ? {
      ...link,
      page: `第 ${pages.join('、')} 页`,
      source_status: 'compiled_pdf_text',
    } : link),
  };
}
