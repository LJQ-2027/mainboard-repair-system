// 历史案例诊断规则库
// 从主页面拆分，便于后续协作维护。
const diagnosisRules = {
  "不开机": [
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 38.9,
      "case_count": 74,
      "fault_type": "少件/物料不良",
      "repair_method": "补件焊接/更换"
    },
    {
      "point": "U1701",
      "point_name": "eMMC/UFS存储",
      "component_type": "IC芯片",
      "probability": 18.9,
      "case_count": 36,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U1601",
      "point_name": "DDR内存",
      "component_type": "IC芯片",
      "probability": 15.8,
      "case_count": 30,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "J3801",
      "point_name": "电池BTB连接器",
      "component_type": "连接器",
      "probability": 8.4,
      "case_count": 16,
      "fault_type": "破损/假焊",
      "repair_method": "更换"
    },
    {
      "point": "U2601",
      "point_name": "电源管理IC",
      "component_type": "IC芯片",
      "probability": 6.3,
      "case_count": 12,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "充电异常": [
    {
      "point": "U3901",
      "point_name": "充电管理IC",
      "component_type": "IC芯片",
      "probability": 88.6,
      "case_count": 39,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U3501",
      "point_name": "电源管理IC",
      "component_type": "IC芯片",
      "probability": 4.5,
      "case_count": 2,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "C3816",
      "point_name": "充电通路电容",
      "component_type": "电容",
      "probability": 3.4,
      "case_count": 1,
      "fault_type": "连锡",
      "repair_method": "清理重焊"
    }
  ],
  "死机重启": [
    {
      "point": "U8001",
      "point_name": "无线收发器(WCN)",
      "component_type": "IC芯片",
      "probability": 33.3,
      "case_count": 9,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 22.2,
      "case_count": 6,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U2601",
      "point_name": "电源管理IC",
      "component_type": "IC芯片",
      "probability": 11.1,
      "case_count": 3,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U2201",
      "point_name": "充电管理IC",
      "component_type": "IC芯片",
      "probability": 11.1,
      "case_count": 3,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U1601",
      "point_name": "DDR内存",
      "component_type": "IC芯片",
      "probability": 11.1,
      "case_count": 3,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "显示异常": [
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 32.7,
      "case_count": 36,
      "fault_type": "假焊",
      "repair_method": "重焊"
    },
    {
      "point": "U2601",
      "point_name": "显示驱动IC",
      "component_type": "IC芯片",
      "probability": 28.2,
      "case_count": 31,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "C5209",
      "point_name": "显示通路电容",
      "component_type": "电容",
      "probability": 9.1,
      "case_count": 10,
      "fault_type": "破损",
      "repair_method": "更换"
    }
  ],
  "音频异常": [
    {
      "point": "U6001",
      "point_name": "音频功放IC",
      "component_type": "IC芯片",
      "probability": 34.6,
      "case_count": 83,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U4101",
      "point_name": "音频功放IC",
      "component_type": "IC芯片",
      "probability": 22.5,
      "case_count": 54,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "M4301",
      "point_name": "副麦克风",
      "component_type": "麦克风",
      "probability": 12.5,
      "case_count": 30,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "MIC101",
      "point_name": "麦克风",
      "component_type": "麦克风",
      "probability": 8.3,
      "case_count": 20,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U4301",
      "point_name": "音频功放IC",
      "component_type": "IC芯片",
      "probability": 4.6,
      "case_count": 11,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "下载失败": [
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 28.5,
      "case_count": 228,
      "fault_type": "少件/连锡/物料不良",
      "repair_method": "补件焊接/清理重焊/更换"
    },
    {
      "point": "U1601",
      "point_name": "DDR内存",
      "component_type": "IC芯片",
      "probability": 25.3,
      "case_count": 203,
      "fault_type": "少件/物料不良",
      "repair_method": "补件焊接/更换"
    },
    {
      "point": "U1701",
      "point_name": "eMMC/UFS存储",
      "component_type": "IC芯片",
      "probability": 12.5,
      "case_count": 100,
      "fault_type": "少件/物料不良",
      "repair_method": "补件焊接/更换"
    },
    {
      "point": "U1801",
      "point_name": "eMMC/UFS存储",
      "component_type": "IC芯片",
      "probability": 4.5,
      "case_count": 36,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U2401",
      "point_name": "快充芯片",
      "component_type": "IC芯片",
      "probability": 3.7,
      "case_count": 30,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "耦合不良": [
    {
      "point": "J301",
      "point_name": "射频座",
      "component_type": "连接器",
      "probability": 19.6,
      "case_count": 40,
      "fault_type": "破损",
      "repair_method": "更换"
    },
    {
      "point": "J303",
      "point_name": "射频座",
      "component_type": "连接器",
      "probability": 19.1,
      "case_count": 39,
      "fault_type": "破损",
      "repair_method": "更换"
    },
    {
      "point": "U9003",
      "point_name": "天线开关",
      "component_type": "IC芯片",
      "probability": 8.8,
      "case_count": 18,
      "fault_type": "物料不良/连锡",
      "repair_method": "更换"
    },
    {
      "point": "ANT301",
      "point_name": "天线",
      "component_type": "天线",
      "probability": 7.4,
      "case_count": 15,
      "fault_type": "破损/撞件",
      "repair_method": "更换"
    },
    {
      "point": "U9002",
      "point_name": "天线开关",
      "component_type": "IC芯片",
      "probability": 4.4,
      "case_count": 9,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "功耗异常": [
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 24.6,
      "case_count": 35,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U2601",
      "point_name": "电源管理IC",
      "component_type": "IC芯片",
      "probability": 14.1,
      "case_count": 20,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U2401",
      "point_name": "快充芯片",
      "component_type": "IC芯片",
      "probability": 7,
      "case_count": 10,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U3501",
      "point_name": "电源管理IC",
      "component_type": "IC芯片",
      "probability": 7,
      "case_count": 10,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U1801",
      "point_name": "eMMC/UFS存储",
      "component_type": "IC芯片",
      "probability": 7,
      "case_count": 10,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "摄像头故障": [
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 34.1,
      "case_count": 41,
      "fault_type": "物料不良/假焊",
      "repair_method": "更换/重焊"
    },
    {
      "point": "R4807",
      "point_name": "摄像头通路电阻",
      "component_type": "电阻",
      "probability": 10.8,
      "case_count": 13,
      "fault_type": "物料不良/撞件",
      "repair_method": "更换"
    },
    {
      "point": "U4501",
      "point_name": "摄像头供电IC",
      "component_type": "IC芯片",
      "probability": 6.7,
      "case_count": 8,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U4503",
      "point_name": "摄像头供电IC",
      "component_type": "IC芯片",
      "probability": 6.7,
      "case_count": 8,
      "fault_type": "假焊",
      "repair_method": "重焊"
    },
    {
      "point": "U1001",
      "point_name": "摄像头供电IC",
      "component_type": "IC芯片",
      "probability": 6.7,
      "case_count": 8,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "触摸故障": [
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 55,
      "case_count": 22,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "J5202",
      "point_name": "连接器",
      "component_type": "连接器",
      "probability": 15,
      "case_count": 6,
      "fault_type": "破损",
      "repair_method": "更换"
    },
    {
      "point": "J5201",
      "point_name": "连接器",
      "component_type": "连接器",
      "probability": 10,
      "case_count": 4,
      "fault_type": "破损",
      "repair_method": "更换"
    }
  ],
  "无线充电": [
    {
      "point": "U3901",
      "point_name": "充电管理IC",
      "component_type": "IC芯片",
      "probability": 100,
      "case_count": 21,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "SIM卡问题": [
    {
      "point": "J304",
      "point_name": "SIM卡座",
      "component_type": "连接器",
      "probability": 43.2,
      "case_count": 22,
      "fault_type": "破损",
      "repair_method": "更换"
    },
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 19.6,
      "case_count": 10,
      "fault_type": "物料不良/连锡",
      "repair_method": "更换"
    },
    {
      "point": "C5206",
      "point_name": "SIM通路电容",
      "component_type": "电容",
      "probability": 5.9,
      "case_count": 3,
      "fault_type": "立件",
      "repair_method": "重新焊接"
    }
  ],
  "传感器故障": [
    {
      "point": "U5501",
      "point_name": "传感器IC",
      "component_type": "IC芯片",
      "probability": 67.6,
      "case_count": 52,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 11.7,
      "case_count": 9,
      "fault_type": "假焊",
      "repair_method": "重焊"
    }
  ],
  "NFC故障": [
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 100,
      "case_count": 24,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "指纹故障": [
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 41.7,
      "case_count": 10,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "J204",
      "point_name": "指纹连接器",
      "component_type": "连接器",
      "probability": 41.7,
      "case_count": 10,
      "fault_type": "破损",
      "repair_method": "更换"
    }
  ],
  "闪光灯故障": [
    {
      "point": "U2601",
      "point_name": "闪光灯驱动IC",
      "component_type": "IC芯片",
      "probability": 78.3,
      "case_count": 18,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "蓝牙故障": [
    {
      "point": "U8001",
      "point_name": "无线收发器(WCN)",
      "component_type": "IC芯片",
      "probability": 84.2,
      "case_count": 16,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "R8403",
      "point_name": "蓝牙通路电阻",
      "component_type": "电阻",
      "probability": 10.5,
      "case_count": 2,
      "fault_type": "物料不良",
      "repair_method": "更换"
    }
  ],
  "WIFI故障": [
    {
      "point": "U0501",
      "point_name": "主芯片(SoC)",
      "component_type": "IC芯片",
      "probability": 66.7,
      "case_count": 14,
      "fault_type": "物料不良",
      "repair_method": "更换"
    },
    {
      "point": "C8203",
      "point_name": "WIFI通路电容",
      "component_type": "电容",
      "probability": 9.5,
      "case_count": 2,
      "fault_type": "偏位",
      "repair_method": "校正重焊"
    }
  ],
  "磁力故障": [
    {
      "point": "U5504",
      "point_name": "磁力传感器IC",
      "component_type": "IC芯片",
      "probability": 100,
      "case_count": 11,
      "fault_type": "物料不良/破损",
      "repair_method": "更换"
    }
  ]
};
