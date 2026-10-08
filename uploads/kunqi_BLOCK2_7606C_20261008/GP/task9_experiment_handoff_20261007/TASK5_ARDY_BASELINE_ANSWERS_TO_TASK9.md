# ARDY 基线交接：应答 Task 9 对接五问（一个 prompt + 方块坐标 → 抓取）

> 写给 Kimodo / 评测侧（Task 9）对接人。日期：2026-10-07。
> 本文是问答索引，细节一律指向交接包内的第一手文件，不重复粘贴。
> **交接包**：宿主机 `/home/group2/workspace/tuchengyuan/task5/ardy_handoff_20261007`（容器内把前缀换成 `/workspace/group2/workspace`），下文用 `$PACK` 代指。包内文件被 `handoff_manifest.json` 哈希锁定，复现前请先跑 `code/verify_handoff.py`。

## Q1. prompt 和坐标是在执行前一次性输入的吗？MuJoCo 回放过程中还会不会追加 prompt？

**一次性输入；回放阶段零 prompt。**

- 生成前一次性提供两样东西：① prompt 文本（一句英文，原文见 `$PACK/README.md` §9.1）；② `--case` 结构化位置（center/near/far/left/right 之一），经 `prepare_conditions.py` 展开成 `constraints.json`——**坐标不从自然语言解析**。
- 约束共三类：fullbody（帧 0–25，以 neutral 站姿作生成初始条件）、root2d（帧 0–399，root 原地）、end-effector（帧 0–399，右手腕朝方块坐标的轨迹）。示例：`$PACK/candidates/center/constraints.json`。
- MuJoCo 执行/回放只读预生成的参考 CSV（body + hand），**不调用文字模型、不追加 prompt、无在线修正**。

## Q2. 一次模型调用生成完整轨迹，还是分阶段调用多次生成？

**每个 candidate = 1 次 ARDY 模型调用，生成完整 16 秒轨迹。**

- 模型：`ARDY-G1-RP-25FPS-Horizon52`，单次扩散前向，**10 步去噪**；文本编码器 Meta-Llama-3-8B-Instruct（本地离线）。证据：`$PACK/fresh_original_seed0_v2/ardy_generation.log`（"Loaded model: ARDY-G1-RP-25FPS-Horizon52"、"Using 10 denoising steps"）。
- 之后的处理**不是模型调用**，全部是确定性变换：trajectory_adaptation（保留手腕世界轨迹的手臂 IK 重定向到 neutral 站姿）+ table_clearance（4–7s 手腕 +3cm 余量）。管线阶段顺序：`prepare_conditions → ardy_generation → trajectory_adaptation → table_clearance → canonical_replay → independent_validation`（`pipeline.json` 有每阶段命令/耗时/退出码）。

## Q3. 每个 trial 只生成一个 candidate 吗？有没有人工选择、修改或失败重试？

如实分四类：

1. **冻结认证候选（`candidates/center`）**：seed 0 **首次生成即被采用，无 best-of-n 挑选**。但必须披露：它是**开发迭代产物**——后处理参数（手腕余量 0 → 1.5cm → 3cm）曾在同一 case 上经 run_01–04 失败后人工调整定型，prompt 措辞也经人工迭代。因此它是"调参后的开发 case 结果"；**正式对比请用未参与调参的 case/seed**（grid_v1 的协议可作参考）。
2. **从头皮实验（`fresh_original_seed0_v2`）**：1 次生成 → 1 次物理回放 → 认证通过（17.61cm）。**没有失败后反复执行直到成功**（README §9.7 原文声明）。
3. **失败与重试记录（全部保留，未删任何分母）**：`fresh_original_seed0`（通道被队友占用，未生成即退出）；`fresh_original_seed0_v3`（误启动的重复生成，已终止，无回放，不计入）；`fresh_center_seed1`（换 prompt+seed1，完整跑通但抓取失败 0.9cm，保留作端到端失败样本）；`grid_v1`（5 位置 × 2 次：center 2/2、near 2/2、left 0/2、right 0/2、far 准备失败未执行——计划 10 实放 8 合格 4，统计口径见 README §9.6）。
4. **运行时人工纠正**：0 次（grid 每条 trial 记录 `runtime_user_corrections: 0`）。

⚠️ 另有一条对比必须知道的执行层事实：**同一候选的单次物理回放成功率不是 100%**——轨迹每次都复现（手腕差 <5mm），成败在拇指毫米级接触（demo 重置后 9 放 3 成；评测侧 4/4 有运气成分）。每个 trial 是一次伯努利采样，正式对比请按 proposal 每 condition ≥20 trial 定可靠性置信区间。

## Q4. S4000 运行命令、输入示例、输出 candidate 文件夹、对应日志？

| 要什么 | 在哪 |
|---|---|
| 复现缓存成功（约 1 分钟，不调生成） | `$PACK/README.md` §9.3：verify_handoff → canonical_grasp.py → validate_grasp_run.py → render_canonical.py |
| 从一句新文字跑全链路 | `$PACK/README.md` §9.4：`generate_from_text.py "<prompt>" --case center --seed 0 --out <新目录>`；`--generate-only` 可只生成不执行 |
| 输入示例 | prompt 原文：README §9.1；结构化约束：`$PACK/candidates/center/constraints.json`；场景设定：`candidates/center/setting.json`（+`setting.npz`） |
| 输出 candidate 文件夹 | `$PACK/candidates/center/`：`reference/`（body_pos/quat/lin_vel/ang_vel、joint_pos/vel、left/right_hand_pos，全部 50Hz CSV）+ setting + constraints；消融基线在 `candidates/integrated/`（无 3cm 余量版） |
| 生成/适配日志 | `$PACK/fresh_original_seed0_v2/`：六个阶段的 `.log` + `pipeline.json` + `pipeline_source/`（当时源码快照） |
| 运行日志（正式对比用） | 每轮 run 目录：`policy_logs/`（q/action/左右手 q/action/encoder_mode/motion_playing 等 50Hz CSV）、`result.json`、`validation.json`、`physics_steps.json`（200Hz 接触/抬升）、`provenance.json`（哈希/初始状态/命令）、`simulation.npz` |
| 原始 ARDY 输出 | `$PACK/sources/`（seed0 的 ardy_motion.npz/csv，身体动作来源） |

## Q5. 卡号/卡数、生成开始与结束时间、是否 warm-up？

第一手数据已汇总在 **`$PACK/profiling/generation_timing.json`**（由 pipeline.json 直接提取）。要点：

- **卡**：物理卡 4，单卡（`MUSA_VISIBLE_DEVICES=4 CUDA_VISIBLE_DEVICES=4`；日志里的 `cuda:0` 是 MUSA 兼容层逻辑名，不是另用了卡 0）。
- **耗时**（共享机器墙钟，非独占设备基准）：
  - 原 prompt/seed0（v2，认证通过）：生成 **138.26s**，准备 6.08s，适配 6.61s，余量 2.14s，回放 55.99s，校验 0.55s，**全程 209.6s（约 3.5 分钟）**。
  - 新 prompt/seed1（失败样本）：生成 134.45s。
- **warm-up**：**每次管线运行都是冷启动**——138s 内含文本编码器与扩散模型加载（日志可见权重加载与 LOAD REPORT）；未做独立 warm-up，也未把"加载"与"纯去噪"分开计时。若对比需要暖态/分解数字，请告知，我们补一组同进程二次调用实验。
- **DDS / SONIC / MuJoCo 侧 profiling**：按约定归 Task 9，我们未改动相关代码路径。

## 附：正式对比材料清单（视频之外的）

1. **body/hand reference**：`candidates/center/reference/`（50Hz CSV，关节顺序见 `setting.json` 的 body/hand_joint_order）。
2. **setting**：`candidates/center/setting.json` + 合同 `remote_results/CANONICAL_TABLETOP_EXPERIMENT_BASE.md`（场景/判据/PD/摩擦全部冻结）。
3. **运行日志**：见 Q4 表"运行日志"行；认证批次为 `task5/canonical_grasp_20261007/run_05–07、manual_01、manual_XX` + `$PACK/fresh_original_seed0_v2/run_01`。
4. **协议与全部结果**：`grid_v1/protocol.json`、`summary.json`（含失败分母）。

## 回给 Task 9 的三条对比纪律（来自我方交接文档 §5）

1. **同一执行栈与判据**：canonical SONIC + 同一手 PD + 同一评测器；轨迹时长必须统一（旧共享配置 11s vs 本批 16s，已在 grid 协议记录差异）。
2. **方法标注**：ARDY 原始 / ARDY+约束 / ARDY+轨迹适配 分开计；本候选属第三类。ARDY 换 prompt **不是**第二种方法（项目要求两种不同生成方法 = Kimodo vs ARDY）。
3. **case 与次数**：调参 case（center/seed0）双方都可用于开发；最终报告用未调参 case；每 condition 次数由统一协议定（proposal 目标 ≥20）。
