# 五组抓取与完整 episode 采集

这是受支撑的 IK + 力矩 PD 抓取基线：骨盆约束保留，尚未接 SONIC。
第三方源码和机器人资产不修改。成功数据也可能存在机器人碰桌，不能直接当作自由站立、无碰撞的训练集。

## 位置配置

只编辑 `configs/grasp_cases.json`，不要复制五份 XML 或手动调关节角度。

| 序号 | ID | x (m) | y (m) |
|---|---|---:|---:|
| 1 | center | 0.40 | -0.15 |
| 2 | near | 0.30 | -0.15 |
| 3 | far | 0.50 | -0.15 |
| 4 | left | 0.40 | 0.00 |
| 5 | right | 0.40 | -0.30 |

z 从桌面高度和方块半尺寸计算，当前为 0.785 m。位置单位是世界坐标米。
JSON 读取于启动时；编辑 JSON 后重新启动程序。范围检查防止方块初始放到桌外，但不保证任意桌面位置都可达。
当前零朝向五点经过验证；其他位置/旋转仍需试验，不能假定固定抓取姿态能泛化。

## GUI 与手动重置

在 g1-grasp 环境、项目根目录运行：

```bash
python scripts/pick_red_cube.py
```
这条命令打开第 1 组并自动执行、记录完整抓取；结束后暂停在末帧。

先点击 MuJoCo 画面使窗口获得键盘焦点，然后：

- `R`：完全重置并重新运行当前组。
- `N`：完全重置，切换到下一组并运行；第 5 组后回到第 1 组。
- `P`：上一组并运行。

重置会恢复机器人姿态、速度、控制器、外力、方块、计时和评估计数。
方块在重置时直接放到指定初始位置，不是让机器人拿着它移动到下一个位置。
运行中的方块始终由物理动力学控制，不改坐标搬运。
中途重置或关闭窗口时，未完成的数据进入 failure，标记为 interrupted/未完成；已保存的数据不会被覆盖。

```bash
python scripts/pick_red_cube.py --case far
```
这条命令直接进入 far 案例；也可用 `--case 3`。

```bash
python scripts/pick_red_cube.py --no-record
```
这条命令只调试 GUI 抓取，不保存图像和完整数据，运行更快。

`--preview` 只看场景，不推进物理；仍可用按键切换位置。GUI 默认使用 pick_red_cube.py 中的自由相机参数，保持机器人在前、桌子在后的后侧视角；截图使用 XML 的 task_overview，相机采集使用独立 head/wrist 相机。
默认单次仿真 11 秒。双相机采集可能比真实时间慢，仿真时间戳和数据对齐不受影响。

## 批量采集

```bash
python scripts/collect_episodes.py
```
这条命令按 JSON 顺序自动执行 5 组，每组 2 次，自动重置，保存成功和失败数据，不打开 GUI。

```bash
python scripts/collect_episodes.py --case center --repeats 1
```
这条命令只采集中心位置一次，适合验证配置。

默认目录是项目根目录的 `outputs/episodes/`。所有输出被 .gitignore 排除。
每轮批量采集有独立 run_id，每条 episode 有唯一 ID；不会覆盖已有数据。
两次重复没有随机扰动，主要验证复现性，不能当作两个不同位置或独立的数据分布样本。

## 文件结构

```text
outputs/episodes/
  manifest.jsonl                    # 每次尝试一行，成功/失败都记录
  runs/<run_id>/
    config.json
    provenance.json                # Git 版本、文件哈希、环境版本
    source/                        # 采集代码和场景快照，不复制 third_party
    summary.json
  success/<episode_id>/            # 完成并通过抓取判定
    metadata.json
    states.npz
    images.npz
    head_first.png, head_last.png
    wrist_first.png, wrist_last.png
    body_reference/
      joint_pos.csv, joint_vel.csv
      body_pos.csv, body_quat.csv
      hand_ref_q.csv, timestamps.csv
  failure/<episode_id>/            # 失败或中途终止，不导出成功 reference CSV
```

## 数据约定

包含 t=0 和 t=11 的端点，所以完整 episode 有 T=551 个状态、N=111 对图像。

| 字段 | 形状 | 含义 |
|---|---|---|
| body_q / body_dq | [T,29] | 实际本体关节位置、速度 |
| hand_q / hand_dq | [T,7] | 实际右手位置、速度 |
| body_ref_q / body_ref_dq | [T,29] | expert 本体参考位置、后处理参考速度 |
| hand_ref_q / hand_ref_dq | [T,7] | expert 右手参考位置、后处理参考速度 |
| timestamps | [T] | 从零开始的仿真秒，间隔 0.02 |
| root_pos / root_quat | [T,3] / [T,4] | 实际浮动基座位姿 |
| root_ref_pos / root_ref_quat | [T,3] / [T,4] | 独立保存的初始固定根部目标 |
| block_pos / block_quat | [T,3] / [T,4] | privileged 方块真值，不作为 VA 输入 |
| eef_pos / eef_quat | [T,3] / [T,4] | right_wrist_yaw_link 的世界位姿，不是指尖 |
| contact_thumb/index/middle | [T] | 对应手指与方块接触，bool |
| qpos / qvel / ctrl | [T,nq/nv/nu] | 完整仿真状态和实际下发力矩，供复查 |
| phase | [T] | 接近/下降/闭手/抬升/保持，编码在 metadata |
| action_valid | [T] | 最后一行 false：末帧没有后续执行区间 |
| success | scalar bool | 完成且通过成功判定 |

images.npz：head_rgb / wrist_rgb 为 [N,240,320,3] uint8 RGB，obs_indices 指向 states.npz 的行，image_timestamps 保存相同时间。
每 10 个物理步记录状态，每 50 个物理步记录图像；不使用墙钟定时采样。
状态和当前 expert reference 在同一物理步、积分之前记录。参考来自规划器，不是复制实际 q。
参考速度由 50 Hz reference 位置 np.gradient 后处理生成：内部中心差分、端点单边差分。它不是控制器单独使用的速度指令。

所有位姿为 MuJoCo 世界坐标；位置米，关节角弧度，四元数 wxyz。
关节按明确名称映射。本体顺序：左腿 6、右腿 6、腰 3、左臂 7、右臂 7。
右手顺序：thumb_0、thumb_1、thumb_2、index_0、index_1、middle_0、middle_1。
metadata 保存完整名字、qpos/qvel 地址、相机局部位姿、视场角、控制参数、源文件哈希等。

head_rgb 是固定在 torso_link 头部位置的虚拟相机，因为此模型没有独立 head body。
wrist_rgb 是刚性跟随右手腕、带偏移的虚拟相机。两者不是实际硬件标定参数。
隐藏碰撞网格的渲染以减少重复表面；物理碰撞仍保留。

## 成功、质量和训练

完整 episode 结束时，连续至少 2 秒满足：抬升 >=10 cm、拇指和另一个手指有接触、方块不接触桌面。
中途关闭/重置即使曾短暂抬起，也不进入成功集合。
success 中的数据可用于 supported baseline 的 positive BC pipeline，但需要查看 quality_flags。
`clean_bc_eligible` 只有成功且未检测到机器人碰桌时才为 true；当前数据可能为 false。
当前尚未检测所有禁止自碰撞、未验证位置泛化和长时间持物，不是最终课程评估协议。

CSV 无表头，行与 timestamps.csv 对齐。joint_pos/vel 是本体 reference，body_pos/quat 是 root reference，hand_ref_q 单独导出。
这些是明确命名顺序的中间参考格式；尚未验证 SONIC deployment 的输入协议，不能称为可直接导入 SONIC 的最终格式。

训练/验证应按位置或场景划分，不能把同一位置的确定性重复分别放到两边造成数据泄漏。

## 验证

```bash
python scripts/verify_episodes.py
```
这条命令检查保存数据的形状、时间对齐、关节映射、四元数、成功信号和 CSV 一致性。

```bash
python scripts/verify_resets.py
```
这条命令验证 5 组的完整重置不会带入上一轮速度、外力、控制器状态或计数。
