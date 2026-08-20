const REQUIRED_ASSET_KEYS = ['title', 'data', 'schematic', 'side_manifest'];

export function resolveBoardKey(url, catalog) {
  const requested = url.searchParams.get('board')?.trim();
  return requested || catalog.default_board_key;
}

export function resolveBoardAssets(catalog, boardKey) {
  const board = catalog.boards?.[boardKey];
  if (!board) throw new Error(`Unknown board key: ${boardKey}`);

  REQUIRED_ASSET_KEYS.forEach((key) => {
    if (typeof board[key] !== 'string' || !board[key].trim()) {
      throw new Error(`Board ${boardKey} requires ${key}`);
    }
  });

  const geometryEntries = Object.entries(board.geometry_by_side || {});
  if (!geometryEntries.length || geometryEntries.some(([, url]) => typeof url !== 'string' || !url.trim())) {
    throw new Error(`Board ${boardKey} requires geometry_by_side`);
  }

  return {
    ...board,
    shield: board.shield || null,
    atlas: board.atlas || null,
  };
}
