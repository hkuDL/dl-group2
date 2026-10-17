# G1 + Dex3-1 真机部署实操手册（Replay-first）

## 先说结论

这套项目支持两种工作方式：

1. **明天首选：离线生成再回放。** Kimodo/ARDY/VA 在 H100 或 S4000 生成动作，完整文件先复制到 Jetson；机器人运行时不依赖远程服务器，所以不存在 S4000→Jetson 的实时网络延迟问题。
2. **以后再做：电脑实时推理。** Linux GPU 电脑持续给 Jetson 发短窗口 reference/token，Jetson 仍负责 SONIC、Unitree DDS、安全和急停。这个模式必须在 golden replay 通过后再测。

Mac 可以管理 Git、看文档和做格式测试，但不作为真机运行电脑。真机侧需要 Linux、NVIDIA/Jetson 环境和现场网络。

当前已经验证的是：代码单元测试、golden reference 结构、S4000 源文件/权重哈希，以及本项目打包数据与 S4000 SONIC 原始 packer 的逐字节一致性。**尚未验证**的是 H100 三模型真实前向、H100 显存/latency、Jetson ZMQ 端到端和 G1 实际动作。

## 一、三种输出并不是同一个 64D

- Kimodo → G1 kinematic qpos → canonical motion → SONIC protocol v1。
- ARDY → G1 kinematic qpos → canonical motion → SONIC protocol v1。
- VA v4.1 → `body_tokens [10,64]` + `hand_ref [50,14]` → SONIC protocol v4。

它们共用相同的项目、验证入口和 SONIC 打包层，但 VA token 不能假装成 29 个关节角。Jetson 上的 SONIC v4 decoder 负责解释 VA token。

## 二、H100 准备：三个独立环境

Kimodo 与 ARDY 的 Transformers 版本不同，最稳妥的做法是建三个虚拟环境。以下命令在克隆后的项目根目录执行。

### 1. 公共检查

```bash
nvidia-smi
python3 --version
git status --short
```

必须看到 NVIDIA H100。项目 benchmark 脚本也会检查 GPU 名称；不是 H100 就拒绝生成“H100结果”。

### 2. Kimodo 环境

```bash
python3 -m venv .venv-kimodo
source .venv-kimodo/bin/activate
python -m pip install --upgrade pip
# 先按现场 CUDA/驱动安装匹配的 PyTorch，再执行：
python -m pip install -r requirements-kimodo.txt
deactivate
```

Kimodo 最小 Apache-2.0 运行时代码已经在 `third_party/kimodo/`，不需要 simulator、mesh、demo 或训练数据。

Kimodo/ARDY 如需复现带动作约束的任务，把上游已生成并审核的 constraints JSON 放进项目的 `inputs/`，再在各自 YAML 中填写相对路径 `constraints_file`。推理时只读取这份便携条件文件，不启动 simulator。

### 3. ARDY 环境

```bash
python3 -m venv .venv-ardy
source .venv-ardy/bin/activate
python -m pip install --upgrade pip
# 先按现场 CUDA/驱动安装匹配的 PyTorch，再执行：
python -m pip install -r requirements-ardy.txt
deactivate
```

ARDY 固定到公开 commit `693f74d13b3d04a0a22ce127ee79c929dd89756b`。

### 4. VA 环境

```bash
python3 -m venv .venv-va
source .venv-va/bin/activate
python -m pip install --upgrade pip
# 先按现场 CUDA/驱动安装匹配的 PyTorch，再执行：
python -m pip install -r requirements-va.txt
deactivate
```

## 三、放置权重（绝不提交 Git）

目标位置全部是项目相对路径：

```text
models/Kimodo-G1-RP-v1/{config.yaml,model.safetensors,stats/...}
models/ARDY-G1-RP-25FPS-Horizon52/{config.yaml,denoiser.safetensors,tokenizer.safetensors,stats/...}
models/va_v4_1/checkpoint_compat.pt
```

权重的期望文件名、大小和 SHA-256 在 `models/model_requirements.json`。从 S4000 复制后逐个比对：

```bash
sha256sum models/Kimodo-G1-RP-v1/model.safetensors
sha256sum models/ARDY-G1-RP-25FPS-Horizon52/denoiser.safetensors
sha256sum models/ARDY-G1-RP-25FPS-Horizon52/tokenizer.safetensors
sha256sum models/va_v4_1/checkpoint_compat.pt
```

任何一个哈希不一致都停止。不要把 `models/` 强制加入 Git。

## 四、先验证 golden reference

在任意装好基础依赖的 Linux/Mac 上都可以做这一步：

```bash
python -m scripts.validate_reference test_reference/golden_ardy --mode dry-run
python -m scripts.reference_sender test_reference/golden_ardy
```

期望：结构总结果为 `PASS`，但 `robot_safety` 明确显示 `NOT_EVALUATED`；第二条命令只 dry-run，不开 socket、不发数据。

这条 golden reference 有 810 帧、50 Hz，并通过了原 ARDY task-policy 的抓取/抬升判定；但记录到 26 个右拇指/桌面接触 step（0.13 秒），所以它只能作为集成 golden，不能被当作自动真机安全批准。

## 五、H100 分别跑三个独立 pipeline

### Kimodo

```bash
source .venv-kimodo/bin/activate
CUDA_VISIBLE_DEVICES=0 python -m scripts.run_inference kimodo \
  --config configs/kimodo.h100.yaml \
  --output outputs/kimodo_run_01
python -m scripts.validate_reference outputs/kimodo_run_01 --mode dry-run
deactivate
```

### ARDY

```bash
source .venv-ardy/bin/activate
CUDA_VISIBLE_DEVICES=0 python -m scripts.run_inference ardy \
  --config configs/ardy.h100.yaml \
  --output outputs/ardy_run_01
python -m scripts.validate_reference outputs/ardy_run_01 --mode dry-run
deactivate
```

### VA

先准备 `inputs/va_input.npz`，必须只有明确的当前输入：`rgb [H,W,3] uint8`、`body [68]`、`hand [28]`。它不读取 simulator state，也不读取训练 dataset。

```bash
source .venv-va/bin/activate
CUDA_VISIBLE_DEVICES=0 python -m scripts.run_inference va \
  --config configs/va.h100.yaml \
  --output outputs/va_run_01
deactivate
```

VA 输出是 SONIC v4 token bundle，不使用 canonical motion validator。

## 六、记录 H100 latency 和显存

每个环境中分别执行：

```bash
python -m scripts.benchmark_h100 kimodo --config configs/kimodo.h100.yaml --report benchmark_results/kimodo.json
python -m scripts.benchmark_h100 ardy   --config configs/ardy.h100.yaml   --report benchmark_results/ardy.json
python -m scripts.benchmark_h100 va     --config configs/va.h100.yaml     --report benchmark_results/va.json
```

默认 2 次 warm-up、5 次正式测量，固定 `batch=1`。统计范围是“模型已加载后的前向 + SONIC reference adapter”；加载时间单列。把三个 JSON 的 GPU 型号、mean/p50/p95 latency、peak allocated/reserved bytes 抄入 `BENCHMARKS_H100.md`，并保留原 JSON 作为本地实验记录（默认不进 Git）。

## 七、明天现场网络检查

1. PC/Jetson/G1 使用实验室批准的有线网段；关闭 Wi-Fi 路由依赖。
2. 记录 PC 和 Jetson 的网卡名/IP，IP 只放本地 `.env`，不提交 Git。
3. PC 到 Jetson 连续检查：

```bash
ping -c 100 JETSON_IP
```

4. 条件允许时跑 30 秒双向 `iperf3`，记录丢包、吞吐和抖动。
5. 首次 replay 把 reference 文件先复制到 Jetson，并在 Jetson 本机使用 `tcp://127.0.0.1:5556`；这一步不让外网进入控制环。

没有测量结果时不要猜 latency 阈值。最低门槛是持续测试零丢包、无明显尖峰，并由机器人负责人确认现场阈值。S4000 跨公网/VPN 链路不用于首次真机。

## 八、Golden reference → Jetson SONIC → G1

### A. 上电前

- G1 支撑/吊架和测试姿态按实验室 SOP 准备。
- 实体急停可用；一人操作、一人只看机器人并随时急停。
- 清空工作区；桌面/物体位置与 reference 任务一致。
- 确认 Jetson 上使用的是已审核的 SONIC real binary、policy、encoder/decoder、observation config 和 Unitree 网卡。
- CRC 保持启用；不要使用 simulation loopback 或 `--disable-crc-check`。

### B. 只启动接收端，不启动动作

使用实验室已经验证过的 SONIC real 启动命令，并明确配置：

```text
--input-type zmq
--zmq-host localhost
--zmq-port 5556
--zmq-topic pose
--zmq-conflate
```

实际 binary、网卡、policy 和 reference 目录必须从 Jetson 的已验证配置读取，本项目不猜这些值。

### C. Jetson 本机 dry-run 后发布

```bash
python -m scripts.validate_reference test_reference/golden_ardy --mode dry-run
python -m scripts.reference_sender test_reference/golden_ardy
```

确认无误后，才加 `--send`：

```bash
python -m scripts.reference_sender test_reference/golden_ardy --send \
  --bind tcp://127.0.0.1:5556 --countdown 10
```

sender 只发布 reference，不发送“启动控制”命令。机器人控制切换仍由现场 SONIC 操作员完成。首次动作使用最低风险、最低速度/增益和支撑方案；这些数值必须来自机器人负责人，不能从本项目默认值推断。

### D. 晋级顺序

```text
network test
  → golden dry-run
  → golden Jetson-local ZMQ reception
  → supported/low-risk golden motion
  → Kimodo artifact dry-run + replay
  → ARDY artifact dry-run + replay
  → VA v4 token dry-run + decoder check + replay
  → nearby Linux GPU PC live inference
  → 最后才评估 S4000 live inference
```

每一步只在上一层证据保存并签字后进入下一层。

## 九、任何一项出现就停止

- 哈希、shape、dtype、50 Hz、四元数约定或关节顺序不一致；
- 当前 29-DoF 姿态与 reference 首帧不在现场批准范围；
- SONIC source/binary/policy/encoder/decoder 与审核版本不一致；
- 网络丢包、延迟尖峰、数据过期、frame index 重复/倒退；
- G1 抖动、失衡、异常接触、手指夹持异常、电机温度/故障告警；
- 操作员、观察员、实体急停或机器人负责人不在位。

