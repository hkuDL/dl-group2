# Task 9 Pilot20 结果报告（2026-10-08）

## 结论先行

本次完成了一个 **20 条计划分母的 development pilot**：5 个方块位置 × 2 个 seed × 2 个方法。它可以用于汇报端到端可行性、失败分布与当前性能证据，但 `formal_score=false`，不能替代正式大样本可靠性实验。

| 方法 | 计划 trial | 成功生成并回放 | 生成/准备失败 | 物理成功 | 严格 `expert_valid` |
|---|---:|---:|---:|---:|---:|
| ARDY | 10 | 8 | 2 | 2/10（20%） | 0/10（0%） |
| Kimodo | 10 | 6 | 4 | 3/10（30%） | 3/10（30%） |

若只看已经进入有效物理回放的 trial，ARDY 物理成功为 2/8（25%），Kimodo 物理及严格成功均为 3/6（50%）。主报告仍应优先使用上表的**计划分母**，因为协议规定准备失败也留在分母中。

这批结果不支持简单宣称“Kimodo 比 ARDY 快几倍”或“Kimodo 的正式成功率更高”。两个方法的生成 recipe、扩散步数、序列长度和可用 profiling 字段并不完全一致；每个 method×case 也只有 2 次。

## 按位置分解

| Case | ARDY（2 seeds） | Kimodo（2 seeds） |
|---|---|---|
| center | 0/2 物理成功 | 1/2 物理且严格成功 |
| near | 2/2 物理成功；0/2 严格成功 | 2/2 物理且严格成功 |
| far | 2/2 准备失败，未回放 | 2/2 准备失败，未回放 |
| left | 0/2 物理成功 | 2/2 准备失败，未回放 |
| right | 0/2 物理成功 | 0/2 物理成功 |

ARDY 的两个物理成功 trial 为：

- `p20-near-s2-ardy`：最大抬升 0.165372 m，连续保持 4.73 s，800 帧；`physical_success=true`，`expert_valid=false`。
- `p20-near-s3-ardy`：最大抬升 0.143432 m，连续保持 4.64 s，800 帧；`physical_success=true`，`expert_valid=false`。

二者严格失败原因均包含 `robot_environment_support_contact`。冻结协议区分了“普通 robot-table contact 仅诊断”和“借助外部支撑则不允许”。当前 evaluator 将上述接触判为 support，因此本报告保留物理成功，但不把它计为严格成功。正式发表严格成功率前，应由 evaluator/协议负责人确认该 failure reason 确实代表承重支撑，而不只是本应仅记录的普通碰桌。

Kimodo 的三个严格成功 trial 为 `center-s3`、`near-s2`、`near-s3`。其中 `center-s3` 最大抬升 0.158765 m，连续保持 4.915 s。

## 使用的成功定义

物理成功要求：

- 方块相对初始位置抬升至少 0.10 m；
- 右手拇指与食指或中指形成对向接触，法向力大于 `1e-4 N`；
- qualifying hold 期间方块不与桌面接触；
- 连续满足上述条件至少 2.0 s。

严格 `expert_valid` 还要求完整、有限、同步、无辅助的 canonical SONIC 回放，并通过无跌倒、无 weld/attachment、无外部支撑和完整性检查。

## Profiling 目前能说明什么

### 生成阶段示例

以下为 `center-s2` 的单条示例，不是全样本均值，也不适合直接做模型速度排名：

| 方法 | 已记录阶段 | 时间 |
|---|---|---:|
| ARDY | prepare conditions | 6.144 s |
| ARDY | model generation | 137.476 s |
| ARDY | trajectory adaptation | 6.441 s |
| ARDY | table clearance | 2.186 s |
| ARDY | 上述阶段合计 | 152.246 s |
| Kimodo | model load | 18.542 s |
| Kimodo | model generation | 51.580 s |
| Kimodo | process load + generation | 71.657 s |

ARDY 使用一次完整轨迹生成和 10 个 denoising steps；Kimodo 使用 segmented generation 和 100 个 denoising steps。计时边界、模型调用结构和序列长度不同，因此这里只能作链路诊断。

### 回放阶段已有粗粒度证据

- ARDY 的 body tracking RMSE 范围：0.0634–0.1457 rad（8 条有效回放）。
- Kimodo 的 body tracking RMSE 范围：0.1118–0.1803 rad（5 条具有有限数值的回放；另 1 条为 `null`）。
- ARDY 的 `physics_and_evidence_p99_wall_seconds`：3.569–4.023 ms。
- Kimodo 的 `physics_and_evidence_p99_wall_seconds`：3.643–5.918 ms（5 条具有有限数值的回放）。
- Kimodo 已记录 SONIC 初始化约 36.691–36.801 s、实际 replay 约 16.195–16.200 s；ARDY 没有同名字段，不能进行对称比较。

`physics_and_evidence_*` 只覆盖物理步进与 evidence 采集片段，不是整个 DDS→SONIC→控制器闭环延迟。不能据此单独宣称完整 5 ms deadline 达标或超时。

## 与冻结计划的偏差和限制

1. **序列长度不完全一致。** 冻结计划写的是 810 帧 / 16.2 s；实际 ARDY reference 为 800 帧 / 约 16.0 s，Kimodo 为 810 帧 / 16.2 s。结果必须披露该偏差，不能声称二者输入规模完全一致。
2. **未产出 profiling v0.3 event stream。** 当前结果包含阶段 wall time、RMSE 和部分回放时间，但没有规范要求的完整 monotonic event、进程/线程、accelerator、transport 和 manifest coverage 字段。不能事后伪造 `profile_events.jsonl`；正式 profiling 必须插桩后重跑。
3. **生成 recipe 不同。** ARDY 10-step full-trajectory 与 Kimodo 100-step segmented generation 的原始 wall time只作描述，不作公平速度榜单。
4. **样本量小。** 每个 method×case 只有 n=2；百分比是 pilot 描述值，不是可靠性估计。
5. **环境冲突被隔离。** `p20-near-s2-ardy` 首次回放在 0 帧前遇到外部 `canonical_va` DDS 占用；无模型 trial 实际发生。该无效目录已归档到 `setup_failures/dds_busy_20261008T012131/p20-near-s2-ardy_zero_frame`，随后只做了一次有效回放。其余失败均留在分母中。
6. **设备适配不改变模型。** 为避开占用卡，Task9 工作区副本只把 ARDY 的 GPU guard/child environment 从物理卡 4 改为 5；Task5 原冻结交接包未修改，模型、prompt、约束、adapter 与判据没有因此改变。

## 数据位置与复核入口

- S4000 容器结果根目录：`/workspace/group2/workspace/kunqi/task9_pilot20_20261007`
- 每条 trial：`runs/p20-<case>-s<seed>-<method>/`
- ARDY 批处理日志：`logs/ardy_generation_batch_v3_resume.log`
- 物理回放日志：`logs/physical_replay_batch_v4_resume.log`
- 被隔离的无效基础设施尝试：`setup_failures/dds_busy_20261008T012131/`
- 冻结协议：本目录 `PILOT_PROTOCOL_FREEZE.json`
- 固定运行顺序：本目录 `PILOT20_RUN_PLAN.json`

## 下一步

1. 先由 Task5、Task8、Task9 三方复核本报告的 case-level 状态和 support-contact 解释。
2. 演讲可使用本 pilot 的计划分母表、失败类型和三个严格成功视频，但明确标注 development pilot。
3. 若要做正式 profiling，在两条方法的同一位置插入 v0.3 instrumentation，先各跑 1 条 smoke 检查 coverage，再决定是否扩展。
4. 若要声称正式成功率，每个 condition 至少 20 次时总量为 5 case × 2 method × 20 = 200 条，应另开 formal run plan，不能把本 pilot 事后扩充分母。
