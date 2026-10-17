# 明天真机部署 Checklist

## 0. 人员与安全

- [ ] 机器人负责人批准本次测试范围。
- [ ] 操作员 + 独立观察员到位，实体急停验证可用。
- [ ] 支撑/吊架、低风险初始姿态、低速/增益由现场负责人确认。
- [ ] 工作区清空，桌面/物体位置与任务一致。

## 1. Network test

- [ ] PC/Jetson 使用有线网络；记录网卡名和本地 IP（不提交 Git）。
- [ ] `ping -c 100 JETSON_IP`：记录丢包、平均和最大 RTT。
- [ ] 可用时完成双向 30 秒 `iperf3` 并保存结果。
- [ ] 首次 golden replay 改为 Jetson-local `127.0.0.1:5556`，排除网络变量。

## 2. Golden reference

- [ ] `reference.npz` SHA-256 为 `e16dc4b3125a0a611e15a0b555b9164ec268e71d63d44c70aba96d3b7608e053`。
- [ ] dry-run validator 为 PASS，且团队理解 `robot_safety=NOT_EVALUATED`。
- [ ] 团队复核“26 个桌面接触 step / 0.13 秒”的限制。
- [ ] SONIC real binary/policy/encoder/decoder/observation config 哈希与现场批准版本一致。
- [ ] SONIC 以 `zmq + localhost + 5556 + pose` 启动，CRC 未关闭。
- [ ] 先确认接收日志，再由现场人员切换控制；完成支撑状态下低风险回放。
- [ ] 保存日志、版本、hash、现场结论；不通过则停止。

## 3. Kimodo

- [ ] H100 单卡，`CUDA_VISIBLE_DEVICES=0`，batch=1。
- [ ] 权重 SHA-256 匹配 manifest。
- [ ] 无 simulator、无训练数据、配置无服务器绝对路径。
- [ ] 输出 canonical validator PASS。
- [ ] 记录 H100 mean/p50/p95 latency 和 peak allocated/reserved VRAM。
- [ ] 先离线复制到 Jetson，再重复 golden 的接收和低风险回放流程。

## 4. ARDY

- [ ] 固定源码 commit `693f74d13b3d04a0a22ce127ee79c929dd89756b`。
- [ ] H100 单卡、batch=1；两个权重 SHA-256 匹配 manifest。
- [ ] 无 simulator、无训练数据、配置无服务器绝对路径。
- [ ] 输出 canonical validator PASS；记录 H100 latency/VRAM。
- [ ] 离线复制到 Jetson，低风险回放并保存证据。

## 5. VA v4.1

- [ ] 输入只有 `rgb [H,W,3]`、`body [68]`、`hand [28]`。
- [ ] checkpoint SHA-256 匹配；H100 单卡、batch=1。
- [ ] 输出 `body_tokens [10,64]` 和 `hand_ref [50,14]`。
- [ ] SONIC protocol v4 decoder/observation config 哈希匹配。
- [ ] 记录 H100 latency/VRAM；先做 decoder/接收 dry-run，再考虑动作。

## 6. 最终放行

- [ ] 三个模型逐项完成，不并行混测，不跳过 golden。
- [ ] 任一 shape/hash/时钟/关节顺序/首帧/网络/硬件告警异常立即急停。
- [ ] 附上所有 JSON 报告、命令、commit hash、SONIC binary hash 和签字结论。
- [ ] 只有上述均通过，才讨论 nearby-PC live inference；S4000 live inference 仍保持关闭。

