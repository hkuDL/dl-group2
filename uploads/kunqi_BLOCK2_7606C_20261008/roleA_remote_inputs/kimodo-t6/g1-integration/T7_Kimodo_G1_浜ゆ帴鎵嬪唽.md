# T7 Kimodo G1：环境、合并与接手运行手册

更新时间：2026-10-06（Asia/Shanghai）。依据 Task6 运行手册、Amy 提供的服务器源码/日志和运行截图整理。

**当前结论：G1 动作生成已跑通；固定场景抓取尚未完成。目录合并脚本已准备，远端尚待执行。** 本文不能作为 manipulation 成功证明。

## 1. 服务器与容器

| 项目 | 地址 / 名称 |
|---|---|
| 服务器 / 容器主机名 | `10.123.0.38` / `worker00038` |
| Amy SSH 用户 / Docker 容器 | `mccxadmin` / `va-train` |
| GPU | 8 张 MTT S4000，各 48 GiB；上次生成使用 `musa:1`，运行前重新检查占用 |
| Python / PyTorch / torch_musa | 3.10 / 2.9.0 / 2.9.0+8432052 |
| Amy 虚拟环境 | `/workspace/group2/workspace/amy/kimodo-work/.venv` |
| Transformers / torchada | 虚拟环境 5.1.0 / 系统继承 0.1.90 |

保持连接服务器的 VPN，在本地 PowerShell 登录：

```powershell
ssh mccxadmin@10.123.0.38
```

宿主机中进入容器：

```bash
docker exec -it va-train bash
```

## 2. 重要目录与合并方式

```text
/workspace/group2/kimodo-t6/
├── kimodo-main/                  # Task6 原源码；保留
├── models/Kimodo-SOMA-RP-v1/     # Task6 SOMA；保留
├── kimodo-viser-main/            # 保留
├── soma-x/                      # 保留
├── test_walk.npz                # Task6 手册记录的结果
└── g1-integration/              # 执行本次脚本后创建
    ├── kimodo-upload/           # Amy 源码及现有 Git 信息
    ├── checkpoints/Kimodo-G1-RP-v1/
    ├── outputs/                 # 现有 NPZ、CSV
    ├── logs/                    # 现有日志与补丁备份
    ├── activate-g1.sh
    └── merge-manifest.json      # 全部复制文件 SHA256 + Git 状态
```

这是统一父目录下的 G1 集成副本，尚未将两套源码逐文件合成同一版本。两套模型和环境不同，覆盖 Task6 源码会丢失可复现的 baseline。复制不移动原文件、不升级依赖、不修改 Task6 已有目录；已有目标目录时立即停止。虚拟环境不搬迁：启动文件继续使用 Amy 原虚拟环境，通过 `PYTHONPATH` 加载新目录源码，故原 `.venv` 仍是依赖，不能删除。共享文本权重仍读取 `/workspace/group2/workspace/fuyuhan/ardy/text_encoders`，不改写。

## 3. 已确认的环境与测试结果

- `torch.musa.is_available()` 为 True；torchada 将 `cuda:0` 映射到 `musa:0` 的基础计算通过。
- 文本编码器改成底模 → MNTP → 合并 → supervised 的加载顺序；两套 adapter 分别核验 448 个张量。模型身份保留为 `meta-llama/Meta-Llama-3-8B-Instruct`。
- CPU 文本编码得到 `(1,1,4096)` 有限值 embedding。
- 官方 `nvidia/Kimodo-G1-RP-v1` 已下载、传入容器；包含 `config.yaml`、`model.safetensors`、`stats/`。此加载代码的 `CHECKPOINT_DIR` 指向 checkpoints 父目录。
- 单段 `A person raises the right hand.`、seed 0、单样本：2 秒/10 步生成 60 帧，5 秒/100 步生成 150 帧。两次均导出 NPZ、CSV。60 帧文件数值有限检查通过，CSV 为 `(60,36)`；150 帧文件已导出，尚无相同数值检查或可视化质量证据。
- 上述结果没有输入方块、初始站姿、手腕约束，也没有执行手指闭合或 SONIC 抓取回放。
- `lm_head.weight` 多余权重是使用编码 backbone 的加载差异；张量复制与注意力 dtype 警告未阻止此次导出。不能据此证明抓取质量。
- 两套 adapter 缺少 `llm2vec_config.json`，当前使用默认 mean pooling、最大长度 512、skip_instruction=True；与训练配置的完全一致性仍待核对。

## 4. 当前源码中的最小 MUSA 补丁

1. `kimodo/scripts/generate.py` 首先导入 torchada，随后 torch、torch_musa；从 `KIMODO_DEVICE` 读取设备，并检查 MUSA 可用。
2. `kimodo/model/llm2vec/llm2vec.py` 显式指定设备时走单进程分支。
3. adapter 目录读取真正本地 Llama 底模路径，保留用于格式化提示词的模型身份，验证 adapter 后按序加载和合并。

原目录分支记录为 `kimodo-musa-adaptation`，具体 commit 由合并时 manifest 记录。曾出现大量换行相关 Git 差异，不能将所有差异都当作本次功能修改；不 reset、不整体提交。保留全部备份。

## 5. 执行目录合并与验证

在本地 PowerShell 执行（脚本和手册已位于此目录）：

```powershell
Set-Location "D:\DASC7606C DL-ppt\course project"
scp -r .\handoff\kimodo-t7 mccxadmin@10.123.0.38:~/amy-t7-handoff
ssh mccxadmin@10.123.0.38
```

宿主机执行：

```bash
docker cp /home/mccxadmin/amy-t7-handoff va-train:/tmp/amy-t7-handoff
docker exec -it va-train bash
```

容器执行；复制前停止对 Amy 源目录写文件的生成任务：

```bash
python /tmp/amy-t7-handoff/merge_into_t6.py
source /workspace/group2/kimodo-t6/g1-integration/activate-g1.sh
python -c 'import kimodo; print(kimodo.__file__); assert kimodo.__file__.startswith("/workspace/group2/kimodo-t6/g1-integration/")'
python -m kimodo.scripts.generate --help
mthreads-gmi
```

只有打印 `MERGE FILES VERIFIED` 才表示文件复制与校验完成；导入检查通过才表示新源码路径接入。manifest 中 `execution_not_tested` 明确表示它不验证生成或抓取。若复制失败，暂存目录保留供检查，原目录保持不动。不要直接删除不明目录。

## 6. 固定场景、输入与成功标准

项目场景目录：`/workspace/group2/dl-group2`。事实来自 `configs/grasp_cases.json`、`configs/neutral_standing.json`、`scenes/tabletop.xml` 及提供的运行脚本。

| 项目 | 已确定 setting |
|---|---|
| 坐标 | MuJoCo 世界坐标，米，Z 向上；以下坐标均为该坐标系 |
| 机器人 | 根位置 XY=(0,0)，初始四元数 wxyz=(1,0,0,0)，朝向 +X；高度按足部碰撞几何求解，不硬编码 |
| 初始关节 | 肩 pitch=0.7，双肩向外 roll=0.45，肘=0.4，腕=0；膝=0.3，hip pitch 与 ankle pitch=-0.15 rad；14 手部关节=0，速度清零 |
| 桌面 | 高度 0.75 m，前缘 X=0.25 m |
| 方块 | 边长 0.07 m，质量 0.1 kg；中心 case=(0.40,-0.15,0.785)，yaw=0 |
| 其他 cases XY | near=(0.30,-0.15)，far=(0.50,-0.15)，left=(0.40,0)，right=(0.40,-0.30) |
| 测试 | 11 秒，状态 50 Hz，图像 10 Hz；每 case 重复 2 次，无随机化，用于检查重复性 |

物理成功需方块抬升至少 0.10 m、右拇指与食指或中指形成对向接触（力超过 1e-4 N）、方块脱离桌面，结束时连续保持至少 2 秒，机器人不倒地。不能用 NPZ 导出成功或腕部到达目标替代。

`run_sonic_grasp.py` 的最终 expert_valid 还要求 `metadata.source_success` 等来源证据。Kimodo 候选不能伪造这一字段；应增加独立 learned-candidate 评估入口，保留同样物理成功检查与辅助支撑检查，将来源证明和物理结果分别报告。

## 7. 对标 Task7 与下一步接手

[Task7 原始要求](https://github.com/hkuDL/dl-group2/issues/7)：接入 G1 环境、object/goal、坐标、轨迹、机器人执行、必要的 SONIC，并第一次完成 manipulation。完成标准是 Kimodo 在任务环境完成任务。

| 要求 | 当前状态 | 接手动作 |
|---|---|---|
| 模型部署 | G1 权重与生成通过 | 完成第 5 节合并及导入验证 |
| G1 环境 / object goal | 已定位 setting，未接入生成 | 从场景及 case 读取方块，固定 neutral 初始状态 |
| 坐标 | 需落实转换 | 世界 (x,y,z) → Kimodo (y,z,x)；同时转换姿态，不能只换位置 |
| 轨迹 | 只有抬手样例 | 生成 reach、grasp、lift、hold 的候选，记录每段文字、持续时间、目标和 seed |
| 执行 / SONIC | 未验证 | 适配参考格式、同步手指控制、无支撑回放 |
| 首次 manipulation | 未完成 | 输出物理评估报告与视频，确认成功再扩大到 5 cases×2 repeats |

推荐先做 center 一个 case：

1. 读取 scene 的 neutral 姿态，通过同一 G1 模型 FK 转成 Kimodo 首帧 fullbody 约束，加入根位置和朝向；不要用抬手样例首帧替代。
2. 从方块与掌部几何确定接近、抓取、抬升目标。手腕目标不能直接等于方块中心。读取本地 G1 `04_ee_constraint` 与 `03_full_body_keyframes` 的 JSON 格式、约束类和命令帮助后写约束；这些截图尚未包含完整末端类及 CLI，所以本文不虚构最终生成命令。
3. 第一轮每 seed 单样本，建议先固定 seed 0；失败后如调 prompt、约束或 seed，保留全部失败记录并记录尝试次数。2 次重复不是 best-of-N 选择。11 秒回放需与模型支持的分段时长对齐，可将最终保持单独作为适配阶段记录。
4. 把 Kimodo 输出按关节名称映射到 SONIC，30 Hz → 50 Hz；位置/角度插值、四元数 Slerp，使用部署 G1 XML 验证 FK。CSV 是根位置 3 + wxyz 4 + 身体关节 29；没有手指，需要额外 14 维开合轨迹。生成 candidate 所需时间戳、body q/dq、hand q/dq、root pos/quat 和 metadata。
5. `server-convert_ardy.py` 要求 NPZ 中 fps/text，当前 Kimodo NPZ 缺少，不能直接套用；同时其输出格式仍需转为项目 candidate 格式。转换脚本路径见下一节。
6. 为 learned candidate 提供如实评估入口后，再用 `python scripts/run_sonic_grasp.py --episode <已创建的episode目录> --candidate <候选目录名> --robot sonic --band off --startup-support none --pelvis-support none --run-name kimodo_center_seed0`。尖括号是尚需创建的实际路径，不可直接粘贴。SONIC 的进程与通信端口运行前需检查，避免干扰正在运行的实验。
7. 验证日志、contact/hold/lift/fall 指标及视频；只有完整成功报告才能标记 Task7 完成。

## 8. 交接所需四项信息与证据路径

1. **方块与机器人：** 第 6 节是确定场景；现有抬手结果未约束为该初始状态。
2. **prompt / 目标：** 现有两次生成均使用同一单段英文抬右手 prompt；没有额外手腕或手部目标。未来抓取段数和目标尚未定稿。
3. **结果 / 重试：** 现有每次 num_samples=1、seed=0；10 步和 100 步是两次不同配置测试，不是抓取成功重试。固定评测每 case 重复 2 次，不意味着允许挑选成功结果。
4. **机器与路径：** `worker00038` / `va-train`；原源码 `/workspace/group2/workspace/amy/kimodo-work/kimodo-upload`，原结果同父目录 `outputs/`。合并执行后源码为 `/workspace/group2/kimodo-t6/g1-integration/kimodo-upload`，结果为 `/workspace/group2/kimodo-t6/g1-integration/outputs`，日志为 `.../logs`。原虚拟环境仍使用原路径。

结果：`g1_smoke_right_hand.{npz,csv}`、`g1_right_hand_100steps.{npz,csv}`。证据：`text-encoder-fixed.log`、`g1-smoke-right-hand.log`、`g1-right-hand-100steps.log`。提供的服务器脚本在日志副本中保留，供比较，不代表已修改部署评估器。

SONIC runner：`/workspace/group2/dl-group2/scripts/run_sonic_grasp.py`；参考生成：`.../scripts/expert_trajectory.py`；ARDY 转换：`/workspace/group2/workspace/fuyuhan/GR00T-WholeBodyControl/gear_sonic_deploy/reference/convert_ardy.py`。

不升级核心依赖，不覆盖 Task6 SOMA 或 soma-x，不修改共享权重，不将生成成功记为抓取成功，不修改来源字段来绕过评估。
