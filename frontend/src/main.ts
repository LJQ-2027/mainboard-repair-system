/**
 * 智能主板维修系统 v9.0 - 入口文件
 */

import './style.css';
import { migrateFromLocalStorage } from './utils/storage';
import { checkHealth } from './modules/aiService';

// ====== 主题切换 ======
function initThemeToggle() {
  const btn = document.createElement('button');
  btn.id = 'themeToggle';
  btn.title = '切换主题';
  btn.textContent = '🌙';
  btn.onclick = () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (isDark) {
      document.documentElement.removeAttribute('data-theme');
      btn.textContent = '🌙';
      localStorage.setItem('theme', 'light');
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
      btn.textContent = '☀️';
      localStorage.setItem('theme', 'dark');
    }
  };

  // 恢复主题
  const saved = localStorage.getItem('theme');
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.setAttribute('data-theme', 'dark');
    btn.textContent = '☀️';
  }

  document.body.appendChild(btn);
}

// ====== 响应式检测 ======
function initResponsive() {
  const mq = window.matchMedia('(max-width: 480px)');
  document.documentElement.setAttribute('data-viewport', mq.matches ? 'mobile' : 'desktop');
  mq.addEventListener('change', (e) => {
    document.documentElement.setAttribute('data-viewport', e.matches ? 'mobile' : 'desktop');
  });
}

// ====== 初始化 ======
migrateFromLocalStorage().then((migrated) => {
  if (migrated) console.log('[Storage] 数据已迁移到 IndexedDB');
});

checkHealth().then((health) => {
  if (health) console.log(`[Health] ${health.provider} | ${health.default_model}`);
  else console.warn('[Health] AI 代理服务未连接');
});

initThemeToggle();
initResponsive();

console.log('智能主板维修系统 v9.0 已加载');
