/**
 * 智能主板维修系统 v9.0 - FastAPI + Vite + TypeScript
 * 入口文件
 */

import './style.css';
import { migrateFromLocalStorage } from './utils/storage';
import { checkHealth } from './modules/aiService';

// 数据迁移（从 localStorage → IndexedDB）
migrateFromLocalStorage().then((migrated) => {
  if (migrated) {
    console.log('[Storage] 数据已从 localStorage 迁移到 IndexedDB');
  }
});

// 健康检查
checkHealth().then((health) => {
  if (health) {
    console.log(`[Health] ${health.provider} | ${health.default_model}`);
  } else {
    console.warn('[Health] AI 代理服务未连接');
  }
});

// TODO: 初始化 UI 组件（后续实现）
// import { App } from './components/App';
// const app = new App(document.getElementById('app')!);

console.log('智能主板维修系统 v9.0 已加载');
