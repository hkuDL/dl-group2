# Task 9 固定 reference profiling smoke 报告

日期：2026-10-07  
性质：`not_final_smoke`，不是正式 ARDY/Kimodo 成绩。

## 结论

同一 Kimodo reference 在 profiling 关闭和开启时均完整完成抓取并抬升。profiling-on 记录 3240 个 200 Hz control-step 事件，5 ms 预算内零次 miss；未观察到 profiling 导致的任务结果或明显时延退化。

冻结 reference SHA-256：

`640bc21a9f93cdd60f8e27a4f3b027d80652734bcef1ed631b8188abe25313c7`

## 对比

| 指标 | Profiling off | Profiling on |
|---|---:|---:|
| physical/expert success | true / true | true / true |
| 最大抬升 | 0.124621 m | 0.125202 m |
| 最终抬升 | 0.102804 m | 0.103083 m |
| 连续保持 | 4.730 s | 4.735 s |
| 50 Hz reference frames | 810 | 810 |
| 200 Hz playback steps | 3239 | 3240 |
| 机器人触桌步 | 9 | 8 |
| 跌倒步 | 0 | 0 |
| body tracking RMSE | 0.140311 rad | 0.140339 rad |
| replay wall time | 16.1952 s | 16.2006 s |

Profiling-on 的 `loop_compute_total`：

- 3240 个事件；
- mean 3.278 ms；
- P95 3.631 ms；
- P99 3.790 ms；
- max 4.446 ms；
- 5 ms deadline miss：0。

## Manifest 修正记录

首版 smoke manifest 错误地沿用了 baseline 实测的 3239 步，汇总器因此正确返回 coverage fail。该失败报告已保留。冻结计划按 `810 × 4 = 3240` 修正后，v2 coverage pass。

这是 smoke 阶段对计划错误的修正，不能倒算成正式证据。后续所有 pilot/formal run 必须在运行前使用 3240 的 manifest。

## 限制

- 本次仅验证 Kimodo 固定 reference，不是双模型比较。
- Kimodo candidate 在冻结前经历过 development tuning。
- 当前覆盖 controller startup、完整 execution 和 buffered control-loop compute。
- DDS command age、GPU kernel、generation、adapter 与资源采样仍需由对应实现组接入。
- 两次运行不是位级确定；一个 control step 和一个触桌步的差异按运行时抖动披露。
