const DATABASE_NAME = 'mainboard-visual-qc';
const DATABASE_VERSION = 1;
const CASE_STORE = 'cases';

function openDatabase() {
  return new Promise((resolve, reject) => {
    if (!globalThis.indexedDB) {
      reject(new Error('IndexedDB is unavailable in this browser.'));
      return;
    }
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(CASE_STORE)) {
        const store = database.createObjectStore(CASE_STORE, { keyPath: 'case_id' });
        store.createIndex('updated_at', 'updated_at');
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function requestResult(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function withStore(mode, operation) {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(CASE_STORE, mode);
    const result = await operation(transaction.objectStore(CASE_STORE));
    await new Promise((resolve, reject) => {
      transaction.oncomplete = resolve;
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
    return result;
  } finally {
    database.close();
  }
}

export function saveVisualQcCase(visualCase, imageBlob = null) {
  const record = {
    ...structuredClone(visualCase),
    image_blob: imageBlob,
    updated_at: new Date().toISOString(),
  };
  return withStore('readwrite', (store) => requestResult(store.put(record)));
}

export async function loadVisualQcCase(caseId) {
  const record = await withStore('readonly', (store) => requestResult(store.get(caseId)));
  if (!record) return null;
  const { image_blob: imageBlob, updated_at: updatedAt, ...visualCase } = record;
  return { visualCase, imageBlob, updatedAt };
}

export async function listVisualQcCases() {
  const records = await withStore('readonly', (store) => requestResult(store.getAll()));
  return records
    .map(({ image_blob: _imageBlob, ...record }) => record)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

export function deleteVisualQcCase(caseId) {
  return withStore('readwrite', (store) => requestResult(store.delete(caseId)));
}
