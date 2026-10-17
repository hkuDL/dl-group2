# G1 Sonic Deployment

本目录位于 `paopaolin/dl-group2/deployment/g1_replay/`。克隆仓库后先进入本目录，再执行本文和操作手册中的命令：

```bash
cd dl-group2/deployment/g1_replay
```

当前状态：推理入口和打包工具已整理，golden 的格式与哈希已验证，SONIC v1/v4 打包已与源实现比对。三个模型仍需在 H100 上实际加载和执行；Jetson 接收、关节顺序映射、首帧与限幅检查、VA checkpoint 结构和 token 时序仍需完成验证。现有 `--mode real` 参数和 `--send` 参数不能作为硬件安全门禁或上机批准；现场验证通过前只用于离线检查和无执行的接收测试。

面向 Unitree G1 + Dex3-1 的独立真机部署仓库。当前里程碑只做四件事：

1. 在单张 NVIDIA GPU、`batch=1` 条件下运行 Kimodo、ARDY、VA 推理；
2. 推理时不启动 simulator，不读取训练数据；
3. 把 Kimodo/ARDY 输出转换为 SONIC protocol v1 motion reference，把 VA 输出转换为 SONIC protocol v4 token reference；
4. 先完成 network test 和 golden-reference replay，再允许模型输出进入 G1。

模型权重、训练数据、视频、日志、服务器绝对路径以及密钥不会进入 Git。仓库默认 fail-closed：没有现场 IP、关节限幅、首帧姿态和机器人负责人批准时，不会声称 reference 可上真机。

详细中文操作步骤见 `MANUAL_ZH.md` 和 `CHECKLIST_TOMORROW_ZH.md`（实现过程中生成）。

