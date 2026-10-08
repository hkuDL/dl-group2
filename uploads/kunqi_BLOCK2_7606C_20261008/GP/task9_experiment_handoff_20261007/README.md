# Task 9 评测执行包（2026-10-07）

## 先看结论

这个包用于让 ARDY/Task 5 与 Kimodo/Task 8 的实现同学各自运行自己的方法，再把统一格式的结果交回 Task 9。**Task 9 不要求重新搭建两套生成环境，也不负责替实现组修模型。**

当前可执行的是 `pilot20`：5 个位置 × 2 个 seed × 2 个方法，共 20 个端到端 trial。它用于快速比较可行性、失败类型与性能链路，`formal_score=false`。因为每个 method×case 只有 2 次，不能把它写成可靠性充分的正式成功率。

若要做每个 condition 至少 20 次的统计实验，5 个位置 × 2 个方法 × 20 次 = 200 个端到端 trial，必须另建 formal run plan，不能把本次 20 条 pilot 复制扩充分母。

## 已冻结的 pilot 规则

- 任务：右手抓取方块并抬升；不包含 place。
- 场景：canonical tabletop；reference 50 Hz、810 帧、16.2 s；physics/control 200 Hz、理论 3240 步。
- 成功：抬升至少 0.10 m；右拇指与食指或中指形成对向有效接触；qualifying hold 内方块不碰桌；连续保持至少 2.0 s；完整同步回放；无跌倒、weld、support、teleport 或外力。
- robot-table contact：完整记录，但仅作诊断，不自动判失败。
- 每条 run：一次模型调用、一个 candidate、一次 replay、失败不补跑、不人工挑选、不在线修正。
- 两种方法都在 S4000 上生成与执行，不再使用 H100；记录物理 device ID、是否共享、warm-up 和显存/利用率。
- pilot 开始后不得根据结果修改 prompt、约束、adapter、clearance、case 或阈值。必须修复时，旧 batch 保留并作废，提升版本后两种方法一起重跑。

## 方法名称必须如实写

- ARDY：`ARDY + structured coordinate constraints + trajectory adaptation`。
- Kimodo：`Kimodo + segmented constraints + canonical adapter`。

二者的 native generation recipe 不完全相同。ARDY 当前为一次完整 16 s 生成、10 denoising steps；Kimodo 当前为分阶段约束/生成流程。原始 generation latency 可以记录和分阶段解释，但在模型调用结构、扩散步数、warm-up 或 S4000 负载不一致时，不能直接写“某模型快几倍”。

## 谁负责运行什么

1. Task 5/ARDY 同学使用自己的哈希交接包运行 `PILOT20_RUN_PLAN.json` 中 `method=ardy` 的 10 条。
2. Task 8/Kimodo 同学使用自己的 v3/final 包运行 `method=kimodo` 的 10 条。
3. Task 9 同学在运行前核对 manifest、顺序和 GPU；运行后只做独立校验、profiling 汇总、配对检查、表格和失败分析。
4. 两组不得只交成功视频；生成失败、adapter 失败、runtime 失败和任务失败都要交回并进入分母。

## 执行顺序

1. 三方确认 `PILOT_PROTOCOL_FREEZE.json`，填写其中仍为 `null` 的 live hash/device 字段。
2. 对交接包运行只读 hash verifier；保存输出。
3. 检查目标 GPU 无他人任务，保存一次 `mthreads-gmi`；不要并发运行 ARDY 和 Kimodo。
4. 严格按 `PILOT20_RUN_PLAN.json` 顺序运行。每个 `run_id` 只允许出现一次，输出目录已存在就停止。
5. 生成一个 candidate，保存原始输出、约束、prompt、seed、模型和 generation profiling。
6. 执行 frozen adapter，保存 adapter 前后 reference 和 hash；禁止看到结果后调参数。
7. 使用同一 SONIC、Hand PD、scene 和 evaluator 回放一次，同时保存完整 profiling JSONL。
8. 无论成功失败，都填写 `EXECUTOR_RETURN_TEMPLATE.md` 所列交付物并计算 SHA-256。
9. Task 9 使用 `validate_trial.py`、`summarize_profile.py` 和配对检查统一汇总。

## 当前已有 smoke 证据

Kimodo 冻结 reference 已完成 profiling-off/on smoke：两次均成功；profiling-on 3240 个 control-step，P95 3.631 ms，5 ms deadline miss 为 0。该结果证明 profiling 接入没有观察到明显回归，不是 Kimodo 对 ARDY 的成绩。

ARDY 已有 Task 5 端到端成功/失败与 development grid，但还需要按 Task 9 的 TrialLog 和 profiling v0.3 格式迁移一次 smoke。ARDY owner 可先做该 smoke，再执行 10 条 pilot；它不占 `pilot20` 分母。

## 本包文件

- `PILOT_PROTOCOL_FREEZE.json`：pilot 的冻结条件与已知限制。
- `PILOT20_RUN_PLAN.json`：20 条不可事后更改的运行顺序。
- `EXECUTOR_RETURN_TEMPLATE.md`：每组必须交回的文件和结果字段。
- `TASK5_ARDY_HANDOFF_INTEGRATION.md`：Task 5 交接内容如何进入 Task 9。
- `TASK9_OWNER_ACCEPTANCE.md`：Task 9 收件和验收步骤。

完整通用 schema、validator、profiling 规范位于相邻目录 `../t9_eval_prep/`。
