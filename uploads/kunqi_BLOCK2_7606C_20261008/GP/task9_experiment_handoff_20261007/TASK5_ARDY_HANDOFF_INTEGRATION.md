# Task 5 ARDY 交付如何进入 Task 9

本地随包附带的原始问答索引为 `TASK5_ARDY_BASELINE_ANSWERS_TO_TASK9.md`，SHA-256：

`4e5b04b6bb92046654faa9c10f0a235942a2f41fd31713632304c101e7867a4c`

它是交接说明，不替代 S4000 上 `handoff_manifest.json` 对实际 artifact 的逐文件校验。

## 已确认可用的内容

| Task 5 交付 | Task 9 用途 | 能否作为正式结果 |
|---|---|---|
| `handoff_manifest.json` + verifier | 核对交付未被修改 | 只证明完整性 |
| `fresh_original_seed0_v2` | 端到端成功 smoke；生成与各阶段耗时参考 | 否，center/seed0 属开发条件 |
| `fresh_center_seed1` | 端到端失败样本与失败分类 | 否 |
| `grid_v1` | 多位置开发失败分析、adapter coverage | 否，缓存/重定向且有缺失执行 |
| `candidates/center/reference` | 固定 reference 的 Task 9 profiling smoke | 否，开发调参候选 |
| `profiling/generation_timing.json` | 冷启动 generation/adapter/replay 阶段基线 | 可披露，不能跨不同条件直接排名 |

## ARDY 当前实际流程

```text
一条文本 prompt + 结构化 case 坐标
  → prepare_conditions
  → 单次 ARDY 生成完整 16 s trajectory
  → neutral-pose trajectory adaptation
  → 4–7 s wrist +3 cm table clearance
  → canonical SONIC + Hand PD replay
  → independent evaluator
```

回放阶段不再提交 prompt，也没有机器人状态反馈回 ARDY。SONIC 对机器人状态闭环跟踪 reference，但 ARDY 不是这条低层实时闭环的一部分。

## 必须披露的开发历史

- 冻结 center candidate 没有 best-of-N 挑选，但 prompt 与 table-clearance 参数曾经人工迭代。
- center/seed0 不可当 held-out final；本 pilot 改用 seed 2、3，但仍只是 development pilot。
- 同一 reference 重放的物理成功并非确定性；旧记录出现 9 次重放 3 次成功。因此一次 candidate 只回放一次时，结果同时包含 generator/reference 质量与执行随机性。
- 旧 `grid_v1` 的正确报告方式是：执行成功 4/8、计划覆盖成功 4/10、执行覆盖 8/10。far 是 adapter preparation failure，不得伪装为已执行任务失败。

## Task 9 仍需 ARDY owner 补交

1. 用交接包 verifier 输出确认当前包 hash。
2. pilot seed 2、3 的每次原始 generation、constraints、adapter 前后 reference 和完整 pipeline log。
3. 物理 S4000 device ID、设备是否共享、warm-up policy、模型/adapter/checkpoint hash。
4. Task 9 profiling v0.3 JSONL：至少 generation_total、model_load、model_generate、candidate_preparation_total、controller_startup、每个 loop_compute_total、execution、episode_total。
5. 对应的标准 TrialLog；任何失败照样提交。

Task 9 不要求 ARDY owner 改成 Kimodo 的多阶段生成，也不要求 Task 9 同学复制 ARDY 环境。公平性来自相同任务输入、candidate/retry 预算、下游执行栈和判定；native recipe 的差异应被记录并用于解释耗时。
