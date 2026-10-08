# ARDY / Kimodo 执行组交回清单

每一条 `run_id` 建一个独立目录。目录已存在时停止，不覆盖。

## 必须交回

- `request.json`：run_id、method、case、精确 XYZ/yaw、semantic instruction、native prompt/phases、seed。
- `environment.json`：host、container digest、S4000 物理 device ID、是否共享、开始/结束占用、Python/MUSA/MuJoCo 版本。
- `method.json`：方法完整标签、source/checkpoint/adapter hash、native generation recipe、precision、warm-up policy。
- `constraints/`：方法实际收到的全部约束及来源；不能只交自然语言摘要。
- `generator_raw/`：原始模型输出、stdout/stderr、exit code。
- `reference/`：adapter 后统一 body/hand reference、joint order、频率、帧数。
- `profile_events.jsonl`：符合 Task 9 profiling v0.3。
- `result.json`、`validation.json`、`physics_steps.json`、`provenance.json`、`simulation.npz`。
- 视频或渲染；失败也要保留。
- `trial.json`：符合 Task 9 TrialLog schema，`run_type=pilot`、`formal_score=false`。
- `MANIFEST.sha256`：以上所有 artifact 的相对路径 hash。

## 每条 run 必须回答

```text
run_id:
method label:
case / XYZ / seed:
candidate requested/generated/selected/attempted:
generation exit code / wall time:
adapter exit code / wall time:
replay exit code / wall time:
runtime user correction count:
physical_success:
safety_success:
overall_success:
max_lift_m / final_lift_m / hold_s:
failure phase/category/reasons:
robot-table contact steps:
cube-table contact during qualifying hold:
reference frames / physics steps:
source/checkpoint/adapter/reference/evaluator hashes:
```

## 禁止事项

- 失败后换 seed 或补一条成功覆盖原 run_id。
- 看过结果后改 prompt、clearance、IK、phase timing 或 evaluator。
- 只交成功视频，删除生成失败或 adapter 失败。
- 把 logical `cuda:0` 当作物理卡号；必须交物理 S4000 device ID。
- 把模型加载、warm-up、generation、adapter、controller startup 和 execution 混成一个无法解释的耗时。
- 在条件不一致时声称 raw generation latency 是模型速度排名。
