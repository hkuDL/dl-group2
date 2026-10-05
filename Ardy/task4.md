# Task 4：ARDY 动作接入 SONIC，并在 G1 仿真中回放

本文说明如何把一句文字描述生成的 ARDY 动作，转换为 SONIC 的参考动作，再让 MuJoCo 中的 G1 机器人执行。示例统一使用“沿圆圈行走”。

流程：**文字 prompt → ARDY `.npz/.csv` → SONIC 参考目录 → SONIC 身体控制器 → MuJoCo 仿真**。

本流程验证身体动作回放。场景中的桌子和木块是物理对象；抓取还需要另外的手指控制和接触规划。

## 1. 环境与目录约定

以下软件和资源应当已经准备好：

- 远程开发机 `10.123.0.38`，以及 `va-train` 容器。
- 同一个个人工作目录中的 `ardy` 和 `GR00T-WholeBodyControl` 两个仓库。
- ARDY 所需依赖、本地 G1 checkpoint、本地 Llama/LLM2Vec 文本编码器，以及对应的本地加载配置。
- 已编译好的 MUSA 版 SONIC 控制器、发布的 encoder/decoder ONNX 和 observation 配置。
- 已创建的 `scene_43dof_blocks.xml`；显示服务 `:1` 对应 VNC 端口 `5901`。

本文沿用已有环境，不包含安装依赖、下载权重或编译步骤。我们组使用物理卡 **4–7**，下文统一使用卡 **4**。

宿主机和容器内的路径前缀不同：

| 所在位置 | 个人工作目录 |
|---|---|
| 宿主机 | `/home/group2/workspace/<个人目录>` |
| 容器内 | `/workspace/group2/workspace/<个人目录>` |

下面用 `devuser` 作为目录名示例，执行前替换为自己的目录名。后续所有 Python 和 SONIC 命令均在**容器内**运行。

## 2. 登录开发机，进入容器

在本机终端执行：

```bash
ssh group2@10.123.0.38
```

在远程宿主机上切换账户并进入容器：

```bash
su - mccxadmin
docker ps --format 'table {{.Names}}\t{{.Image}}'
docker exec -it va-train /bin/bash
```

输入管理员提供的密码。账户名是 `mccxadmin`；使用容器名称，避免依赖可能变化的容器 ID。

进入容器后设置路径：

```bash
WORKSPACE=/workspace/group2/workspace/devuser
ARDY_ROOT="$WORKSPACE/ardy"
SONIC_ROOT="$WORKSPACE/GR00T-WholeBodyControl"
```

这些变量只在当前终端有效。后面新开终端时，也需要先进入容器并设置相同变量。

## 3. 使用 ARDY 生成 G1 动作

在容器终端中执行：

```bash
cd "$ARDY_ROOT"
export MUSA_VISIBLE_DEVICES=4
export CUDA_VISIBLE_DEVICES=4
export TEXT_ENCODERS_DIR="$ARDY_ROOT/text_encoders"
export TEXT_ENCODER_MODE=local
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

python scripts/generate.py "A person walks in a circle." \
  --model g1 \
  --checkpoints_dir ./checkpoints \
  --duration 5 \
  --seed 0 \
  --output baseline_walk_circle
```

参数含义：

| 参数或变量 | 含义 |
|---|---|
| prompt | 希望生成的动作文字描述 |
| `--model g1` | 选择 Unitree G1 骨架模型 |
| `--checkpoints_dir` | 本地 checkpoint 的父目录；当前包含 `ARDY-G1-RP-25FPS-Horizon52` |
| `--duration 5` | 生成约 5 秒动作 |
| `--seed 0` | 指定随机种子，便于复现 |
| `--output baseline_walk_circle` | 输出文件名，不带扩展名；这种裸文件名会写到 `outputs/` |
| `TEXT_ENCODER_MODE=local` | 在本地加载文本编码器 |
| `TEXT_ENCODERS_DIR` | 本地 Llama/LLM2Vec 模型所在目录 |
| 两个 `OFFLINE=1` 变量 | 禁止访问 Hugging Face；所需模型必须已经完整下载并配置好 |

程序显示的 `cuda:0` 是进程内设备编号，应结合可见设备变量判断所用物理卡。

生成后应得到：

```text
ardy/outputs/baseline_walk_circle.npz
ardy/outputs/baseline_walk_circle.csv
```

`.npz` 保存 ARDY 的骨架动作、根部位置、帧率等信息。G1 的 `.csv` 保存 MuJoCo qpos，每帧 36 列：根部位置 3 列、四元数 4 列、身体关节角度 29 列。

原来的 `run_generate.txt` 在个人工作目录下，可以作为命令参考；本文已经列出完整命令，无需依赖复制该文件。

## 4. 转换为 SONIC 参考动作

生成完成后，在同一个容器终端执行：

```bash
cd "$SONIC_ROOT"
python gear_sonic_deploy/reference/convert_ardy.py \
  "$ARDY_ROOT/outputs/baseline_walk_circle.npz" \
  --output-dir gear_sonic_deploy/reference/ardy/walk_circle
```

转换脚本将 G1 动作重采样为 SONIC 使用的 **50 Hz**，调整关节顺序，并计算身体部位的位置、旋转和速度。输入旁边存在同名 `.csv` 时，会优先复用它；没有时，使用 ARDY 的官方转换器在 CPU 上计算 qpos。

输出目录如下：

```text
GR00T-WholeBodyControl/gear_sonic_deploy/reference/ardy/
└── walk_circle/
    ├── joint_pos.csv
    ├── joint_vel.csv
    ├── body_pos.csv
    ├── body_quat.csv
    ├── body_lin_vel.csv
    ├── body_ang_vel.csv
    ├── metadata.txt
    └── info.txt
```

每个动作占一个子目录。给 SONIC 的路径是父目录 **`reference/ardy/`**，SONIC 会加载它下面的动作目录。

更换动作时，保持生成和转换的文件名一致。例如生成 `--output baseline_dancing`，转换时输入 `baseline_dancing.npz`，输出到 `reference/ardy/dancing`。原来的 `run_ardy_2_sonic.txt` 也在个人工作目录下，其输入文件名需要随生成结果调整。

## 5. 打开远程桌面

接下来保留几个独立终端：

| 终端 | 工作内容 |
|---|---|
| A（可选） | 运行 websockify，将 VNC 映射为网页 |
| B | 运行 MuJoCo 仿真 |
| C | 运行 SONIC 控制器，并接收播放按键 |

B、C 必须是两个独立的容器终端；可以使用两个 SSH 会话，或远程桌面中的两个终端。不要让同一组仿真和控制器重复启动。

如果浏览器已经能连接远程桌面，直接使用已有服务，无需再次启动 websockify。只有未启动网页代理时，才在容器终端 A 执行：

```bash
/usr/bin/websockify \
  --web=/usr/share/novnc \
  0.0.0.0:6080 \
  127.0.0.1:5901
```

这条命令将网页端口 `6080` 转发到已有 VNC 服务 `5901`，本身不会创建显示服务 `:1`。命令在前台运行时保持终端 A 打开。

在本机浏览器打开：

```text
http://10.123.0.38:6080/vnc.html
```

点击连接，输入管理员提供的 VNC 密码。`0.0.0.0` 是服务监听地址，浏览器使用开发机 IP。若通过 VS Code 转发了远程端口 6080，则使用 VS Code 提供的本地地址，例如 `http://127.0.0.1:6080/vnc.html`。

## 6. 启动 MuJoCo 仿真

在容器终端 B 中设置上述路径变量，然后执行：

```bash
cd "$SONIC_ROOT"
DISPLAY=:1 python gear_sonic/scripts/run_sim_loop.py \
  --interface lo \
  --scene-path gear_sonic/data/robot_model/model_data/g1/scene_43dof_blocks.xml
```

- `DISPLAY=:1`：把窗口显示到远程 VNC 桌面。
- `--interface lo`：通过本机回环接口与 SONIC 通信，两端接口要一致。
- `--scene-path`：选择包含桌子、木块和 G1 的场景。

浏览器中的远程桌面应出现 MuJoCo 窗口。先保持吊绳启用，继续启动 SONIC 控制器。

**吊绳按键需要先点击 MuJoCo 窗口，使它获得焦点：**

| 按键 | 作用 |
|---|---|
| `9` | 切换弹力绳启用/停用；首次按下通常释放机器人 |
| `7` / `8` | 调整弹力绳的竖直支撑目标 |

`9` 是切换开关，并非“收吊绳”命令；重复按下会再次改变状态。建议在 SONIC 接管后再释放，避免机器人在没有控制时倒下。

## 7. 启动 SONIC 控制器

在容器终端 C 中设置路径变量，然后执行：

```bash
cd "$SONIC_ROOT/gear_sonic_deploy"
MUSA_VISIBLE_DEVICES=4 CUDA_VISIBLE_DEVICES=4 \
./target/release/g1_deploy_onnx_ref \
  lo \
  policy/release/model_decoder.onnx \
  reference/ardy/ \
  --obs-config policy/release/observation_config.yaml \
  --encoder-file policy/release/model_encoder.onnx \
  --input-type keyboard \
  --policy-precision 32 \
  --disable-crc-check \
  --enable-csv-logs \
  --logs-dir ./logs/baseline
```

这条命令加载参考动作、encoder 和 decoder，通过 MuJoCo 反馈的机器人状态计算身体控制命令。它与仿真进程分开运行，使用相同的 `lo` 接口。

| 参数 | 说明 |
|---|---|
| `reference/ardy/` | ARDY 转换出的参考动作集合 |
| `--encoder-file` | 身体动作参考使用的 encoder ONNX |
| `model_decoder.onnx` | 根据参考和当前状态生成控制输出的 decoder ONNX |
| `--obs-config` | 控制器输入观测的配置 |
| `--input-type keyboard` | 从当前终端读取按键 |
| `--policy-precision 32` | 使用当前 MUSA 环境下的 FP32 策略 |
| `--disable-crc-check` | 沿用当前仿真流程，关闭 CRC 检查 |
| `--enable-csv-logs` / `--logs-dir` | 保存控制器状态和动作日志 |

本流程使用 MUSA 版参考动作控制器，不需要传 TensorRT planner 文件，也不需要切换到 planner 模式。初始化可能需要几十秒，看到 **`Init Done`** 后再操作。

## 8. 接管、选动作、播放

按照下面的顺序操作，注意窗口焦点：

1. **点击 SONIC 所在终端 C**，按 `]`，让 SONIC 开始控制机器人。
2. **点击 MuJoCo 窗口**，按 `9` 停用吊绳，观察机器人能否稳定站立。
3. **回到 SONIC 终端 C**，使用 `n` / `p` 选择动作，并查看终端打印的动作名称，确认选中 `walk_circle`。
4. 按 `t` 开始播放，在 MuJoCo 窗口观察机器人运动。
5. 需要重播时，在 SONIC 终端按 `r` 回到首帧，再按 `t`。

SONIC 的按键大小写均可，直接按键即可，**无需回车**：

| 按键 | 参考动作模式中的作用 |
|---|---|
| `]` | 开始控制 |
| `n` / `p` | 下一个 / 上一个动作 |
| `t` | 开始或继续播放 |
| `r` | 回到当前动作首帧，并暂停播放 |
| `o` | 停止控制 |

如果集合中只有一个动作，通常无需切换。生成新动作并转换后，重启控制器，让它重新扫描参考目录。

**按键位置总结：吊绳按键在 MuJoCo 窗口，动作按键在 SONIC 终端。** 即使终端和窗口都显示在同一远程桌面上，也必须先点击对应窗口。

ARDY 自带可视化展示生成的骨架动作；这里展示的是 SONIC 在物理仿真中跟踪该动作。两者可能有跟踪偏差，需要以实际仿真结果判断动作质量。

## 9. 查看日志与结束运行

日志位于：

```text
GR00T-WholeBodyControl/gear_sonic_deploy/logs/baseline/
```

可查看身体关节、控制输出、姿态、手部状态和当前动作名等 CSV。重复使用同一个日志目录可能覆盖之前记录；要保留不同测试结果，可以将启动命令中的路径改为 `--logs-dir ./logs/walk_circle_01`。

结束时先停止 SONIC 控制器（`o` 或终端中的 `Ctrl+C`，以进程是否退出为准），再在仿真终端 B 按 `Ctrl+C`。仅关闭 noVNC 浏览器页面不会自动结束远程进程；关闭运行控制器的终端可能使前台进程结束。已有的共享 VNC/websockify 服务可以保持运行。

## 10. 常见问题

| 现象 | 检查方法 |
|---|---|
| 路径不存在 | 确认已经进入容器，使用 `/workspace/group2/...`，并替换示例中的 `devuser` |
| 离线加载提示缺少模型 | 检查 checkpoint 和文本编码器是否完整，以及本地加载配置；离线变量不会自动下载模型 |
| SONIC 找不到新动作 | 确认转换输出是 `reference/ardy/<动作名>/`，控制器读取父目录；转换后重启控制器 |
| 网页打不开 | 确认 VNC 5901 与 websockify 6080 已运行，或使用 VS Code 的端口转发；不要重复启动占用同一端口的服务 |
| MuJoCo 窗口不可见 | 确认显示服务 `:1` 存在，启动命令带 `DISPLAY=:1` |
| 按键无反应 | 先点击正确窗口；SONIC 按键输入到运行控制器的终端 |
| 机器人仍然悬挂 | 点击 MuJoCo 窗口，用 `9` 切换吊绳状态 |
| SONIC 收不到机器人状态 | 保持仿真进程运行，确认两端都使用 `lo`，且没有重复启动同一组进程 |
| 机器人不动 | 等待 `Init Done`，依次确认已按 `]` 接管、选择正确动作、按 `t` 播放 |

