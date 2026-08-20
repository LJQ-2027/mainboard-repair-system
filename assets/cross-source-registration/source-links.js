export function mergeCompiledSchematicLinks(entity, compiled) {
  const occurrences = compiled.components?.[entity.designator];
  if (!occurrences?.length || !entity.schematic_links?.length) return entity;
  const pages = [...new Set(occurrences.map((occurrence) => occurrence.page))].sort((left, right) => left - right);
  const previews = [...occurrences]
    .filter((occurrence) => occurrence.preview_image)
    .sort((left, right) => left.page - right.page)
    .filter((occurrence, index, items) => index === 0 || occurrence.preview_image !== items[index - 1].preview_image)
    .map((occurrence) => ({ page: occurrence.page, source: occurrence.preview_image }));
  return {
    ...entity,
    schematic_links: entity.schematic_links.map((link, index) => index === 0 ? {
      ...link,
      page: `第 ${pages.join('、')} 页`,
      source_status: 'compiled_pdf_text',
      previews,
    } : link),
  };
}
