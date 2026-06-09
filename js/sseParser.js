/**
 * SSE (Server-Sent Events) 流式解析器
 * 兼容多种 SSE 格式：
 * - Anthropic 格式: data: {"type":"content_block_delta",...}
 * - Kimi Code 格式: data:{"type":"content_block_delta",...} (无空格)
 */

/**
 * 解析单条 SSE data 行，提取文本内容
 * @param {string} line - SSE 行内容
 * @returns {string|null} - 提取的文本，非 content_block_delta 返回 null
 */
function parseSSELine(line) {
    if (!line.startsWith('data:')) {
        return null;
    }
    const dataStr = line.slice(5).trim();
    if (!dataStr) {
        return null;
    }
    if (dataStr === '[DONE]') {
        return null; // OpenAI 流结束标记
    }
    try {
        const event = JSON.parse(dataStr);
        if (event.type === 'content_block_delta' && event.delta && event.delta.text) {
            return event.delta.text;
        }
        if (event.type === 'message_stop') {
            return null; // 消息结束
        }
        if (event.type === 'error') {
            throw new Error(event.error?.message || 'SSE 流返回错误');
        }
        return null;
    } catch (e) {
        // 重新抛出 SSE 错误，其他解析错误静默跳过
        if (e instanceof Error && (e.message.includes('SSE 流返回错误') || line.includes('"type":"error"'))) {
            throw e;
        }
        return null;
    }
}

/**
 * 将 SSE 原始文本解析为完整文本
 * @param {string} rawText - 完整的 SSE 响应文本
 * @returns {string} - 提取的完整文本
 */
function parseSSEStream(rawText) {
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
 * @param {string} chunk - 新接收的数据块
 * @param {string} buffer - 上次的缓冲区
 * @returns {{text: string, buffer: string}} - 提取的文本和新的缓冲区
 */
function parseSSEChunk(chunk, buffer = '') {
    let fullText = '';
    buffer += chunk;
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // 保留不完整的最后一行
    for (const line of lines) {
        const text = parseSSELine(line);
        if (text) {
            fullText += text;
        }
    }
    return { text: fullText, buffer };
}

module.exports = {
    parseSSELine,
    parseSSEStream,
    parseSSEChunk
};
