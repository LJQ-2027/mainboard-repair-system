// 项目案例库（按项目分组的故障案例和位号映射）
// 每个项目拥有独立的诊断规则和故障现象索引
// 未匹配到项目时回退到全局 diagnosisRules + phenomenaSearchIndex

const projectCases = {
  "X6878": {
    "projectName": "X6878-Q352",
    "description": "智能手机主板 (SM7635/QRD7635平台)",
    "diagnosisRules": {
      "不开机": [
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 11.6,
          "case_count": 265,
          "fault_type": "少件",
          "repair_method": ""
        },
        {
          "point": "U0501U1601U1701",
          "point_name": "U0501U1601U1701",
          "component_type": "IC芯片",
          "probability": 6.9,
          "case_count": 158,
          "fault_type": "少件",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 4.4,
          "case_count": 101,
          "fault_type": "误测",
          "repair_method": ""
        },
        {
          "point": "移板",
          "point_name": "移板",
          "component_type": "其他",
          "probability": 4.1,
          "case_count": 94,
          "fault_type": "其它",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 3.8,
          "case_count": 86,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9003",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 3.1,
          "case_count": 70,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U3501",
          "point_name": "副PMIC / MT6315",
          "component_type": "IC芯片",
          "probability": 2.8,
          "case_count": 65,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 2.4,
          "case_count": 56,
          "fault_type": "制程报废移植",
          "repair_method": ""
        },
        {
          "point": "U1701",
          "point_name": "UFS存储",
          "component_type": "IC芯片",
          "probability": 2.4,
          "case_count": 54,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 2.3,
          "case_count": 52,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U1601",
          "point_name": "LPDDR4X内存",
          "component_type": "IC芯片",
          "probability": 2,
          "case_count": 45,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U2601",
          "point_name": "主PMIC电源管理 / MT6360",
          "component_type": "IC芯片",
          "probability": 1.9,
          "case_count": 44,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 1.9,
          "case_count": 43,
          "fault_type": "未知",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 1.8,
          "case_count": 41,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "U3901",
          "point_name": "充电管理IC",
          "component_type": "IC芯片",
          "probability": 1.6,
          "case_count": 37,
          "fault_type": "物料不良",
          "repair_method": ""
        }
      ],
      "校准失败": [
        {
          "point": "U0501/U1701/U1601",
          "point_name": "U0501/U1701/U1601",
          "component_type": "IC芯片",
          "probability": 4.4,
          "case_count": 75,
          "fault_type": "少件",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 4,
          "case_count": 69,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U6607",
          "point_name": "射频收发器 / SDR435",
          "component_type": "IC芯片",
          "probability": 3,
          "case_count": 51,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U6001",
          "point_name": "音频功放PA / AW87319",
          "component_type": "IC芯片",
          "probability": 2.9,
          "case_count": 50,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 2.5,
          "case_count": 43,
          "fault_type": "未知",
          "repair_method": ""
        },
        {
          "point": "U9003",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 2.4,
          "case_count": 42,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U6614",
          "point_name": "U6614",
          "component_type": "IC芯片",
          "probability": 2.2,
          "case_count": 38,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U6805",
          "point_name": "射频开关 / QDM2316",
          "component_type": "IC芯片",
          "probability": 2,
          "case_count": 35,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 2,
          "case_count": 34,
          "fault_type": "误测",
          "repair_method": ""
        },
        {
          "point": "U6603",
          "point_name": "U6603",
          "component_type": "IC芯片",
          "probability": 1.9,
          "case_count": 32,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U3901",
          "point_name": "充电管理IC",
          "component_type": "IC芯片",
          "probability": 1.9,
          "case_count": 32,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U2601",
          "point_name": "主PMIC电源管理 / MT6360",
          "component_type": "IC芯片",
          "probability": 1.8,
          "case_count": 31,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 1.3,
          "case_count": 23,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U2401",
          "point_name": "PMIV0108充电管理",
          "component_type": "IC芯片",
          "probability": 1.3,
          "case_count": 23,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U6902",
          "point_name": "U6902",
          "component_type": "IC芯片",
          "probability": 1.2,
          "case_count": 21,
          "fault_type": "物料不良",
          "repair_method": ""
        }
      ],
      "撞件/破损": [
        {
          "point": "ANT10801",
          "point_name": "天线连接器 / RF Connector",
          "component_type": "天线/射频",
          "probability": 7.1,
          "case_count": 108,
          "fault_type": "变形",
          "repair_method": ""
        },
        {
          "point": "ANT10801",
          "point_name": "天线连接器 / RF Connector",
          "component_type": "天线/射频",
          "probability": 4.9,
          "case_count": 74,
          "fault_type": "撞件",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 4,
          "case_count": 61,
          "fault_type": "未知",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 3.3,
          "case_count": 51,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U9003",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 2.9,
          "case_count": 44,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U2601",
          "point_name": "主PMIC电源管理 / MT6360",
          "component_type": "IC芯片",
          "probability": 2.5,
          "case_count": 38,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U3501",
          "point_name": "副PMIC / MT6315",
          "component_type": "IC芯片",
          "probability": 1.8,
          "case_count": 28,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "ANT10801",
          "point_name": "天线连接器 / RF Connector",
          "component_type": "天线/射频",
          "probability": 1.7,
          "case_count": 26,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "J3801",
          "point_name": "电池BTB连接器 / Main FPC BTB",
          "component_type": "连接器",
          "probability": 1.5,
          "case_count": 23,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "J5202",
          "point_name": "副板连接器",
          "component_type": "连接器",
          "probability": 1.4,
          "case_count": 22,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U3901",
          "point_name": "充电管理IC",
          "component_type": "IC芯片",
          "probability": 1.4,
          "case_count": 22,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "J5201",
          "point_name": "LCD连接器",
          "component_type": "连接器",
          "probability": 1.4,
          "case_count": 21,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U2401",
          "point_name": "PMIV0108充电管理",
          "component_type": "IC芯片",
          "probability": 1.3,
          "case_count": 20,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U5501",
          "point_name": "传感器IC",
          "component_type": "IC芯片",
          "probability": 1.2,
          "case_count": 19,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U1701",
          "point_name": "UFS存储",
          "component_type": "IC芯片",
          "probability": 1.1,
          "case_count": 17,
          "fault_type": "物料不良",
          "repair_method": ""
        }
      ],
      "无服务": [
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 9,
          "case_count": 138,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U2601",
          "point_name": "主PMIC电源管理 / MT6360",
          "component_type": "IC芯片",
          "probability": 3.1,
          "case_count": 47,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9003",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 2.6,
          "case_count": 40,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 2.5,
          "case_count": 39,
          "fault_type": "误测",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 2.5,
          "case_count": 39,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U3901",
          "point_name": "充电管理IC",
          "component_type": "IC芯片",
          "probability": 2.5,
          "case_count": 39,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "J301",
          "point_name": "射频座",
          "component_type": "连接器",
          "probability": 2.5,
          "case_count": 38,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U9002",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 2.2,
          "case_count": 34,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U3501",
          "point_name": "副PMIC / MT6315",
          "component_type": "IC芯片",
          "probability": 2,
          "case_count": 30,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "ANT10801",
          "point_name": "天线连接器 / RF Connector",
          "component_type": "天线/射频",
          "probability": 1.6,
          "case_count": 25,
          "fault_type": "变形",
          "repair_method": ""
        },
        {
          "point": "J303",
          "point_name": "射频座",
          "component_type": "连接器",
          "probability": 1.6,
          "case_count": 24,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "J304",
          "point_name": "SIM卡座 / 指纹连接器",
          "component_type": "连接器",
          "probability": 1.3,
          "case_count": 20,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "C3601",
          "point_name": "C3601",
          "component_type": "电容",
          "probability": 1.2,
          "case_count": 19,
          "fault_type": "立件",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 1.2,
          "case_count": 18,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 1.2,
          "case_count": 18,
          "fault_type": "软件",
          "repair_method": ""
        }
      ],
      "重力不良": [
        {
          "point": "U5501",
          "point_name": "传感器IC",
          "component_type": "IC芯片",
          "probability": 35.9,
          "case_count": 14,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 5.1,
          "case_count": 2,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "U2401",
          "point_name": "PMIV0108充电管理",
          "component_type": "IC芯片",
          "probability": 5.1,
          "case_count": 2,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 5.1,
          "case_count": 2,
          "fault_type": "未知",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "误测",
          "repair_method": ""
        },
        {
          "point": "ANT10801",
          "point_name": "天线连接器 / RF Connector",
          "component_type": "天线/射频",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "变形",
          "repair_method": ""
        },
        {
          "point": "Y1801",
          "point_name": "Y1801",
          "component_type": "晶振",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "R3812",
          "point_name": "电阻",
          "component_type": "电阻",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "J9001",
          "point_name": "J9001",
          "component_type": "连接器",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U8001",
          "point_name": "无线收发器WCN / WCN6755",
          "component_type": "IC芯片",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "C9010",
          "point_name": "C9010",
          "component_type": "电容",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U302",
          "point_name": "U302",
          "component_type": "IC芯片",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "SH_TRANS",
          "point_name": "射频收发屏蔽罩",
          "component_type": "屏蔽罩",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "少件",
          "repair_method": ""
        },
        {
          "point": "U6613",
          "point_name": "U6613",
          "component_type": "IC芯片",
          "probability": 2.6,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        }
      ],
      "充电异常": [
        {
          "point": "U3901",
          "point_name": "充电管理IC",
          "component_type": "IC芯片",
          "probability": 22.8,
          "case_count": 69,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U3501",
          "point_name": "副PMIC / MT6315",
          "component_type": "IC芯片",
          "probability": 7.3,
          "case_count": 22,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 4,
          "case_count": 12,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U2601",
          "point_name": "主PMIC电源管理 / MT6360",
          "component_type": "IC芯片",
          "probability": 3.3,
          "case_count": 10,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U2401",
          "point_name": "PMIV0108充电管理",
          "component_type": "IC芯片",
          "probability": 3,
          "case_count": 9,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 2.3,
          "case_count": 7,
          "fault_type": "误测",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 2.3,
          "case_count": 7,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "ANT10801",
          "point_name": "天线连接器 / RF Connector",
          "component_type": "天线/射频",
          "probability": 2,
          "case_count": 6,
          "fault_type": "撞件",
          "repair_method": ""
        },
        {
          "point": "U9003",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 2,
          "case_count": 6,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 1.3,
          "case_count": 4,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "ANT10801",
          "point_name": "天线连接器 / RF Connector",
          "component_type": "天线/射频",
          "probability": 1.3,
          "case_count": 4,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U1701",
          "point_name": "UFS存储",
          "component_type": "IC芯片",
          "probability": 1.3,
          "case_count": 4,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U6001",
          "point_name": "音频功放PA / AW87319",
          "component_type": "IC芯片",
          "probability": 1.3,
          "case_count": 4,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "C3816",
          "point_name": "C3816",
          "component_type": "电容",
          "probability": 1,
          "case_count": 3,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "R3820",
          "point_name": "R3820",
          "component_type": "电阻",
          "probability": 1,
          "case_count": 3,
          "fault_type": "破损",
          "repair_method": ""
        }
      ],
      "WIFI不良": [
        {
          "point": "U8001",
          "point_name": "无线收发器WCN / WCN6755",
          "component_type": "IC芯片",
          "probability": 23.1,
          "case_count": 15,
          "fault_type": "少件",
          "repair_method": ""
        },
        {
          "point": "U8001",
          "point_name": "无线收发器WCN / WCN6755",
          "component_type": "IC芯片",
          "probability": 21.5,
          "case_count": 14,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 6.2,
          "case_count": 4,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 4.6,
          "case_count": 3,
          "fault_type": "PCB不良",
          "repair_method": ""
        },
        {
          "point": "U3901",
          "point_name": "充电管理IC",
          "component_type": "IC芯片",
          "probability": 4.6,
          "case_count": 3,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 3.1,
          "case_count": 2,
          "fault_type": "误测",
          "repair_method": ""
        },
        {
          "point": "U302",
          "point_name": "U302",
          "component_type": "IC芯片",
          "probability": 3.1,
          "case_count": 2,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "ANT10801",
          "point_name": "天线连接器 / RF Connector",
          "component_type": "天线/射频",
          "probability": 3.1,
          "case_count": 2,
          "fault_type": "撞件",
          "repair_method": ""
        },
        {
          "point": "U8001/U0501",
          "point_name": "U8001/U0501",
          "component_type": "IC芯片",
          "probability": 1.5,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U8401",
          "point_name": "U8401",
          "component_type": "IC芯片",
          "probability": 1.5,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "C8203",
          "point_name": "C8203",
          "component_type": "电容",
          "probability": 1.5,
          "case_count": 1,
          "fault_type": "偏位",
          "repair_method": ""
        },
        {
          "point": "C7005",
          "point_name": "C7005",
          "component_type": "电容",
          "probability": 1.5,
          "case_count": 1,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U8403",
          "point_name": "U8403",
          "component_type": "IC芯片",
          "probability": 1.5,
          "case_count": 1,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "C7005",
          "point_name": "C7005",
          "component_type": "电容",
          "probability": 1.5,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U6607",
          "point_name": "射频收发器 / SDR435",
          "component_type": "IC芯片",
          "probability": 1.5,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        }
      ],
      "蓝牙不良": [
        {
          "point": "U8001",
          "point_name": "无线收发器WCN / WCN6755",
          "component_type": "IC芯片",
          "probability": 50,
          "case_count": 13,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U8001",
          "point_name": "无线收发器WCN / WCN6755",
          "component_type": "IC芯片",
          "probability": 11.5,
          "case_count": 3,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "U8404",
          "point_name": "U8404",
          "component_type": "IC芯片",
          "probability": 7.7,
          "case_count": 2,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "C8410",
          "point_name": "C8410",
          "component_type": "电容",
          "probability": 3.8,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "R8403",
          "point_name": "R8403",
          "component_type": "电阻",
          "probability": 3.8,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 3.8,
          "case_count": 1,
          "fault_type": "PCB不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 3.8,
          "case_count": 1,
          "fault_type": "误测",
          "repair_method": ""
        },
        {
          "point": "U6616",
          "point_name": "U6616",
          "component_type": "IC芯片",
          "probability": 3.8,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U302",
          "point_name": "U302",
          "component_type": "IC芯片",
          "probability": 3.8,
          "case_count": 1,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "R38112",
          "point_name": "R38112",
          "component_type": "电阻",
          "probability": 3.8,
          "case_count": 1,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "SPKP1",
          "point_name": "SPKP1",
          "component_type": "扬声器",
          "probability": 3.8,
          "case_count": 1,
          "fault_type": "假焊",
          "repair_method": ""
        }
      ],
      "音频不良": [
        {
          "point": "M4301",
          "point_name": "副麦克风",
          "component_type": "麦克风/马达",
          "probability": 8.5,
          "case_count": 21,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "MIC101",
          "point_name": "主麦克风",
          "component_type": "麦克风/马达",
          "probability": 7.7,
          "case_count": 19,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U4301",
          "point_name": "U4301",
          "component_type": "IC芯片",
          "probability": 5.6,
          "case_count": 14,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 4,
          "case_count": 10,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 3.6,
          "case_count": 9,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U4302",
          "point_name": "U4302",
          "component_type": "IC芯片",
          "probability": 3.2,
          "case_count": 8,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U4101",
          "point_name": "U4101",
          "component_type": "IC芯片",
          "probability": 3.2,
          "case_count": 8,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U3901",
          "point_name": "充电管理IC",
          "component_type": "IC芯片",
          "probability": 2.4,
          "case_count": 6,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "J5201",
          "point_name": "LCD连接器",
          "component_type": "连接器",
          "probability": 2.4,
          "case_count": 6,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "C319/L313",
          "point_name": "C319/L313",
          "component_type": "电容",
          "probability": 2,
          "case_count": 5,
          "fault_type": "撞件",
          "repair_method": ""
        },
        {
          "point": "U2601",
          "point_name": "主PMIC电源管理 / MT6360",
          "component_type": "IC芯片",
          "probability": 1.6,
          "case_count": 4,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U3501",
          "point_name": "副PMIC / MT6315",
          "component_type": "IC芯片",
          "probability": 1.6,
          "case_count": 4,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 1.6,
          "case_count": 4,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U6606",
          "point_name": "U6606",
          "component_type": "IC芯片",
          "probability": 1.6,
          "case_count": 4,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "U9003",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 1.6,
          "case_count": 4,
          "fault_type": "连锡",
          "repair_method": ""
        }
      ],
      "指纹不良": [
        {
          "point": "J204",
          "point_name": "J204",
          "component_type": "连接器",
          "probability": 23.3,
          "case_count": 10,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "J204",
          "point_name": "J204",
          "component_type": "连接器",
          "probability": 18.6,
          "case_count": 8,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 16.3,
          "case_count": 7,
          "fault_type": "误测",
          "repair_method": ""
        },
        {
          "point": "J204",
          "point_name": "J204",
          "component_type": "连接器",
          "probability": 14,
          "case_count": 6,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "J5201",
          "point_name": "LCD连接器",
          "component_type": "连接器",
          "probability": 9.3,
          "case_count": 4,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 4.7,
          "case_count": 2,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 2.3,
          "case_count": 1,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "J5201",
          "point_name": "LCD连接器",
          "component_type": "连接器",
          "probability": 2.3,
          "case_count": 1,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U4505",
          "point_name": "U4505",
          "component_type": "IC芯片",
          "probability": 2.3,
          "case_count": 1,
          "fault_type": "偏位",
          "repair_method": ""
        },
        {
          "point": "C9030",
          "point_name": "C9030",
          "component_type": "电容",
          "probability": 2.3,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U6704",
          "point_name": "U6704",
          "component_type": "IC芯片",
          "probability": 2.3,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 2.3,
          "case_count": 1,
          "fault_type": "未知",
          "repair_method": ""
        }
      ],
      "磁力不良": [
        {
          "point": "U5504",
          "point_name": "U5504",
          "component_type": "IC芯片",
          "probability": 43.2,
          "case_count": 16,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "C5513",
          "point_name": "C5513",
          "component_type": "电容",
          "probability": 5.4,
          "case_count": 2,
          "fault_type": "撞件",
          "repair_method": ""
        },
        {
          "point": "U2601",
          "point_name": "主PMIC电源管理 / MT6360",
          "component_type": "IC芯片",
          "probability": 5.4,
          "case_count": 2,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U5504",
          "point_name": "U5504",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "撞件",
          "repair_method": ""
        },
        {
          "point": "U3901",
          "point_name": "充电管理IC",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "R9009",
          "point_name": "电阻",
          "component_type": "电阻",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U6614",
          "point_name": "U6614",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "J102",
          "point_name": "J102",
          "component_type": "连接器",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "J101",
          "point_name": "J101",
          "component_type": "连接器",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "少件",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "J5201",
          "point_name": "LCD连接器",
          "component_type": "连接器",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "U3501",
          "point_name": "副PMIC / MT6315",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9003",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "R3829",
          "point_name": "R3829",
          "component_type": "电阻",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        }
      ],
      "摄像头不良": [
        {
          "point": "J4801",
          "point_name": "J4801",
          "component_type": "连接器",
          "probability": 8.4,
          "case_count": 7,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 7.2,
          "case_count": 6,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 4.8,
          "case_count": 4,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 4.8,
          "case_count": 4,
          "fault_type": "误测",
          "repair_method": ""
        },
        {
          "point": "U4501",
          "point_name": "U4501",
          "component_type": "IC芯片",
          "probability": 4.8,
          "case_count": 4,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "J4802",
          "point_name": "J4802",
          "component_type": "连接器",
          "probability": 3.6,
          "case_count": 3,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U4501",
          "point_name": "U4501",
          "component_type": "IC芯片",
          "probability": 3.6,
          "case_count": 3,
          "fault_type": "假焊",
          "repair_method": ""
        },
        {
          "point": "U4506",
          "point_name": "U4506",
          "component_type": "IC芯片",
          "probability": 3.6,
          "case_count": 3,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 3.6,
          "case_count": 3,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "U1001",
          "point_name": "U1001",
          "component_type": "IC芯片",
          "probability": 2.4,
          "case_count": 2,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "R4501",
          "point_name": "R4501",
          "component_type": "电阻",
          "probability": 2.4,
          "case_count": 2,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "R0714",
          "point_name": "R0714",
          "component_type": "电阻",
          "probability": 2.4,
          "case_count": 2,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "J4802",
          "point_name": "J4802",
          "component_type": "连接器",
          "probability": 2.4,
          "case_count": 2,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U2601",
          "point_name": "主PMIC电源管理 / MT6360",
          "component_type": "IC芯片",
          "probability": 2.4,
          "case_count": 2,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9003",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 2.4,
          "case_count": 2,
          "fault_type": "连锡",
          "repair_method": ""
        }
      ],
      "GPS不良": [
        {
          "point": "U0501",
          "point_name": "主芯片SoC / PMK7635主PMIC",
          "component_type": "IC芯片",
          "probability": 5.4,
          "case_count": 2,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 5.4,
          "case_count": 2,
          "fault_type": "连锡",
          "repair_method": ""
        },
        {
          "point": "J5202",
          "point_name": "副板连接器",
          "component_type": "连接器",
          "probability": 5.4,
          "case_count": 2,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "U9005",
          "point_name": "天线开关 / 射频前端",
          "component_type": "IC芯片",
          "probability": 5.4,
          "case_count": 2,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "未知/未记录",
          "point_name": "未知/未记录",
          "component_type": "未知",
          "probability": 5.4,
          "case_count": 2,
          "fault_type": "未知",
          "repair_method": ""
        },
        {
          "point": "R8405",
          "point_name": "R8405",
          "component_type": "电阻",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U9002",
          "point_name": "天线开关",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U6001",
          "point_name": "音频功放PA / AW87319",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U8401",
          "point_name": "U8401",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U2601",
          "point_name": "主PMIC电源管理 / MT6360",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "U4302",
          "point_name": "U4302",
          "component_type": "IC芯片",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "C3611",
          "point_name": "C3611",
          "component_type": "电容",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "物料不良",
          "repair_method": ""
        },
        {
          "point": "ANT3902",
          "point_name": "ANT3902",
          "component_type": "天线/射频",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "撞件",
          "repair_method": ""
        },
        {
          "point": "ANT9003",
          "point_name": "ANT9003",
          "component_type": "天线/射频",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "破损",
          "repair_method": ""
        },
        {
          "point": "R3828",
          "point_name": "R3828",
          "component_type": "电阻",
          "probability": 2.7,
          "case_count": 1,
          "fault_type": "撞件",
          "repair_method": ""
        }
      ]
    },
    "phenomenaSearchIndex": {
      "浮高": {
        "phenomena": "浮高 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 28.7,
            "case_count": 27,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-BB",
            "component_type": "屏蔽罩",
            "probability": 17,
            "case_count": 16,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_BB",
            "component_type": "屏蔽罩",
            "probability": 9.6,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-TRANS",
            "component_type": "屏蔽罩",
            "probability": 9.6,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_RFPA",
            "component_type": "屏蔽罩",
            "probability": 8.5,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "T104",
            "component_type": "变压器/晶体管",
            "probability": 8.5,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J101",
            "component_type": "连接器",
            "probability": 7.4,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_MOTOR",
            "component_type": "屏蔽罩",
            "probability": 2.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-RFPA",
            "component_type": "屏蔽罩",
            "probability": 2.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "VIB_P",
            "component_type": "其他",
            "probability": 2.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 94
      },
      "BB_TEST:Connect_with_preloader": {
        "phenomena": "BB_TEST:Connect_with_preloader (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 22.4,
            "case_count": 93,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 8,
            "case_count": 33,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 7.2,
            "case_count": 30,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 6.5,
            "case_count": 27,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 4.6,
            "case_count": 19,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 4.6,
            "case_count": 19,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1601",
            "component_type": "IC芯片",
            "probability": 3.9,
            "case_count": 16,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 3.1,
            "case_count": 13,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 2.4,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 2.2,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 415
      },
      "下载无端口": {
        "phenomena": "下载无端口 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 30.2,
            "case_count": 259,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501U1601U1701",
            "component_type": "IC芯片",
            "probability": 18.9,
            "case_count": 162,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 36,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 2.4,
            "case_count": 21,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 2,
            "case_count": 17,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 2,
            "case_count": 17,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 1.9,
            "case_count": 16,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 1.9,
            "case_count": 16,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 1.7,
            "case_count": 15,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 1.6,
            "case_count": 14,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 858
      },
      "开始校准终测；\n若是MTK校准终测DLL报错": {
        "phenomena": "开始校准终测；\n若是MTK校准终测DLL报错 (X6878-Q352)",
        "top_components": [
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 5,
            "case_count": 86,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501/U1701/U1601",
            "component_type": "IC芯片",
            "probability": 4.6,
            "case_count": 78,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 4.2,
            "case_count": 71,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 3.7,
            "case_count": 63,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 3.2,
            "case_count": 55,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6607",
            "component_type": "IC芯片",
            "probability": 2.9,
            "case_count": 50,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 2.6,
            "case_count": 44,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 2.5,
            "case_count": 43,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6805",
            "component_type": "IC芯片",
            "probability": 2.4,
            "case_count": 41,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6614",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 40,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1707
      },
      "直接显示MTK定义的错误代码": {
        "phenomena": "直接显示MTK定义的错误代码 (X6878-Q352)",
        "top_components": [
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 5,
            "case_count": 86,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501/U1701/U1601",
            "component_type": "IC芯片",
            "probability": 4.6,
            "case_count": 78,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 4.2,
            "case_count": 71,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 3.7,
            "case_count": 63,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 3.2,
            "case_count": 55,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6607",
            "component_type": "IC芯片",
            "probability": 2.9,
            "case_count": 50,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 2.6,
            "case_count": 44,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 2.5,
            "case_count": 43,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6805",
            "component_type": "IC芯片",
            "probability": 2.4,
            "case_count": 41,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6614",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 40,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1707
      },
      "与ATE工具显示的错误代码一致": {
        "phenomena": "与ATE工具显示的错误代码一致 (X6878-Q352)",
        "top_components": [
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 5,
            "case_count": 86,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501/U1701/U1601",
            "component_type": "IC芯片",
            "probability": 4.6,
            "case_count": 78,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 4.2,
            "case_count": 71,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 3.7,
            "case_count": 63,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 3.2,
            "case_count": 55,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6607",
            "component_type": "IC芯片",
            "probability": 2.9,
            "case_count": 50,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 2.6,
            "case_count": 44,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 2.5,
            "case_count": 43,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6805",
            "component_type": "IC芯片",
            "probability": 2.4,
            "case_count": 41,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6614",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 40,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1707
      },
      "不下载": {
        "phenomena": "不下载 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 28,
            "case_count": 87,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501 U1601 U1701",
            "component_type": "IC芯片",
            "probability": 7.7,
            "case_count": 24,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 7.4,
            "case_count": 23,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1601",
            "component_type": "IC芯片",
            "probability": 4.5,
            "case_count": 14,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 3.9,
            "case_count": 12,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 3.5,
            "case_count": 11,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 3.2,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 2.6,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 2.6,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2201",
            "component_type": "IC芯片",
            "probability": 1.9,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 311
      },
      "弹片撞件/偏位": {
        "phenomena": "弹片撞件/偏位 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 27.4,
            "case_count": 139,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 6.1,
            "case_count": 31,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9001",
            "component_type": "天线/射频",
            "probability": 3.9,
            "case_count": 20,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 3.6,
            "case_count": 18,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9103",
            "component_type": "天线/射频",
            "probability": 2.6,
            "case_count": 13,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 2.4,
            "case_count": 12,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 2,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9101",
            "component_type": "天线/射频",
            "probability": 1.6,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SPKN1",
            "component_type": "扬声器",
            "probability": 1.6,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J3801",
            "component_type": "连接器",
            "probability": 1.6,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 507
      },
      "耦合不良": {
        "phenomena": "耦合不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 12.7,
            "case_count": 187,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 5.5,
            "case_count": 82,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 3.7,
            "case_count": 55,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9002",
            "component_type": "IC芯片",
            "probability": 3.6,
            "case_count": 53,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 3.5,
            "case_count": 52,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 3,
            "case_count": 44,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 2.6,
            "case_count": 39,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J301",
            "component_type": "连接器",
            "probability": 2.6,
            "case_count": 39,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 2.6,
            "case_count": 39,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9009",
            "component_type": "电阻",
            "probability": 2.6,
            "case_count": 38,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1478
      },
      "Write_Flag_Fail": {
        "phenomena": "Write_Flag_Fail (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "撞件/破损": {
        "phenomena": "撞件/破损 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 7.9,
            "case_count": 80,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 5.7,
            "case_count": 58,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 4,
            "case_count": 41,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 3.2,
            "case_count": 33,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 3.1,
            "case_count": 32,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 29,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 2.6,
            "case_count": 26,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5202",
            "component_type": "连接器",
            "probability": 2.4,
            "case_count": 24,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 2.1,
            "case_count": 21,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 1.9,
            "case_count": 19,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1018
      },
      "重力不良": {
        "phenomena": "重力不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U5501",
            "component_type": "IC芯片",
            "probability": 35.9,
            "case_count": 14,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 7.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 7.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 5.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3812",
            "component_type": "电阻",
            "probability": 5.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 2.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "Y1801",
            "component_type": "晶振",
            "probability": 2.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J9001",
            "component_type": "连接器",
            "probability": 2.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8001",
            "component_type": "IC芯片",
            "probability": 2.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C9010",
            "component_type": "电容",
            "probability": 2.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 39
      },
      "检测SIM卡": {
        "phenomena": "检测SIM卡 (X6878-Q352)",
        "top_components": [
          {
            "point": "J304",
            "component_type": "连接器",
            "probability": 58.6,
            "case_count": 17,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6606",
            "component_type": "IC芯片",
            "probability": 17.2,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 13.8,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J201",
            "component_type": "连接器",
            "probability": 3.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J403",
            "component_type": "连接器",
            "probability": 3.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 3.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 29
      },
      "少件": {
        "phenomena": "少件 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_LFEM",
            "component_type": "屏蔽罩",
            "probability": 44.9,
            "case_count": 62,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J303",
            "component_type": "连接器",
            "probability": 2.9,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 2.9,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3812",
            "component_type": "电阻",
            "probability": 2.2,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 2.2,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J301",
            "component_type": "连接器",
            "probability": 2.2,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 2.2,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9103",
            "component_type": "天线/射频",
            "probability": 2.2,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_GYR SH_GYR SH_BB",
            "component_type": "屏蔽罩",
            "probability": 2.2,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT301",
            "component_type": "天线/射频",
            "probability": 1.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 138
      },
      "BB_TEST:ScanPSN": {
        "phenomena": "BB_TEST:ScanPSN (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 50,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C6541",
            "component_type": "电容",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6607",
            "component_type": "IC芯片",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6604",
            "component_type": "IC芯片",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5504",
            "component_type": "IC芯片",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 10
      },
      "假焊": {
        "phenomena": "假焊 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 60.7,
            "case_count": 74,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-BB",
            "component_type": "屏蔽罩",
            "probability": 10.7,
            "case_count": 13,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-TRANS",
            "component_type": "屏蔽罩",
            "probability": 9.8,
            "case_count": 12,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-PMU",
            "component_type": "屏蔽罩",
            "probability": 6.6,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_BB",
            "component_type": "屏蔽罩",
            "probability": 4.1,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-GYR",
            "component_type": "屏蔽罩",
            "probability": 1.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-RFPA",
            "component_type": "屏蔽罩",
            "probability": 1.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_PMU",
            "component_type": "屏蔽罩",
            "probability": 1.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_TRANS SH_PMU",
            "component_type": "屏蔽罩",
            "probability": 1.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_LFEM",
            "component_type": "屏蔽罩",
            "probability": 1.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 122
      },
      "Set_Phone_FTM_Mode": {
        "phenomena": "Set_Phone_FTM_Mode (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 28.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 28.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 28.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 7
      },
      "变形": {
        "phenomena": "变形 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 25.6,
            "case_count": 11,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 20.9,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-BB",
            "component_type": "屏蔽罩",
            "probability": 16.3,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 14,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_LFEM",
            "component_type": "屏蔽罩",
            "probability": 4.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U303",
            "component_type": "IC芯片",
            "probability": 4.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-PMU",
            "component_type": "屏蔽罩",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_GYR",
            "component_type": "屏蔽罩",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_PMU",
            "component_type": "屏蔽罩",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT5605",
            "component_type": "天线/射频",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 43
      },
      "少锡": {
        "phenomena": "少锡 (X6878-Q352)",
        "top_components": [
          {
            "point": "U303",
            "component_type": "IC芯片",
            "probability": 35.7,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 14.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J304",
            "component_type": "连接器",
            "probability": 14.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 14.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J101",
            "component_type": "连接器",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT3908",
            "component_type": "天线/射频",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J202",
            "component_type": "连接器",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 14
      },
      "STATUS_TESTER_INITIALIZE_FAILED": {
        "phenomena": "STATUS_TESTER_INITIALIZE_FAILED (X6878-Q352)",
        "top_components": [
          {
            "point": "U3801",
            "component_type": "IC芯片",
            "probability": 16.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 16.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 16.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 16.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 16.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 16.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 12
      },
      "沾锡": {
        "phenomena": "沾锡 (X6878-Q352)",
        "top_components": [
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 44.4,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J9002",
            "component_type": "连接器",
            "probability": 22.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6606",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9002",
            "component_type": "天线/射频",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 9
      },
      "错料": {
        "phenomena": "错料 (X6878-Q352)",
        "top_components": [
          {
            "point": "R5806",
            "component_type": "电阻",
            "probability": 33.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_RFPA",
            "component_type": "屏蔽罩",
            "probability": 33.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C9106",
            "component_type": "电容",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C9006",
            "component_type": "电容",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 6
      },
      "空焊": {
        "phenomena": "空焊 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 50,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_WCN",
            "component_type": "屏蔽罩",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "M4301",
            "component_type": "麦克风/马达",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J301",
            "component_type": "连接器",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5504",
            "component_type": "IC芯片",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5209",
            "component_type": "电容",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C3005",
            "component_type": "电容",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 7.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 14
      },
      "MMI不开机": {
        "phenomena": "MMI不开机 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 13.3,
            "case_count": 57,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 12.6,
            "case_count": 54,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 7.7,
            "case_count": 33,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 6.3,
            "case_count": 27,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8001",
            "component_type": "IC芯片",
            "probability": 5.4,
            "case_count": 23,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J3801",
            "component_type": "连接器",
            "probability": 3.5,
            "case_count": 15,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 12,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 12,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9009",
            "component_type": "电阻",
            "probability": 2.3,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3812",
            "component_type": "电阻",
            "probability": 1.9,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 429
      },
      "偏位": {
        "phenomena": "偏位 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_LFEM",
            "component_type": "屏蔽罩",
            "probability": 22.4,
            "case_count": 15,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SPKN1",
            "component_type": "扬声器",
            "probability": 19.4,
            "case_count": 13,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J9005",
            "component_type": "连接器",
            "probability": 4.5,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8401",
            "component_type": "IC芯片",
            "probability": 4.5,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L306",
            "component_type": "电感",
            "probability": 4.5,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-LFEM",
            "component_type": "屏蔽罩",
            "probability": 4.5,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L9009",
            "component_type": "电感",
            "probability": 3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9108",
            "component_type": "电阻",
            "probability": 3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9005",
            "component_type": "天线/射频",
            "probability": 3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J9001",
            "component_type": "连接器",
            "probability": 3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 67
      },
      "屏蔽盖假焊": {
        "phenomena": "屏蔽盖假焊 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 47.2,
            "case_count": 34,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_PMU",
            "component_type": "屏蔽罩",
            "probability": 13.9,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-PMU",
            "component_type": "屏蔽罩",
            "probability": 9.7,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-TRANS",
            "component_type": "屏蔽罩",
            "probability": 8.3,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 4.2,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_BB",
            "component_type": "屏蔽罩",
            "probability": 1.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 1.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L9024",
            "component_type": "电感",
            "probability": 1.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 1.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 72
      },
      "屏蔽盖凹陷": {
        "phenomena": "屏蔽盖凹陷 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_PMU",
            "component_type": "屏蔽罩",
            "probability": 47.4,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 26.3,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_LFEM",
            "component_type": "屏蔽罩",
            "probability": 10.5,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_RFPA",
            "component_type": "屏蔽罩",
            "probability": 5.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_GYR",
            "component_type": "屏蔽罩",
            "probability": 5.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_PMU J4801 SH_CAM",
            "component_type": "屏蔽罩",
            "probability": 5.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 19
      },
      "STATUS_WCDMA_SET_POWER_CONTROL_MODE_FAILED": {
        "phenomena": "STATUS_WCDMA_SET_POWER_CONTROL_MODE_FAILED (X6878-Q352)",
        "top_components": [
          {
            "point": "C2814",
            "component_type": "电容",
            "probability": 40,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 20,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2201",
            "component_type": "IC芯片",
            "probability": 20,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C319/L313",
            "component_type": "电容",
            "probability": 20,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 5
      },
      "STATUS_WCDMA_REPLACE_GAIN_TABLE_FAILED": {
        "phenomena": "STATUS_WCDMA_REPLACE_GAIN_TABLE_FAILED (X6878-Q352)",
        "top_components": [
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 2
      },
      "排插、FPC不良": {
        "phenomena": "排插、FPC不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "J4802",
            "component_type": "连接器",
            "probability": 7.5,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6614",
            "component_type": "IC芯片",
            "probability": 7.5,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 5.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 5.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 5.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 5.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6606",
            "component_type": "IC芯片",
            "probability": 5.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J204",
            "component_type": "连接器",
            "probability": 3.8,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J301",
            "component_type": "连接器",
            "probability": 3.8,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 3.8,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 53
      },
      "排插下陷": {
        "phenomena": "排插下陷 (X6878-Q352)",
        "top_components": [
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 61.1,
            "case_count": 11,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J3801",
            "component_type": "连接器",
            "probability": 16.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U303",
            "component_type": "IC芯片",
            "probability": 16.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J304",
            "component_type": "连接器",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 18
      },
      "连锡": {
        "phenomena": "连锡 (X6878-Q352)",
        "top_components": [
          {
            "point": "J101",
            "component_type": "连接器",
            "probability": 33.3,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9011",
            "component_type": "电阻",
            "probability": 11.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J304",
            "component_type": "连接器",
            "probability": 11.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R120",
            "component_type": "电阻",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C319",
            "component_type": "电容",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R5810",
            "component_type": "电阻",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C9010",
            "component_type": "电容",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C124",
            "component_type": "电容",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R307",
            "component_type": "电阻",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 18
      },
      "侧立": {
        "phenomena": "侧立 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_LDO1",
            "component_type": "屏蔽罩",
            "probability": 33.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3820",
            "component_type": "电阻",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "RT0502",
            "component_type": "电阻",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L9105",
            "component_type": "电感",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C6410",
            "component_type": "电容",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 6
      },
      "DUT - RF performance check failed": {
        "phenomena": "DUT - RF performance check failed (X6878-Q352)",
        "top_components": [
          {
            "point": "U6606",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5299",
            "component_type": "电容",
            "probability": 8.3,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_BBSH_GYRANT10801",
            "component_type": "屏蔽罩",
            "probability": 8.3,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U7901",
            "component_type": "IC芯片",
            "probability": 5.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J301",
            "component_type": "连接器",
            "probability": 5.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3820",
            "component_type": "电阻",
            "probability": 5.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9103",
            "component_type": "天线/射频",
            "probability": 5.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L6310",
            "component_type": "电感",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 36
      },
      "反向": {
        "phenomena": "反向 (X6878-Q352)",
        "top_components": [
          {
            "point": "U9002",
            "component_type": "IC芯片",
            "probability": 25,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "D5501",
            "component_type": "二极管",
            "probability": 10,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J9001",
            "component_type": "连接器",
            "probability": 5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5504",
            "component_type": "IC芯片",
            "probability": 5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "T101",
            "component_type": "变压器/晶体管",
            "probability": 5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "无",
            "component_type": "其他",
            "probability": 5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT303",
            "component_type": "天线/射频",
            "probability": 5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3812",
            "component_type": "电阻",
            "probability": 5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 20
      },
      "弹片下陷": {
        "phenomena": "弹片下陷 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 29.6,
            "case_count": 16,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 7.4,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9007",
            "component_type": "天线/射频",
            "probability": 5.6,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9009",
            "component_type": "天线/射频",
            "probability": 5.6,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 5.6,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6607",
            "component_type": "IC芯片",
            "probability": 3.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 3.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 3.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 3.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 3.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 54
      },
      "不识USB端口": {
        "phenomena": "不识USB端口 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 36.8,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 26.3,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT302",
            "component_type": "天线/射频",
            "probability": 10.5,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 5.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5299",
            "component_type": "电容",
            "probability": 5.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 5.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5504",
            "component_type": "IC芯片",
            "probability": 5.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L6821",
            "component_type": "电感",
            "probability": 5.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 19
      },
      "WIFI不良": {
        "phenomena": "WIFI不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U8001",
            "component_type": "IC芯片",
            "probability": 44.6,
            "case_count": 29,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 9.2,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 6.2,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 4.6,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 4.6,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C7005",
            "component_type": "电容",
            "probability": 3.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U302",
            "component_type": "IC芯片",
            "probability": 3.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8001/U0501",
            "component_type": "IC芯片",
            "probability": 1.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8401",
            "component_type": "IC芯片",
            "probability": 1.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C8203",
            "component_type": "电容",
            "probability": 1.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 65
      },
      "无线充电不过": {
        "phenomena": "无线充电不过 (X6878-Q352)",
        "top_components": [
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 26.5,
            "case_count": 69,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 7.7,
            "case_count": 20,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 5.4,
            "case_count": 14,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 4.2,
            "case_count": 11,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 11,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 3.8,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6606",
            "component_type": "IC芯片",
            "probability": 1.5,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 260
      },
      "功耗不良": {
        "phenomena": "功耗不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 36.5,
            "case_count": 81,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 8.1,
            "case_count": 18,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 7.7,
            "case_count": 17,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C3601",
            "component_type": "电容",
            "probability": 5.9,
            "case_count": 13,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 4.5,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5202",
            "component_type": "连接器",
            "probability": 2.7,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2201",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "M4301",
            "component_type": "麦克风/马达",
            "probability": 2.3,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 1.8,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 222
      },
      "蓝牙打不开、收不到蓝牙、连接不到蓝牙": {
        "phenomena": "蓝牙打不开、收不到蓝牙、连接不到蓝牙 (X6878-Q352)",
        "top_components": [
          {
            "point": "U8001",
            "component_type": "IC芯片",
            "probability": 64,
            "case_count": 16,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8404",
            "component_type": "IC芯片",
            "probability": 8,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 8,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C8410",
            "component_type": "电容",
            "probability": 4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6616",
            "component_type": "IC芯片",
            "probability": 4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U302",
            "component_type": "IC芯片",
            "probability": 4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R38112",
            "component_type": "电阻",
            "probability": 4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SPKP1",
            "component_type": "扬声器",
            "probability": 4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 25
      },
      "距离感不良": {
        "phenomena": "距离感不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 39.5,
            "case_count": 17,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 11.6,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9101",
            "component_type": "天线/射频",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8401",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J9001",
            "component_type": "连接器",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6402",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5299",
            "component_type": "电容",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 43
      },
      "按键不良": {
        "phenomena": "按键不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 22.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R5602",
            "component_type": "电阻",
            "probability": 22.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT5605",
            "component_type": "天线/射频",
            "probability": 22.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R5604",
            "component_type": "电阻",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R5603",
            "component_type": "电阻",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "MIC101",
            "component_type": "麦克风/马达",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 9
      },
      "开机死机、重启等": {
        "phenomena": "开机死机、重启等 (X6878-Q352)",
        "top_components": [
          {
            "point": "U8001",
            "component_type": "IC芯片",
            "probability": 34.3,
            "case_count": 36,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 17.1,
            "case_count": 18,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 11.4,
            "case_count": 12,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501 U1601 U1701",
            "component_type": "IC芯片",
            "probability": 3.8,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1601",
            "component_type": "IC芯片",
            "probability": 2.9,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 2.9,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 1.9,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 1.9,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501 U1601U1701",
            "component_type": "IC芯片",
            "probability": 1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501 U8001",
            "component_type": "IC芯片",
            "probability": 1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 105
      },
      "闪光灯不亮": {
        "phenomena": "闪光灯不亮 (X6878-Q352)",
        "top_components": [
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 46.9,
            "case_count": 15,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 9.4,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6602",
            "component_type": "IC芯片",
            "probability": 6.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8402",
            "component_type": "IC芯片",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J102",
            "component_type": "连接器",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6611",
            "component_type": "IC芯片",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C7005",
            "component_type": "电容",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5203",
            "component_type": "电容",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 32
      },
      "副麦克无声、杂音、破音": {
        "phenomena": "副麦克无声、杂音、破音 (X6878-Q352)",
        "top_components": [
          {
            "point": "M4301",
            "component_type": "麦克风/马达",
            "probability": 15.3,
            "case_count": 20,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "MIC101",
            "component_type": "麦克风/马达",
            "probability": 13,
            "case_count": 17,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 5.3,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 4.6,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C319/L313",
            "component_type": "电容",
            "probability": 3.8,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 3.1,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 3.1,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 2.3,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 131
      },
      "指纹不良": {
        "phenomena": "指纹不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "J204",
            "component_type": "连接器",
            "probability": 55.8,
            "case_count": 24,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 18.6,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 11.6,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4505",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C9030",
            "component_type": "电容",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6704",
            "component_type": "IC芯片",
            "probability": 2.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 43
      },
      "开机黑屏、花屏、偏色": {
        "phenomena": "开机黑屏、花屏、偏色 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 27.6,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5202",
            "component_type": "连接器",
            "probability": 6.9,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5209",
            "component_type": "电容",
            "probability": 6.9,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1601",
            "component_type": "IC芯片",
            "probability": 6.9,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L3403",
            "component_type": "电感",
            "probability": 3.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 3.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3401",
            "component_type": "IC芯片",
            "probability": 3.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3403",
            "component_type": "电阻",
            "probability": 3.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5207",
            "component_type": "电容",
            "probability": 3.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L3401",
            "component_type": "电感",
            "probability": 3.4,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 29
      },
      "快充测试": {
        "phenomena": "快充测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "C3816",
            "component_type": "电容",
            "probability": 20.8,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 16.7,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3820",
            "component_type": "电阻",
            "probability": 8.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C3515",
            "component_type": "电容",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6805",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "M4301",
            "component_type": "麦克风/马达",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6304",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 24
      },
      "板面脏污": {
        "phenomena": "板面脏污 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_PMU",
            "component_type": "屏蔽罩",
            "probability": 44.4,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH-BB",
            "component_type": "屏蔽罩",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9009",
            "component_type": "电阻",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT301",
            "component_type": "天线/射频",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5204",
            "component_type": "电容",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 9
      },
      "读取MTK校准终测配置文件；获取工具界面配置信息": {
        "phenomena": "读取MTK校准终测配置文件；获取工具界面配置信息 (X6878-Q352)",
        "top_components": [
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 13.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5504",
            "component_type": "IC芯片",
            "probability": 13.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 13.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6603",
            "component_type": "IC芯片",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C4317",
            "component_type": "电容",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3820",
            "component_type": "电阻",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 15
      },
      "喇叭测试": {
        "phenomena": "喇叭测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 20,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "PCB",
            "component_type": "其他",
            "probability": 20,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9104",
            "component_type": "电阻",
            "probability": 20,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4101",
            "component_type": "IC芯片",
            "probability": 20,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8401",
            "component_type": "IC芯片",
            "probability": 20,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 5
      },
      "STATUS_GSM_AGC_DONE": {
        "phenomena": "STATUS_GSM_AGC_DONE (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501U1601U1701",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "耳机无声、杂音、破音、单音": {
        "phenomena": "耳机无声、杂音、破音、单音 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 25,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4401",
            "component_type": "IC芯片",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C4312",
            "component_type": "电容",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J304",
            "component_type": "连接器",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C7803",
            "component_type": "电容",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 8
      },
      "弹片/按键卡死": {
        "phenomena": "弹片/按键卡死 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 61.7,
            "case_count": 37,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9001",
            "component_type": "天线/射频",
            "probability": 5,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9009",
            "component_type": "天线/射频",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9008",
            "component_type": "天线/射频",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9104",
            "component_type": "天线/射频",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6306",
            "component_type": "IC芯片",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1001",
            "component_type": "IC芯片",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9101",
            "component_type": "天线/射频",
            "probability": 1.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT5601",
            "component_type": "天线/射频",
            "probability": 1.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 60
      },
      "后摄像头不拍照、不聚焦": {
        "phenomena": "后摄像头不拍照、不聚焦 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 28.1,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 9.4,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4802",
            "component_type": "连接器",
            "probability": 9.4,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4501",
            "component_type": "IC芯片",
            "probability": 6.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 6.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5204",
            "component_type": "电容",
            "probability": 6.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R4501",
            "component_type": "电阻",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4502",
            "component_type": "IC芯片",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J303",
            "component_type": "连接器",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 3.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 32
      },
      "血氧测试": {
        "phenomena": "血氧测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "J304",
            "component_type": "连接器",
            "probability": 21.1,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 13.2,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 7.9,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R5224",
            "component_type": "电阻",
            "probability": 5.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 5.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6607",
            "component_type": "IC芯片",
            "probability": 5.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R5225",
            "component_type": "电阻",
            "probability": 2.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U303",
            "component_type": "IC芯片",
            "probability": 2.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C6832",
            "component_type": "电容",
            "probability": 2.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 2.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 38
      },
      "不读SIM卡2": {
        "phenomena": "不读SIM卡2 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 52.9,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 5.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4005",
            "component_type": "IC芯片",
            "probability": 5.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5202",
            "component_type": "连接器",
            "probability": 5.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4001",
            "component_type": "IC芯片",
            "probability": 5.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 5.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C9015",
            "component_type": "电容",
            "probability": 5.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6614",
            "component_type": "IC芯片",
            "probability": 5.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "M4301",
            "component_type": "麦克风/马达",
            "probability": 5.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 17
      },
      "音频测试不良": {
        "phenomena": "音频测试不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U4301",
            "component_type": "IC芯片",
            "probability": 16.4,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 14.8,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4302",
            "component_type": "IC芯片",
            "probability": 6.6,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "MIC101",
            "component_type": "麦克风/马达",
            "probability": 6.6,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "SH_GYR SH_BB SH_PMU",
            "component_type": "屏蔽罩",
            "probability": 6.6,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "M4301",
            "component_type": "麦克风/马达",
            "probability": 4.9,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4301 U4101",
            "component_type": "IC芯片",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4101",
            "component_type": "IC芯片",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C4119",
            "component_type": "电容",
            "probability": 3.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 61
      },
      "测试关机": {
        "phenomena": "测试关机 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 66.7,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 33.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 3
      },
      "OTG不良": {
        "phenomena": "OTG不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 29.2,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 25,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 12.5,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3801",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R6301",
            "component_type": "电阻",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5203",
            "component_type": "电容",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6603",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4302",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 24
      },
      "磁力不良": {
        "phenomena": "磁力不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U5504",
            "component_type": "IC芯片",
            "probability": 45.9,
            "case_count": 17,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5513",
            "component_type": "电容",
            "probability": 5.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 5.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 5.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 5.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9009",
            "component_type": "电阻",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6614",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J102",
            "component_type": "连接器",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J101",
            "component_type": "连接器",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 37
      },
      "开机定屏": {
        "phenomena": "开机定屏 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 45.5,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 36.4,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501 U1701",
            "component_type": "IC芯片",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6606",
            "component_type": "IC芯片",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 11
      },
      "卡机": {
        "phenomena": "卡机 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 45.5,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 36.4,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501 U1701",
            "component_type": "IC芯片",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6606",
            "component_type": "IC芯片",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 11
      },
      "充电不良": {
        "phenomena": "充电不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U3801",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "后摄像头打不开": {
        "phenomena": "后摄像头打不开 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 13.3,
            "case_count": 11,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 9.6,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4501",
            "component_type": "IC芯片",
            "probability": 8.4,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 7.2,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4802",
            "component_type": "连接器",
            "probability": 6,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 4.8,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4506",
            "component_type": "IC芯片",
            "probability": 3.6,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1001",
            "component_type": "IC芯片",
            "probability": 2.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R4807",
            "component_type": "电阻",
            "probability": 2.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R4501",
            "component_type": "电阻",
            "probability": 2.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 83
      },
      "听筒无声、杂音、破音": {
        "phenomena": "听筒无声、杂音、破音 (X6878-Q352)",
        "top_components": [
          {
            "point": "U4301",
            "component_type": "IC芯片",
            "probability": 20.8,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 12.5,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "B6003",
            "component_type": "其他",
            "probability": 8.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 8.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "B6004",
            "component_type": "其他",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C4311",
            "component_type": "电容",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C4304",
            "component_type": "电容",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9001",
            "component_type": "天线/射频",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT301",
            "component_type": "天线/射频",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 4.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 24
      },
      "老化超时": {
        "phenomena": "老化超时 (X6878-Q352)",
        "top_components": [
          {
            "point": "U1601",
            "component_type": "IC芯片",
            "probability": 81.8,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 11
      },
      "测试红外发射器": {
        "phenomena": "测试红外发射器 (X6878-Q352)",
        "top_components": [
          {
            "point": "Q5501",
            "component_type": "其他",
            "probability": 27.3,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "D5501",
            "component_type": "二极管",
            "probability": 27.3,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6902",
            "component_type": "IC芯片",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5204",
            "component_type": "电容",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9003",
            "component_type": "天线/射频",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3828",
            "component_type": "电阻",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 11
      },
      "主麦克无声、杂音、破音": {
        "phenomena": "主麦克无声、杂音、破音 (X6878-Q352)",
        "top_components": [
          {
            "point": "U4101",
            "component_type": "IC芯片",
            "probability": 20,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 13.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 13.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 13.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R0606 R0604",
            "component_type": "电阻",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J9001",
            "component_type": "连接器",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9009",
            "component_type": "电阻",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5207",
            "component_type": "电容",
            "probability": 6.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 15
      },
      "前摄像头打不开": {
        "phenomena": "前摄像头打不开 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 20,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 20,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R0710",
            "component_type": "电阻",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "MIC101",
            "component_type": "麦克风/马达",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U302",
            "component_type": "IC芯片",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6302",
            "component_type": "IC芯片",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6804",
            "component_type": "IC芯片",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 10
      },
      "陀螺仪测试": {
        "phenomena": "陀螺仪测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "U5501",
            "component_type": "IC芯片",
            "probability": 22.9,
            "case_count": 11,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 8.3,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 6.2,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5504",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 4.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 2.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R6910",
            "component_type": "电阻",
            "probability": 2.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 48
      },
      "GPS不良": {
        "phenomena": "GPS不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 10.8,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 5.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5202",
            "component_type": "连接器",
            "probability": 5.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 5.4,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R8405",
            "component_type": "电阻",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9002",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8401",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4302",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 37
      },
      "NFC测试不过": {
        "phenomena": "NFC测试不过 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 32.3,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 6.5,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J303",
            "component_type": "连接器",
            "probability": 6.5,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U10801",
            "component_type": "IC芯片",
            "probability": 3.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L10802",
            "component_type": "电感",
            "probability": 3.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C10803",
            "component_type": "电容",
            "probability": 3.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT5605 ANT5606",
            "component_type": "天线/射频",
            "probability": 3.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT5602",
            "component_type": "天线/射频",
            "probability": 3.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 3.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 3.2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 31
      },
      "不触屏、触屏不准": {
        "phenomena": "不触屏、触屏不准 (X6878-Q352)",
        "top_components": [
          {
            "point": "J5202",
            "component_type": "连接器",
            "probability": 28.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5204",
            "component_type": "电容",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R6910",
            "component_type": "电阻",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 7
      },
      "下载失败": {
        "phenomena": "下载失败 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 8,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 8,
            "case_count": 9,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 6.2,
            "case_count": 7,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 4.5,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 4.5,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 4.5,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 4.5,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 2.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 2.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 112
      },
      "STATUS_STOP_RF_FAILED": {
        "phenomena": "STATUS_STOP_RF_FAILED (X6878-Q352)",
        "top_components": [
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9009",
            "component_type": "电阻",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6001",
            "component_type": "IC芯片",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9001",
            "component_type": "天线/射频",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6704",
            "component_type": "IC芯片",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT5605",
            "component_type": "天线/射频",
            "probability": 12.5,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 8
      },
      "BB_TEST:Connect_In_MetaMode": {
        "phenomena": "BB_TEST:Connect_In_MetaMode (X6878-Q352)",
        "top_components": [
          {
            "point": "移板",
            "component_type": "其他",
            "probability": 90.8,
            "case_count": 99,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501.U1601.U1701",
            "component_type": "IC芯片",
            "probability": 7.3,
            "case_count": 8,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501.U1701.U1601",
            "component_type": "IC芯片",
            "probability": 0.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 0.9,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 109
      },
      "STATUS_GET_NVRAM_BUFFER_FIELD_FAILED": {
        "phenomena": "STATUS_GET_NVRAM_BUFFER_FIELD_FAILED (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_BB",
            "component_type": "屏蔽罩",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L4402",
            "component_type": "电感",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6503",
            "component_type": "IC芯片",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT5606",
            "component_type": "天线/射频",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 4
      },
      "收音机不良": {
        "phenomena": "收音机不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "U8001 6#到 R0608开路",
            "component_type": "IC芯片",
            "probability": 33.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8001 16#到 R0609开路",
            "component_type": "IC芯片",
            "probability": 33.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 33.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 3
      },
      "飞件": {
        "phenomena": "飞件 (X6878-Q352)",
        "top_components": [
          {
            "point": "C4802",
            "component_type": "电容",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R6910",
            "component_type": "电阻",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 2
      },
      "无振动": {
        "phenomena": "无振动 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 28.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9009",
            "component_type": "电阻",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1601",
            "component_type": "IC芯片",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1701",
            "component_type": "IC芯片",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6508",
            "component_type": "IC芯片",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R0714",
            "component_type": "电阻",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 7
      },
      "翻贴": {
        "phenomena": "翻贴 (X6878-Q352)",
        "top_components": [
          {
            "point": "J9001",
            "component_type": "连接器",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R4801",
            "component_type": "电阻",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 2
      },
      "下载大电流": {
        "phenomena": "下载大电流 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501 U1601U1701",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "充电电流不良": {
        "phenomena": "充电电流不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "获取端口失败": {
        "phenomena": "获取端口失败 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 50,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3801",
            "component_type": "IC芯片",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 4
      },
      "前摄像头不拍照、不聚焦": {
        "phenomena": "前摄像头不拍照、不聚焦 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 22.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R0615",
            "component_type": "电阻",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4506",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4701",
            "component_type": "连接器",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 9
      },
      "光感不良": {
        "phenomena": "光感不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 9.8,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 7.8,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 7.8,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 5.9,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 5.9,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 3.9,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4802",
            "component_type": "连接器",
            "probability": 3.9,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 3.9,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 3.9,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9018",
            "component_type": "电阻",
            "probability": 2,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 51
      },
      "蓝牙测试": {
        "phenomena": "蓝牙测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "R8403",
            "component_type": "电阻",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "喇叭无声、杂音、破音": {
        "phenomena": "喇叭无声、杂音、破音 (X6878-Q352)",
        "top_components": [
          {
            "point": "U4302",
            "component_type": "IC芯片",
            "probability": 33.3,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4101",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT10810",
            "component_type": "天线/射频",
            "probability": 8.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6808",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 8.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3820",
            "component_type": "电阻",
            "probability": 8.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 12
      },
      "耳机测试": {
        "phenomena": "耳机测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "U4101",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "不读SIM卡1": {
        "phenomena": "不读SIM卡1 (X6878-Q352)",
        "top_components": [
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 28.6,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9009",
            "component_type": "电阻",
            "probability": 14.3,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R4010",
            "component_type": "电阻",
            "probability": 9.5,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4002",
            "component_type": "IC芯片",
            "probability": 9.5,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5206",
            "component_type": "电容",
            "probability": 4.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1601",
            "component_type": "IC芯片",
            "probability": 4.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9010",
            "component_type": "电阻",
            "probability": 4.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C9101",
            "component_type": "电容",
            "probability": 4.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C9030",
            "component_type": "电容",
            "probability": 4.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8401",
            "component_type": "IC芯片",
            "probability": 4.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 21
      },
      "不识耳机": {
        "phenomena": "不识耳机 (X6878-Q352)",
        "top_components": [
          {
            "point": "U4401",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "老化少项": {
        "phenomena": "老化少项 (X6878-Q352)",
        "top_components": [
          {
            "point": "U1601",
            "component_type": "IC芯片",
            "probability": 45.5,
            "case_count": 5,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9002",
            "component_type": "天线/射频",
            "probability": 18.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J303",
            "component_type": "连接器",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT303",
            "component_type": "天线/射频",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 9.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 11
      },
      "后置闪光灯测试": {
        "phenomena": "后置闪光灯测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "J4803",
            "component_type": "连接器",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "移植板": {
        "phenomena": "移植板 (X6878-Q352)",
        "top_components": [
          {
            "point": "PCB",
            "component_type": "其他",
            "probability": 41.7,
            "case_count": 15,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U1001",
            "component_type": "IC芯片",
            "probability": 27.8,
            "case_count": 10,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U0501",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "L6606",
            "component_type": "电感",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5204 C5209 C5299",
            "component_type": "电容",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6614",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6701",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4005",
            "component_type": "IC芯片",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C3513",
            "component_type": "电容",
            "probability": 2.8,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 36
      },
      "红外测试不过": {
        "phenomena": "红外测试不过 (X6878-Q352)",
        "top_components": [
          {
            "point": "D5501",
            "component_type": "二极管",
            "probability": 33.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "Q5501",
            "component_type": "其他",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U2401",
            "component_type": "IC芯片",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J303",
            "component_type": "连接器",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J4802",
            "component_type": "连接器",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 6
      },
      "SIM卡测试": {
        "phenomena": "SIM卡测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "J5202",
            "component_type": "连接器",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "无线充电测试": {
        "phenomena": "无线充电测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "无法进入省功耗PSM模式": {
        "phenomena": "无法进入省功耗PSM模式 (X6878-Q352)",
        "top_components": [
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 60,
            "case_count": 6,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 20,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9009",
            "component_type": "电阻",
            "probability": 10,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 10
      },
      "距感测试": {
        "phenomena": "距感测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "U5502",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "立件": {
        "phenomena": "立件 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT10801",
            "component_type": "天线/射频",
            "probability": 16.7,
            "case_count": 3,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R3811",
            "component_type": "电阻",
            "probability": 11.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J3801",
            "component_type": "连接器",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6607",
            "component_type": "IC芯片",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U8001",
            "component_type": "IC芯片",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U4401",
            "component_type": "IC芯片",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "MIC101",
            "component_type": "麦克风/马达",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6901",
            "component_type": "IC芯片",
            "probability": 5.6,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 18
      },
      "多件": {
        "phenomena": "多件 (X6878-Q352)",
        "top_components": [
          {
            "point": "J3802",
            "component_type": "连接器",
            "probability": 28.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J202",
            "component_type": "连接器",
            "probability": 28.6,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9103",
            "component_type": "天线/射频",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5204",
            "component_type": "电容",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U7003",
            "component_type": "IC芯片",
            "probability": 14.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 7
      },
      "写入SN到手机APBP": {
        "phenomena": "写入SN到手机APBP (X6878-Q352)",
        "top_components": [
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "R9008",
            "component_type": "电阻",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3901",
            "component_type": "IC芯片",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5504",
            "component_type": "IC芯片",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 4
      },
      "听筒测试": {
        "phenomena": "听筒测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "C4704",
            "component_type": "电容",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "短路": {
        "phenomena": "短路 (X6878-Q352)",
        "top_components": [
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 4,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 4
      },
      "指纹测试": {
        "phenomena": "指纹测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 2
      },
      "压件": {
        "phenomena": "压件 (X6878-Q352)",
        "top_components": [
          {
            "point": "J4801",
            "component_type": "连接器",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "PCBA",
            "component_type": "其他",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6805",
            "component_type": "IC芯片",
            "probability": 25,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 4
      },
      "Mic测试": {
        "phenomena": "Mic测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "U9005",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "下载FR失败": {
        "phenomena": "下载FR失败 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT9103",
            "component_type": "天线/射频",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 2
      },
      "显示LTE线损": {
        "phenomena": "显示LTE线损 (X6878-Q352)",
        "top_components": [
          {
            "point": "J4802",
            "component_type": "连接器",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "发送ATAstart指令": {
        "phenomena": "发送ATAstart指令 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT9002",
            "component_type": "天线/射频",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "充电测试": {
        "phenomena": "充电测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "U6503",
            "component_type": "IC芯片",
            "probability": 33.3,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT9002",
            "component_type": "天线/射频",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J9001",
            "component_type": "连接器",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J3801",
            "component_type": "连接器",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "C5204",
            "component_type": "电容",
            "probability": 16.7,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 6
      },
      "加速度传感器": {
        "phenomena": "加速度传感器 (X6878-Q352)",
        "top_components": [
          {
            "point": "SH_TRANS",
            "component_type": "屏蔽罩",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "光感测试": {
        "phenomena": "光感测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "重力传感器测试": {
        "phenomena": "重力传感器测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT9104",
            "component_type": "天线/射频",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "SAR测试不良": {
        "phenomena": "SAR测试不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT5605",
            "component_type": "天线/射频",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U3501",
            "component_type": "IC芯片",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 2
      },
      "STATUS_TESTER_CTRL_DEINIT_FAILED": {
        "phenomena": "STATUS_TESTER_CTRL_DEINIT_FAILED (X6878-Q352)",
        "top_components": [
          {
            "point": "U7701",
            "component_type": "IC芯片",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6606",
            "component_type": "IC芯片",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 2
      },
      "STATUS_READ_NVRAM_FAILED": {
        "phenomena": "STATUS_READ_NVRAM_FAILED (X6878-Q352)",
        "top_components": [
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 22.2,
            "case_count": 2,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6301",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT5603",
            "component_type": "天线/射频",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "ANT5606",
            "component_type": "天线/射频",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "PCBA",
            "component_type": "其他",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6302",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U7003",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U5504",
            "component_type": "IC芯片",
            "probability": 11.1,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 9
      },
      "STATUS_WRITE_CAL_FILE_FAILED": {
        "phenomena": "STATUS_WRITE_CAL_FILE_FAILED (X6878-Q352)",
        "top_components": [
          {
            "point": "U6606",
            "component_type": "IC芯片",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "M4301",
            "component_type": "麦克风/马达",
            "probability": 50,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 2
      },
      "无功率": {
        "phenomena": "无功率 (X6878-Q352)",
        "top_components": [
          {
            "point": "U9003",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "反向充电不良": {
        "phenomena": "反向充电不良 (X6878-Q352)",
        "top_components": [
          {
            "point": "C4317",
            "component_type": "电容",
            "probability": 33.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "U6901",
            "component_type": "IC芯片",
            "probability": 33.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          },
          {
            "point": "J5201",
            "component_type": "连接器",
            "probability": 33.3,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 3
      },
      "连接WIFI": {
        "phenomena": "连接WIFI (X6878-Q352)",
        "top_components": [
          {
            "point": "U10801",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "NFC测试": {
        "phenomena": "NFC测试 (X6878-Q352)",
        "top_components": [
          {
            "point": "U2601",
            "component_type": "IC芯片",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "综测不开机": {
        "phenomena": "综测不开机 (X6878-Q352)",
        "top_components": [
          {
            "point": "ANT9104",
            "component_type": "天线/射频",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "检查GSM校准标志位": {
        "phenomena": "检查GSM校准标志位 (X6878-Q352)",
        "top_components": [
          {
            "point": "C6735",
            "component_type": "电容",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "不能识别T卡": {
        "phenomena": "不能识别T卡 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      },
      "板边漏铜": {
        "phenomena": "板边漏铜 (X6878-Q352)",
        "top_components": [
          {
            "point": "未知/未记录",
            "component_type": "未知",
            "probability": 100,
            "case_count": 1,
            "fault_type": "",
            "repair_method": ""
          }
        ],
        "total_count": 1
      }
    },
    "componentMap": {
      "屏蔽罩": [
        {
          "位号": "SH_TRANS",
          "型号": "",
          "功能": "射频收发屏蔽罩"
        },
        {
          "位号": "SH_BB",
          "型号": "",
          "功能": "基带屏蔽罩"
        },
        {
          "位号": "SH_RFPA",
          "型号": "",
          "功能": "射频PA屏蔽罩"
        },
        {
          "位号": "SH-BB",
          "型号": "",
          "功能": "SH-BB"
        },
        {
          "位号": "SH_MOTOR",
          "型号": "",
          "功能": "马达屏蔽罩"
        },
        {
          "位号": "SH-PMU",
          "型号": "",
          "功能": "电源屏蔽罩"
        },
        {
          "位号": "SH_LFEM",
          "型号": "",
          "功能": "低频前端屏蔽罩"
        },
        {
          "位号": "SH-TRANS",
          "型号": "",
          "功能": "射频收发屏蔽罩"
        },
        {
          "位号": "SH-RFPA",
          "型号": "",
          "功能": "SH-RFPA"
        },
        {
          "位号": "SH-GYR",
          "型号": "",
          "功能": "SH-GYR"
        },
        {
          "位号": "SH_PMU",
          "型号": "",
          "功能": "SH_PMU"
        },
        {
          "位号": "SH_LDO1",
          "型号": "",
          "功能": "SH_LDO1"
        },
        {
          "位号": "SH_TRANS SH_PMU",
          "型号": "",
          "功能": "SH_TRANS SH_PMU"
        },
        {
          "位号": "SH_GYR",
          "型号": "",
          "功能": "SH_GYR"
        },
        {
          "位号": "SH_WCN",
          "型号": "",
          "功能": "SH_WCN"
        },
        {
          "位号": "SH-MRF",
          "型号": "",
          "功能": "SH-MRF"
        },
        {
          "位号": "SH-LFEM",
          "型号": "",
          "功能": "SH-LFEM"
        },
        {
          "位号": "SH_RF",
          "型号": "",
          "功能": "SH_RF"
        },
        {
          "位号": "SH_BBSH_GYR",
          "型号": "",
          "功能": "SH_BBSH_GYR"
        },
        {
          "位号": "SH_BB ANT10801",
          "型号": "",
          "功能": "SH_BB ANT10801"
        }
      ],
      "IC芯片": [
        {
          "位号": "U0501",
          "型号": "",
          "功能": "主芯片SoC / PMK7635主PMIC"
        },
        {
          "位号": "U5501",
          "型号": "",
          "功能": "传感器IC"
        },
        {
          "位号": "U1701",
          "型号": "",
          "功能": "UFS存储"
        },
        {
          "位号": "U2401",
          "型号": "",
          "功能": "PMIV0108充电管理"
        },
        {
          "位号": "U2601",
          "型号": "",
          "功能": "主PMIC电源管理 / MT6360"
        },
        {
          "位号": "U1601",
          "型号": "",
          "功能": "LPDDR4X内存"
        },
        {
          "位号": "U3501",
          "型号": "",
          "功能": "副PMIC / MT6315"
        },
        {
          "位号": "U6001",
          "型号": "",
          "功能": "音频功放PA / AW87319"
        },
        {
          "位号": "U3801",
          "型号": "",
          "功能": "充电管理IC"
        },
        {
          "位号": "U6701",
          "型号": "",
          "功能": "U6701"
        },
        {
          "位号": "U6614",
          "型号": "",
          "功能": "U6614"
        },
        {
          "位号": "U9003",
          "型号": "",
          "功能": "天线开关"
        },
        {
          "位号": "U6502",
          "型号": "",
          "功能": "U6502"
        },
        {
          "位号": "U6607",
          "型号": "",
          "功能": "射频收发器 / SDR435"
        },
        {
          "位号": "U6603",
          "型号": "",
          "功能": "U6603"
        },
        {
          "位号": "U7003",
          "型号": "",
          "功能": "U7003"
        },
        {
          "位号": "U6802",
          "型号": "",
          "功能": "U6802"
        },
        {
          "位号": "U1001",
          "型号": "",
          "功能": "U1001"
        },
        {
          "位号": "U6616",
          "型号": "",
          "功能": "U6616"
        },
        {
          "位号": "U7001",
          "型号": "",
          "功能": "U7001"
        },
        {
          "位号": "U6806",
          "型号": "",
          "功能": "U6806"
        },
        {
          "位号": "U6304",
          "型号": "",
          "功能": "U6304"
        },
        {
          "位号": "U6702",
          "型号": "",
          "功能": "U6702"
        },
        {
          "位号": "U7901",
          "型号": "",
          "功能": "U7901"
        },
        {
          "位号": "U6805",
          "型号": "",
          "功能": "射频开关 / QDM2316"
        },
        {
          "位号": "U6602",
          "型号": "",
          "功能": "U6602"
        },
        {
          "位号": "U6613",
          "型号": "",
          "功能": "U6613"
        },
        {
          "位号": "U6902",
          "型号": "",
          "功能": "U6902"
        },
        {
          "位号": "U6302",
          "型号": "",
          "功能": "U6302"
        },
        {
          "位号": "U8401",
          "型号": "",
          "功能": "U8401"
        }
      ],
      "变压器/晶体管": [
        {
          "位号": "T104",
          "型号": "",
          "功能": "变压器/晶体管"
        },
        {
          "位号": "T101",
          "型号": "",
          "功能": "T101"
        },
        {
          "位号": "TP_VBAT",
          "型号": "",
          "功能": "TP_VBAT"
        },
        {
          "位号": "TP205",
          "型号": "",
          "功能": "TP205"
        },
        {
          "位号": "TP203",
          "型号": "",
          "功能": "TP203"
        }
      ],
      "天线/射频": [
        {
          "位号": "ANT9007",
          "型号": "",
          "功能": "ANT9007"
        },
        {
          "位号": "ANT5603",
          "型号": "",
          "功能": "ANT5603"
        },
        {
          "位号": "ANT301",
          "型号": "",
          "功能": "ANT301"
        },
        {
          "位号": "ANT5605",
          "型号": "",
          "功能": "ANT5605"
        },
        {
          "位号": "ANT3901",
          "型号": "",
          "功能": "ANT3901"
        },
        {
          "位号": "ANT5604",
          "型号": "",
          "功能": "ANT5604"
        },
        {
          "位号": "ANT10801",
          "型号": "",
          "功能": "天线连接器 / RF Connector"
        },
        {
          "位号": "ANT9002",
          "型号": "",
          "功能": "ANT9002"
        },
        {
          "位号": "ANT9004",
          "型号": "",
          "功能": "ANT9004"
        },
        {
          "位号": "ANT9005",
          "型号": "",
          "功能": "ANT9005"
        },
        {
          "位号": "ANT9103",
          "型号": "",
          "功能": "ANT9103"
        },
        {
          "位号": "ANT3917",
          "型号": "",
          "功能": "ANT3917"
        },
        {
          "位号": "ANT9003",
          "型号": "",
          "功能": "ANT9003"
        },
        {
          "位号": "ANT9105",
          "型号": "",
          "功能": "ANT9105"
        },
        {
          "位号": "ANT9102",
          "型号": "",
          "功能": "ANT9102"
        },
        {
          "位号": "ANT9101",
          "型号": "",
          "功能": "ANT9101"
        },
        {
          "位号": "ANT5606",
          "型号": "",
          "功能": "ANT5606"
        },
        {
          "位号": "ANT9001",
          "型号": "",
          "功能": "ANT9001"
        },
        {
          "位号": "ANT5601",
          "型号": "",
          "功能": "ANT5601"
        },
        {
          "位号": "ANT5602",
          "型号": "",
          "功能": "ANT5602"
        },
        {
          "位号": "ANT9008",
          "型号": "",
          "功能": "ANT9008"
        },
        {
          "位号": "ANT9009",
          "型号": "",
          "功能": "ANT9009"
        },
        {
          "位号": "ANT3908",
          "型号": "",
          "功能": "ANT3908"
        },
        {
          "位号": "ANT3902",
          "型号": "",
          "功能": "ANT3902"
        },
        {
          "位号": "ANT6601",
          "型号": "",
          "功能": "ANT6601"
        },
        {
          "位号": "ANT6504",
          "型号": "",
          "功能": "ANT6504"
        },
        {
          "位号": "ANT3915",
          "型号": "",
          "功能": "ANT3915"
        },
        {
          "位号": "ANT9104",
          "型号": "",
          "功能": "ANT9104"
        },
        {
          "位号": "ANT1801",
          "型号": "",
          "功能": "ANT1801"
        },
        {
          "位号": "ANT303",
          "型号": "",
          "功能": "ANT303"
        }
      ],
      "电容": [
        {
          "位号": "C9014",
          "型号": "",
          "功能": "电容"
        },
        {
          "位号": "C1628",
          "型号": "",
          "功能": "C1628"
        },
        {
          "位号": "C5299",
          "型号": "",
          "功能": "电容"
        },
        {
          "位号": "C2815",
          "型号": "",
          "功能": "C2815"
        },
        {
          "位号": "C3027",
          "型号": "",
          "功能": "C3027"
        },
        {
          "位号": "C6825",
          "型号": "",
          "功能": "C6825"
        },
        {
          "位号": "C5204",
          "型号": "",
          "功能": "显示通路电容"
        },
        {
          "位号": "C2416",
          "型号": "",
          "功能": "C2416"
        },
        {
          "位号": "C2814",
          "型号": "",
          "功能": "C2814"
        },
        {
          "位号": "C4801",
          "型号": "",
          "功能": "C4801"
        },
        {
          "位号": "C6802",
          "型号": "",
          "功能": "C6802"
        },
        {
          "位号": "C7008",
          "型号": "",
          "功能": "C7008"
        },
        {
          "位号": "C7012",
          "型号": "",
          "功能": "C7012"
        },
        {
          "位号": "C6603",
          "型号": "",
          "功能": "C6603"
        },
        {
          "位号": "C6855",
          "型号": "",
          "功能": "C6855"
        },
        {
          "位号": "C6135",
          "型号": "",
          "功能": "C6135"
        },
        {
          "位号": "C9119",
          "型号": "",
          "功能": "C9119"
        },
        {
          "位号": "C3018",
          "型号": "",
          "功能": "C3018"
        },
        {
          "位号": "C9010",
          "型号": "",
          "功能": "C9010"
        },
        {
          "位号": "C6129",
          "型号": "",
          "功能": "C6129"
        },
        {
          "位号": "C1424",
          "型号": "",
          "功能": "C1424"
        },
        {
          "位号": "C6007",
          "型号": "",
          "功能": "C6007"
        },
        {
          "位号": "C3816",
          "型号": "",
          "功能": "C3816"
        },
        {
          "位号": "C6807",
          "型号": "",
          "功能": "C6807"
        },
        {
          "位号": "C6812",
          "型号": "",
          "功能": "C6812"
        },
        {
          "位号": "C7005",
          "型号": "",
          "功能": "C7005"
        },
        {
          "位号": "C6847",
          "型号": "",
          "功能": "C6847"
        },
        {
          "位号": "C10824",
          "型号": "",
          "功能": "C10824"
        },
        {
          "位号": "C6640",
          "型号": "",
          "功能": "C6640"
        },
        {
          "位号": "C6650",
          "型号": "",
          "功能": "C6650"
        }
      ],
      "电阻": [
        {
          "位号": "R9017",
          "型号": "",
          "功能": "电阻"
        },
        {
          "位号": "R3812",
          "型号": "",
          "功能": "电阻"
        },
        {
          "位号": "R5806",
          "型号": "",
          "功能": "电阻"
        },
        {
          "位号": "R9108",
          "型号": "",
          "功能": "R9108"
        },
        {
          "位号": "R4010",
          "型号": "",
          "功能": "R4010"
        },
        {
          "位号": "R5225",
          "型号": "",
          "功能": "R5225"
        },
        {
          "位号": "R3829",
          "型号": "",
          "功能": "R3829"
        },
        {
          "位号": "R9011",
          "型号": "",
          "功能": "R9011"
        },
        {
          "位号": "R103",
          "型号": "",
          "功能": "R103"
        },
        {
          "位号": "R9007",
          "型号": "",
          "功能": "R9007"
        },
        {
          "位号": "R6507",
          "型号": "",
          "功能": "R6507"
        },
        {
          "位号": "R6635",
          "型号": "",
          "功能": "R6635"
        },
        {
          "位号": "R6619",
          "型号": "",
          "功能": "R6619"
        },
        {
          "位号": "R6901",
          "型号": "",
          "功能": "R6901"
        },
        {
          "位号": "R6903",
          "型号": "",
          "功能": "R6903"
        },
        {
          "位号": "R6505",
          "型号": "",
          "功能": "R6505"
        },
        {
          "位号": "R9003",
          "型号": "",
          "功能": "R9003"
        },
        {
          "位号": "R6502",
          "型号": "",
          "功能": "R6502"
        },
        {
          "位号": "R8311",
          "型号": "",
          "功能": "R8311"
        },
        {
          "位号": "R6811",
          "型号": "",
          "功能": "R6811"
        },
        {
          "位号": "R6501",
          "型号": "",
          "功能": "R6501"
        },
        {
          "位号": "R5604",
          "型号": "",
          "功能": "R5604"
        },
        {
          "位号": "R9014",
          "型号": "",
          "功能": "R9014"
        },
        {
          "位号": "R0606 R0604",
          "型号": "",
          "功能": "R0606 R0604"
        },
        {
          "位号": "R5603",
          "型号": "",
          "功能": "R5603"
        },
        {
          "位号": "R120",
          "型号": "",
          "功能": "R120"
        },
        {
          "位号": "R8405",
          "型号": "",
          "功能": "R8405"
        },
        {
          "位号": "R5224",
          "型号": "",
          "功能": "R5224"
        },
        {
          "位号": "R3820",
          "型号": "",
          "功能": "R3820"
        },
        {
          "位号": "R4501",
          "型号": "",
          "功能": "R4501"
        }
      ],
      "连接器": [
        {
          "位号": "J301",
          "型号": "",
          "功能": "射频座"
        },
        {
          "位号": "J304",
          "型号": "",
          "功能": "SIM卡座 / 指纹连接器"
        },
        {
          "位号": "J101",
          "型号": "",
          "功能": "J101"
        },
        {
          "位号": "J9002",
          "型号": "",
          "功能": "连接器"
        },
        {
          "位号": "J9003",
          "型号": "",
          "功能": "连接器"
        },
        {
          "位号": "J9001",
          "型号": "",
          "功能": "J9001"
        },
        {
          "位号": "J9005",
          "型号": "",
          "功能": "J9005"
        },
        {
          "位号": "J4802",
          "型号": "",
          "功能": "J4802"
        },
        {
          "位号": "J3801",
          "型号": "",
          "功能": "电池BTB连接器 / Main FPC BTB"
        },
        {
          "位号": "J4801",
          "型号": "",
          "功能": "J4801"
        },
        {
          "位号": "J204",
          "型号": "",
          "功能": "J204"
        },
        {
          "位号": "J5201",
          "型号": "",
          "功能": "LCD连接器"
        },
        {
          "位号": "J201",
          "型号": "",
          "功能": "J201"
        },
        {
          "位号": "J9004",
          "型号": "",
          "功能": "J9004"
        },
        {
          "位号": "J4803",
          "型号": "",
          "功能": "J4803"
        },
        {
          "位号": "J5202",
          "型号": "",
          "功能": "副板连接器"
        },
        {
          "位号": "J202",
          "型号": "",
          "功能": "J202"
        },
        {
          "位号": "J303",
          "型号": "",
          "功能": "射频座"
        },
        {
          "位号": "J316",
          "型号": "",
          "功能": "J316"
        },
        {
          "位号": "J9006",
          "型号": "",
          "功能": "J9006"
        },
        {
          "位号": "J302",
          "型号": "",
          "功能": "J302"
        },
        {
          "位号": "J403",
          "型号": "",
          "功能": "J403"
        },
        {
          "位号": "J4701",
          "型号": "",
          "功能": "J4701"
        },
        {
          "位号": "J3802",
          "型号": "",
          "功能": "J3802"
        },
        {
          "位号": "J102",
          "型号": "",
          "功能": "J102"
        },
        {
          "位号": "J4804",
          "型号": "",
          "功能": "J4804"
        },
        {
          "位号": "J6401",
          "型号": "",
          "功能": "J6401"
        },
        {
          "位号": "J401",
          "型号": "",
          "功能": "J401"
        },
        {
          "位号": "J9101",
          "型号": "",
          "功能": "J9101"
        },
        {
          "位号": "J9002.1",
          "型号": "",
          "功能": "J9002.1"
        }
      ],
      "电感": [
        {
          "位号": "L6316",
          "型号": "",
          "功能": "电感"
        },
        {
          "位号": "L6303",
          "型号": "",
          "功能": "电感"
        },
        {
          "位号": "L6319",
          "型号": "",
          "功能": "电感"
        },
        {
          "位号": "L6605",
          "型号": "",
          "功能": "电感"
        },
        {
          "位号": "L6502",
          "型号": "",
          "功能": "电感"
        },
        {
          "位号": "L9001",
          "型号": "",
          "功能": "电感"
        },
        {
          "位号": "L9009",
          "型号": "",
          "功能": "电感"
        },
        {
          "位号": "L6721",
          "型号": "",
          "功能": "L6721"
        },
        {
          "位号": "L6606",
          "型号": "",
          "功能": "L6606"
        },
        {
          "位号": "L2801",
          "型号": "",
          "功能": "L2801"
        },
        {
          "位号": "L6622",
          "型号": "",
          "功能": "L6622"
        },
        {
          "位号": "L2902",
          "型号": "",
          "功能": "L2902"
        },
        {
          "位号": "L6607",
          "型号": "",
          "功能": "L6607"
        },
        {
          "位号": "L2806",
          "型号": "",
          "功能": "L2806"
        },
        {
          "位号": "L2805",
          "型号": "",
          "功能": "L2805"
        },
        {
          "位号": "L9101",
          "型号": "",
          "功能": "L9101"
        },
        {
          "位号": "L6625",
          "型号": "",
          "功能": "L6625"
        },
        {
          "位号": "L6407",
          "型号": "",
          "功能": "L6407"
        },
        {
          "位号": "L3403",
          "型号": "",
          "功能": "L3403"
        },
        {
          "位号": "L6315",
          "型号": "",
          "功能": "L6315"
        },
        {
          "位号": "L6101",
          "型号": "",
          "功能": "L6101"
        },
        {
          "位号": "L306",
          "型号": "",
          "功能": "L306"
        },
        {
          "位号": "L9005",
          "型号": "",
          "功能": "L9005"
        },
        {
          "位号": "L9006",
          "型号": "",
          "功能": "L9006"
        },
        {
          "位号": "L8404",
          "型号": "",
          "功能": "L8404"
        },
        {
          "位号": "L6321",
          "型号": "",
          "功能": "L6321"
        },
        {
          "位号": "L6727",
          "型号": "",
          "功能": "L6727"
        },
        {
          "位号": "L9004",
          "型号": "",
          "功能": "L9004"
        },
        {
          "位号": "L6118",
          "型号": "",
          "功能": "L6118"
        },
        {
          "位号": "L6805",
          "型号": "",
          "功能": "L6805"
        }
      ],
      "其他": [
        {
          "位号": "VIB_P",
          "型号": "",
          "功能": "VIB_P"
        },
        {
          "位号": "SN0007",
          "型号": "",
          "功能": "SN0007"
        },
        {
          "位号": "PCB",
          "型号": "",
          "功能": "PCB"
        },
        {
          "位号": "Q5501",
          "型号": "",
          "功能": "Q5501"
        },
        {
          "位号": "B6004",
          "型号": "",
          "功能": "B6004"
        },
        {
          "位号": "无",
          "型号": "",
          "功能": "无"
        },
        {
          "位号": "移板",
          "型号": "",
          "功能": "移板"
        },
        {
          "位号": "OU501",
          "型号": "",
          "功能": "OU501"
        },
        {
          "位号": "pcb",
          "型号": "",
          "功能": "pcb"
        },
        {
          "位号": "B6003",
          "型号": "",
          "功能": "B6003"
        },
        {
          "位号": "SSALWBG006",
          "型号": "",
          "功能": "SSALWBG006"
        },
        {
          "位号": "PCBA",
          "型号": "",
          "功能": "PCBA"
        },
        {
          "位号": "B6007",
          "型号": "",
          "功能": "B6007"
        },
        {
          "位号": "VIB_N",
          "型号": "",
          "功能": "VIB_N"
        },
        {
          "位号": "SCITDAT103",
          "型号": "",
          "功能": "SCITDAT103"
        },
        {
          "位号": ",J3801",
          "型号": "",
          "功能": ",J3801"
        },
        {
          "位号": "B103",
          "型号": "",
          "功能": "B103"
        },
        {
          "位号": "F101",
          "型号": "",
          "功能": "F101"
        },
        {
          "位号": "Q3801",
          "型号": "",
          "功能": "Q3801"
        },
        {
          "位号": "Q3804",
          "型号": "",
          "功能": "Q3804"
        }
      ],
      "扬声器": [
        {
          "位号": "SPKN1",
          "型号": "",
          "功能": "SPKN1"
        },
        {
          "位号": "SPKP1",
          "型号": "",
          "功能": "SPKP1"
        }
      ],
      "二极管": [
        {
          "位号": "D5501",
          "型号": "",
          "功能": "D5501"
        },
        {
          "位号": "D9003",
          "型号": "",
          "功能": "D9003"
        },
        {
          "位号": "D3902",
          "型号": "",
          "功能": "D3902"
        },
        {
          "位号": "D3919",
          "型号": "",
          "功能": "D3919"
        },
        {
          "位号": "D3804",
          "型号": "",
          "功能": "D3804"
        }
      ],
      "麦克风/马达": [
        {
          "位号": "MIC101",
          "型号": "",
          "功能": "主麦克风"
        },
        {
          "位号": "M4301",
          "型号": "",
          "功能": "副麦克风"
        }
      ],
      "晶振": [
        {
          "位号": "Y1801",
          "型号": "",
          "功能": "Y1801"
        }
      ]
    }
  }
};

// 导出为全局变量（兼容现有 HTML 的 <script src> 加载方式）
