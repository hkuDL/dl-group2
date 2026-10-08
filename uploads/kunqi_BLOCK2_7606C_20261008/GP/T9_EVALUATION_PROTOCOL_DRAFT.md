# Task 9 统一评测协议草案

> 状态：DRAFT v0.3 — pilot 规则已部分冻结；不得据此宣称完成正式统计比较  
> 日期：2026-10-07  
> 负责人：KunnnnnQ / ZhangKunQi-008  
> 对应 Issue：[hkuDL/dl-group2#9](https://github.com/hkuDL/dl-group2/issues/9)

## 0. 先读结论

本协议用于在**相同的机器人、场景、控制器、任务条件和评价器**下比较 ARDY final 与 Kimodo final。

当前可以按单独交付的 `pilot20` 计划做不计正式分数的端到端试跑；正式统计实验仍未开放。开始正式跑数前，必须同时满足：

1. T5 已交付可复现的 ARDY final；
2. T8 已交付可复现的 Kimodo final；
3. S4000 上的共享代码已经冻结为可标识的 snapshot；
4. 两个方法均已转换为同一 motion-reference interface；
5. 场景、case、成功标准、碰撞口径、trial 数量和日志格式已由全组确认；
6. 两个方法的输入信息、候选数量、选择方式和重试预算已统一；
7. 两个方法各完成至少一次标记为 `not_final` 的 smoke test。

在这些条件满足前，只允许完善协议、schema、validator、smoke-test 和明确标记为 `pilot` 的运行，不得勾选 Issue #9 中的正式结果项。

## 1. 评测问题与公平性原则

### 1.1 要回答的问题

在完全相同的下游控制和仿真条件下，ARDY 与 Kimodo 生成的 motion reference 在以下方面有何差异：

- 抓取成功率；
- 安全性与碰撞；
- 生成时间和物理执行时间；
- 最大/最终抬升高度与连续保持时间；
- 对不同物体初始位置的鲁棒性；
- 失败类型和失败发生阶段。

### 1.2 唯一允许变化的部分

```text
ARDY  ── adapter ──┐
                   ├─► 统一 motion reference ─► SONIC(body) + Hand PD ─► MuJoCo ─► 同一 evaluator
Kimodo ─ adapter ──┘
```

正式比较中只允许以下内容因方法不同而变化：

- 上游 motion/reference generator；
- 为适配统一接口所必需、且已记录版本的 method-specific adapter；
- 对应的模型 checkpoint。

以下内容必须完全相同：

- G1 robot model 和 joint mapping；
- neutral initial pose；
- tabletop、cube 和 physics；
- case 坐标、姿态和 reset 规则；
- SONIC body controller；
- Hand PD；
- 仿真步长、reference/observation 频率；
- instruction、seed 列表、timeout 和 trial 数；
- 外部输入信息预算，包括物体位姿、指定抓取手、专家约束与手指参考；
- 每个 trial 的候选数量、选择策略和重试预算；
- evaluator、成功阈值和失败分类；
- 日志与视频采集规则。

Dense expert trajectory、专家手指参考、视觉约束和物体位姿约束都属于方法实际收到的输入，必须记录 provenance；不得把它们隐藏成普通 adapter 细节。若生成硬件不同，物理执行仍应使用同一冻结环境，但 generation time 只能按硬件分层披露，不能直接用于 ARDY/Kimodo 速度排名。

## 2. 证据等级与 source of truth

同一个事实可能同时出现在聊天、README、服务器文件和代码中。正式评测按以下优先级判定：

1. 本次实验冻结的 S4000 source snapshot、配置、checkpoint 和二进制 hash；
2. 本次实验实际执行的代码和生成的 machine-readable log；
3. 经对应版本验证的接口文档；
4. README、会议纪要和聊天记录。

聊天中出现的“已跑通”只能作为定位证据的线索，不能单独用于勾选 Issue。

### 2.1 正式实验前必须填写的版本表

| 项目 | 必填值 | 当前状态 |
|---|---|---|
| Canonical repository | URL | TBD |
| Shared branch/tag | 名称 | TBD |
| Shared commit | 完整 SHA | TBD |
| Dirty working tree | `clean`；否则保存 diff/hash | TBD |
| S4000 workspace | 绝对路径 | `/workspace/group2` 待核实用途 |
| Container/image | 名称与 digest | TBD |
| MuJoCo | 版本 | TBD |
| SONIC source/binary | commit 与 binary hash | TBD |
| Hand PD | source、Kp、Kd、频率 | TBD |
| ARDY | commit、checkpoint、adapter hash | TBD |
| Kimodo | commit、checkpoint、adapter hash | TBD |
| Scene/config | 文件路径与 SHA-256 | TBD |
| Evaluator | 文件路径与 SHA-256 | TBD |

如果 S4000 当前代码没有 Git 分支，代码负责人应在正式跑数前提供以下至少一种冻结方式：

- 创建只用于评测的 branch/tag/commit；或
- 保存完整 source archive、`git status`、当前 HEAD、dirty diff 和 SHA-256 manifest。

## 3. 当前已核验但不能直接当作最终标准的事实

公开候选实现 [`haohao030115/dl-group2:grasp-pipeline`](https://github.com/haohao030115/dl-group2/tree/grasp-pipeline) 提供了以下可参考事实：

- free-base、gravity-on、无 weld/band/object attachment 的 SONIC body replay；
- body 29 DoF，hand 14 DoF，手部由独立 Hand PD 控制；
- reference/state 50 Hz，RGB 10 Hz；
- 当前公开 schema 使用 lift 至少 0.10 m、连续 hold 至少 2 s、真实对向手指接触、无跌倒等认证条件；
- 公开五点 pilot 使用的是中心点附近的 ±2 cm 轴向偏移；
- 机器人与桌面接触会被记录，但现有成功 pilot 仍允许抓取阶段的拇指碰桌。

这些事实来自候选 fork，而不是已冻结的 S4000 正式评测 snapshot。正式协议必须重新核对 live code，不能直接复制为最终值。

### 3.1 2026-10-06 Kimodo `not_final_smoke` 证据

当前已归档一组固定场景 Kimodo→G1 projection→SONIC 抓取抬升证据：

- generation host class：H100；
- integration revision：`7e47fc6b2522b7754e64ee357e7244a117d7be84`，记录为 clean；
- Kimodo revision：`58e781898b3d7e328a676a75d3e338c45dce3ad9`；
- 固定左手、cube position `[0.39, 0.15, 0.785]`、seed `42`；
- 一次生成调用得到 3 个 candidates，目前附件只证明 sample index `0` 被执行；选择策略与 retry 语义尚未确认；
- 输入含 dense expert constraints：双手、双脚各 298 个中间末端目标，并使用独立专家手指参考；
- physical execution：798/798 帧，最大抬升 `0.132051 m`，最终抬升 `0.115765 m`，最长连续保持 `4.31 s`，无跌倒、无 attachment、无 teleport；
- 同时记录到 174 个 robot-table contact steps，接触 body 为左拇指。

机器可读登记位于 `t9_eval_prep/evidence/kimodo_not_final_smoke_20261006/kimodo_not_final_smoke.json`。该结果只证明**强专家约束下的固定场景集成 smoke 可运行**；它不是语言条件下的普通 Kimodo 结果，不进入正式统计，也不关闭 G4。

### 3.2 2026-10-07 ARDY Task 5 交付事实

Task 5 的哈希交接包位于 S4000 容器内 `/workspace/group2/workspace/tuchengyuan/task5/ardy_handoff_20261007`。当前方法必须标为 **`ARDY + structured coordinate constraints + trajectory adaptation`**，不能简写成 raw ARDY：

- 每个 candidate 在执行前一次性接收一条 prompt 与结构化 `case` 坐标；坐标不从自然语言解析；
- 每个 candidate 只调用一次 ARDY，生成完整 16 s trajectory；模型为 `ARDY-G1-RP-25FPS-Horizon52`，10 denoising steps；
- 生成后执行确定性的 neutral-pose trajectory adaptation 与 3 cm table-clearance 修正；
- MuJoCo 回放阶段不再调用语言模型、不追加 prompt、无在线人工修正；
- `fresh_original_seed0_v2` 保存了 1 次生成、1 次回放成功的端到端证据；`fresh_center_seed1` 保存了完整失败样本；
- `grid_v1` 是开发网格：计划 10、执行 8、成功 4；far 在 adapter 阶段因 IK error 未执行；
- center/seed0 和 3 cm clearance 经开发调参，不是 held-out formal case；失败和准备失败必须保留在分母/coverage 中；
- 冷启动单卡 S4000 生成约 138.26 s，全链路约 209.6 s；该数字包含模型加载且来自共享设备，不能与不同 warm-up/负载条件的 Kimodo 直接排名。

同一 ARDY reference 的多次物理回放仍可能因毫米级手指接触而成败不同。因此“每个 method×case 两次”的 20-run 计划只提供展示性 pilot 描述，不能代替每个 condition 至少 20 次的可靠性估计。

### 3.3 2026-10-07 Kimodo Task 8 development 交付事实

S4000 development 包位于 `/workspace/group2/kimodo-t6/g1-integration/task8_development_20261007_v3`，接受的开发候选为 `accepted_touch_allowed_profile`。当前方法必须标为 **`Kimodo + segmented constraints + canonical adapter`**：

- 接受候选在冻结前经历过 4 次 adapter/replay 开发尝试，因此只能用于 smoke、profiling 和开发演示；
- 接受配置 SHA-256 为 `6826f1a852484e35819007fa189d0763a873dc61372cd3857d29cc4c5ca3b891`；
- reference SHA-256 为 `640bc21a9f93cdd60f8e27a4f3b027d80652734bcef1ed631b8188abe25313c7`；
- 接受 replay 最大抬升约 0.1248 m、连续保持约 4.735 s、810 reference frames，并通过修正后的独立验证；
- Task 8 v3 没有读取 ARDY 的抓取 trajectory、prompt、reference 或成功结果；系统中出现的 ARDY 路径只涉及已安装包的 metadata，不是数据依赖。

### 3.4 2026-10-07 固定 reference profiling smoke

同一冻结 Kimodo reference 已完成 profiling-off / profiling-on 对照，两次均成功。profiling-on 记录 3240 个 200 Hz control-step event，`loop_compute_total` mean 3.278 ms、P95 3.631 ms、P99 3.790 ms、max 4.446 ms，5 ms deadline miss 为 0。两次运行有一个 physics step 和一个 robot-table contact step 的运行抖动差异，不是位级确定。该结果只证明 profiling 接入没有观察到明显行为回归，不是 ARDY/Kimodo 性能结论。

## 4. 开放决策（正式实验前必须关闭）

| ID | 必须决定的问题 | 已知冲突 | 决议/批准人 |
|---|---|---|---|
| D-01 | Canonical repo/branch/commit 是什么？ | 组织仓库、个人 `grasp-pipeline`、`musa-migration`、S4000 live copy 并存 | TBD |
| D-02 | 正式 case 是哪几个精确坐标？ | Issue 写 Center/Left/Right/Far；旧 JSON 有 Near；free-base pilot 是 ±2 cm | TBD |
| D-03 | 正式任务是否包含 place/target area？ | 已确认正式任务为抓取并抬升 | **CLOSED 2026-10-06：`grasp-and-lift`，不含 place；`place_error_m=null`** |
| D-04 | 每个 method×case 的正式 trial 数？ | Issue 写 10；Proposal 目标至少 20 | TBD |
| D-05 | 任何机器人碰桌是否判失败？ | 成功 replay 可出现短暂手指/机器人碰桌 | **CLOSED 2026-10-07：robot-table contact 作为诊断字段，不自动判失败；qualifying hold 内 cube-table contact 仍判任务失败；跌倒、weld、teleport、外力和冻结规则定义的 unsafe collision 仍判失败** |
| D-06 | 是否随机化？使用哪些 seed？ | 当前候选 pilot 主要为固定位置/确定性 reset | TBD |
| D-07 | 使用一条固定 instruction 还是 instruction set？ | 中文旧配置与英文新 schema 不同 | TBD |
| D-08 | generation timeout 与 execution timeout 各是多少？ | 未冻结 | TBD |
| D-09 | 使用 single-shot、best-of-K 还是 sequential retry？ | Kimodo smoke 一次生成 3 个 candidates，但只证明 sample 0 被执行 | TBD |
| D-10 | 正式主比较允许多少 conditioning/information budget？ | Kimodo smoke 使用 dense expert constraints 与独立专家手指参考 | TBD |
| D-11 | generation 是否要求同硬件？ | 旧 Kimodo smoke 为 H100，ARDY 主要在 S4000 | **pilot 冻结：H100 不进入新比较；ARDY/Kimodo 均在 S4000 生成和执行，并记录物理 device ID、共享状态与 warm-up；条件不一致时 raw generation time 只分层披露，不排名** |

原则：case 名称不足以识别实验条件，必须同时记录精确 XYZ、quaternion/yaw 和 config hash。

D-03、D-05 已关闭；D-11 已为 pilot 冻结。最低 lift/hold 阈值已按 canonical evaluator 采用 0.10 m / 2.0 s，但正式运行仍须把 evaluator 文件与 hash 写入 manifest。若以后增加 place，必须提升 `protocol_version` 并让两个方法从头按新协议运行。

## 5. 统一输入输出契约

### 5.1 Evaluation request

每次 trial 的输入至少包含：

```json
{
  "protocol_version": "t9_eval_v0.2",
  "run_id": "...",
  "method": "ardy|kimodo",
  "case_id": "...",
  "object_pose": {
    "position_xyz_m": [0.0, 0.0, 0.0],
    "quaternion_wxyz": [1.0, 0.0, 0.0, 0.0]
  },
  "grasp_arm": "left|right|unspecified",
  "instruction": "TBD exact frozen string",
  "seed": 0,
  "input_spec_hash": "...",
  "conditioning_regime": "text_and_object_pose|expert_sparse|expert_dense",
  "constraint_bundle_hash": null,
  "candidate_budget": 1,
  "selection_policy": "single_sample",
  "retry_policy": "no_retry",
  "generation_timeout_s": null,
  "execution_timeout_s": null
}
```

### 5.2 Method adapter output

ARDY 与 Kimodo 的原始输出允许不同，但 adapter 必须输出同一 reference bundle。字段以最终 SONIC live code 为准，至少核查：

- body joint position/velocity reference，29 DoF；
- body/root position、quaternion；
- body/root linear/angular velocity；
- hand position/velocity reference，14 DoF，由 Hand PD 消费；
- timestamps/reference rate；
- body/hand joint names 与 name-based mapping；
- coordinate frame、quaternion convention 和单位。

禁止按照“前 29 列”等 index 假设进行静默映射。adapter 必须验证 joint names、shape、有限值、时间单调性和 quaternion norm。

Adapter 文档还必须声明所有输入 provenance。专家轨迹约束、专家手指 reference、projection、retiming 和人工选择 candidate 都不是可忽略的 adapter 内部细节，必须进入 TrialLog 和 artifact manifest。

### 5.3 Adapter 失败规则

以下情况记为本 trial 失败，不得删除后重跑来替代：

- 生成超时；
- 缺字段、shape 不符或 NaN/Inf；
- joint mapping 不完整；
- reference 越过安全/关节限制；
- 时间轴不合法；
- adapter/runtime 抛出异常。

## 6. Case 与 reset 规范

正式 manifest 应为每个 case 保存：

- `case_id`；
- cube 精确 position/quaternion；
- cube size、mass、friction 的 source file/hash；
- table geometry 的 source file/hash；
- robot initial pose definition/hash；
- reset function 与 stabilization steps/time；
- seed；
- reset 后允许的姿态/速度容差；
- camera roles；
- 是否属于 train、pilot 或 final-eval。

每个 trial 前必须执行同一 reset，并验证：

1. 全部目标状态已恢复；
2. qvel/control/外力/控制器内部状态已清零或按规范初始化；
3. cube 没有穿透或掉出台面；
4. reset 后稳定窗口通过；
5. 评测 case 未出现在训练数据中，或已明确披露训练重合关系。

## 7. Trial 执行流程

### 7.1 Trial、candidate 与 retry 定义

一个 trial 从首次调用该方法开始，而不是从选出成功 candidate 后才开始。`pilot20` 已冻结为 `single-shot, K=1, no retry`：一个预声明 seed 只生成一个 candidate，只执行一次，不允许失败后补跑替换。正式主协议是否沿用仍由 D-09 的正式签字决定。

如果组内选择 best-of-K 或 sequential retry，必须：

- 对两个方法使用相同且预先冻结的 K、selection policy 和 retry budget；
- 保存每个 candidate 的原始输出、validator 结果和是否被执行；
- 在运行前决定选择策略，不能看到物理结果后再挑最好样本；
- 将全部 candidates 的总生成时间作为该 trial 的 generation cost；
- 失败 candidate 和失败尝试不得从记录中删除。

每个 method×case×seed 必须遵循同一顺序：

1. 记录完整版本信息和配置 hash；
2. 执行统一 reset 与 preflight；
3. 启动计时并调用 method adapter；
4. 保存所有原始 candidates、选择依据和最终统一 reference；
5. 通过 reference validator；
6. 用相同 SONIC + Hand PD 执行；
7. 逐物理步采集接触、安全和成功指标；
8. 保存状态、日志及规定的视频；
9. evaluator 只依据保存数据生成结果；
10. 原子写入一条 TrialLog；
11. 失败 trial 也必须保留，不得从分母中删除。

### 7.2 运行顺序

为减少温度、资源和时间漂移，建议按相同 case/seed 交替运行两种方法，并预先生成不可更改的 run plan。例如：

```text
center seed-01: ARDY → Kimodo
center seed-02: Kimodo → ARDY
...
```

如果资源限制导致只能分批运行，必须记录 batch、节点、容器和开始/结束时间，并在结果中披露。

`generation_env` 与 `execution_env` 必须分开记录。物理结果的主比较应使用同一冻结 S4000 scene、SONIC、Hand PD 和 evaluator；若生成硬件不同，generation time 只能按硬件分层展示，不得据此判断方法本身更快。

## 8. 成功与安全判定

### 8.1 Primary success

本协议 v0.2 的正式任务已冻结为 `grasp-and-lift`，不含 place。最终阈值必须从冻结的 evaluator 中读取并写入 manifest，建议以现有 physical certification 为起点核查：

- cube 相对初始高度达到阈值；
- thumb 与至少一个对向手指产生有效接触；
- cube 在 hold 阶段不接触桌面；
- 连续满足条件达到 hold 阈值；
- 机器人没有跌倒；
- 状态有限且 frame coverage 完整；
- SONIC 与 Hand PD reference 同步。

本版本的 `place_error_m` 必须为 `null`，不能用 0 表示“没有误差”；`place` 也不得作为本版本的 failure phase/category。如果以后加入 target area，需新增 place success、target center、容差和稳定时间，提升 protocol version，并让两个方法重新运行。

### 8.2 Task success、collision 与 safety 分开保存

每个 trial 至少保存以下四个独立量：

- `runtime_valid`：完整执行、状态有限、reference 同步、无 attachment/teleport；
- `task_success`：满足抓取接触、lift、hold、hold 阶段 cube 不接触桌面等任务条件；
- `collision_observed`：检测到并保存了碰撞事件，只描述事实，不自动等于安全失败；
- `safety_success`：无跌倒、无冻结规则定义的 unsafe collision、无 joint-limit violation；
- `overall_success`：`task_success && safety_success`。

因此一次运行可以同时是 `task_success=true`、`collision_observed=true`、`safety_success=true`：robot-table contact 会保留为诊断证据，但不自动触发 safety failure。只有冻结规则明确列出的 unsafe collision、跌倒、joint-limit violation、weld/attachment、teleport 或外力等才使 `safety_success=false`。

当前实现可能在成功抓取时仍发生机器人碰桌，因此日志必须至少拆分：

- cube-table contact；
- robot-table contact；
- robot self-contact；
- left-arm environment contact；
- contact body/geom；
- contact start/end time 与 phase；
- full-rate contact steps；
- 是否触发安全失败。

不得静默丢弃 contact，也不得把所有 contact 合并成一个布尔值。至少区分 robot-table、cube-table、self-contact、接触 body/geom、phase、持续步数和是否触发冻结规则下的安全失败。

## 9. TrialLog schema

每次 trial 保存一行 JSONL；CSV 可由 JSONL 派生，不作为唯一 source of truth。

| 字段 | 类型 | 说明 |
|---|---|---|
| `protocol_version` | string | 本协议/manifest 版本 |
| `run_id` | string | 全局唯一 ID |
| `method` | enum | `ardy` / `kimodo` |
| `case_id` | string | 与 manifest 一致 |
| `trial_index` | int | method×case 内编号 |
| `seed` | int/null | 实际使用 seed |
| `instruction` | string | 完整原文 |
| `object_pose` / `grasp_arm` | object/string | 精确位姿和指定抓取手 |
| `input_spec_hash` | string | 两种方法输入预算的统一标识 |
| `conditioning_regime` | enum | text/object pose 或 expert sparse/dense |
| `uses_expert_constraints` | bool | 是否使用专家约束 |
| `constraint_bundle_hash` | string/null | 约束包 SHA-256 |
| `hand_reference_source` | string/null | 手指 reference provenance |
| `samples_requested` / `samples_generated` | int | candidate 预算与实际数量 |
| `selected_sample_index` | int/null | 预冻结策略选择的 candidate |
| `selection_policy` | string | single/first/ranked 等预定义策略 |
| `attempted_sample_indices` | int[] | 实际执行过的 candidates |
| `retry_count` | int | trial 内重试次数 |
| `source_commit` | string | 共享 snapshot SHA |
| `dirty_diff_hash` | string/null | clean 时为 null |
| `generator_revision` | string | ARDY/Kimodo generator revision |
| `integration_revision` | string | method integration revision |
| `integration_dirty` | bool | integration tree 是否含未保存修改 |
| `model_checkpoint` | string | 路径/ID及 hash |
| `adapter_version` | string | commit/hash |
| `scene_config_hash` | string | 场景与 case 配置 |
| `controller_hash` | string | SONIC/Hand PD 配置 |
| `evaluator_hash` | string | 判定代码/config |
| `generation_env` | object | host、GPU、container digest、runtime versions |
| `execution_env` | object | host、GPU、container digest、runtime versions |
| `generation_time_scope` | string | 单 candidate 或全部 candidates |
| `generation_time_s` | float/null | 不含物理执行；多 candidate 时记录总时间 |
| `execution_time_s` | float/null | 物理执行时间 |
| `raw_output_hash` | string | 原始模型输出 SHA-256 |
| `reference_hash` | string | adapter 后 reference SHA-256 |
| `postprocess_steps` | string[] | projection、retiming 等变换 |
| `expected_frames` / `recorded_frames` | int | 执行完整性 |
| `completed` | bool | 是否完整执行 |
| `runtime_valid` | bool | 执行完整性判定 |
| `task_success` | bool | grasp-and-lift 任务判定 |
| `collision_observed` | bool | 是否检测到碰撞事件 |
| `safety_success` | bool | 按冻结安全规则判定；robot-table contact 本身不自动置 false |
| `overall_success` | bool/null | task 与 safety 都确定后计算 |
| `max_lift_m` | float/null | 相对初始高度 |
| `final_lift_m` | float/null | 结束高度差 |
| `max_hold_s` | float/null | 最长连续有效 hold |
| `grasp_error_m` | float/null | 必须定义测量方式 |
| `place_error_m` | float/null | 无 place task 时为 null |
| `fall` | bool | 是否跌倒 |
| `cube_table_contact_steps` | int/null | full-rate |
| `robot_table_contact_steps` | int/null | full-rate |
| `unsafe_collision` | bool/null | 按冻结口径 |
| `runtime_failure_category` | enum/null | 生成、适配、执行或记录故障 |
| `task_failure_category` | enum/null | 抓取抬升任务失败 |
| `safety_failure_categories` | enum[] | 可同时存在多个安全问题 |
| `failure_phase` | enum/null | reset/generate/adapter/reach/grasp/lift/hold |
| `failure_reason` | string/null | 人类可读细节 |
| `raw_output_path` | string | 原始模型输出 |
| `reference_path` | string | 统一 reference |
| `log_path` | string | 完整日志 |
| `video_path` | string/null | 按采集规则 |
| `started_at_utc` | string | RFC3339 |

## 10. Failure taxonomy

Failure 不再用一个字段覆盖所有语义：

- `runtime_failure_category`：至多一个主类别；当 `runtime_valid=false` 时使用；
- `task_failure_category`：至多一个主类别；当 runtime 有效但 `task_success=false` 时使用；
- `safety_failure_categories`：列表，可同时记录 fall、unsafe collision、joint-limit violation；
- `collision_observed=true` 可以与 `task_success=true` 同时出现。

Runtime 类别：

```text
reset_error
generation_timeout
generation_error
invalid_reference
adapter_error
sonic_startup_error
sonic_runtime_error
hand_control_error
execution_timeout
logging_error
unknown
```

Task 类别：

```text
missed_object
object_slip
insufficient_lift
insufficient_hold
```

Safety 类别：

```text
robot_fall
unsafe_collision
joint_limit_violation
```

优先级建议：基础设施/数据错误优先于任务表现错误。例如 reference 含 NaN 导致未执行，应记 `invalid_reference`，不能记 `missed_object`。

## 11. 汇总与统计

每个 method×case 至少报告：

- trials、completed 与各类 successes；
- task success、safety success、overall success 及各自置信区间；
- collision-observed、unsafe-collision 和 fall rate；
- generation time 与 execution time 的 median、IQR、mean；
- lift、hold 与 grasp error 的分布；
- failure-category 计数；
- 成功和失败视频索引。

总体结果必须同时给出 macro average（各 case 等权）和 pooled result（所有 trial 合并），避免某个 case 的 trial 数更多而改变结论。

若两个方法使用一一对应的相同 case/seed，可报告 paired comparison；在样本量小且分布未知时，优先展示原始点、比例置信区间和非参数/配对结果，不只展示均值。

Generation time 只有在 generation hardware、candidate budget、selection policy 和计时范围都相同时才能横向比较；否则必须按环境分层披露，不能作方法速度结论。

不得：

- 删除失败 trial；
- 只挑最好视频作为统计证据；
- 方法失败后修改场景再重跑；
- 对两种方法使用不同 retry 次数；
- 把 pilot/开发调参数据混入 final result。

## 12. Artifact 与目录约定

推荐布局：

```text
outputs/t9_eval/<protocol_version>/<run_batch>/
├── frozen_manifest.yaml
├── run_plan.json
├── trials.jsonl
├── summary.json
├── figures/
├── ardy/<case_id>/<run_id>/
│   ├── request.json
│   ├── raw_output/
│   ├── reference/
│   ├── execution/
│   └── result.json
└── kimodo/<case_id>/<run_id>/...
```

大体积数据可不提交 Git，但必须提交 manifest、schema、汇总脚本和可追溯路径。README/PPT 中的任何数字都应能回溯到 `trials.jsonl` 和相应原始 artifact。

## 13. 是否需要 evaluation harness

### 13.1 当前阶段

起草和评审协议**不需要 Harness**。现在最重要的是先关闭第 4 节的开放决策，并取得 T5/T8 的可复现交付。

### 13.2 正式实验阶段

建议实现一个最小 evaluation harness，避免人工操作让两个方法条件不同。它只负责 orchestration，不重写 SONIC、Hand PD、scene 或 evaluator：

```text
manifest loader
  → deterministic run-plan generator
  → ARDY/Kimodo adapter
  → shared reference validator
  → shared runner
  → shared evaluator
  → atomic TrialLog writer
  → summary/plot generator
```

最小能力：

- `--dry-run` 输出计划但不执行；
- 可从中断处 resume，且不重复已完成 run_id；
- 保存 stdout/stderr/exit code；
- 强制执行预冻结的 candidate、selection 和 retry budget；
- 失败同样写 TrialLog；
- 拒绝覆盖已有 artifact；
- 检查 manifest/config/source hash；
- 不允许 method adapter 修改共享场景或判定阈值。

只有在两种方法的最小调用样例稳定后才实现 harness；过早编写会把尚未确定的接口固化错。

## 14. 正式实验 Gate

| Gate | 通过条件 | 状态 |
|---|---|---|
| G1 Source freeze | repo/commit/diff/container/config 全部记录 | BLOCKED |
| G2 Shared environment | scene/SONIC/Hand PD/evaluator hashes 相同 | BLOCKED |
| G3 ARDY final | 可复现命令、checkpoint、adapter、成功/失败样例 | PARTIAL；Task 5 哈希交接包、成功/失败样例和命令已提供，正式 held-out candidate 尚未冻结 |
| G4 Kimodo final | 可复现命令、checkpoint、adapter、成功/失败样例 | PARTIAL；Task 8 v3 development 包已验收，正式 held-out candidate 尚未冻结 |
| G5 Protocol decisions | D-01 至 D-11 已签字确认 | BLOCKED；D-03、D-05 已关闭，D-11 已为 pilot 冻结 |
| G6 Logging | TrialLog schema validator 通过 | PARTIAL；本地 schema/validator 单元测试已通过，Kimodo profiling live smoke 已通过，仍需 ARDY profiling live smoke |
| G7 Smoke tests | 每种方法至少 1 个 `not_final` trial 可追溯 | PARTIAL；Kimodo 固定 reference smoke 完整，ARDY 有 Task 5 端到端证据但仍需按 Task 9 profiling/TrialLog 格式迁移 |
| G8 Run plan lock | case/seed/order/trial 数不可再变 | PILOT READY；`pilot20` 单独计划可签字后执行，formal 仍 BLOCKED |

只有全部 Gate 通过，才能开始 Issue #9 的正式 10/20-run checklist。

## 15. 变更控制

- 协议变化必须提升 `protocol_version`；
- 正式跑数开始后，不得修改 case、阈值、控制器或 trial 数；
- 必须修改时，旧 batch 保留并作废说明，使用新版本从头运行两个方法；
- 每次评审记录日期、参与人、决议和对应 commit；
- T5/T8 的新 checkpoint 不得混入同一 batch。

## 16. 组内评审签字区

| 项目 | 确认人 | 日期 | 结论 |
|---|---|---|---|
| Canonical source snapshot |  |  |  |
| ARDY final delivery |  |  |  |
| Kimodo final delivery |  |  |  |
| Shared SONIC/Hand PD/scene |  |  |  |
| Case、trial、seed |  |  |  |
| Success/collision criteria |  |  |  |
| Logging/statistics |  |  |  |

## 17. 可贴入 GitHub Issue #9 的摘要

```markdown
### T9 Evaluation Protocol Draft v0.3

Task 5 ARDY 与 Task 8 Kimodo development 交付已到位，可执行单独冻结的 20-run pilot；正式统计比较仍等待 held-out 配置和全部 Gate。

- [ ] 冻结 S4000 canonical repo/branch/commit、dirty diff、container 与配置 hash
- [ ] 冻结统一 scene、SONIC、Hand PD、joint mapping 和 evaluator
- [ ] 确认正式 case 的精确坐标（Issue 四点 / 旧 JSON 五点 / ±2 cm pilot 尚未统一）
- [x] 正式任务确认为 grasp-and-lift；不含 place/target area，`place_error_m=null`
- [ ] 确认 10 还是至少 20 trials/method/case
- [ ] 确认 instruction、seed 与 generation/execution timeout
- [ ] 冻结 single-shot/best-of-K、candidate 选择与 retry 规则
- [ ] 冻结 ARDY/Kimodo 相同的 conditioning/information budget
- [x] pilot 不再使用 H100；两种方法均在 S4000，且记录 device/负载/warm-up；不同条件不作 raw latency 排名
- [x] robot-table contact 冻结为诊断项；cube-table hold contact、跌倒及其他 unsafe 条件仍判失败
- [x] 已获得 ARDY Task 5 和 Kimodo Task 8 development 交付路径、成功/失败样例与最小命令；formal held-out 版本仍待冻结
- [ ] 完成 TrialLog schema/failure taxonomy 的 live 验证（v0.1 本地单元测试已通过）
- [ ] 两种方法各完成一次 `not_final` smoke test

所有 Gate 通过前，Issue 中正式 run/结果/图表 checkbox 保持未勾选。
```

## 18. 当前参考链接

- Task 9 Issue：<https://github.com/hkuDL/dl-group2/issues/9>
- 候选 `grasp-pipeline`：<https://github.com/haohao030115/dl-group2/tree/grasp-pipeline>
- 候选 episode schema：<https://github.com/haohao030115/dl-group2/blob/grasp-pipeline/docs/dataset_schema.md>
- 候选 free-base expert 说明：<https://github.com/haohao030115/dl-group2/blob/grasp-pipeline/docs/freebase_expert.md>
- 候选五点 pilot：<https://github.com/haohao030115/dl-group2/blob/grasp-pipeline/docs/pilot_xy_results.md>
