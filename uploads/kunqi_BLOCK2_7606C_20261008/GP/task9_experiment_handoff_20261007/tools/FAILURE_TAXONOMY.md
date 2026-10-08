# Task 9 失败分类

失败必须按发生阶段记录，不能只写“抓取失败”，也不能从最终视频倒推并覆盖原始日志。

## 1. 一级分类

| 层级 | TrialLog 字段 | 例子 |
|---|---|---|
| 输入/冻结契约 | `formal_eligible=false` | scene、seed、约束预算不一致 |
| 生成运行时 | `runtime_failure_category` + `failure_phase=generate` | timeout、OOM、模型异常 |
| 候选准备 | `runtime_failure_category=adapter_error` | IK 不可达、关节映射错误、非法 reference |
| SONIC/执行运行时 | `sonic_*`、`execution_timeout` | controller 未启动、DDS 冲突、缺帧 |
| 任务失败 | `task_failure_category` | missed object、insufficient lift/hold、slip |
| 安全失败 | `safety_failure_categories` | robot fall、unsafe collision、joint limit |
| 证据完整性 | `formal_eligible=false` | 缺少日志、视频、hash、frame coverage |

## 2. 判定顺序

1. 先判 reset/generation/adapter/runtime 是否有效；
2. 运行有效后才判物理任务成功；
3. 独立判安全，不把所有桌面接触自动解释为 unsafe；
4. 最后判证据是否满足 formal eligibility；
5. `overall_success` 只能在任务成功、安全成功和 formal eligibility 都已冻结时生成。

## 3. 当前 ARDY development grid 的分类

| Case | 分类 | 依据 |
|---|---|---|
| center r1/r2 | success | lift、hold、接触、完整 800 帧均通过 |
| near r1/r2 | success | lift、hold、接触、完整 800 帧均通过 |
| left r1/r2 | task failure: `insufficient_hold` | lift 超过 0.10 m，但保持仅 0.635/0.925 s，最后回到桌面；可附观察标签 `lift_threshold_reached_then_object_returned_to_table` |
| right r1/r2 | task failure: `insufficient_lift` | 最大抬升约 0.0103 m，未达到阈值 |
| far | pre-execution candidate-preparation failure | `adapter_error`，IK error 0.0335196 m，高于 0.001 m 门限；没有伪造为已执行 trial |

当前网格必须同时报告：

- executed-trial 成功率：4/8 = 50%；
- planned coverage 成功率：4/10 = 40%；
- execution coverage：8/10 = 80%；
- 正式状态：development only，不能作为 held-out ARDY/Kimodo final comparison。

`far` 是否在正式协议中直接计作失败，需在冻结 run plan 时写明。当前工具将其计入 planned coverage 的未成功 slot，同时保留“未执行”的事实。

