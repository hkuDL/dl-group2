# Task 9 统一评测准备工具

这套文件用于在 ARDY 与 Kimodo 交付结果后，立即检查记录是否完整、是否把试跑误当成正式成绩，以及两种方法是否使用了相同条件。

当前状态：**工具 v0.3 可用；20-run development pilot 可按单独执行包预检后运行，正式统计实验仍未开放。**

## 文件说明

| 文件 | 作用 |
|---|---|
| `trial_schema.json` | 一次尝试对应一条 TrialLog 的结构契约 |
| `validate_trial.py` | 无第三方依赖的结构与内部一致性校验器 |
| `frozen_manifest.template.yaml` | 统一场景、输入、控制器和成功标准的冻结清单模板 |
| `run_plan.template.json` | 正式运行顺序模板；当前故意保持 `runs: []` |
| `examples/kimodo_not_final_trial.json` | 从 2026-10-06 Kimodo 证据迁移出的标准化 smoke 示例 |
| `tests/test_validate_trial.py` | 校验器单元测试 |
| `evidence/` | 原始证据；不要在这里覆盖或修改组员交付的文件 |
| `analyze_ardy_grid.py` | 解析 ARDY development grid，分开报告执行成功率、计划覆盖率和候选准备失败 |
| `profiling_schema.json` | 每个 profiling JSONL event 的字段契约 |
| `summarize_profile.py` | 校验 profiling event，并汇总 mean/P50/P95/max/deadline miss |
| `PROFILING_SPEC.md` | 生成、adapter、初始化、SONIC control loop 和 MuJoCo 的计时边界 |
| `examples/profile_manifest.example.json` | v0.3 的 synthetic 覆盖清单示例；不属于实验结果 |
| `FAILURE_TAXONOMY.md` | generation/adapter/runtime/task/safety/integrity 失败分类 |
| `SMOKE_TEST_CHECKLIST.md` | ARDY/Kimodo 进入 pilot/formal 前的统一 smoke gate |
| `canonical_observation_20261007.json` | S4000 canonical 文件、环境和 Git 版本的只读观察快照；不是正式冻结清单 |
| `ARDY_DEVELOPMENT_SUMMARY_20261007.md` | 当前 ARDY grid 的非正式进度摘要 |

## 三层使用顺序

### 1. 单条日志校验

每一次生成/执行尝试都必须保留一条记录，包括失败尝试。先运行：

```powershell
cd C:\Users\kunqi\Kun\HKU_SH\BLOCK2_7606C\GP\t9_eval_prep
python .\validate_trial.py .\examples\kimodo_not_final_trial.json
```

预期输出：

```text
OK: 1 TrialLog record(s) validated
```

若两组交付的是多条 JSONL：

```powershell
python .\validate_trial.py .\trials.jsonl
```

### 2. 单模型 smoke/pilot

组员交付结果后：

1. 将原始命令、日志、报告、reference 和视频原样放入新的 `evidence/<method>/<run_id>/`；
2. 计算并记录 artifact SHA-256；
3. 按 `trial_schema.json` 创建一条标准记录；
4. `run_type` 使用 `not_final_smoke` 或 `pilot`；
5. 通过校验后才能进入开发汇总，但仍不得计入正式成功率。

### 3. 正式配对检查

只有 manifest 已冻结、run plan 已锁定后才使用：

```powershell
python .\validate_trial.py .\formal_trials.jsonl --require-formal --check-pairs
```

`--check-pairs` 会检查同一 case/trial 的 ARDY 和 Kimodo 是否具有相同：

- object pose 与 grasp arm；
- instruction、seed、conditioning regime 和 input spec；
- candidate budget、selection policy 和 retry policy；
- scene、controller、evaluator hash；
- execution environment。

Generation environment 可以不同，但此时不得直接比较 generation speed。

## Validator 当前检查内容

- `not_final_smoke` / `pilot` 不能伪装成 formal；
- candidate 数量、选择索引、尝试索引与 retry 字段自洽；
- expert conditioning 必须披露 constraint provenance 和 hash；
- Git SHA、SHA-256、object pose、quaternion 和 UTC 时间格式；
- completed、frame coverage、runtime validity 的关系；
- `task_success`、`collision_observed`、`safety_success`、`overall_success` 的关系；
- 碰桌记录不会自动被解释为任务失败；
- `grasp_and_lift` 协议中 `place_error_m` 必须为 `null`；
- duplicate run ID、duplicate method/case/trial；
- 可选的 ARDY/Kimodo 配对一致性。

## Validator 不负责什么

本工具只校验**日志结构和内部一致性**，不会：

- 重新运行 MuJoCo 或重新计算 evaluator；
- 证明某个宣称的成功结果真实发生；
- 自动判断碰桌是否属于 unsafe collision；
- 解析或冻结 YAML manifest；
- 替代原始日志、视频、state dump 和 artifact hash 核验。

因此“校验通过”不等于“正式成功”。正式结果还必须绑定冻结的 manifest、run plan 和实际 artifact。

## 测试

```powershell
python -m unittest discover -s tests -v
```

当前测试覆盖：合法 smoke、合法 formal、试跑混入正式结果、非有限数值、pose/hash/UTC、candidate bookkeeping、expert provenance、runtime/failure taxonomy、task/safety/overall 关系、JSONL 错误和 ARDY/Kimodo 配对。

## ARDY development grid 解析

在 S4000 容器中可直接读取现有结果，不修改任何源 artifact：

```bash
python /path/to/analyze_ardy_grid.py \
  /workspace/group2/workspace/tuchengyuan/task5/ardy_handoff_20261007/grid_v1 \
  --output-dir /your/own/task9-output/ardy-grid
```

输出包括 JSON、CSV 和 Markdown。工具会把 `far` 这类候选准备失败保留为 pre-execution failure，并同时报告：

- executed-trial success rate；
- planned coverage success rate；
- execution coverage；
- 未解释的缺失 trial。

这些指标不能混成一个成功率，也不能把未执行 trial 伪装成已执行失败。

## Profiling 汇总

当前 profiling 子工具为 v0.3。先按 `PROFILING_SPEC.md` 记录一行一个 event 的 JSONL。下面的 event 与 manifest 都是带 `synthetic=true` 的格式测试数据，不属于实验结果：

```powershell
python .\summarize_profile.py .\examples\profile_events.example.jsonl
```

加入 manifest 后会同时检查计划 run、阶段数量和 control-step frame 覆盖：

```powershell
python .\summarize_profile.py .\examples\profile_events.example.jsonl `
  --manifest .\examples\profile_manifest.example.json
```

真实运行可用 `--json-out` 和 `--csv-out` 写出新文件；工具拒绝覆盖已有文件。v0.3 同时汇总异步 DDS 的 new/reused/missing/stale command 计数，并保留 experiment/config 身份、S4000 device、卡数、后端、精度、warm-up、显存和利用率元数据。正式结果必须提供 manifest；v0.1/v0.2 日志必须按真实 provenance 迁移，不能只改版本号。

这次 profiling 升级没有修改抓取成功阈值或 TrialLog evaluator。它只收紧性能事件、实验身份和覆盖完整性；成功率仍由冻结的评测协议、`trial_schema.json` 和实际证据决定。若 device、卡数、共享状态、时钟或 profiling 开销口径不同，工具会拆分条件，原始 generation latency 不得直接排名。

## 当前仍需小组确认

- 统一 scene、机器人初始状态和 object pose；
- 一段还是分阶段 prompt；
- 两个模型允许获得的手腕/末端目标约束；
- single-shot、候选数量与 retry 规则；
- trial 数、seed、timeout；
- S4000 canonical snapshot、controller 和 evaluator hash。

已冻结：robot-table contact 必须完整记录，但只作诊断，不自动判失败；qualifying hold 内 cube-table contact、跌倒、weld/attachment、teleport、外力和冻结规则定义的 unsafe collision 仍判失败。

单独可转发的执行包位于 `../task9_experiment_handoff_20261007/`。其中 `pilot20` 是 5 cases × 2 methods × 2 seeds 的 20 条端到端 development pilot，不是“每个 condition 20 次”的正式统计实验。
