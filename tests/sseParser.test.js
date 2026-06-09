/**
 * @jest-environment jsdom
 */

const { parseSSELine, parseSSEStream, parseSSEChunk } = require('../js/sseParser');

describe('SSE Parser', () => {
    describe('parseSSELine', () => {
        test('should extract text from Anthropic format (with space)', () => {
            const line = 'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"hello"}}';
            expect(parseSSELine(line)).toBe('hello');
        });

        test('should extract text from Kimi Code format (without space)', () => {
            const line = 'data:{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"world"}}';
            expect(parseSSELine(line)).toBe('world');
        });

        test('should return null for non-data lines', () => {
            expect(parseSSELine('event: content_block_delta')).toBeNull();
            expect(parseSSELine('')).toBeNull();
            expect(parseSSELine('random text')).toBeNull();
        });

        test('should return null for empty data', () => {
            expect(parseSSELine('data: ')).toBeNull();
            expect(parseSSELine('data:')).toBeNull();
        });

        test('should return null for message_stop', () => {
            const line = 'data:{"type":"message_stop"}';
            expect(parseSSELine(line)).toBeNull();
        });

        test('should throw error for SSE error event', () => {
            const line = 'data:{"type":"error","error":{"message":"API key invalid"}}';
            expect(() => parseSSELine(line)).toThrow('API key invalid');
        });

        test('should handle Chinese text', () => {
            const line = 'data:{"type":"content_block_delta","delta":{"text":"这是中文"}}';
            expect(parseSSELine(line)).toBe('这是中文');
        });

        test('should handle multi-byte UTF-8 characters', () => {
            const line = 'data:{"type":"content_block_delta","delta":{"text":"QRD7635平台"}}';
            expect(parseSSELine(line)).toBe('QRD7635平台');
        });
    });

    describe('parseSSEStream', () => {
        test('should parse complete Anthropic SSE stream', () => {
            const stream = `event:message_start\ndata:{"type":"message_start"}\n\nevent:content_block_delta\ndata:{"type":"content_block_delta","delta":{"text":"Hello "}}\n\nevent:content_block_delta\ndata:{"type":"content_block_delta","delta":{"text":"World"}}\n\nevent:message_stop\ndata:{"type":"message_stop"}\n\n`;
            expect(parseSSEStream(stream)).toBe('Hello World');
        });

        test('should parse Kimi Code SSE stream (no spaces)', () => {
            const stream = `event:content_block_start\ndata:{"type":"content_block_start"}\n\nevent:content_block_delta\ndata:{"type":"content_block_delta","delta":{"text":"主板"}}\n\nevent:content_block_delta\ndata:{"type":"content_block_delta","delta":{"text":"维修"}}\n\n`;
            expect(parseSSEStream(stream)).toBe('主板维修');
        });

        test('should return empty string for empty stream', () => {
            expect(parseSSEStream('')).toBe('');
        });

        test('should handle mixed format stream', () => {
            const stream = `data: {"type":"content_block_delta","delta":{"text":"A"}}\ndata:{"type":"content_block_delta","delta":{"text":"B"}}\ndata: {"type":"content_block_delta","delta":{"text":"C"}}\n`;
            expect(parseSSEStream(stream)).toBe('ABC');
        });
    });

    describe('parseSSEChunk', () => {
        test('should handle chunked data correctly', () => {
            let result = parseSSEChunk('data:{"type":"content_block_delta","delta":{"text":"Hel"}}\ndata:{"type":"content_block_delta","delta":{"text":"lo"}}\n');
            expect(result.text).toBe('Hello');
            expect(result.buffer).toBe('');
        });

        test('should preserve incomplete line in buffer', () => {
            const chunk1 = 'data:{"type":"content_block_delta","delta":{"text":"Hello"}}\ndata:{"type":"content_block_delta","delta":{"text":" Wo';
            let result = parseSSEChunk(chunk1);
            expect(result.text).toBe('Hello');
            expect(result.buffer).toBe('data:{"type":"content_block_delta","delta":{"text":" Wo');

            const chunk2 = 'rld"}}\n';
            result = parseSSEChunk(chunk2, result.buffer);
            expect(result.text).toBe(' World');
            expect(result.buffer).toBe('');
        });

        test('should handle empty chunks', () => {
            const result = parseSSEChunk('', 'some buffer');
            expect(result.text).toBe('');
            expect(result.buffer).toBe('some buffer');
        });
    });
});
