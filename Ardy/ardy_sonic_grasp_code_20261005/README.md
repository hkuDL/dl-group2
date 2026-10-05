# ARDY → SONIC → Dex3：主要代码说明

从开发机 `va-train` 容器复制的当前代码快照，共 13 个代码文件和 3 个场景 XML，保留两个仓库的相对目录结构。

本文件夹用于阅读、比较和归档。实际运行依赖完整上游仓库、MUSA 容器、模型权重、机器人网格资源和已经编译的 SONIC 手部播放版本。

## 目录

```text
GR00T-WholeBodyControl/
  gear_sonic/scripts/run_sim_loop.py
  gear_sonic/utils/mujoco_sim/configs.py
  gear_sonic/data/robot_model/model_data/g1/scene_43dof_blocks*.xml
  gear_sonic_deploy/reference/*.py
  gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/
  gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/src/
ardy/
  ardy/model/llm2vec/llm2vec.py
```

## 新增的接入和抓取脚本

以下文件位于 `GR00T-WholeBodyControl/gear_sonic_deploy/reference/`。

| 文件 | 作用 |
| --- | --- |
| `convert_ardy.py` | 将 ARDY 输出转换到 SONIC 的坐标系和关节顺序，重采样到 50 Hz，生成身体参考 CSV。 |
| `prepare_block_constraints.py` | 从场景和机器人几何制作 ARDY 约束：初始全身姿态、root 路径、右手伸出及抬起的位置、双脚与骨盆；支持 `--arms-at-sides`。IK 只制作条件姿态。 |
| `generate_hand_motion.py` | 根据抓握、释放等关键词，生成 Dex3 手指张开和闭合的规则命令，使用平滑过渡。 |
| `generate_ardy_with_hands.py` | 串联官方 ARDY 生成、身体转换和手指规则生成；使用本地权重，GPU 参数仅允许 4–7。 |
| `finish_block_motion.py` | 为本次抓取设置具体的手指目标与闭合时序，检查参考手位置误差；保留 ARDY 身体轨迹。 |
| `test_ardy_grasp.py` | 使用原 BaseSimulator 和现有 SONIC 控制器，关闭吊绳、设置初始站位、同步播放动作，记录实际物理状态和抓取指标。 |
| `render_ardy_grasp.py` | 将记录的机器人和物体状态渲染成 MP4，并导出初始、闭合及抬起时的截图。 |

## 修改的现有 SONIC / 仿真代码

以下路径相对于 `GR00T-WholeBodyControl/`。

| 文件 | 改动 |
| --- | --- |
| `gear_sonic/scripts/run_sim_loop.py` | 支持通过配置指定场景文件。 |
| `gear_sonic/utils/mujoco_sim/configs.py` | 增加可选 `scene_path` 配置。 |
| `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/motion_data_reader.hpp` | 增加可选的 `left_hand_pos.csv`、`right_hand_pos.csv` 读取，每只手每帧 7 个关节值。 |
| `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/src/g1_deploy_onnx_ref.cpp` | 使用身体参考的同一个播放帧号更新手指目标，通过现有 Dex3 控制接口发送。 |
| `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/keyboard_handler.hpp` | 增加手指开合快捷键：U/Y 为右手闭合/张开，K/M 为左手闭合/张开。 |

复制的是完整文件，以上列出的是我们增加的功能。在另一份完整仓库中应用 C++ 改动后，需要重新编译控制器；当前开发机已经具有编译好的版本。

## ARDY 文本编码器的本地加载

`ardy/ardy/model/llm2vec/llm2vec.py` 修复本地 MNTP adapter 的加载：显式读取 `adapter_config.json` 找到基模型，支持通过 `TEXT_ENCODERS_DIR` 解析相对路径，先合并 MNTP adapter，再加载 supervised adapter。

本地权重和离线环境变量配合使用，解决开发机无法连接 Hugging Face 时的加载问题。没有训练或修改 ARDY 身体生成模型。

## 三个场景文件

位于 `GR00T-WholeBodyControl/gear_sonic/data/robot_model/model_data/g1/`。

| 文件 | 木块初始坐标（米） | 用途 |
| --- | --- | --- |
| `scene_43dof_blocks.xml` | `(0.58, -0.12, 0.735)` | 原桌子和方块场景，作为参照。 |
| `scene_43dof_blocks_ardy.xml` | `(0.565, -0.13, 0.735)` | 第一版抓取，三次成功，抬升约 13 cm。 |
| `scene_43dof_blocks_ardy_sides.xml` | `(0.475, -0.177, 0.735)` | 双臂在身侧起步的新版，三次成功，抬升约 12.8 cm。 |

两个副本只改变木块初始坐标。机器人、桌子、红块、质量、摩擦和碰撞参数沿用原场景。场景的 include 文件和网格资源由完整仓库提供。

## 从身体动作到物理抓取

1. prompt 和场景约束交给 ARDY，生成伸手、停住、抬手的身体动作。
2. `convert_ardy.py` 生成 SONIC 身体参考；SONIC 跟踪动作并维持身体平衡。
3. 规则模块另外生成手指目标，因为 ARDY 的 G1 输出没有手指关节。
4. 控制器同步播放身体和手指命令，Dex3 通过 PD 控制闭合。
5. 按实际闭合位置摆放木块，通过 MuJoCo 接触和摩擦夹住、抬起。

目前是固定动作、固定摆放的演示。全程关闭吊绳，机器人基座自由，木块没有绑定到手上。

## 双臂在身体两侧起步

G1 模型的肘关节角为 0 时，前臂朝前。`--arms-at-sides` 将初始约束和仿真初始化中的两侧 elbow 设为 `1.4`，左/右 shoulder roll 设为 `0.15`/`-0.15` 弧度。肩部略向外张，让手与躯干留出间隙。新版约束还让左手在后续动作中保持在身侧。

动作数据已在开发机生成。下面的命令在容器内的完整 `GR00T-WholeBodyControl` 仓库根目录执行：

```bash
CUDA_VISIBLE_DEVICES=7 MUSA_VISIBLE_DEVICES=7 \
python gear_sonic_deploy/reference/test_ardy_grasp.py \
  --arms-at-sides --robot-x 0.24 --robot-y -0.03 --hand-kp 6 \
  --motion-dir gear_sonic_deploy/reference/ardy_grasp_sides \
  --scene gear_sonic/data/robot_model/model_data/g1/scene_43dof_blocks_ardy_sides.xml \
  --output-dir outputs/ardy_grasp/my_sides_run
```

身体和手指数据、视频及完整生成命令另有复现包，位于开发机个人工作目录下的 `ardy_sonic_grasp_reproduce/arms_at_sides/`。本文件夹专门保存上述代码和场景文件。
