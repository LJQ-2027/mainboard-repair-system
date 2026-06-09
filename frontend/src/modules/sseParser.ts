/**
 * SSE (Server-Sent Events) 流式解析器
 * 兼容多种 SSE 格式：Anthropic (data: {...}) / Kimi Code (data:{...})
 */

import type { SSEEvent } from '../types';

/**
 * 解析单条 SSE data 行，提取文本内容
 */
export function parseSSELine(line: string): string | null {
  if (!line.startsWith('data:')) {
    return null;
  }

  const dataStr = line.slice(5).trim();
  if (!dataStr || dataStr === '[DONE]') {
    return null;
  }

  try {
    const event = JSON.parse(dataStr) as SSEEvent;

    if (event.type === 'content_block_delta' && event.delta?.text) {
      return event.delta.text;
    }

    if (event.type === 'message_stop') {
      return null;
    }

    if (event.type === 'error') {
      throw new Error(event.error?.message || 'SSE 流返回错误');
    }

    return null;
  } catch (e) {
    if (e instanceof Error && line.includes('"type":"error"')) {
      throw e;
    }
    return null;
  }
}

/**
 * 将 SSE 原始文本解析为完整文本
 */
export function parseSSEStream(rawText: string): string {
  let fullText = '';
  const lines = rawText.split('\n');

  for (const line of lines) {
    const text = parseSSELine(line);
    if (text) {
      fullText += text;
    }
  }

  return fullText;
}

/**
 * 增量解析 SSE 流（模拟前端逐块读取）
 */
export function parseSSEChunk(
  chunk: string,
  buffer: string = ''
): { text: string; buffer: string } {
  let fullText = '';
  buffer += chunk;
  const lines = buffer.split('\n');
  buffer = lines.pop() || '';

  for (const line of lines) {
    const text = parseSSELine(line);
    if (text) {
      fullText += text;
    }
  }

  return { text: fullText, buffer };
}
