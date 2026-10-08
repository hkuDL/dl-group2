# Task 9 正式对比实验报告：ARDY vs. Kimodo

> 实验 ID：`task9_formal40_20261008`  
> 实验日期：2026-10-08  
> 报告状态：本次固定 `center` setting 的正式结果；不代表跨位置、跨任务的通用结论  
> 远端结果根目录：`/workspace/group2/workspace/kunqi/task9_formal40_20261008`  
> 冻结 manifest SHA-256：`5b80620fe7bcb711f9c634617c02e41ce28278d056b0c5de64511f3d4fb03edd`

## 1. 结论摘要

在同一 `center` 抓取抬升任务、相同 seed 列表（1000–1019）、相同 SONIC/MuJoCo 执行逻辑和相同主评价标准下，ARDY 与 Kimodo 的**完整证据验证成功率均为 19/20（95%）**。本实验没有观察到成功率优势。

两种方法的失败性质不同：

- Kimodo seed 1006 是真实的物理任务失败：没有形成有效接触，未抬升，连续保持时间为 0。
- ARDY seed 1007 的物理抓取成功，但状态帧覆盖不完整且 reference cursor stale，未通过运行/证据完整性检查，因此正式主指标判失败。

Kimodo 的中位端到端墙钟时间为 162.678 s，ARDY 为 182.749 s；本次记录中 Kimodo 低约 20.071 s（12.3%）。时间差主要来自生成阶段。不过，两种方法实际使用了不同物理卡号（Kimodo GPU 1、ARDY GPU 7，均为 MTT S4000），且运行顺序未交替、共享负载未完全控制，因此该时间差应作为**描述性结果**，不能单独归因于模型架构。

本实验只检验固定 `center` setting 下的 seed 稳定性。20 条不是 20 个不同位置或不同任务，不能据此声称模型具有 95% 的跨位置泛化成功率。

## 2. 评测问题

本实验回答以下受限问题：

> 在固定 center 场景、固定输入任务、固定 adapter/calibration 和统一物理回放标准下，ARDY 与 Kimodo 的冻结端到端 pipeline 对不同随机 seed 的任务成功率、证据完整性和墙钟耗时有何差异？

本实验不回答：

- 两个模型在不同物体位置上的泛化能力；
- 未经过 adapter/calibration 的原始模型能力；
- 视觉闭环或实时 prompt 更新能力；
- 严格禁止任何机器人—桌面接触时的任务成功率；
- 在完全独占、同一物理 GPU 上的纯模型吞吐量排名。

## 3. 被比较的方法

### 3.1 Kimodo pipeline

本报告中的 Kimodo 指：

```text
Kimodo segmented generation
→ frozen canonical adapter
→ tracking calibration / contact and approach refinement
→ SONIC body control + Hand PD
→ MuJoCo replay
→ frozen task/evidence validation
```

它不是未经处理的 raw Kimodo 输出。正式运行中每条 trial 只有一个 candidate，不进行 best-of-K、人工选择或失败后调参重跑。

### 3.2 ARDY pipeline

本报告中的 ARDY 指：

```text
ARDY segmented generation
→ frozen ARDY adapter
→ center tracking calibration
→ SONIC body control + Hand PD
→ MuJoCo replay
→ frozen task/evidence validation
```

它不是 raw ARDY 零后处理结果。正式运行入口为：

```text
/workspace/group2/workspace/fuyuhan/ardy_tabletop_segmented_20261008/run.sh
```

使用的 calibration 为：

```text
/workspace/group2/workspace/fuyuhan/ardy_tabletop_segmented_20261008/config/center_segmented_tracking_seed0.json
```

## 4. 实验设计

| 项目 | 冻结设置 |
|---|---|
| Case | `center` |
| Seed | 1000–1019，共 20 个 |
| 每种方法 trial 数 | 20 |
| 总计划 trial 数 | 40 |
| Candidate budget | 每个 seed 1 个 |
| Retry | 方法/物理失败不重试；仅零帧外部基础设施失败允许同 candidate 重试 |
| Reference | 810 帧，50 Hz |
| Episode duration | 16.2 s |
| Execution | SONIC body controller + Hand PD + MuJoCo |
| 任务 | 右手抓取红色方块、抬升并稳定保持 |
| 主 lift 阈值 | 0.10 m |
| 主 hold 阈值 | 连续 2.0 s |
| Robot-table contact | 主指标允许并记录；strict no-table 单独报告 |
| Cube-table contact | qualifying hold 内不允许 |
| 执行顺序 | Kimodo 1000–1019，随后 ARDY 1000–1019 |

### 4.1 硬件和运行环境

- 主机：`worker00038`
- 容器：`va-train`
- 加速卡型号：MTT S4000
- Kimodo：formal plan 记录 `physical_gpu=1`
- ARDY：正式运行命令使用 `--gpu 7`
- H100 未进入本次正式对比

两种方法都在 S4000 上运行，但不是同一物理 device ID。运行期间还观察到 DDS 资源等待；调度器在每条 ARDY trial 前等待共享 DDS 释放。因而墙钟时间同时包含方法本身、设备状态和部分运行环境影响。

### 4.2 协议符合性与已知偏差

符合项：

- `center` case、1000–1019 seed 列表和每种方法 20 条均按计划执行；
- single candidate、方法失败不重试；
- Kimodo 全部完成后才运行 ARDY，符合本次 `protocol.json` 的执行顺序；
- 两种方法均完成生成、adapter、SONIC/MuJoCo 回放和独立验证；
- 40 个计划槽位均有结果，未删除失败 trial。

明确偏差：

- 冻结 `protocol.json` 写明两种方法使用 physical GPU 1，但 ARDY 实际启动参数为 `--gpu 7`；两张卡型号均为 MTT S4000。

处理方式：不修改已冻结协议或结果，不重跑替换；在报告中保存实际 device ID。成功率比较仍可作为同型号 S4000 上的物理结果，但时间差降级为描述性比较。如果课程/项目要求严格逐字段符合 manifest，应把本批标记为“formal execution with disclosed hardware-device deviation”，并补做同一物理卡的 timing-only 对照；不得静默声称 GPU ID 完全一致。

### 4.3 Primary success

一条正式主成功 trial 至少需要：

1. 方块抬升不少于 0.10 m；
2. 右手拇指与 index/middle 至少一侧形成有效对向接触；
3. qualifying hold 内方块不接触桌面；
4. 连续保持不少于 2.0 s；
5. replay 完整、状态有限、reference 同步；
6. 无跌倒、weld、attachment、teleport 或人工外力；
7. 独立 task/evidence validator 通过。

Robot-table support contact 在主指标中作为诊断记录，不自动判主任务失败。strict no-table 指标另行保存。

## 5. 主结果

### 5.1 汇总

| 指标 | Kimodo | ARDY |
|---|---:|---:|
| 计划 trial | 20 | 20 |
| 完整流水线执行 | 20 | 20 |
| 物理抓取成功 | 19/20（95%） | 20/20（100%） |
| 完整证据验证成功 | 19/20（95%） | 19/20（95%） |
| 完整证据验证失败 seed | 1006 | 1007 |
| 缺失 task report | 0 | 0 |
| 缺失 result | 0 | 0 |
| 端到端中位墙钟时间 | 162.678 s | 182.749 s |

对 19/20 的成功率，95% Wilson 区间约为 76.4%–99.1%。ARDY 的物理成功率 20/20 对应 Wilson 区间约为 83.9%–100%。样本量不足以支持小差异的稳定排序。

### 5.2 配对 seed 结果

| Seed | Kimodo 物理 | Kimodo 正式验证 | ARDY 物理 | ARDY 正式验证 | 说明 |
|---:|:---:|:---:|:---:|:---:|---|
| 1000 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1001 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1002 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1003 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1004 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1005 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1006 | ✗ | ✗ | ✓ | ✓ | Kimodo 物理任务失败 |
| 1007 | ✓ | ✓ | ✓ | ✗ | ARDY 物理成功但证据完整性失败 |
| 1008 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1009 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1010 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1011 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1012 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1013 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1014 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1015 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1016 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1017 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1018 | ✓ | ✓ | ✓ | ✓ | 双方通过 |
| 1019 | ✓ | ✓ | ✓ | ✓ | 双方通过 |

完整证据验证结果的配对不一致项恰好相反：seed 1006 只有 ARDY 通过，seed 1007 只有 Kimodo 通过。McNemar 双侧精确检验为 `p=1.0`，本样本没有提供成功率差异证据。

### 5.3 Lift 与 hold

以下描述统计仅用于描述成功轨迹，不把 lift 更高直接解释为方法更优。

| 指标（仅正式验证成功 trial） | Kimodo | ARDY |
|---|---:|---:|
| N | 19 | 19 |
| Mean lift | 0.126150 m | 0.139196 m |
| Median lift | 0.126125 m | 0.139129 m |
| Lift SD | 0.001524 m | 0.003102 m |
| Lift range | 0.124051–0.129846 m | 0.132315–0.146418 m |
| Mean hold | 4.6308 s | 4.8466 s |
| Median hold | 4.6500 s | 4.8450 s |
| Hold SD | 0.0828 s | 0.0094 s |
| Hold range | 4.4700–4.7500 s | 4.8300–4.8700 s |

两种方法的成功 trial 都明显超过 0.10 m / 2.0 s 阈值。ARDY 的成功轨迹在本固定场景中 lift 与 hold 更高、更集中，但这可能主要来自 method-specific adapter、hand schedule 和 calibration，不应解释成 raw generator 的独立优势。

## 6. 失败分析

### 6.1 Kimodo seed 1006

记录：

- `physical_success=false`
- `expert_valid=false`
- `support_contact_steps=0`
- `max_lift_m=null`
- `hold_s=0.0`
- raw motion hash：`b7c4baf7fbed…`

分类：**任务失败 / 抓取未建立 / insufficient lift and hold**。

这是完整新生成 trial 的真实失败，按冻结协议进入分母且不得调参或重跑替换。

### 6.2 ARDY seed 1007

物理结果：

- `physical_success=true`
- lift：0.137024 m
- hold：4.820 s

正式验证失败项：

- `complete_state_frame_coverage=false`
- `other_integrity_failures_absent=false`
- `reference_cursor_stale`
- `frame_coverage_failed`

同时记录：

- `robot_environment_support_contact`
- strict validator 的 `no_support_contacts=false`

分类：**SONIC/执行运行时与证据完整性失败**，而不是物理抓取失败。Robot-table support contact 只影响 strict no-table 诊断，不是本次主指标失败的根因。

该 trial 已进入物理回放并形成有效抓取，不属于协议允许重试的“零帧外部基础设施失败”，因此仍作为正式失败保留。

## 7. 时间对比与原因

### 7.1 端到端时间

| 指标 | Kimodo | ARDY | ARDY − Kimodo |
|---|---:|---:|---:|
| Median end-to-end wall time | 162.678 s | 182.749 s | +20.071 s |
| 相对差异 | — | — | +12.3% |

ARDY 的逐 trial 总时间：

- mean：178.608 s
- median：182.749 s
- SD：8.330 s
- range：167.400–188.994 s

当前本地证据只保存了 Kimodo 的中位总时间，没有复制全部逐 trial timing 数值，因此不在本报告中给出 Kimodo 总时间的 SD、区间或配对时间显著性检验。远端 `kimodo/status.json` 保留这些原始数据。

### 7.2 阶段中位数

| 阶段 | Kimodo | ARDY | 解释 |
|---|---:|---:|---|
| Model load | 17.571 s | 未单独拆分 | ARDY load 包含在 generate 中 |
| Generation | 50.705 s | 97.227 s | ARDY 的主要时间来源 |
| Model load + generation | 68.276 s | 97.227 s | ARDY 多约 28.951 s |
| Adapter | 5.727 s | 8.304 s | ARDY 多约 2.577 s |
| SONIC init | 36.721 s | 未单独拆分 | ARDY 包含在 replay 中 |
| Replay execution | 16.200 s | — | Kimodo 单独记录 |
| SONIC init + replay | 52.921 s | 56.567 s | ARDY 多约 3.646 s |
| ARDY prepare | — | 6.350 s | 计时边界不同 |
| ARDY verify | — | 0.863 s | 计时边界不同 |

阶段中位数不能直接相加重建“中位 trial”，因为中位数来自不同 trial，且两个 pipeline 的计时边界不完全相同。正式结论使用端到端总时间；阶段结果只用于解释差异来源。

### 7.3 时间结论的限制

尽管两者都使用 S4000，本次实际物理卡号不同，且没有交替运行或记录完全一致的设备负载、温度、warm-up 状态。因此：

- 可以报告本次运行观察到的墙钟差异；
- 可以说明生成阶段是主要差异来源；
- 不应声称 Kimodo 模型在严格同设备独占条件下必然快 12.3%；
- 如需发布强性能排名，应在同一物理 GPU、相同 warm-up、交替顺序和独占窗口下补充 timing-only run。

## 8. Seed 与重复性

20 个 seed 只改变生成阶段的随机采样，不改变 case、prompt、坐标、场景、adapter、calibration、SONIC 或成功阈值。

Kimodo 20 个 trial 的 raw SHA-256 全部唯一，说明没有直接重复使用同一个 raw motion。成功 trial 的 lift/hold 仍高度集中，表明固定 adapter、refinement 与 SONIC 对原始生成差异有明显压缩作用。

因此本实验衡量的是：

> 固定 center 任务下，冻结端到端 pipeline 对生成随机性的稳定性。

它不衡量跨位置、跨物体或跨指令的泛化。

## 9. Robot-table contact 与 strict 指标

ARDY 的 `strict_no_table_expert_valid` 为 0/20。每条 ARDY trial 都发生了 strict 定义下不允许的 robot/environment support contact。

Kimodo 正式报告没有直接输出同名 strict 字段；其成功 trial 的 `support_contact_steps` 为非零，因此按相同 strict 定义预计也无法通过，但该结论应标为**派生判断**，不能冒充独立 validator 的直接输出。

正式主指标允许 robot-table contact，是项目在正式运行前冻结的决定。报告必须同时披露 contact，不应将其隐藏，也不应在实验完成后改用 strict 口径重新挑选赢家。

## 10. 有效性与公平性限制

### 10.1 固定 center 且 calibration 同源

本次只运行 `center`，并使用 center development calibration。它最适合检验固定场景稳定性，不是 held-out spatial generalization。

### 10.2 Method-specific adapter 贡献显著

结果属于完整 pipeline，不属于 raw generator。高成功率可能主要由 trajectory adaptation、contact refinement、hand schedule 和 SONIC tracking 共同产生。

### 10.3 不同物理 GPU 与共享状态

两种方法使用同型号但不同 device ID；DDS 还出现等待窗口。成功率主要依赖物理回放结果，时间排名则受到设备与共享负载影响。

### 10.4 批量顺序而非交替顺序

运行顺序为全部 Kimodo 后全部 ARDY，而不是按 seed 交替。温度、系统负载和时间漂移可能影响 timing。

### 10.5 小样本

20 次只能识别大差异。双方 19/20 的置信区间很宽，不能将 95% 当作精确的总体可靠率。

### 10.6 Input/conditioning 不是 raw-model 等价

两种 pipeline 的 generator 和 adapter 不同。比较对象应始终写成：

- `Kimodo + segmented constraints + canonical adapter`
- `ARDY + segmented constraints + frozen ARDY adapter`

## 11. 可复核证据路径

### 11.1 顶层

```text
/workspace/group2/workspace/kunqi/task9_formal40_20261008/protocol.json
/workspace/group2/workspace/kunqi/task9_formal40_20261008/formal_freeze_manifest.sha256
/workspace/group2/workspace/kunqi/task9_formal40_20261008/logs/remaining_all_master.log
```

### 11.2 Kimodo

```text
/workspace/group2/workspace/kunqi/task9_formal40_20261008/kimodo/plan.json
/workspace/group2/workspace/kunqi/task9_formal40_20261008/kimodo/status.json
/workspace/group2/workspace/kunqi/task9_formal40_20261008/kimodo/worker.log
/workspace/group2/workspace/kunqi/task9_formal40_20261008/kimodo/trials/seed_XXXX/
/workspace/group2/workspace/kunqi/task9_formal40_20261008/kimodo/episodes/
```

### 11.3 ARDY

```text
/workspace/group2/workspace/kunqi/task9_formal40_20261008/ardy/center_seedXXXX/
/workspace/group2/workspace/kunqi/task9_formal40_20261008/logs/ardy_formal/center_seedXXXX.log
```

每条 ARDY run 的核心文件包括：

```text
pipeline.json
replay/result.json
replay/validation.json
replay/task_validation.json
```

## 12. 可公开的结论与禁止表述

### 12.1 可以表述

> 在固定 center setting、20 个预声明随机 seed、single-candidate/no-retry 和 touch-allowed 主标准下，Kimodo 与 ARDY 的冻结端到端流水线均取得 19/20（95%）完整证据验证成功率。Kimodo 的失败是物理任务失败；ARDY 的失败是物理成功但回放证据完整性失败。本次 Kimodo 中位端到端墙钟时间比 ARDY 低约 12.3%，差异主要来自生成阶段，但由于物理 device ID 和共享负载不同，该时间差仅作描述性结果。

### 12.2 不应表述

- “Kimodo/ARDY 的通用抓取成功率是 95%。”
- “20 次代表 20 个不同位置。”
- “ARDY 的模型物理失败率为 5%。”——其唯一正式失败实际上物理成功。
- “Kimodo 在严格同硬件条件下确定快 12.3%。”
- “结果证明某方法显著优于另一方法。”
- “ARDY 通过 strict no-table 标准。”

## 13. 建议的后续实验

1. **跨位置 held-out grid**：预先冻结 center/near/far/left/right 精确坐标，每个方法在每个位置使用相同 seed 列表。
2. **同卡 timing-only 对照**：同一物理 S4000、相同 warm-up、交替顺序、独占运行窗口。
3. **Adapter 消融**：分别比较 raw reference、基础 adapter、contact/approach refinement 后的差异，量化成功率由哪一层贡献。
4. **参考轨迹多样性**：计算 raw motion、candidate 和实际 SONIC input reference 的跨 seed RMSE，验证 adapter 是否压缩了生成差异。
5. **运行完整性修复**：定位 ARDY seed 1007 的 state frame coverage/reference cursor stale，但不得用修复后的结果替换本次正式失败。
6. **统一 strict validator**：对 Kimodo 和 ARDY 使用同一脚本派生 no-table 指标，作为诊断而非事后主指标。
7. **功效分析后扩样本**：根据希望检测的成功率差异确定 trial 数，不以单个 20-trial batch 下强结论。

## 14. 最终结论

本次正式实验显示，在固定 center setting 和冻结开发调优 pipeline 下，Kimodo 与 ARDY 都具有较高的 seed 稳定性，完整证据验证成功率同为 95%。两者没有成功率上的可辨别差异。ARDY 的物理抓取为 20/20，但有一条运行/证据完整性失败；Kimodo 有一条真实物理任务失败。

Kimodo 在本次记录中的端到端中位时间更低，主要优势来自生成阶段；鉴于不同物理 GPU、非交替顺序和共享机器状态，该结果应作为当前部署条件下的描述性性能观察，而不是不受条件影响的模型速度定律。

更重要的是，这个实验验证的是**固定 center、固定 calibration、method-specific adapter 下的端到端可靠性**。任何关于跨位置泛化、raw model 能力或严格无桌面接触性能的结论，都需要新的预注册实验。

---

## 附：群内简短同步版本

> Task 9 formal40 已完成：Kimodo 与 ARDY 各 20 条，固定 center、seeds 1000–1019、single candidate/no retry。完整证据验证成功率双方均为 19/20（95%），没有观察到成功率差异。Kimodo seed1006 是物理抓取失败；ARDY seed1007 物理抓取成功，但因 frame coverage 不完整与 reference cursor stale 未通过正式证据验证。Kimodo/ARDY 中位端到端耗时分别为 162.68/182.75 秒，本次 Kimodo 低约 12.3%，主要差在生成阶段；由于实际使用不同 S4000 device ID 且共享负载未完全控制，耗时只作描述性比较。该结果只适用于固定 center 的冻结端到端 pipeline，不能外推为跨位置通用成功率。
