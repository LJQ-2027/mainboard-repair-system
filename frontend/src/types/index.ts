/** 智能主板维修系统 - TypeScript 类型定义 */

/** AI 设置 */
export interface AISettings {
  apiUrl: string;
  model: string;
}

/** SSE 事件 */
export interface SSEEvent {
  type: 'content_block_delta' | 'message_stop' | 'error' | 'message_start';
  index?: number;
  delta?: {
    type?: string;
    text?: string;
  };
  error?: {
    message: string;
  };
}

/** AI 请求 Payload */
export interface AIChatPayload {
  model: string;
  system?: string;
  messages: AIMessage[];
  max_tokens?: number;
  temperature?: number;
  stream?: boolean;
}

/** AI 消息 */
export interface AIMessage {
  role: 'user' | 'assistant';
  content: string | ContentBlock[];
}

/** 内容块（支持文本/图片） */
export interface ContentBlock {
  type: 'text' | 'image';
  text?: string;
  source?: {
    type: 'base64';
    media_type: string;
    data: string;
  };
}

/** 诊断结果 */
export interface DiagnosisResult {
  id?: number;
  mode: string;
  keyword: string;
  time: string;
  summary: string;
  fullText?: string;
}

/** 健康检查响应 */
export interface HealthResponse {
  status: string;
  api_configured: boolean;
  provider: string;
  provider_id: string;
  default_model: string;
  supports_vision: boolean;
  models: string[];
}

/** 项目器件信息 */
export interface ComponentInfo {
  位号: string;
  型号?: string;
  功能: string;
  模块: string;
}

/** 项目模块 */
export interface ProjectModule {
  [moduleName: string]: ComponentInfo[];
}

/** 项目器件映射 */
export interface ComponentMap {
  [projectName: string]: ProjectModule;
}

/** 原理图图片数据 */
export interface SchematicImageData {
  base64: string;
  media_type: string;
}

/** 诊断规则 */
export interface DiagnosisRule {
  point: string;
  point_name: string;
  probability: number;
  case_count: number;
  repair_method: string;
}
