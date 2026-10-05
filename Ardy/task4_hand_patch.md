# Task 4：通过一个 prompt 播放 ARDY 身体动作和 Dex3 抓取手势

当前实现可以用一个英文 prompt 生成身体动作和配套的手指轨迹，在 SONIC + MuJoCo 中同步播放。例如，机器人伸出右臂后，右手逐渐闭合。

身体动作由 ARDY 生成；手指动作由新增脚本根据关键词和预设姿态生成。当前没有训练 ARDY 的手指生成能力，也没有根据木块的位置规划抓取。目标是先看到伸手、握合、张开的动作，不要求真正抓住木块。

## 1. 环境与目录

使用远程开发机现有的 `va-train` 容器。以下运行步骤都在容器中执行，只有连接主机、切换用户和进入容器这一步在宿主机执行。

```bash
# 本机终端：连接远程主机
ssh group2@10.123.0.38

# 远程宿主机：切换用户并进入容器
su - mccxadmin
docker exec -it va-train /bin/bash
```

在每个容器终端中设置路径。将 `<个人目录>` 替换为实际目录；两个仓库应位于同一个父目录下：

```bash
WORKSPACE="/workspace/group2/workspace/<个人目录>"
SONIC_ROOT="$WORKSPACE/GR00T-WholeBodyControl"
ARDY_ROOT="$WORKSPACE/ardy"
cd "$SONIC_ROOT"
```

使用已经配置好的环境：

- ARDY 的 G1 checkpoint，以及本地 Llama、MNTP 和 supervised adapter。
- MUSA 版 SONIC 控制器、encoder/decoder 模型和 observation 配置。
- 已有的 `scene_43dof_blocks.xml` 木块场景。
- 已有显示环境 `DISPLAY=:1`，用于查看 MuJoCo 窗口。

本补丁没有安装新的依赖或修改公共环境。ARDY 生成默认使用第 7 张卡，可以选择 4～7；下面的 SONIC 播放示例使用第 4 张卡。

## 2. 从 prompt 生成身体和手指动作

在容器终端中执行：

```bash
cd "$SONIC_ROOT"

python gear_sonic_deploy/reference/generate_ardy_with_hands.py \
  "A person reaches out with the right hand and grasps a block." \
  --duration 5 \
  --seed 0 \
  --gpu 7 \
  --output-dir gear_sonic_deploy/reference/prompt_hands/grasp_block
```

这个入口依次执行：

1. 调用 ARDY 的 `scripts/generate.py`，生成 G1 身体动作。
2. 调用已有的 `convert_ardy.py`，将身体动作转换成 SONIC 的 50 FPS 参考数据。
3. 根据同一个 prompt 生成左右手各 7 个关节的轨迹。
4. 将全部文件写入指定动作目录。

脚本默认使用相邻的 `../ardy` 仓库和其中的 `checkpoints/`、`text_encoders/`。它只在 ARDY 子进程中设置 GPU、本地文本编码器和 Hugging Face 离线环境变量，不修改当前终端的全局配置。

结果目录：

```text
gear_sonic_deploy/reference/prompt_hands/grasp_block/
├── ardy_motion.npz          # ARDY 原始动作
├── ardy_motion.csv          # ARDY 原始 MuJoCo qpos
├── joint_pos.csv            # SONIC 身体参考：29 个关节
├── joint_vel.csv
├── body_pos.csv
├── body_quat.csv
├── body_lin_vel.csv
├── body_ang_vel.csv
├── left_hand_pos.csv        # 新增：左手 7 个关节
├── right_hand_pos.csv       # 新增：右手 7 个关节
├── hand_plan.json           # prompt、手部规则和时间安排
├── metadata.txt
└── info.txt
```

本次已经生成了上述 `grasp_block` 示例。只想查看现有结果时，可以直接进入第 3 节，不必重新生成。

## 3. 在仿真中播放

需要两个容器终端。每个终端都先设置第 1 节的路径变量。

### 终端 A：启动木块场景

```bash
cd "$SONIC_ROOT"

DISPLAY=:1 python gear_sonic/scripts/run_sim_loop.py \
  --interface lo \
  --scene-path gear_sonic/data/robot_model/model_data/g1/scene_43dof_blocks.xml
```

MuJoCo 窗口显示在远程的 `:1` 显示环境中，通过已有的远程画面访问方式查看。`run_sim_loop.py` 负责物理仿真、状态反馈和接收电机命令。

场景已经包含 G1 的 Dex3 三指灵巧手：身体 29 个关节，加上左右手各 7 个关节，共 43 个关节，无须另换手模型。

### 终端 B：启动 SONIC 控制器

```bash
cd "$SONIC_ROOT/gear_sonic_deploy"

MUSA_VISIBLE_DEVICES=4 CUDA_VISIBLE_DEVICES=4 \
./target/release/g1_deploy_onnx_ref \
  lo \
  policy/release/model_decoder.onnx \
  reference/prompt_hands/ \
  --obs-config policy/release/observation_config.yaml \
  --encoder-file policy/release/model_encoder.onnx \
  --input-type keyboard \
  --policy-precision 32 \
  --disable-crc-check
```

控制器读取的是动作集合的父目录 `reference/prompt_hands/`，不是单个 `grasp_block/` 子目录。加载成功时会看到：

```text
Loaded grasp_block (250 timesteps)
Dex3 hand trajectories enabled
```

等待 `Init Done`，然后在**控制器终端 B**按键，不需要回车：

| 按键 | 作用 |
|---|---|
| `]` | 启动控制 |
| `t` | 播放动作，身体和手指同步推进 |
| `r` | 回到第 0 帧并暂停；本例的手指也回到张开目标 |
| `n` / `p` | 有多个动作时切换动作 |
| `o` | 停止控制并退出控制器 |

本例总长 5 秒：前 2 秒手指保持张开，第 2～3 秒逐渐闭合，之后保持握合。手指会自动播放，无须按 `u/y`。

更新动作 CSV 或重新编译代码后，需要重启控制器，才能加载新数据或新程序。仿真终端可以继续保留；退出仿真使用终端 A 的 `Ctrl+C`。

## 4. 修改手部动作

### 4.1 关键词与左右手

当前是简单英文规则，不使用额外的语言模型理解 prompt：

| 描述 | 手指轨迹 |
|---|---|
| `grasp`、`grab`、`grip`、`hold`、`pick up` | 张开 → 平滑闭合 → 保持 |
| `release`、`let go`、`open right hand` 等 | 初始闭合 → 平滑张开 |
| 同时包含抓取和释放描述 | 先闭合，再在动作末段张开 |
| 没有识别到手部动作关键词 | 双手保持张开 |

描述中包含 `left`、`right` 或 `both` 时选择对应手；未指定时默认右手。也可以用 `--hand left`、`--hand right` 或 `--hand both` 明确覆盖选择。

复杂否定、多个不同手部动作的叙述和中文 prompt 不在这版规则的支持范围内。建议使用明确的英文动作描述。

### 4.2 调整闭合时间

默认闭合开始和结束时间为总时长的 40% 和 60%。可以在生成入口上添加参数：

```text
--close-start 1.5 --close-end 2.5
```

单位是秒。对于同时包含抓取和释放的描述，默认在总时长的 80%～95% 之间释放。

已经转换好的身体动作，可以只重新生成手指文件：

```bash
cd "$SONIC_ROOT"

python gear_sonic_deploy/reference/generate_hand_motion.py \
  "A person grasps a block with the right hand." \
  --output-dir gear_sonic_deploy/reference/prompt_hands/grasp_block \
  --close-start 1.5 \
  --close-end 2.5
```

这不会重新运行 ARDY。修改后重启控制器。

### 4.3 复用已有 ARDY 动作

```bash
cd "$SONIC_ROOT"

python gear_sonic_deploy/reference/generate_ardy_with_hands.py \
  "A person reaches out with the right hand and grasps a block." \
  --input-npz gear_sonic_deploy/reference/prompt_hands/grasp_block/ardy_motion.npz \
  --output-dir gear_sonic_deploy/reference/prompt_hands/grasp_block
```

`--input-npz` 跳过身体生成，重新转换指定的身体动作，并根据本次 prompt 编排手指。换成其他现有 `.npz` 路径也可以；此时 prompt 不会改变已有的身体动作。

## 5. 代码具体做了什么

所有路径以下面的仓库根目录为基准：`GR00T-WholeBodyControl/`。

| 文件 | 修改内容 |
|---|---|
| `gear_sonic_deploy/reference/generate_ardy_with_hands.py` | 新增统一入口，串联 ARDY 生成、身体格式转换和手指轨迹生成 |
| `gear_sonic_deploy/reference/generate_hand_motion.py` | 新增关键词规则、左右手选择、平滑轨迹和 CSV/JSON 输出 |
| `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/motion_data_reader.hpp` | 为 `MotionSequence` 增加可选手部数组，并读取两个手部 CSV |
| `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/src/g1_deploy_onnx_ref.cpp` | 按当前身体动作帧读取手指目标，交给现有 `Dex3Hands` |
| `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/keyboard_handler.hpp` | 前一步已加入的左右手张开、闭合键盘控制，继续保留 |
| `gear_sonic_deploy/reference/README_prompt_hands.md` | 新增运行及参数说明 |

已有的 `convert_ardy.py` 继续负责身体数据转换。本次没有修改 ARDY 模型权重、仿真手指 PD 或 DDS 通信实现。

### 5.1 手指预设与插值

每只手的关节顺序与现有模型、SDK 一致：

```text
thumb_0, thumb_1, thumb_2, middle_0, middle_1, index_0, index_1
```

目标角度单位为弧度：

```python
open_pose = [0, 0, 0, 0, 0, 0, 0]
left_closed = [0, 0.2, 1.0, -0.9, -1.0, -0.9, -1.0]
right_closed = [0, -0.2, -1.0, 0.9, 1.0, 0.9, 1.0]
```

闭合时采用平滑插值：

```python
p = clip((t - start) / (end - start), 0, 1)
amount = p * p * (3 - 2 * p)
q = amount * closed_pose
```

生成器读取身体 `joint_pos.csv` 的实际帧数，按 50 FPS 生成相同帧数的左右手数据。每个手部 CSV 第一行为表头，随后每行包含 7 个角度，不额外增加时间或帧号列。

### 5.2 加载与同步播放

`MotionSequence` 新增左右手姿态数组，以及 `HasHandPositions()`、`HandPositions()` 访问方法。读取器会检查存在的手部文件是否匹配身体帧数，以及每帧是否对应一个 7 关节姿态；不匹配时跳过该动作。

控制循环使用当前动作的同一个帧号读取身体和手指：

```cpp
if (current_motion_copy->HasHandPositions(true)) {
    left_hand_joint_buffer_ =
        current_motion_copy->HandPositions(current_frame_copy, true);
}
if (current_motion_copy->HasHandPositions(false)) {
    right_hand_joint_buffer_ =
        current_motion_copy->HandPositions(current_frame_copy, false);
}
```

随后复用原有链路：

```text
手指目标角度
    → Dex3Hands::setAllJointsCommand()
    → Dex3Hands::writeOnce()
    → rt/dex3/left/cmd、rt/dex3/right/cmd
    → unitree_sdk2py_bridge.py
    → base_sim.py 的手指 PD 力矩控制
    → MuJoCo 手指运动与状态反馈
```

存在某侧手部 CSV 时，该侧以 CSV 目标为准，键盘姿态不会覆盖它。没有相应 CSV 的旧动作继续使用键盘控制：`u/y` 为右手闭合/张开，`k/m` 为左手闭合/张开。

### 5.3 重新编译

本次已重新编译 MUSA 控制器。以后修改 C++ 代码时，在容器中执行：

```bash
cd "$SONIC_ROOT"
cmake --build gear_sonic_deploy/build-musa \
  --target g1_deploy_onnx_ref -j4
```

可执行文件仍位于 `gear_sonic_deploy/target/release/g1_deploy_onnx_ref`。

## 6. 验证结果与当前边界

已在远程容器中完成：

- 使用本地 ARDY/Llama 权重，从示例 prompt 完整生成 5 秒动作。
- 检查右手、左手、双手、释放、抓取后释放和无抓取描述的规则。
- 检查左右手 CSV 为 250×7，插值平滑，并可覆盖闭合时间。
- 编译并验证 C++ 读取器加载新轨迹，同时兼容不带手部文件的旧动作。
- 在 MuJoCo 与 MUSA 控制器中自动播放，并执行重播归零。

播放记录共 450 帧：控制器手指目标与生成 CSV 的最大误差为 0；`right_hand_thumb_2_joint` 实际角度达到约 0.956 弧度，重播后回到约 0.000065 弧度；左手目标保持张开。

验证日志保存在远程仓库的 `outputs/hand_control_check/`，其中 `prompt_verification.json` 为结果摘要，`prompt_playback/` 为动作目标和实际关节反馈。本次测试进程已停止。

当前闭合时间是预设，不会自动识别 ARDY 伸手的完成时刻，也不感知木块位置。如果手指闭合过早或过晚，先调整 `--close-start` 和 `--close-end`。这版实现的是同步抓取手势，物理抓住并抬起木块仍需要进一步处理手掌位置、接触和抓取稳定性。
