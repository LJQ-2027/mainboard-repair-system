// 项目案例库（按项目分组的故障案例和位号映射）
// 每个项目拥有独立的诊断规则和故障现象索引
// 未匹配到项目时回退到全局 diagnosisRules + phenomenaSearchIndex

const projectCases = {
  "X6878": {
    projectName: "X6878-Q352",
    description: "智能手机主板 (SM7635/QRD7635平台)",

    // 项目专属诊断规则（覆盖全局规则）
    diagnosisRules: {
      "不开机": [
        { "point": "U0501", "point_name": "PMK7635主PMIC", "component_type": "IC芯片", "probability": 45.0, "case_count": 185, "fault_type": "少件/虚焊", "repair_method": "补焊或更换" },
        { "point": "U2201", "point_name": "PM7550辅助电源", "component_type": "IC芯片", "probability": 22.0, "case_count": 90, "fault_type": "输出异常", "repair_method": "量测各路BUCK/LDO，异常更换" },
        { "point": "U1601", "point_name": "LPDDR4X内存", "component_type": "IC芯片", "probability": 15.0, "case_count": 62, "fault_type": "虚焊", "repair_method": "重新植球" },
        { "point": "J2401", "point_name": "电池BTB连接器", "component_type": "连接器", "probability": 10.0, "case_count": 41, "fault_type": "氧化/变形", "repair_method": "清洁或更换BTB" },
        { "point": "U2401", "point_name": "PMIV0108充电管理", "component_type": "IC芯片", "probability": 8.0, "case_count": 33, "fault_type": "充电通路断开", "repair_method": "量测VBUS_OVP，更换" }
      ],
      "充电异常": [
        { "point": "U2401", "point_name": "PMIV0108充电IC", "component_type": "IC芯片", "probability": 40.0, "case_count": 120, "fault_type": "充电通路异常", "repair_method": "量测各管脚阻抗，更换" },
        { "point": "U3401", "point_name": "SMB1393快充芯片", "component_type": "IC芯片", "probability": 30.0, "case_count": 90, "fault_type": "快充失效", "repair_method": "检查Fly电容，更换Charge Pump" },
        { "point": "J2401", "point_name": "电池BTB连接器", "component_type": "连接器", "probability": 15.0, "case_count": 45, "fault_type": "接触不良", "repair_method": "检查BTB扣合，更换FPC" },
        { "point": "U0501", "point_name": "PMK7635主PMIC", "component_type": "IC芯片", "probability": 10.0, "case_count": 30, "fault_type": "充电逻辑异常", "repair_method": "更换PMIC" },
        { "point": "D2401", "point_name": "TVS保护二极管", "component_type": "二极管", "probability": 5.0, "case_count": 15, "fault_type": "击穿短路", "repair_method": "更换TVS" }
      ],
      "无服务": [
        { "point": "U8001", "point_name": "WCN6755 WiFi/BT", "component_type": "IC芯片", "probability": 35.0, "case_count": 70, "fault_type": "虚焊", "repair_method": "重新焊接" },
        { "point": "ANT10801", "point_name": "天线连接器", "component_type": "连接器", "probability": 25.0, "case_count": 50, "fault_type": "破损/接触不良", "repair_method": "更换同轴线" },
        { "point": "U5502", "point_name": "射频PA芯片", "component_type": "IC芯片", "probability": 20.0, "case_count": 40, "fault_type": "烧毁", "repair_method": "更换PA" },
        { "point": "U6805", "point_name": "射频开关", "component_type": "IC芯片", "probability": 12.0, "case_count": 24, "fault_type": "通路断开", "repair_method": "量测阻抗，更换" },
        { "point": "U6607", "point_name": "射频收发器", "component_type": "IC芯片", "probability": 8.0, "case_count": 16, "fault_type": "物料不良", "repair_method": "更换" }
      ],
      "无显示": [
        { "point": "J5401", "point_name": "显示FPC连接器", "component_type": "连接器", "probability": 40.0, "case_count": 80, "fault_type": "变形/虚焊", "repair_method": "检查FPC扣合，更换连接器" },
        { "point": "U3001", "point_name": "PMIV0108 OLED驱动", "component_type": "IC芯片", "probability": 30.0, "case_count": 60, "fault_type": "输出电压异常", "repair_method": "量测AVDD/ELVDD，更换" },
        { "point": "U0501", "point_name": "PMK7635主PMIC", "component_type": "IC芯片", "probability": 15.0, "case_count": 30, "fault_type": "显示供电缺失", "repair_method": "量测LDO输出" },
        { "point": "C5401", "point_name": "显示滤波电容", "component_type": "电容", "probability": 10.0, "case_count": 20, "fault_type": "短路", "repair_method": "更换电容" },
        { "point": "D5401", "point_name": "背光驱动IC", "component_type": "IC芯片", "probability": 5.0, "case_count": 10, "fault_type": "烧毁", "repair_method": "更换背光IC" }
      ],
      "卡logo/重启": [
        { "point": "U1701", "point_name": "UFS存储", "component_type": "IC芯片", "probability": 35.0, "case_count": 70, "fault_type": "坏块/虚焊", "repair_method": "更换UFS" },
        { "point": "U1601", "point_name": "LPDDR4X内存", "component_type": "IC芯片", "probability": 30.0, "case_count": 60, "fault_type": "虚焊", "repair_method": "重新植球" },
        { "point": "U0501", "point_name": "PMK7635主PMIC", "component_type": "IC芯片", "probability": 20.0, "case_count": 40, "fault_type": "电压不稳", "repair_method": "量测各路输出" },
        { "point": "Y2601", "point_name": "26MHz晶体", "component_type": "晶振", "probability": 10.0, "case_count": 20, "fault_type": "频偏/不起振", "repair_method": "更换晶体" },
        { "point": "U8002", "point_name": "NFC芯片", "component_type": "IC芯片", "probability": 5.0, "case_count": 10, "fault_type": "短路导致重启", "repair_method": "更换NFC" }
      ]
    },

    // 项目专属故障现象索引
    phenomenaSearchIndex: {
      "校准失败": {
        "phenomena": "校准终测报错 (X6878-Q352)",
        "top_components": [
          { "point": "U0501", "component_type": "IC芯片", "probability": 35.0, "case_count": 120, "fault_type": "少件", "repair_method": "重新焊接" },
          { "point": "U6805", "component_type": "IC芯片", "probability": 8.0, "case_count": 28, "fault_type": "物料不良", "repair_method": "更换" }
        ],
        "total_count": 380
      },
      "下载无端口": {
        "phenomena": "无法进入下载模式 (X6878-Q352)",
        "top_components": [
          { "point": "U0501", "component_type": "IC芯片", "probability": 50.0, "case_count": 200, "fault_type": "少件", "repair_method": "重新焊接" },
          { "point": "U1601", "component_type": "IC芯片", "probability": 3.0, "case_count": 12, "fault_type": "物料不良", "repair_method": "更换" }
        ],
        "total_count": 400
      },
      "WIFI不良": {
        "phenomena": "WiFi无法连接/信号弱 (X6878-Q352)",
        "top_components": [
          { "point": "U8001", "component_type": "IC芯片", "probability": 75.0, "case_count": 30, "fault_type": "虚焊", "repair_method": "重新焊接" },
          { "point": "ANT10801", "component_type": "连接器", "probability": 25.0, "case_count": 10, "fault_type": "破损", "repair_method": "更换天线" }
        ],
        "total_count": 40
      }
    },

    // 项目器件位号映射（AI诊断时注入）
    componentMap: {
      "电源管理": [
        { "位号": "U0501", "型号": "PMK7635", "功能": "主PMIC，提供各路BUCK/LDO" },
        { "位号": "U2201", "型号": "PM7550", "功能": "辅助电源，6路SMPS + 多路LDO" },
        { "位号": "U2401", "型号": "PMIV0108", "功能": "充电管理+电量计" },
        { "位号": "U3401", "型号": "SMB1393", "功能": "快充Charge Pump" }
      ],
      "存储与内存": [
        { "位号": "U1701", "型号": "UFS 3.1", "功能": "闪存存储" },
        { "位号": "U1601", "型号": "LPDDR4X", "功能": "运行内存" }
      ],
      "射频": [
        { "位号": "U8001", "型号": "WCN6755", "功能": "WiFi/BT/FM三合一" },
        { "位号": "U5502", "型号": "QPA6590", "功能": "射频功率放大器" },
        { "位号": "U6607", "型号": "SDR435", "功能": "射频收发器" },
        { "位号": "U6805", "型号": "QDM2316", "功能": "分集接收模组" },
        { "位号": "ANT10801", "型号": "RF Connector", "功能": "天线同轴连接座" }
      ],
      "显示": [
        { "位号": "U3001", "型号": "PMIV0108", "功能": "OLED驱动电源" },
        { "位号": "J5401", "型号": "Display FPC", "功能": "显示排线连接器" }
      ],
      "时钟": [
        { "位号": "Y2601", "型号": "26MHz TCXO", "功能": "系统主时钟晶体" }
      ],
      "连接器": [
        { "位号": "J2401", "型号": "Battery BTB", "功能": "电池板对板连接器" },
        { "位号": "J3801", "型号": "Main FPC BTB", "功能": "主板排线连接器" }
      ]
    }
  }
  // 后续新增项目：
  // "Q352A": { ... },
  // "Camon20": { ... }
};

// 导出为全局变量（兼容现有 HTML 的 <script src> 加载方式）
