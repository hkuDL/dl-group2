# G1 桌面场景

## Quickstart：从安装 conda 到跑出画面

按下面的顺序走一遍即可。命令以 **Linux（含 WSL）** 为准，Windows 有差异的地方单独标注。

### 0. 环境版本

| Component       | Version                            |
| --------------- | ---------------------------------- |
| Python          | **3.9**                            |
| Conda           | ≥ 25.5.1（实测 26.7.1 可用）       |
| MuJoCo Python   | 3.3.2                              |
| Unitree G1 模型 | third_party，用 git submodule 拉取 |

### 1. 安装 Miniconda（已装 conda 可跳过）

Linux / WSL：

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

Windows：下载并运行 `Miniconda3-latest-Windows-x86_64.exe`
（`https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe`），
之后建议统一用开始菜单里的 **Anaconda Prompt** 打开终端。

安装完成后**关闭当前终端再重新打开**，conda 才会生效。验证：

```bash
conda --version
```

预期输出：`conda 26.7.1`（版本号 ≥ 25.x 即可）。

### 2. 创建并激活 Conda 环境

```bash
conda create -n robot-g1 python=3.9
conda activate robot-g1
```

`robot-g1` 只是示例环境名，可以换成任意名字。
**每开一个新终端都要先 `conda activate` 一次。**

> Windows 的 PowerShell 如果报「conda 不是可识别的命令」，先执行 `conda init powershell` 再重开终端。

### 3. 安装 MuJoCo

```bash
pip install mujoco
```

pip 装不上时改用 conda：

```bash
conda install -c conda-forge mujoco
```

验证：

```bash
python -c "import mujoco; print(mujoco.__version__)"
```

预期输出：`3.3.2`。

### 4. 拉取 G1 模型（third_party 子模块）

在**仓库根目录**执行：

```bash
git clone git@github.com:hkuDL/dl-group2.git dl-group2
cd dl-group2
git submodule update --init --recursive
```

预期输出：third_party/GR00T-WholeBodyControl 被检出到本项目指定的 commit `b042411...`。
**不要**手改 third_party 里的任何文件，也不要动这个 commit。

### 5. 先验证再跑

```bash
python scripts/pick_red_cube.py --check
```

预期输出：

```
G1: nq=57, nv=55, nu=43
SUPPORTED PHYSICS: pelvis welded to world; IK + PD; no SONIC; cube has no attachment.
```

这两行出现就说明完整场景能加载。这一步**不弹窗口**，适合先确认环境没问题。

### 6. 运行

```bash
python scripts/pick_red_cube.py
```

预期输出：

```
G1: nq=57, nv=55, nu=43
SUPPORTED PHYSICS: pelvis welded to world; IK + PD; no SONIC; cube has no attachment.
CASE 1/5: center xy=[0.4, -0.15]
GUI_OPENED | R: reset current | N/P: next/previous
 0.00s reach
```

随后弹出 MuJoCo 窗口，机械臂按 0–2 s 接近、2–4 s 下降、4–6 s 闭手、6–8 s 抬升、8–11 s 保持
的节奏抓取桌面红方块，11 秒后停在结束姿态。

#### GUI 里的按键

| 按键 | 全称 | 作用 |
| ---- | ---- | ---- |
| `R` | **Reset** | 重跑当前位置：回到这一组位置的标准初始状态，重新来一次 |
| `N` | **Next** | 切到 5 个位置里的**下一组** |
| `P` | **Previous** | 切回**上一组** |

5 组位置定义在 `configs/grasp_cases.json`（`center` / `near` / `far` / `left` / `right`），
按 N 或 P 到头会**循环**回去。每次切换会把刚跑完那一轮存进
`outputs/episodes/success/` 或 `outputs/episodes/failure/`，所以会有约 0.6 秒的写盘停顿。

> MuJoCo 界面自带的 **Reset 按钮**也可以用。脚本检测到仿真时间被重置后会自动重跑当前位置，
> 方块会回到当前 case 规定的位置，而不是 MuJoCo 模型里的默认位置。

#### 不弹窗口的跑法

```bash
python scripts/pick_red_cube.py --headless --report grasp_report.json
```

直接跑完整个物理动作并输出指标 JSON；未满足抓取成功判定时返回非零状态。
服务器、纯终端、没有图形界面的 WSL 用这个。

### 7. 结果存在哪里

每一轮跑完（以及按 `R`/`N`/`P` 切换时）都会把刚结束的那一轮存进 `outputs/`。
**整个 `outputs/` 已被 .gitignore 排除，不会进仓库、不会提交。**

```text
outputs/episodes/
├── manifest.jsonl                 # 每跑完一条追加一行，一行一条 episode
├── runs/<run_id>/                 # 每轮批量采集的运行标记
├── success/<episode_id>/
│   ├── states.npz                 # 50 Hz 关节/手部/根/方块状态、参考轨迹、控制信号
│   ├── images.npz                 # 10 Hz head / wrist RGB
│   ├── metadata.json              # case、配置、成功判定、相机内参、脚本与模型的 sha256
│   ├── body_reference/            # 仅成功时导出：joint_pos / joint_vel / body_pos /
│   │                              #   body_quat / hand_ref_q / timestamps 的 CSV
│   └── head_first.png  head_last.png  wrist_first.png  wrist_last.png
└── failure/<episode_id>/          # 同上，但没有 body_reference/
```

- `<episode_id>` 形如 `20261001T040858023991Z_center_r1_09e66b`
  = `时间戳_位置ID_第几次_随机后缀`，天然唯一，不会覆盖已有数据。
- 满足成功判定的进 `success/`，没满足的进 `failure/`。
- **中途按 `R`/`N`/`P` 或直接关窗口**：未跑完的也存进 `failure/`，
  `completed=false`、`failure_reason` 标记为 interrupted/未完成；已存好的数据不会被覆盖。
- `_pending/` 是写盘过程中的临时目录，写完才原子改名到最终位置，因此不会留下半截数据。
- `manifest.jsonl` 每行是一条 episode，主要字段：
  `episode_id`、`path`、`case_id`、`success`、`max_lift_m`、
  `max_continuous_grasp_hold_seconds`、`failure_reason`、`robot_table_contact_steps`。
- **体积参考**：单条 `images.npz` 最大约 4.6 MB，跑满几批后 `outputs/` 会到几百 MB，
  建议定期清理，或把 `--output` 指向别处。

常用的输出相关开关：

| 目的 | 命令 |
| --- | --- |
| 换输出目录 | `python scripts/pick_red_cube.py --output outputs/my_run` |
| 只调 GUI、不存盘 | `python scripts/pick_red_cube.py --no-record` |
| 不开 GUI 跑一批 | `python scripts/collect_episodes.py`（5 组 × 每组 2 次，自动重置） |
| 只采某一组一次 | `python scripts/collect_episodes.py --case center --repeats 1` |

采集参数由 `configs/grasp_cases.json` 控制：`state_hz=50`、`image_hz=10`、
图像 320×240、单次仿真 11 秒、每组默认重复 2 次。

### Windows 差异速查

| 步骤 | Linux / WSL | Windows |
| ---- | ----------- | ------- |
| 装 conda | `.sh` 脚本，`bash xxx.sh` | `.exe` 安装器 |
| 打开终端 | 任意终端，重装后重开即可 | 推荐 Anaconda Prompt；PowerShell 需先 `conda init powershell` |
| 激活环境 | `conda activate g1-grasp` | 完全相同 |
| 装 MuJoCo | `pip install mujoco` | 完全相同 |
| 拉子模块 | `git submodule update --init --recursive` | 完全相同 |
| 运行 | `python scripts/pick_red_cube.py` | 完全相同 |
| 弹 GUI | WSL 需要 WSLg（Win11 自带）；没有就用 `--headless` | 原生窗口，直接弹出 |

路径分隔符 Windows 用 `\`，但上面命令里的 `/` 也能正常运行。

### 8. 整体结构

```text
dl-group2/
├── README.md                    课题说明与任务分解（T1–T12）
├── AGENTS.md                    项目硬约束：third_party 只读、GUI 相机参数不可改
├── .gitignore                   忽略 outputs/ 与临时文件
├── .gitmodules                  声明 third_party 子模块
├── configs/
│   └── grasp_cases.json         5 组位置、采集频率、单次仿真时长
├── scenes/
│   ├── README.md                本文件：Quickstart + 场景说明
│   ├── EPISODES.md              episode 数据格式与批量采集
│   └── tabletop.xml             只含地面 / 桌子 / 红方块 / 灯光 / 相机
├── scripts/
│   ├── pick_red_cube.py         主入口：GUI / headless / preview / check
│   ├── collect_episodes.py      批量采集，不开 GUI
│   ├── record_episode.py        50 Hz 状态 + 10 Hz 双目采集与写盘
│   ├── grasp.py                 IK + 力矩 PD 抓取控制器
│   ├── scene.py                 在内存里合并上游 G1 与 tabletop.xml
│   ├── cases.py                 读 case，并按 case 做确定性 reset
│   └── verify_*.py              校验 episodes / reset / grasp
├── models/
│   ├── README.md                conda、MuJoCo、G1 模型的安装步骤
│   └── g1/                      G1 29-DoF + 手的 MJCF 与 STL 网格
├── playground/                  早期草稿场景，保留未用
├── third_party/
│   └── GR00T-WholeBodyControl/  子模块：git 只存 commit 指针，内容不进仓库
└── outputs/                     运行产物，已整体被 .gitignore 排除
    ├── episodes/                正式采集结果（success / failure / manifest.jsonl）
    ├── validation_episodes/     旧版遗留，当前脚本不再写入
    └── validation_gui/          旧版遗留，当前脚本不再写入
```

数据流：

```text
third_party G1 XML ┐
scenes/tabletop.xml ┴─► scripts/scene.py ──► 完整场景（内存拼接，不改上游）
configs/grasp_cases.json ─────► scripts/cases.py ──► 方块初始位置
                                        │
                                        ▼
                          scripts/pick_red_cube.py        ← GUI 里用 R / N / P 控制
                                        │  scripts/grasp.py：IK + 力矩 PD
                                        ▼
                          scripts/record_episode.py
                                        ▼
                          outputs/episodes/{success,failure}/<episode_id>/
```

五组 JSON 位置、GUI 重置按键和完整 episode 数据格式见 [EPISODES.md](EPISODES.md)。

`tabletop.xml` 只定义我们自己的地面、桌子、红方块、灯光和相机。
`../scripts/scene.py` 从 third_party 读取 pnp_cube_43dof 使用的
`g1_29dof_with_hand_rev_1_0_activatedfinger.xml`，在内存中合并场景并解析 mesh 的绝对路径。
不复制 STL，不修改上游，不依赖启动时的工作目录。此 XML 是环境片段，请通过脚本加载完整场景。



## 物理抓取基线

`scripts/grasp.py` 使用腰部和右臂的逆运动学规划，以及力矩 PD + bias compensation。
轨迹是手写的固定任务：0–2 秒接近并旋转手掌，2–4 秒下降，4–6 秒闭手，6–8 秒抬升，8–11 秒保持。
这不是自然语言模型；也还没有接 ARDY、Kimodo 或 SONIC。

默认运行会在内存中添加 `debug_pelvis_support` 焊接约束，暂时把骨盆支撑在世界坐标系。
该约束只用于分离站立与抓取问题，不修改 third_party XML。重力、手指碰撞和方块自由关节均保留。
方块没有绑定到手上，没有通过改写方块 qpos、施加外力或隐藏约束搬运。

当前名义场景实测：最大抬升约 0.136 m，11 秒时抬升约 0.125 m，连续有效夹持约 3.6 秒。
成功标准：比初始中心高度高至少 0.10 m，拇指和至少另一根手指均接触方块、方块不接触桌面，连续保持至少 2 秒。
日志另外记录机器人碰桌情况。当前拇指末节会短暂接触桌面约 1.08 秒，因此这不是无碰撞规划的最终实验结果。
抓取参数针对当前桌面和 7 cm 方块调试。JSON 中 5 个邻近位置已做初步测试；仍不能把结果推广到任意位置或长时间持物。
下一步是消除接近阶段的桌面接触、接 SONIC 验证自由站立和全身动作。

```bash
python scripts/pick_red_cube.py --headless --report grasp_report.json
```
这条命令无需 GUI 跑完整物理动作并输出指标；未满足抓取成功判定时返回非零状态。

```bash
python scripts/pick_red_cube.py --preview
```
这条命令只看原来的暂停场景，不添加骨盆支撑、不推进物理。

`--render output.png` 可保存动作末帧；加 `--preview` 则保存初始场景。
`--duration` 设置仿真总时长；`--seconds` 可设置 GUI 测试的最长墙钟时间。

## 模型选择依据

本地 g1-grasp / MuJoCo 3.3.2 已成功编译上游 pnp_cube_43dof.xml，nq=57、nv=55、nu=43。
43 个执行器是 29 个本体关节加 14 个手指关节；另有机器人与方块两个自由关节。
我们复用它引用的机器人，而不 include 整个 pnp 场景，避免重复桌子、方块与地面。
这是当前带手桌面场景的基础，并不代表 SONIC 兼容性已完成验证。

models/g1/g1.xml 与 gear_sonic_deploy/g1/g1_29dof.xml 的 29 个本体关节顺序、范围相同，
但前者是位置执行器，后者是力矩执行器，body 质量也不完全相同，不能直接互换。
带手模型的手指关节穿插在本体关节序列中；之后接 SONIC 必须按关节名称映射，不能取前 29 项。
后续还需核对 SONIC 的惯量、控制增益、初始姿态、观测和动作映射并完成物理运行验证。

旧 playground 和 models 文件保持原状；新入口使用 scenes/ 与 scripts/。
