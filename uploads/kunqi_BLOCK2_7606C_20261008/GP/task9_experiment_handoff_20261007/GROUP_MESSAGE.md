Task 9 的 development pilot 执行包我整理好了。请 Task 5/ARDY 和 Task 8/Kimodo 两组分别跑 run plan 里各自的 10 条；Task 9 负责统一验收、profiling 汇总和结果对比，不需要重新搭建你们两套生成环境。

本批共 20 条：5 个位置 × 2 个 seed × 2 个方法。每条必须是一次生成、一个 candidate、一次回放、无失败重试、无结果后调参；成功和失败都交回。两种方法都在 S4000 上跑，不再使用 H100。robot-table contact 会记录但不自动判失败，qualifying hold 内 cube-table contact、跌倒、weld/support/teleport/外力仍判失败。

请先看包内 README 和 `PILOT20_RUN_PLAN.json`，再按 `EXECUTOR_RETURN_TEMPLATE.md` 交付。正式开始前还需要三方把 live source/controller/evaluator/checkpoint hash、物理卡号和 timeout 填齐并确认。这个 20-run 是 development pilot，每个 method×case 只有 n=2，能用于展示流程、失败类型和初步性能，不能写成正式可靠性统计；正式每 condition ≥20 次将是 200 条，另开 run plan。
