/**
 * Log 分析器 - MTK/展锐/Android 日志解析
 * 从 mainboard_repair_system_v7.4_updated.html 提取并重构(骨架)
 */

export interface LogAnalysisResult {
  platform: string;
  totalErrors: number;
  errors: LogError[];
  summary: string;
  recommendations: string[];
  hasCalibrationFailure: boolean;
  bands?: string[];
}

export interface LogError {
  type: string;
  band?: string;
  channel?: string;
  message: string;
  line: number;
}

/** 检测日志类型 */
export function detectLogTypes(text: string): { platform: string; types: string[] } {
  const types: string[] = [];
  let platform = '未知';

  if (/MTK|MediaTek|mt[0-9]|ACDB|META/i.test(text)) {
    platform = 'MTK';
    types.push('MTK射频校准');
  }
  if (/SPRD|Spreadtrum|Unisoc/i.test(text)) {
    platform = '展锐';
    types.push('展锐校准');
  }
  if (/Android|kernel|logcat/i.test(text)) {
    types.push('Android系统');
  }

  return { platform, types: types.length ? types : ['未识别'] };
}

/** 快速扫描日志中的错误 */
export function scanErrors(text: string): LogError[] {
  const errors: LogError[] = [];
  const lines = text.split('\n');

  const patterns = [
    { regex: /FAIL|fail|error|Error|NG\b/, type: 'CAL_FAIL' },
    { regex: /timeout|Timeout/i, type: 'TIMEOUT' },
    { regex: /Band\s*(\d+).*fail/i, type: 'BAND_FAIL' },
    { regex: /SRS.*fail/i, type: 'SRS_FAIL' },
    { regex: /MIPI.*fail|CCI.*fail/i, type: 'IO_FAIL' },
  ];

  for (let i = 0; i < lines.length; i++) {
    for (const p of patterns) {
      const m = lines[i].match(p.regex);
      if (m) {
        errors.push({
          type: p.type,
          band: m[1] || undefined,
          line: i + 1,
          message: lines[i].trim().slice(0, 200),
        });
        break;
      }
    }
    if (errors.length > 100) break; // 限制数量
  }

  return errors;
}

/** 分析日志并生成报告 */
export function analyzeLog(text: string, _fileName?: string): LogAnalysisResult {
  const { platform } = detectLogTypes(text);
  const errors = scanErrors(text);

  const bandErrors = errors.filter(e => e.type === 'BAND_FAIL');
  const bands = [...new Set(bandErrors.map(e => e.band).filter(Boolean) as string[])];

  const summary = `共扫描 ${text.split('\n').length} 行，发现 ${errors.length} 个潜在错误` +
    (bands.length ? `，涉及频段: ${bands.join(', ')}` : '');

  const recommendations: string[] = [];
  if (errors.some(e => e.type === 'CAL_FAIL')) {
    recommendations.push('存在校准失败项，建议检查对应射频通路器件');
  }
  if (errors.some(e => e.type === 'SRS_FAIL')) {
    recommendations.push('SRS 校准异常，可能为综测仪连接或天线通路问题');
  }
  if (errors.some(e => e.type === 'IO_FAIL')) {
    recommendations.push('存在通信接口异常，检查 MIPI/CCI 通路');
  }
  if (!recommendations.length) {
    recommendations.push('未发现明显错误特征，建议人工复核');
  }

  return {
    platform,
    totalErrors: errors.length,
    errors,
    summary,
    recommendations,
    hasCalibrationFailure: errors.some(e => e.type === 'CAL_FAIL'),
    bands,
  };
}
