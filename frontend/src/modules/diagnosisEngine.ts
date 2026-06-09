/**
 * 诊断引擎 - 关键词匹配、规则引擎、AI 上下文构建
 * 从 mainboard_repair_system_v7.4_updated.html 提取并重构
 */

import type { DiagnosisResult } from '../types';

// ===== 全局数据引用（由外部 data/*.js 注入） =====
declare const hardwareKnowledgeBase: Record<string, {
  title?: string;
  keywords?: string[];
  principle?: string;
  diagnosis?: string[];
  keySignals?: string;
  commonFaults?: string;
  source?: string;
}> & { analysisMethods?: { steps: string[]; methods: Array<{ name: string; desc: string }> } };

declare const diagnosisRules: Record<string, Array<{
  point: string;
  point_name?: string;
  probability: number;
  case_count: number;
  fault_type?: string;
  repair_method: string;
}>>;

declare const phenomenaSearchIndex: Record<string, {
  phenomena: string;
  top_components: Array<{
    point: string;
    component_type: string;
    probability: number;
    case_count: number;
    fault_type: string;
    repair_method: string;
  }>;
  total_count: number;
}>;

declare const projectDatabase: Record<string, {
  name: string;
  schematicUrl?: string;
  layoutUrl?: string;
  bomUrl?: string;
  sopUrl?: string;
}>;

// ===== 关键词分析 =====

export function analyzeKeywords(
  text: string,
  type: 'resource' | 'diagnosis' = 'diagnosis'
): string[] {
  if (!text) return [];

  if (type === 'resource') {
    const keys = Object.keys(projectDatabase || {});
    return keys
      .filter(k => text.toLowerCase().includes(k.toLowerCase()) || k.toLowerCase().includes(text.toLowerCase()))
      .slice(0, 5);
  }

  const allKeys = [...Object.keys(diagnosisRules || {}), ...Object.keys(phenomenaSearchIndex || {})];
  return allKeys
    .filter(k => text.toLowerCase().includes(k.toLowerCase()) || k.toLowerCase().includes(text.toLowerCase()))
    .slice(0, 5);
}

// ===== 诊断上下文构建（给 AI 用的 system prompt 上下文） =====

export interface DiagnosisContext {
  localMatchInfo: string;
  knowledgeInfo: string;
  frameworkInfo: string;
  projectComponentInfo: string;
  hasLocalMatch: boolean;
  hasProjectMap: boolean;
}

export function buildDiagnosisContext(
  symptom: string,
  _projectModel?: string,
  componentMapText?: string
): DiagnosisContext {
  const symptomLower = symptom.toLowerCase();

  // 1. 匹配本地规则库
  let localMatchInfo = '';
  for (const [faultType, points] of Object.entries(diagnosisRules || {})) {
    if (symptomLower.includes(faultType.toLowerCase())) {
      localMatchInfo += `\n【本地规则库匹配 - ${faultType}】\n`;
      (points as Array<Record<string, unknown>>).slice(0, 5).forEach((p, i) => {
        localMatchInfo += `  ${i + 1}. ${p.point} (${p.point_name || ''}) - 概率${p.probability}% - ${(p as Record<string, number>).case_count || 0}例 - ${p.repair_method}\n`;
      });
      break;
    }
  }

  // 2. 从现象搜索索引匹配
  if (!localMatchInfo) {
    for (const [keyword, data] of Object.entries(phenomenaSearchIndex || {})) {
      if (symptomLower.includes(keyword.toLowerCase())) {
        localMatchInfo += `\n【多维表格案例库匹配 - ${data.phenomena}】共${data.total_count}例\n`;
        data.top_components.slice(0, 5).forEach((p, i) => {
          localMatchInfo += `  ${i + 1}. ${p.point} - 概率${p.probability}% - ${p.case_count}例 - ${p.repair_method}\n`;
        });
        break;
      }
    }
  }

  // 3. 匹配硬件知识库
  let knowledgeInfo = '';
  for (const [key, module] of Object.entries(hardwareKnowledgeBase || {})) {
    if (key === 'analysisMethods') continue;
    const mod = module as { title?: string; keywords?: string[]; principle?: string; keySignals?: string; commonFaults?: string; diagnosis?: string[] };
    const keywords = mod.keywords || [];
    if (keywords.some((kw: string) => symptomLower.includes(kw.toLowerCase()))) {
      knowledgeInfo += `\n【${mod.title}】\n`;
      if (mod.principle) knowledgeInfo += `工作原理：${mod.principle}\n`;
      if (mod.keySignals) knowledgeInfo += `关键信号：${mod.keySignals}\n`;
      if (mod.commonFaults) knowledgeInfo += `常见故障：${mod.commonFaults}\n`;
      if (mod.diagnosis) {
        knowledgeInfo += `排查步骤：\n${mod.diagnosis.map((s: string, i: number) => `  ${i + 1}. ${s}`).join('\n')}\n`;
      }
    }
  }

  // 4. 分析方法框架
  const methods = hardwareKnowledgeBase?.analysisMethods;
  const frameworkInfo = methods
    ? `六步分析法：${methods.steps.join(' → ')}\n分析方法：${methods.methods.map(m => `${m.name}: ${m.desc}`).join('; ')}`
    : '';

  // 5. 项目位号信息
  const projectComponentInfo = componentMapText || '';

  return {
    localMatchInfo,
    knowledgeInfo,
    frameworkInfo,
    projectComponentInfo,
    hasLocalMatch: !!localMatchInfo,
    hasProjectMap: !!projectComponentInfo,
  };
}

// ===== 诊断历史 =====

const DIAGNOSIS_HISTORY_KEY = 'mainboardDiagnosisHistoryV73';
const MAX_HISTORY_SIZE = 20;

export function getDiagnosisHistory(): DiagnosisResult[] {
  try {
    return JSON.parse(localStorage.getItem(DIAGNOSIS_HISTORY_KEY) || '[]');
  } catch {
    return [];
  }
}

export function saveDiagnosisHistory(entry: DiagnosisResult): void {
  const history = [entry, ...getDiagnosisHistory()].slice(0, MAX_HISTORY_SIZE);
  localStorage.setItem(DIAGNOSIS_HISTORY_KEY, JSON.stringify(history));
}

export function clearDiagnosisHistory(): void {
  localStorage.removeItem(DIAGNOSIS_HISTORY_KEY);
}

// ===== 导出历史 =====

export function exportDiagnosisHistory(): string {
  const history = getDiagnosisHistory();
  if (history.length === 0) return '';

  let text = '智能主板维修系统 - 诊断历史导出\n';
  text += '='.repeat(60) + '\n\n';

  history.forEach((entry, i) => {
    text += `#${i + 1} [${entry.mode}] ${entry.time}\n`;
    text += `  关键词: ${entry.keyword}\n`;
    text += `  摘要: ${entry.summary}\n`;
    text += '-'.repeat(60) + '\n';
  });

  return text;
}
