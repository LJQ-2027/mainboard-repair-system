// Log 分析知识库
// 从主页面拆分，便于后续协作维护。
const logKnowledgeBase = {
    categories: {
        calibration: { label: '校准/综测日志', keywords: ['cali', 'calibration', '校准', 'nv', 'write nv', 'final test', '综测', 'factorytest'] },
        mtk: { label: 'MTK 平台日志', keywords: ['mtk', 'md1', 'ccci', 'rilj', 'meta mode', 'mdlog', 'modem warning'] },
        unisoc: { label: '展锐平台日志', keywords: ['unisoc', 'sprd', 'engpc', 'modemd', 'wcn', 'marlin', 'phs'] },
        android: { label: 'Android 系统日志', keywords: ['androidruntime', 'system_server', 'binder', 'anr', 'crash', 'fatal exception'] }
    },
    modules: {
        rf: { label: '射频模块', keywords: ['rf', 'tx', 'rx', 'afc', 'pa', 'coupler', 'rssi', 'band', 'channel'], focus: '关注 band/channel、功率、AFC、天线治具链路' },
        audio: { label: '音频模块', keywords: ['mic', 'speaker', 'audio', 'codec', 'headset', 'loopback'], focus: '关注 codec、mic/speaker 通路、回环值与阈值' },
        sensor: { label: '传感器模块', keywords: ['sensor', 'gyro', 'g-sensor', 'accel', 'als', 'ps', 'proximity'], focus: '关注 sensor hub、I2C 通信、阈值配置与原始读值' },
        nv: { label: 'NV/校准参数', keywords: ['nv', 'nvram', 'efs', 'write imei', 'write nv', 'calibration', 'save cali'], focus: '关注 NV item、写入结果码、分区权限和 META 模式' },
        port: { label: '串口/工具通信', keywords: ['port', 'at', 'usb', 'device not found', 'open port', 'timeout'], focus: '关注 COM 口、USB 枚举、AT 回应和超时点' },
        system: { label: 'Android系统/权限', keywords: ['selinux', 'denied', 'securityexception', 'system_server', 'binder', 'service not found'], focus: '关注服务权限、SELinux、系统服务注册状态' }
    },
    patterns: [
        { name: '校准参数写入失败', module: 'nv', severity: '高', keywords: ['write nv fail', 'nv write fail', 'calibration fail', 'save cali fail', 'write imei fail'], fields: ['NV item', 'result code', 'phase', 'band/channel'], diagnosis: '校准流程已执行到参数写入阶段，但 NV/EFS/分区写入失败，优先检查权限、分区挂载状态、NVRAM/NV 分区健康度。', suggestions: ['确认设备是否处于 META/工程模式', '核对 NV 分区读写权限与剩余空间', '查看是否存在 write protect / secure boot 限制'] },
        { name: '串口/AT 通信异常', module: 'port', severity: '高', keywords: ['open port fail', 'port not found', 'at timeout', 'no response', 'device not found'], fields: ['COM 端口号', 'AT 命令', 'timeout(ms)', 'USB 枚举状态'], diagnosis: '工具与设备通信链路异常，常见于驱动未加载、端口切换失败、设备未进入指定模式。', suggestions: ['检查 USB 驱动和端口识别', '确认 DUT 已进入校准/工厂模式', '复测时固定线材并减少 HUB 中转'] },
        { name: '射频校准失败', module: 'rf', severity: '高', keywords: ['rf cal fail', 'tx fail', 'rx fail', 'afc fail', 'pa current', 'coupler'], fields: ['band', 'channel', 'power', 'AFC', 'PA current'], diagnosis: '日志显示 RF 校准链路异常，需联合射频通路、仪表连接和 NV 参数排查。', suggestions: ['核对天线座/同轴线/治具接触', '查看 band/channel 是否集中失败', '对比良机同站位数据确认是否仪表偏移'] },
        { name: '音频/传感器综测失败', module: 'audio', severity: '中', keywords: ['mic fail', 'speaker fail', 'sensor fail', 'gyro fail', 'als fail', 'ps fail'], fields: ['test item', 'threshold', 'read value', 'device node'], diagnosis: '综测项返回值异常，通常与器件本体、驱动节点或上下限阈值配置有关。', suggestions: ['确认对应器件驱动节点是否正常创建设备文件', '检查上下限阈值是否被错误配置', '结合硬件替换与 I2C/SPI 通信日志交叉验证'] },
        { name: '权限/系统服务异常', module: 'system', severity: '中', keywords: ['permission denied', 'selinux', 'avc: denied', 'service not found', 'securityexception'], fields: ['service name', 'uid/pid', 'selinux domain', 'permission'], diagnosis: '系统权限或服务调用被拦截，可能影响校准工具访问底层服务或节点。', suggestions: ['检查工程版权限策略是否完整', '确认服务已启动且 binder/service name 正确', '结合 dmesg / logcat 查看 SELinux 拒绝详情'] },
        { name: '超时/流程中断', module: 'port', severity: '中', keywords: ['timeout', 'timed out', 'wait response timeout', 'step fail', 'abort'], fields: ['step name', 'timeout value', 'retry count', 'elapsed time'], diagnosis: '流程在特定阶段等待超时，需定位是设备侧未响应还是上位机流程控制问题。', suggestions: ['确认失败前最后一个成功步骤', '统计是否固定在同一阶段超时', '适当增加重试并对比异常前后的关键日志'] },
        { name: 'Modem/RIL 异常', module: 'system', severity: '中', keywords: ['rilj', 'radio not available', 'modem warning', 'ccci', 'md1'], fields: ['RIL request', 'modem state', 'error cause', 'slot id'], diagnosis: '通信栈与 Modem 交互异常，可能影响射频、校准或网络相关测试流程。', suggestions: ['核对 modem 启动状态与版本匹配', '查看 SIM/射频相关流程是否同步异常', '抓取失败前后 RILJ/CCCI 连续日志'] },
        { name: '传感器驱动/总线异常', module: 'sensor', severity: '中', keywords: ['i2c fail', 'probe failed', 'sensor init fail', 'read value fail', 'spi timeout'], fields: ['bus id', 'device addr', 'errno', 'probe stage'], diagnosis: '传感器初始化或总线通信异常，需排查器件本体、电源时序与驱动加载。', suggestions: ['查看 probe 阶段是否已报错', '核对 I2C/SPI 上拉、电压、时钟', '对比良机上电初始化顺序'] },
        { name: '音频回环/编解码异常', module: 'audio', severity: '中', keywords: ['loopback fail', 'codec fail', 'audio path fail', 'headset detect fail'], fields: ['audio device', 'route', 'codec reg', 'loopback result'], diagnosis: '音频路径建立失败或 codec 初始化异常，需联动音频驱动、器件和治具回环路径排查。', suggestions: ['核对 audio route 与 mixer path', '检查 codec 寄存器写入和电源时序', '复测 MIC/SPK/耳机座相关治具接触'] }
    ]
};
