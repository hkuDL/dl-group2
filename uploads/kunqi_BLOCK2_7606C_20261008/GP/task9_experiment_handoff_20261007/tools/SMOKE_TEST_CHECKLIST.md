# Task 9 Smoke Test 检查清单

每个方法至少完成一次不计分 smoke。没有全部勾选前，不进入 pilot/formal。

## A. 资源与隔离

- [ ] 已确认 S4000 节点、容器和本组 GPU 4-7；
- [ ] `mthreads-gmi` 已保存，目标 GPU 无他人任务；
- [ ] 已检查 `kimodo_demo`、`g1_deploy_onnx_ref`、MuJoCo 和 DDS 进程；
- [ ] 输出目录使用新的 `run_id`，不存在则创建，存在则立即停止；
- [ ] 不修改共享权重、公共环境、canonical scene 或其他同学目录；
- [ ] 只停止本次 smoke 自己启动的进程。

## B. 冻结身份

- [ ] 记录 repository URL、branch、full commit、dirty 状态；
- [ ] 记录 generator、adapter、SONIC、Hand PD、evaluator 版本；
- [ ] 记录 checkpoint、scene、initial pose、controller、evaluator SHA-256；
- [ ] 记录容器 image/digest、Python、MUSA、MuJoCo 和驱动版本；
- [ ] 记录生成硬件和执行硬件，二者不得混为一个字段。

## C. 输入与候选

- [ ] 使用 canonical case、机器人初始状态和 grasp arm；
- [ ] 保存完整 prompt phases、object pose、seed 和全部约束；
- [ ] 披露约束来自规则、物体几何还是 expert trajectory；
- [ ] 保存 requested/generated/selected/attempted candidate index；
- [ ] candidate preparation 失败也写日志，不进入“成功候选重试”；
- [ ] 禁止人工实时调整；如发生，明确标记 smoke 非正式。

## D. 执行

- [ ] 同一个 canonical scene、SONIC、Hand PD 和 evaluator；
- [ ] 完整执行约 16 s / 800 reference frames；
- [ ] 无 weld、teleport、外力、骨盆支撑或运行时 body IK；
- [ ] state/action/hand/reference 同步，记录 skipped/missing frames；
- [ ] 没有外来仿真或 controller 进程进入同一 DDS 通道；
- [ ] profiling 关闭时先完成一轮基线 smoke；
- [ ] profiling 开启后行为、帧数和判定未改变。

## E. 成功与失败证据

- [ ] 物块抬升至少 0.10 m；
- [ ] 右拇指与食指或中指形成正法向力对向接触；
- [ ] qualifying hold 期间无 cube-table contact；
- [ ] 连续保持至少 2.0 s；
- [ ] 机器人未跌倒；
- [ ] robot-table contact 已保存 body/geom、phase 和完整步数，但未被自动当作失败；
- [ ] 失败按 `FAILURE_TAXONOMY.md` 分类；
- [ ] candidate-preparation、runtime、task、safety、integrity 失败没有混为一类。

## F. 交付物

- [ ] 原始命令、stdout/stderr 和环境信息；
- [ ] 原始 generator 输出和 adapter 后 reference；
- [ ] controller/physics/evaluator 日志与 state dump；
- [ ] result/report JSON 和视频；
- [ ] profiling JSONL 与汇总；
- [ ] 所有 artifact SHA-256；
- [ ] 标准 TrialLog 通过 `validate_trial.py`；
- [ ] `run_type=not_final_smoke` 且 `formal_score=false`。

## Gate

只有 ARDY 与 Kimodo 都通过同一份 smoke 清单，且 manifest/run plan 已签字冻结，才允许将新运行标为 `formal`。
