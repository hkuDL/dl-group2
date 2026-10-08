# Task 9 收件与验收

## 运行前

- [ ] `PILOT_PROTOCOL_FREEZE.json` 的 live hash/device/timeout 已由三方填写并签字。
- [ ] 20 条 run_id、case、seed 和顺序没有改动。
- [ ] 两种方法各完成一条不计分 profiling smoke。
- [ ] 两组明确接受：一个 candidate、一次 replay、无 retry、失败保留。
- [ ] 输出根目录为空，且不会覆盖 Task 5/Task 8 原交付。

## 每收到一条 run

- [ ] SHA manifest 校验通过。
- [ ] generator/adapter/replay 的命令、exit code 和日志齐全。
- [ ] `trial.json` 通过 `validate_trial.py`。
- [ ] `profile_events.jsonl` 通过 `summarize_profile.py` 的 schema 与 coverage 检查。
- [ ] reference 为 810 帧；预声明物理步数为 3240；偏差有原始日志和原因。
- [ ] contact、lift、hold、fall 和完整性由共享 evaluator 产生，而不是人工看视频填写。
- [ ] 失败阶段与分类明确，未执行和执行失败没有混写。

## 批次完成后

- [ ] 实际收到 20 个唯一 run_id；缺失项不能静默删除。
- [ ] 每个 pair_id 同 case、坐标、seed、semantic instruction 和下游 hash。
- [ ] 分别报告 generation success、adapter coverage、runtime validity、task success、safety success 和 overall success。
- [ ] 报告 20-run pilot 的分母，并标注每 condition 仅 n=2。
- [ ] latency 按 stage、warm-up、device/shared 状态分层；只在条件相同时做直接排名。
- [ ] 表格中使用完整方法名，披露开发调参与 native recipe 差异。
- [ ] 失败案例按 generation / adapter / SONIC-runtime / task / safety / integrity 分类。
- [ ] PPT 和报告明确写 `development pilot; not formal reliability estimate`。

## 不能从这 20 条得出的结论

- 不能声称某方法的真实成功率已经稳定估计。
- 不能用 n=2/condition 做强显著性结论。
- 不能把固定 reference 的 replay profiling 当作端到端 model latency。
- 不能把 adapter preparation failure 改写成“模型抓取失败”，也不能从分母删除。
- 不能把 ARDY 10-step full-trajectory generation 与 Kimodo 不同阶段/步数的 raw time 直接解释为纯模型架构优劣。
