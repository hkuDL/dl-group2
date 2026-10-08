# ARDY canonical development grid（2026-10-07）

来源：S4000 只读终端输出。此摘要未下载或重新计算原始 artifact，因此是进度记录，不是独立验收或正式 Task 9 结果。

## 结果

| Case | 结果 | 最大抬升 | 最大连续保持 | 分类 |
|---|---:|---:|---:|---|
| center r1 | 成功 | 0.17668 m | 4.805 s | success |
| center r2 | 成功 | 0.17768 m | 4.795 s | success |
| near r1 | 成功 | 0.14755 m | 4.700 s | success |
| near r2 | 成功 | 0.15312 m | 4.735 s | success |
| left r1 | 失败 | 0.12346 m | 0.635 s | insufficient hold；最终回到桌面 |
| left r2 | 失败 | 0.12461 m | 0.925 s | insufficient hold；最终回到桌面 |
| right r1 | 失败 | 0.01028 m | 0 s | insufficient lift |
| right r2 | 失败 | 0.01028 m | 0 s | insufficient lift |
| far | 未执行 | - | - | adapter IK error 0.0335196 m > 0.001 m |

已执行成功率为 4/8（50%）；按 5 cases × 2 repeats 的计划覆盖为 4/10（40%），execution coverage 为 8/10（80%）。成功 trial 的平均最大抬升约 0.16376 m，平均最终抬升约 0.14191 m，平均连续保持约 4.75875 s。八次已执行 trial 均未跌倒。

## 限制

- 源 summary 明确标记为 `development robustness, not held-out final comparison`；
- 使用 `cached_ardy_coordinate_retarget`，不代表每次重新调用 ARDY 端到端生成；
- `source_generation_wall_seconds` 和 `candidate_preparation_seconds` 为空，不能用于生成性能比较；
- 当前结果中的自定义 `expert_valid` 不能替代尚未冻结的共享 evaluator certification；
- Kimodo 尚无同一 canonical 设置下的成对结果。

因此这批数据用于失败分析、smoke/profiling 工具开发和 presentation 的“当前进度”，不能写成 ARDY 优于或劣于 Kimodo的正式结论。

