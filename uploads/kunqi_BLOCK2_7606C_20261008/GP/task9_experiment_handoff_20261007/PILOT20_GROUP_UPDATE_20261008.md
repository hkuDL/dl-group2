Task 9 的 20 条 development pilot 已跑完并完成第一轮汇总。计划分母是 5 个位置 × 2 个 seed × 2 个方法，共 20 条，准备失败也保留在分母中。

当前结果：

- ARDY：8/10 成功进入回放，2/10 达到物理抓取成功，但这两条都因 `robot_environment_support_contact` 没通过严格完整性校验，所以严格 `expert_valid` 为 0/10。
- Kimodo：6/10 成功进入回放，3/10 达到物理成功且通过严格校验；另外 4/10 在准备阶段失败。

需要特别说明：这是 `formal_score=false` 的小样本 pilot，每个 method×case 只有 2 次，不能当成正式可靠性结论。ARDY 实际是 800 帧/约 16 s，Kimodo 是 810 帧/16.2 s；两边生成 recipe 和 profiling 字段也不完全一致，因此当前生成耗时只能分阶段描述，不能直接写成公平速度排名。完整 profiling v0.3 事件流这次没有产出，如需正式分析 DDS/SONIC/生成各阶段耗时，需要插桩后另跑 smoke。

麻烦 Task5、Task8 和 evaluator 同学帮忙确认两点：

1. case-level 成功/失败状态是否和各自输出一致；
2. `robot_environment_support_contact` 是否确认属于冻结协议里禁止的承重/外部支撑，而不是仅作诊断的普通 robot-table contact。

完整结果、协议偏差、计时证据和远端数据路径已整理在 `PILOT20_RESULTS_20261008.md`。
