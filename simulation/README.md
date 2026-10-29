# Track 4 仿真与研究代码

本目录恢复了最终报告使用的研究模块：Kimodo/ARDY 五阶段生成、G1 适配与手部规划、SONIC/MuJoCo 执行、数据工厂、VLM 与 VA。源码于 2026-10-29 从 S4000 工作区按文件白名单提取；逐文件来源、大小与 SHA-256 见 [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)。

这是源码恢复与整理版本。轻量测试通过不代表已在新路径完成 GPU 推理、物理抓取或真机验证。原服务器上的依赖、权重、数据和历史证据没有随代码上传。报告实验与当前源码快照的时间关系、已知缺口见 [报告与代码对照](docs/REPORT_CODE_MAP.md)。

## 模块入口

| 路径 | 职责 |
|---|---|
| `research/kimodo/` | 487 帧、30 Hz 五阶段生成，约束构建、导出、抓取验收 |
| `research/ardy/` | 406 帧、25 Hz 分段生成、history/overlap、适配与验收 |
| `research/shared_adapter/` | body-preservation、腕部与手部策略、统一严格检查 |
| `execution/sonic_mujoco/` | free-base 仿真、SONIC、Hand PD、渲染与 native 记录 |
| `contracts/` | reference、policy 与 run manifest 契约 |
| `data_factory/` | 按身份对齐观测/动作、编译、数据集与质量检查 |
| `va_research/` | V4/V4.1 网络、损失、训练、绝对 tick 调度及诊断依赖 |
| `research/ardy/online/qwen/` | VLM prompt 修订与分阶段末帧保持 |
| `experiments/` | 命令构建、可选执行、来源记录和目录索引 |
| `dl-group2/{scripts,configs,scenes}/` | 原工作区 task-support 源码快照；不是嵌套 Git 仓库 |
| `canonical_va/`, `grasp_pipeline/` | 现有调用依赖的兼容模块；暂时保留原路径 |
| `patches/` | SONIC 的 MUSA 改动、VLM hot-reload 差异与记录 instrumentation |

保留这些相对路径是为了不在恢复源码时改变执行语义或使已有 fingerprint 失效。`deployment/g1_replay` 仍是独立的推理/发送包；其 `contracts` 与本研究包不是已经合并的实现。两个目录的测试应分别启动，避免 Python 模块缓存与同名导入互相干扰。

## 可立即运行的源码检查

从仓库根目录进入本目录。使用已有科学计算环境，或在本地隔离环境安装 `requirements-inspection.txt`；不要用这个文件替换 S4000 的 torch/MUSA 环境。

```bash
cd simulation
python scripts/audit_source_snapshot.py
python -m experiments --help
python -m pytest -q
```

这些命令不加载模型权重、不启动机器人、不启动 MuJoCo/DDS。VLM 的独立测试需安装其 `pyproject.toml` 声明的 Python 依赖，从 `research/ardy/online/qwen` 单独运行。

## 运行边界与外部依赖

真实生成、训练与物理执行继续使用服务器现有的 `va-train`，环境约定见 [S4000 环境说明](docs/S4000_ENVIRONMENT.md)。不要重装 torch/torch_musa、复制显卡驱动或改变 DDS/SONIC 时序来适配源码目录。

本快照不是完整容器镜像。要在新机器运行，需要恢复以下外部依赖及其原始版本：

- Kimodo Python runtime、G1 checkpoint、模型配置/normalization stats、LLM2Vec base/adapter/tokenizer。仓库已有 `deployment/g1_replay/models/model_requirements.json` 可用于核对部分权重；服务器 MUSA runtime 的完整源码差异仍需核对。
- ARDY 官方依赖及服务器使用的 MUSA 兼容配置；公开依赖清单固定的提交是 `693f74d13b3d04a0a22ce127ee79c929dd89756b`。本次未成功重新确认该外部 checkout 的工作树，不能声称它与清单逐字节相同。
- SONIC 官方源码、G1 机器人/手部资产、Unitree SDK、策略 encoder/decoder 及 observation config；仅源码补丁在本目录。应用方式见 [patches/README.md](patches/README.md)。
- native 构建产物、按当前主机验证的 EGL profile/driver 路径、数据集与 VA checkpoint。`canonical_va/source_policy.json` 和 `runtime_contract.json` 按原样保留，不能为了通过检查直接改写预期哈希。

现有代码默认把 `simulation/` 视作原工作区根：它下面的 `dl-group2/` 是本次恢复的 task-support；外部 SONIC 与 Kimodo/ARDY 路径仍需按代码支持的 `RESEARCH_ROOT`、`SONIC_REPO`、`ARDY_REPO`、`KIMODO_ROOT` 等配置。某些历史记录使用 `/workspace/group2`，因此新目录的完整可移植执行仍需后续验证，不能把旧路径下的结果当成本次复现。

检查入口和执行入口必须区分。例如 `python -m experiments run ...` 默认写入计划；只有显式执行选项才运行阶段。先查看具体子命令帮助，确认输出目录、依赖和资源后，再在验证过的环境运行。

## 不提交的内容

不包含模型权重、checkpoint、normalization 数组、训练数据、生成轨迹、RGB、视频、日志、驱动、环境目录、可执行程序、凭证或 `.env`。`va_research/models/` 与 `va_research/datasets/` 中的文件是 Python 实现；不能因为目录名含 models/datasets 就误认为它们是权重或训练样本。

本次未重跑正式 40 次比较、未训练模型、未运行 GPU 物理任务、未向机器人发送控制。历史报告中的成功率、VLM 消融和 VA 指标保留原证据口径。
