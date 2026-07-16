const CATEGORY_LABELS = {
  bga_ic: 'BGA 芯片',
  crystal: '晶振',
  connector: '连接器',
  test_point: '测试点',
};

const NAME_LABELS = {
  'Power management IC': '电源管理 IC',
  eMMC: 'eMMC 存储器',
  '26 MHz crystal': '26 MHz 晶振',
  'RF/baseband device': '射频/基带器件',
  'Mainboard connector': '主板连接器',
  'Battery supply test point': '电池供电测试点',
  'Charging input test point': '充电输入测试点',
};

const MODULE_LABELS = {
  'Power management': '电源管理',
  Storage: '存储',
  Clock: '时钟',
  'RF network': '射频网络',
  'USB and power interconnect': 'USB 与电源互连',
  'Basic power': '基础供电',
  'Charging input': '充电输入',
};

const INSTRUCTION_LABELS = {
  'Follow the power-on and PMU checks; confirm supply conditions before component action.': '按开机与电源管理检测步骤排查；处理器件前先确认各路供电条件。',
  'Check the memory power path and record VDDEMMCCORE before escalation.': '检查存储供电路径，并在升级处理前记录 VDDEMMCCORE 测量值。',
  'Measure and record the X2100 output waveform; reference frequency is 26 MHz.': '测量并记录 X2100 输出波形；参考频率为 26 MHz。',
  'Use the schematic relationship for RF path inspection; no component replacement instruction is asserted.': '依据原理图关系检查射频路径；当前资料未提供器件更换结论。',
  'Inspect connector and FPC condition before continuing along the charging path.': '先检查连接器与 FPC 状态，再沿充电路径继续排查。',
  'Record VBAT1 voltage; manual reference range is 3.4 V to 4.35 V.': '记录 VBAT1 电压；手册参考范围为 3.4 V 至 4.35 V。',
  'With a charger connected, record VBUS1; manual reference input is 5 V.': '连接充电器后记录 VBUS1 电压；手册参考输入为 5 V。',
};

function sourceFallback(value) {
  return typeof value === 'string' ? value : '';
}

export function technicianEntityCopy(entity = {}) {
  const category = sourceFallback(entity.category);
  const name = sourceFallback(entity.name);
  const module = sourceFallback(entity.module);
  return {
    category: CATEGORY_LABELS[category] || category.replaceAll('_', ' '),
    name: NAME_LABELS[name] || name,
    module: MODULE_LABELS[module] || module,
  };
}

export function technicianInstruction(instruction) {
  const source = sourceFallback(instruction);
  return INSTRUCTION_LABELS[source] || source;
}
