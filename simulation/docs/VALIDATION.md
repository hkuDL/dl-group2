# 源码恢复检查记录

日期：2026-10-29。检查对象是本次提交的新 `simulation/` 源码，不是服务器历史实验结果。

| 检查 | 结果 | 能支持的结论 |
|---|---|---|
| SOURCE_MANIFEST 哈希、字节数及 Python AST | 405 个恢复文件通过 | 记录来源的源码未被迁移过程改写；Python 语法可解析 |
| `python -m experiments --help` | 通过 | 轻量 CLI 可导入并显示入口；不代表阶段实际执行 |
| 默认轻量测试 | 35 passed | shared adapter、run/reference/policy contract、命令构建、manifest 与 hand-continuity 的现有测试通过 |
| VLM 独立测试 | 5 passed / 1 failed | 失败是 contact-triggered preload 与旧测试预期不同；见 REPORT_CODE_MAP，不掩盖此问题 |
| SONIC 项目补丁 | 对精确官方基线 `git apply --check` 通过 | 7 个源码文件差异可应用；未编译执行 |
| SONIC VLM hot-reload 补丁 | 在上述项目补丁应用后 `git apply --check` 通过 | 3 个源码文件差异可应用；未验证在线控制 |
| 原 deployment 包 | 17 passed，沿用前次对相同代码提交的结果 | 此次未改动该目录；不能用它证明新仿真任务运行成功 |

本次没有执行 GPU 前向、训练、物理回放、EGL/DDS 或机器人控制。没有检查 checkpoint 数值、40 条正式 trial 或 9488 行数据的完整内容。

默认测试命令从 `simulation/` 执行；VLM 测试从 `research/ardy/online/qwen/` 执行。二者的导入路径不同，应分别启动 Python，不能把 deployment 的同名 contracts 混入研究包测试。

本次源码恢复保留现存实验实现，包括已知旧入口问题；不以调整算法、修改 fingerprint 或替换失败证据来换取全绿测试。后续行为修复应单独提交并重新验证。
