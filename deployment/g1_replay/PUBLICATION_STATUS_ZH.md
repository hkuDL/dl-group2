# 本次整理范围与验证状态

本次只向目标仓库新增 `deployment/g1_replay/`，原有模型、脚本和根目录 README 保持原样。

已保留：三个模型的推理入口、Kimodo 最小运行时、ARDY 固定源码引用、模型权重及 normalization stats 哈希清单、canonical validator、SONIC 打包工具、golden reference、benchmark 工具和中文 SOP。

未收录：模型权重、训练数据集、视频、仿真 rollout、日志、凭证、服务器环境和 native binaries。

已验证：golden SHA-256、810 帧/50 Hz 结构、SONIC v1/v4 与 S4000 源 packer 的字节一致性、项目单元测试。

尚待验证：H100 三模型真实前向、安装依赖完整性与版本兼容、VA checkpoint 加载、关节顺序映射、VA token 调度、Jetson 接收与 G1 实机执行。显存和 latency 保持 NOT_RUN_H100。

ARDY 示例使用 checkpoint config 中的 10 步 diffusion schedule。Golden 在任务策略下通过抓取/抬升判定，但严格无桌面接触检查未通过，不能作为首个真机动作批准。

`--mode real` 尚未实现完整的首帧、关节限位和每帧变化检查；sender 的 `--send` 只表示开始发布数据。完成这些门禁和现场审核前，应限于离线与无机器人执行的接收测试。
