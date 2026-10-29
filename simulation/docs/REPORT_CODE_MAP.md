# 最终报告与恢复源码的对照

2026-10-29 从 S4000 工作区恢复；具体文件见上级 SOURCE_MANIFEST.json。状态“找到”指源码存在并已恢复，不代表本次重新验证了报告中的实验结果。

| 最终报告 | 本次恢复的实现 | 核对状态 |
|---|---|---|
| §2–3 Kimodo | `research/kimodo/generation/`、`export/`、`qualification/` | 五阶段、487@30 Hz、810@50 Hz 规划与显式关节名称映射代码已找到 |
| §2、§4 ARDY | `research/ardy/overlap/`、`qualification/`、`adaptation/` | 五阶段、406@25 Hz、history/overlap、校准配置已找到 |
| §2、§3.2、§4.2 适配 | `research/shared_adapter/` 及两方法专属 adapter | body-preservation、手部 profile、几何修正与严格检查已找到；不把后期统一版称为 Oct.8 原版 |
| §2.2 SONIC/Hand PD | `execution/sonic_mujoco/`、`dl-group2/scripts/`、`patches/sonic-project.patch` | 共用执行后端、task scene、手部 PD 与 MUSA 改动已找到；native binary/权重未提交 |
| §2.3 物理与完整性 | 两方法 `qualification/`、`canonical_va/`、共享 validation | physical、reference/recording integrity 和 strict no-table 逻辑已找到 |
| §5 固定 center 比较 | `workspace/kunqi/task9_formal40_20261008/protocol.json`、两方法冻结 config/calibration | 冻结协议和核心配置已找到；服务器历史结果目录存在，本次未核验完整 40-trial 档案，也未上传数据/日志 |
| §6 数据工厂 | `data_factory/runtime/`、`dataset/`、`canonical_va/` | ID 对齐、horizon 检查、数据编译与兼容接口已找到；数据集与 split 实例不上传 |
| §6.1 V2/V5 | 共享 adapter 中相关 body/hand/geometry 策略 | 通用实现已恢复；每个具体实验的完整冻结 run manifest 尚未恢复，不冒充历史比较 runner |
| §7.1 VLM | `research/ardy/online/qwen/`、`patches/sonic-hot-reload.patch` | 模型调用、阶段控制、末帧保持、参考热更新代码已找到；2/10 与 3/10 的 paired trial 配置/记录未完整核验 |
| §7.2 VA V4.1 | `va_research/models/v4*`、`sonic/`、`data_factory/` | 模型、训练与 PlanBuffer 调度源码已找到；权重、9488 样本和训练输出未提交 |
| §8.1 真机接口 | 现有部署包、官方 SONIC 接收端依赖、源码补丁 | 不新增未验证的 receiver/watchdog 实现；本轮未重新验证 Jetson/真机链路 |
| LeRobot 扩展 | 未找到明确的转换实现 | 在 `data_factory` 与 `research` 的本次检索中无 `*lerobot*.py`；不能标为已完成 |

## 已处理的来源缺口

Kimodo 的 matrix-preserving codec 引用了 `kimodo_condition_coordinates`，但该 helper 不在服务器默认 Python 搜索路径。本次在历史源码中找到 33 份 SHA-256 相同的副本，选取 task8 qualification 版本原样恢复至 `research/kimodo/generation/`，与调用它的 codec 同目录。来源与哈希单独记录；没有改写转换算法。

SONIC 当前提交是 `39ea4bc6feffc72a752dff3766e38edd910524f1`，相对官方基线的 7 个源码文件变化已提取为补丁。VLM 使用的 hot-reload 分支还有 3 个源码文件差异，另存独立补丁；不把它自动混入历史离线比较控制器。

## 仍需明确的限制

1. VA registry 中 V4.1 的 offline 路径仍指向 V4 evaluator；V4.1 `oracle_rollout.py` 保留了若干找不到同目录模块的相对导入。它们是服务器原有的迁移/兼容问题，本次没有把旧入口改写成新的实验方法。原报告的 deployment input 是兼容 checkpoint，不等于可直接使用完整 V4.1 checkpoint；应恢复实际 custom evaluation/转换入口后再声称端到端可复现。
2. ARDY 的 `default.json` 保留原始重复 calibration 字段及绝对路径。Python JSON 按最后一个字段值解析；后续可移植配置应在新版本中显式规范，不能悄悄改变历史配置或其 hash。
3. formal protocol 的 hardware 字段写“两方法 GPU1”，而最终报告披露实际设备分配不同。保留原文件并记录这个差异；配置声明不能取代运行记录。
4. 共享适配器的研究契约与 `deployment/g1_replay` 的契约仍分别存在。此前发现的部署包关节映射、旋转插值和端点问题没有在本次源码恢复中修复，也不能因为恢复了研究代码就标为已解决。
5. 原始 runtime/source-policy/graphics-profile 是服务器指纹；它们引用的外部源码、机器人资产、权重和驱动未全部进入公开仓库。禁止跳过这些检查来制造“运行通过”。
6. VLM 独立测试为 5 passed / 1 failed。失败用例 `test_hand_stops_squeezing_on_opposing_contact` 要求接触后保持 amount=0.4；当前服务器实现显式执行一次 preload，把 amount 设为 1.0。代码注释把这一行为说明为防滑预紧，测试与实现不一致。本次原样保留两者，不为了通过测试而改变已用于实验的控制策略；后续应确认报告实验使用的 hand-controller 版本后独立修订。

本次交付范围是补回实现、配置、来源和验证入口；不是产生新训练结果、重算历史数据或重新批准真机部署。
