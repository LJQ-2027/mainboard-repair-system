/**
 * IndexedDB 存储封装 - 替代 localStorage
 * 支持：设置、诊断历史、项目位号数据
 */

import { openDB, type DBSchema, type IDBPDatabase } from 'idb';
import type { DiagnosisResult, ComponentMap } from '../types';

const DB_NAME = 'MainboardRepairDB';
const DB_VERSION = 1;

interface RepairDBSchema extends DBSchema {
  settings: {
    key: string;
    value: { key: string; value: unknown };
  };
  diagnosisHistory: {
    key: number;
    value: DiagnosisResult;
    indexes: { byTime: string };
  };
  componentMaps: {
    key: string;
    value: { project: string; modules: ComponentMap[string] };
  };
}

let dbPromise: Promise<IDBPDatabase<RepairDBSchema>> | null = null;

function getDB(): Promise<IDBPDatabase<RepairDBSchema>> {
  if (!dbPromise) {
    dbPromise = openDB<RepairDBSchema>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        // 设置表
        if (!db.objectStoreNames.contains('settings')) {
          db.createObjectStore('settings', { keyPath: 'key' });
        }
        // 诊断历史表
        if (!db.objectStoreNames.contains('diagnosisHistory')) {
          const historyStore = db.createObjectStore('diagnosisHistory', {
            keyPath: 'id',
            autoIncrement: true,
          });
          historyStore.createIndex('byTime', 'time');
        }
        // 位号数据表
        if (!db.objectStoreNames.contains('componentMaps')) {
          db.createObjectStore('componentMaps', { keyPath: 'project' });
        }
      },
    });
  }
  return dbPromise;
}

/** ===== 设置 ===== */

export async function getSetting<T>(key: string, defaultValue?: T): Promise<T | undefined> {
  const db = await getDB();
  const item = await db.get('settings', key);
  return item ? (item.value as T) : defaultValue;
}

export async function setSetting<T>(key: string, value: T): Promise<void> {
  const db = await getDB();
  await db.put('settings', { key, value });
}

/** ===== 诊断历史 ===== */

export async function getDiagnosisHistory(limit: number = 50): Promise<DiagnosisResult[]> {
  const db = await getDB();
  return db.getAllFromIndex('diagnosisHistory', 'byTime', undefined, limit);
}

export async function addDiagnosisHistory(entry: DiagnosisResult): Promise<void> {
  const db = await getDB();
  await db.add('diagnosisHistory', entry);
  // 只保留最近 100 条
  const all = await db.getAll('diagnosisHistory');
  if (all.length > 100) {
    const toDelete = all.slice(0, all.length - 100);
    const tx = db.transaction('diagnosisHistory', 'readwrite');
    for (const item of toDelete) {
      if (item.id !== undefined) {
        await tx.store.delete(item.id);
      }
    }
    await tx.done;
  }
}

export async function clearDiagnosisHistory(): Promise<void> {
  const db = await getDB();
  await db.clear('diagnosisHistory');
}

/** ===== 项目位号数据 ===== */

export async function getComponentMap(project: string): Promise<ComponentMap[string] | undefined> {
  const db = await getDB();
  const item = await db.get('componentMaps', project);
  return item?.modules;
}

export async function saveComponentMap(project: string, modules: ComponentMap[string]): Promise<void> {
  const db = await getDB();
  await db.put('componentMaps', { project, modules });
}

export async function getAllComponentMaps(): Promise<ComponentMap> {
  const db = await getDB();
  const items = await db.getAll('componentMaps');
  const result: ComponentMap = {};
  for (const item of items) {
    result[item.project] = item.modules;
  }
  return result;
}

/** ===== 数据迁移（从 localStorage） ===== */

export async function migrateFromLocalStorage(): Promise<boolean> {
  // 检查是否已迁移
  const migrated = await getSetting<boolean>('__migrated_from_localStorage', false);
  if (migrated) return false;

  let hasData = false;

  // 迁移设置
  try {
    const oldSettings = localStorage.getItem('aiSettingsV2');
    if (oldSettings) {
      await setSetting('aiSettings', JSON.parse(oldSettings));
      hasData = true;
    }
  } catch {
    // ignore
  }

  // 迁移诊断历史
  try {
    const oldHistory = localStorage.getItem('mainboardDiagnosisHistoryV73');
    if (oldHistory) {
      const entries: DiagnosisResult[] = JSON.parse(oldHistory);
      for (const entry of entries) {
        await addDiagnosisHistory(entry);
      }
      hasData = true;
    }
  } catch {
    // ignore
  }

  // 迁移位号数据
  try {
    const oldMap = localStorage.getItem('projectComponentMapV1');
    if (oldMap) {
      const map: ComponentMap = JSON.parse(oldMap);
      for (const [project, modules] of Object.entries(map)) {
        await saveComponentMap(project, modules);
      }
      hasData = true;
    }
  } catch {
    // ignore
  }

  // 标记已迁移
  await setSetting('__migrated_from_localStorage', true);
  return hasData;
}

/** ===== 导出/导入 ===== */

export async function exportAllData(): Promise<object> {
  const settings: Record<string, unknown> = {};
  const db = await getDB();
  const allSettings = await db.getAll('settings');
  for (const s of allSettings) {
    settings[s.key] = s.value;
  }

  return {
    version: DB_VERSION,
    exportedAt: new Date().toISOString(),
    settings,
    history: await getDiagnosisHistory(1000),
    componentMaps: await getAllComponentMaps(),
  };
}

export async function importAllData(data: {
  history?: DiagnosisResult[];
  componentMaps?: ComponentMap;
}): Promise<void> {
  if (data.history) {
    await clearDiagnosisHistory();
    for (const entry of data.history) {
      await addDiagnosisHistory(entry);
    }
  }

  if (data.componentMaps) {
    const db = await getDB();
    await db.clear('componentMaps');
    for (const [project, modules] of Object.entries(data.componentMaps)) {
      await saveComponentMap(project, modules);
    }
  }
}
