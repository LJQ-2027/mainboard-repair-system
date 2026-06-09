/**
 * AI 服务 - 封装 AI API 调用
 */

import type { AIChatPayload, ContentBlock, HealthResponse, SchematicImageData } from '../types';

const DEFAULT_API_URL = 'http://localhost:8899';

/** 获取 AI 设置 */
export function getAISettings(): { apiUrl: string; model: string } {
  const AI_SETTINGS_KEY = 'aiSettingsV2';
  const defaults = { apiUrl: DEFAULT_API_URL, model: 'kimi-k2-thinking' };

  try {
    const saved = JSON.parse(localStorage.getItem(AI_SETTINGS_KEY) || '{}');
    // 自动清理旧模型设置
    if (saved.model?.startsWith('deepseek')) {
      delete saved.model;
      localStorage.setItem(AI_SETTINGS_KEY, JSON.stringify(saved));
    }
    return { ...defaults, ...saved };
  } catch {
    return defaults;
  }
}

/** 保存 AI 设置 */
export function saveAISettings(apiUrl: string, model: string): void {
  localStorage.setItem('aiSettingsV2', JSON.stringify({ apiUrl, model }));
}

/** 健康检查 */
export async function checkHealth(
  apiUrl: string = DEFAULT_API_URL,
  timeoutMs: number = 3000
): Promise<HealthResponse | null> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const resp = await fetch(`${apiUrl}/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timer);
    return await resp.json();
  } catch {
    return null;
  }
}

/** 流式 AI 调用 */
export async function callAIStream(
  payload: AIChatPayload,
  onChunk: (fullText: string, chunk: string) => void,
  onDone: (fullText: string) => void,
  onError: (error: string) => void
): Promise<void> {
  const settings = getAISettings();

  try {
    const resp = await fetch(`${settings.apiUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }));
      onError(errData.error || `请求失败 (${resp.status})`);
      return;
    }

    const reader = resp.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data:')) {
          const dataStr = line.slice(5).trim();
          if (!dataStr) continue;
          try {
            const event = JSON.parse(dataStr);
            if (event.type === 'content_block_delta' && event.delta?.text) {
              fullText += event.delta.text;
              onChunk(fullText, event.delta.text);
            } else if (event.type === 'error') {
              onError(event.error?.message || 'API 返回错误');
              return;
            }
          } catch {
            // 跳过非 JSON 行
          }
        }
      }
    }

    onDone(fullText);
  } catch (e) {
    onError(
      '网络错误：无法连接到 AI 代理服务。请确认已启动后端服务。'
    );
  }
}

/** 构建 AI 诊断 Payload */
export function buildDiagnosisPayload(
  systemPrompt: string,
  userMessage: string | (string | SchematicImageData)[],
  model?: string
): AIChatPayload {
  const settings = getAISettings();

  let userContent: string | ContentBlock[];

  if (Array.isArray(userMessage)) {
    userContent = userMessage.map((item): ContentBlock => {
      if (typeof item === 'string') {
        return { type: 'text', text: item };
      } else {
        return {
          type: 'image',
          source: {
            type: 'base64',
            media_type: item.media_type,
            data: item.base64,
          },
        };
      }
    });
  } else {
    userContent = userMessage;
  }

  return {
    model: model || settings.model,
    system: systemPrompt,
    messages: [{ role: 'user', content: userContent }],
    max_tokens: 4096,
    temperature: 0.7,
    stream: true,
  };
}
