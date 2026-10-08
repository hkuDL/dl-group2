# DASC7606C 小组项目 Proposal

## 基于 SONIC 的 Unitree G1 语音与视觉语言条件桌面抓取运动生成

### Kimodo 与 ARDY 的受控比较及一体化数据采集与模型训练扩展

| 项目 | 内容 |
|---|---|
| 方向 | Track 4：Humanoid-Robot Motion Generation Deployment |
| 小组人数 | 12 人 |
| 机器人与环境 | Unitree G1 仿真环境，以及 Archon 监督下的真机体验 |
| 必须使用的低层控制器 | SONIC |
| 核心运动生成方法 | Kimodo 与 ARDY |
| 核心任务 | 文本驱动的桌面方块抓取与抬起 |
| 一体化扩展 | 语音转文字输入、仿真数据采集、可训练的视觉语言条件运动生成，以及未见位置泛化 |

### 小组成员

Fu Yuhan；Hao Hao；Huang Xinxuan；Li Jingyao；Luo Mingdi；Meng Guanlin；Mi Siyuan；Tang Zichun；Tu Chengyuan；Zhang Kunqi；Zhang Yixin；Zhang Yuanzhuo。

## 1. 项目摘要

本项目将在仿真中构建并评估一个由自然语言控制的 Unitree G1 桌面操作系统。必做基线将比较两种不同的预训练运动生成方法 Kimodo 和 ARDY。两种方法将共用同一仿真场景、指令集、运动适配接口、SONIC 低层控制器、手部或夹爪控制器以及评估协议。目标行为是让 G1 根据输入的自然语言指令完成向方块伸手、抓取并从桌面抬起的全过程。

本项目还将把原有的多个 bonus 想法整合为一条连贯的可选扩展路线，而不是相互独立的附加功能。扩展包含两个相互衔接的能力：

1. 语音转文字接口，将口头指令转换为与基线相同的文本指令表示；
2. 可训练的视觉语言条件运动生成器，根据仿真头部相机图像和识别后的文本指令，生成可由 SONIC 执行的 G1 上半身参考轨迹。

扩展将进一步包含自动化仿真数据采集、LeRobot 格式转换、模型训练，以及对训练中未出现过的方块位置进行泛化评估。以文字输入为基础的 Kimodo/ARDY 基线将始终保持独立可运行，因此 Track 4 的必做交付物不依赖可选扩展能否全部完成。

## 2. 背景与动机

Track 4 研究如何使用自然语言指令控制 Unitree G1 人形机器人。核心难点不仅是生成视觉上合理的类人动作，还包括把动作适配到 G1 本体、通过 SONIC 执行、协调独立的手部或夹爪控制、保持下半身稳定，并最终与物体发生可靠接触和交互。

Kimodo 和 ARDY 提供了两种不同的运动生成方法，适合进行受控比较。让两种方法使用完全相同的下游控制器和仿真场景，可以比较它们在指令遵循、抓取位姿精度、物理可行性、响应时间、用户纠正次数及集成难度上的差异。

一体化扩展针对纯文本固定场景基线的两个限制。第一，语音指令更自然，但会引入识别错误和额外延迟。第二，固定的文本到运动模型可能不会使用当前视觉信息来适应新的方块位置。通过结合语音转文字和可训练的视觉语言条件运动生成器，扩展将研究从口头意图和视觉观测到可执行机器人动作的完整链路。

## 3. 项目范围与课程要求对应关系

### 3.1 必做核心范围

核心项目将覆盖 Track 4 的全部必做要求：

- 参加并记录 Archon 监督下的 demonstration-recording 和 policy-inference 流程；
- 构建包含桌面和可抓取方块的 Unitree G1 仿真环境；
- 使用 SONIC 作为低层控制器；
- 接收键盘输入的自然语言指令；
- 实现 Kimodo 和 ARDY 两种不同的运动生成方法；
- 将两种方法适配到同一套 G1/SONIC 执行接口；
- 实现所需的独立手部或夹爪控制；
- 在仿真中演示方块抓取和抬起；
- 使用共享指令、可比初始条件、重复实验、明确成功标准和代表性失败案例评估两种方法；
- 解释仅控制上半身时下半身如何保持稳定。

### 3.2 【BONUS】一体化可选扩展

可选扩展包含两个连接在一起的层次：

- **语音交互层：**语音指令 -> 自动语音识别 -> 经过验证的文本指令。
- **可训练视觉运动层：**仿真头部相机图像 + 文本指令 -> 可训练运动生成器 -> SONIC-compatible G1 参考运动。

本项目不会把语音转文字单独宣称为完整的 extra-credit 贡献。实质性扩展是把仿真数据采集、可训练的视觉语言运动生成、SONIC 执行以及未见位置泛化组成一条端到端链路。在将其作为正式 bonus 展示之前，小组会先与 teaching team 确认扩展范围。

### 3.3 范围边界

- 必做基线使用预训练的 Kimodo 和 ARDY checkpoints，不要求进行项目专属微调。
- 键盘文本仍是必做且可靠的输入方式；语音输入是附加层，并保留文本 fallback。
- 第一个稳定版本固定机器人初始姿态、桌面位置和方块位置。
- 方块位置随机化、多种可区分方块、数据集生成和模型训练属于扩展内容。
- 必做 Archon session 的目的是真实体验并理解真机数据采集与推理流程；项目不依赖把本组系统部署到物理机器人上。
- 只有在必做仿真证据完成并通过 TA 审核批准后，才考虑 sim-to-real 部署。

### 3.4 要求追踪表

| Track 4 要求 | 计划提供的证据 |
|---|---|
| Archon session 与 workflow understanding | 参与记录、允许保留的照片或笔记，以及报告中对输入、记录数据、模型输出、控制流程、安全和失败/恢复行为的准确说明 |
| SONIC 集成 | 共享 canonical motion interface、G1 adapter、SONIC 配置、控制流程图、tracking logs，以及下半身稳定策略说明 |
| 文本驱动抓取 | 展示 reach、grasp 和 lift 的文本指令 demo；必要时支持分步骤命令 |
| 两种不同方法 | 在相同 SONIC 控制器和场景下独立实现 Kimodo 与 ARDY |
| 评估与分析 | 重复实验、共享指令与 seeds、成功率、响应时间、纠正次数、精度、物理可行性和失败分类 |
| Demo 与可复现性 | 两种方法的成功和失败视频、公开 GitHub、配置、安装说明和评估脚本 |
| 报告与展示 | 5-8 页报告，不含参考文献；10 分钟展示并包含必做 demo；5 分钟 Q&A |

## 4. 项目目标与研究问题

### 4.1 核心目标

1. 构建可复现的 G1 桌面仿真环境，并将 SONIC 作为共享低层控制器接入。
2. 复现并部署可用的 G1-oriented Kimodo 和 ARDY 推理流程。
3. 定义 canonical motion representation，使两种方法能够公平接入同一个 G1/SONIC 接口。
4. 实现可靠的抓取阶段控制，以及必要的独立手部或夹爪控制。
5. 在匹配的指令、初始条件、算力预算和评估标准下比较 Kimodo 与 ARDY。
6. 输出清晰 demo、失败分析，以及可复现的代码和配置。

### 4.2 核心研究问题

- Kimodo 和 ARDY 在指令遵循和到达指定抓取位姿方面有何差异？
- 空间约束或交互式文本纠正能否提高抓取成功率？
- 运动质量、响应时间、物理可行性和 SONIC 集成难度之间存在什么权衡？
- 失败分别来自运动生成、本体适配、SONIC tracking、手部控制、接触动力学还是指令理解？

### 4.3 【BONUS】扩展研究问题

- 语音转文字能以多高的准确率和多低的延迟，把口头操作命令转换成任务有效指令？
- 与键盘文本相比，语音识别错误会如何影响用户纠正次数、总体响应时间和抓取成功率？
- 轻量级视觉语言条件运动生成器能否根据单帧头部相机图像和文本指令，生成 SONIC-compatible 抓取轨迹？
- 训练后的模型能否泛化到训练集中未出现过的方块位置？
- 如果时间允许，Deterministic Transformer Regression 和 Flow Matching 在运动质量、推理速度和泛化能力上有何差异？

## 5. 整体系统设计

### 5.1 必做基线流程

```text
键盘输入自然语言指令
  -> 指令验证与任务解析
  -> Kimodo 或 ARDY
  -> 方法专属 output adapter
  -> canonical G1 reference motion
  -> SONIC 低层控制器
  -> 独立 hand/gripper controller
  -> 仿真抓取与抬起
```

### 5.2 【BONUS】语音输入流程

```text
语音指令
  -> speech-to-text
  -> 置信度检查和命令标准化
  -> 与基线相同的文本指令接口
  -> Kimodo 或 ARDY
  -> G1 motion adapter
  -> SONIC 与 hand/gripper control
```

当识别置信度过低或解析后的命令无效时，系统将要求用户重复语音，或者允许文本纠正。系统将记录识别 transcript、置信度、延迟、纠正次数以及最终接受的指令。

### 5.3 【BONUS】可训练视觉语言扩展流程

```text
语音 ----------------> speech-to-text ----------------> 指令 L
                                                          |
头部相机图像 I -> 视觉语言条件模型 ------------------------+
                           |
                           v
                   上半身轨迹 Q_upper
                           |
固定 standing reference -> 完整 G1 reference motion Q_ref
                           |
                    SONIC + gripper control
                           |
                    泛化抓取与抬起
```

扩展模型定义为：

$$
f_\theta(I,L) \rightarrow Q_{1:T}^{\mathrm{upper}},
\qquad
I \in \mathbb{R}^{H \times W \times 3}.
$$

下半身首先使用固定 standing reference：

$$
Q_{1:T}^{\mathrm{lower}}=Q^{\mathrm{standing}},
$$

完整轨迹为：

$$
Q_{1:T}^{\mathrm{ref}}
=
\left[Q_{1:T}^{\mathrm{lower}},Q_{1:T}^{\mathrm{upper}}\right]
\in \mathbb{R}^{T\times29}.
$$

关节速度可通过位置差分得到：

$$
\dot q_t^{\mathrm{ref}}
=
\frac{q_t^{\mathrm{ref}}-q_{t-1}^{\mathrm{ref}}}{\Delta t}.
$$

对于 stationary grasping，root position 和 orientation 默认使用 standing reference，除非选定的 SONIC 接口要求另一种表示。手部或夹爪命令将表示为独立序列 $G_{1:T}$，并与手臂轨迹进行时间同步。

## 6. 功能模块与技术方案

### 6.1 模块总览

本节使用以下范围标记：**CORE** 表示完成 Track 4 必做交付物所需的功能；**BONUS** 表示只有在核心基线稳定后才开展、不会阻塞核心提交的可选扩展；**CORE + BONUS** 表示同一基础模块同时服务于核心实验和已完成的扩展实验。

| 编号 | 范围 | 功能模块 | 主要功能 | 输出与验收标准 | 主要负责组 |
|---|---|---|---|---|---|
| M1 | **CORE**；位置随机化、多方块和训练相机数据为 **BONUS** | 仿真场景与任务定义 | 配置 G1、桌面、方块、核心相机、固定初始状态、reset 逻辑和成功条件；为 bonus 预留随机化与数据 hooks | 核心：可确定性 reset 和固定场景抓取；Bonus：可达区域位置随机化、多目标设置与训练观测 | Team 1 |
| M2 | **CORE** | Canonical motion interface 与 SONIC 集成 | 定义运动 schema、映射关节顺序和单位、重采样轨迹、计算速度参考、配置 standing/root reference 并通过 SONIC 执行 | Kimodo 和 ARDY 均能通过同一接口发送可比 reference motion | Team 1，Teams 2 和 3 配合 |
| M3 | **CORE** | 抓取与手部控制 | 实现 open、pre-grasp、approach、close、lift、release 和 recovery 状态；同步手部命令与 reference motion | 能够抓取并抬起方块；单独记录 hand/gripper 行为 | Team 1 |
| M4 | **CORE** | Kimodo pipeline | 复现官方推理、定义输入和约束、生成动作、适配输出并记录方法局限 | 可复现的 Kimodo -> SONIC -> G1 抓取流程 | Team 2 |
| M5 | **CORE** | ARDY pipeline | 复现官方 G1 推理、研究 interactive/streaming generation、适配输出并记录纠正行为 | 可复现的 ARDY -> SONIC -> G1 抓取流程 | Team 3 |
| M6 | **BONUS** | 语音转文字与指令接口 | 采集音频、运行 ASR、标准化指令、验证任务语法、处理置信度和重试，并提供文本 fallback | 语音稳定进入同一文本接口；记录 transcript、置信度、延迟和纠正次数 | Team 4 |
| M7 | **BONUS** | 仿真数据采集与 LeRobot 导出 | 生成 expert trajectory，采集同步图像/状态/动作，保存指令和时间戳，标记 episode boundaries，进行质量检查并转为 LeRobot 格式 | 包含脚本、schema、metadata、质量报告和可访问数据或链接的可复用数据集 | Team 1 主导，Team 4 负责质量控制 |
| M8 | **BONUS** | 可训练视觉语言运动模型 | 实现视觉/文本编码器、多模态融合、deterministic Transformer trajectory decoder、loss、训练、checkpoint 和 SONIC inference adapter；Diffusion/Flow Matching 仅作为后续可选 ablation | 训练模型生成 SONIC-compatible 上半身轨迹，并在共享场景运行 | Teams 2 和 3 |
| M9 | **CORE + BONUS** | 评估、日志与失败分析 | 核心阶段评估 Kimodo 与 ARDY；仅在扩展完成后增加 STT、数据质量、训练模型与泛化评估 | 核心公平比较及可复现结果表；完成 bonus 时另附独立扩展结果 | Team 4 |
| M10 | **CORE** | Archon、安全、文档与发布 | 记录监督流程，维护安装说明和个人贡献证据，检查 license/data restrictions，整合报告/demo/repository | 准确的 Archon 章节；不含受限材料的公开仓库；完整贡献说明 | Team 4 主导，全组参与 |

### 6.2 共享运动接口

为了避免各条 pipeline 不兼容，所有运动方法进入 SONIC 前必须导出统一表示：

```text
CanonicalMotion
  joint_names
  q_ref[T, 29]
  qdot_ref[T, 29] 或速度计算规则
  timestamps[T]
  root_position[T]
  root_orientation[T]
  optional_hand_command[T]
  metadata: method, instruction, seed, object pose, checkpoint
```

接口规范将明确关节顺序、单位、坐标系、采样频率、轨迹时长、缺失关节处理、clipping 规则及 interpolation。Kimodo 和 ARDY 可以在内部保留各自表示，但评估前必须经过同一 canonical contract。

### 6.3 仿真与任务状态机

初始任务状态机为：

```text
RESET
  -> STAND
  -> RECEIVE INSTRUCTION
  -> GENERATE MOTION
  -> PRE-GRASP
  -> APPROACH
  -> CLOSE HAND/GRIPPER
  -> LIFT
  -> VERIFY SUCCESS
  -> END 或 RECOVER
```

核心实验固定机器人初始姿态、桌面位置、方块位置和相机位姿。两种基线方法稳定后，扩展将在明确的可达区域内随机化方块位置。如果场景包含多个方块，则在指令中加入颜色或身份信息，使 language conditioning 真正有意义。

### 6.4 Kimodo 方法

Kimodo 组将：

- 复现可用的 G1-oriented 预训练推理示例；
- 记录文本输入、kinematic constraints、motion representation、checkpoint、预处理和算力要求；
- 生成 reaching、grasp-approach 和 lifting reference motion；
- 研究从物体位姿推导的手部或 end-effector 约束能否提高精度；
- 将 Kimodo 输出映射到 canonical motion contract；
- 接入共享 SONIC 与 gripper 接口；
- 记录方法专属失败，包括无法满足约束、轨迹不连续、关节越界和接触失败。

### 6.5 ARDY 方法

ARDY 组将：

- 复现预训练 G1 配置和官方推理示例；
- 记录模型输入、输出、checkpoints、预处理和算力要求；
- 在技术可行时研究 interactive 或 streaming generation；
- 在相同任务定义下实现对应的 reaching、grasp-approach 和 lifting 行为；
- 将 ARDY 输出映射到 canonical motion contract；
- 接入同一 SONIC 与 gripper 接口；
- 记录方法专属失败，以及交互式纠正可能带来的影响。

### 6.6 【BONUS】语音转文字接口

语音模块不会直接控制机器人，而是为基线文本接口生成经过验证的文字指令。初始命令语法将支持目标身份和操作阶段，例如：

```text
Pick up the red block.
Reach toward the blue block.
Adjust the right hand above the block.
Grasp the block.
Lift the block.
```

该模块包含：

- 带明确开始/停止控制的音频采集；
- 根据延迟、隐私和部署测试选择 offline 或 online ASR engine；
- 对物体名称、颜色和动作动词进行文本标准化；
- 置信度阈值和超出任务范围命令的拒绝机制；
- 低置信度时的确认或重试；
- 文本纠正和文本 fallback；
- 对 raw transcript、normalized command、confidence、latency 和纠正次数进行记录；
- 未经允许不公开任何参与者语音记录的隐私规则。

### 6.7 【BONUS】仿真数据采集

训练扩展中的每个 episode 将执行：

1. 将 G1 reset 到固定 standing pose；
2. 在桌面可达区域随机采样方块位置；
3. 渲染 head-camera RGB image；
4. 分配键盘输入或语音识别得到的指令；
5. 使用 scripted inverse kinematics 或 motion planner 生成 expert pre-grasp、grasp 和 lift trajectory；
6. 在仿真中执行轨迹；
7. 验证成功并标记失败原因；
8. 保存同步 observation、robot state、action、joint reference、hand command、timestamp 和 episode boundary；
9. 将合格 episodes 转换为 LeRobot 格式。

紧凑训练目标可以写为：

$$
D_i=\left(I_i,L_i,Q_i^{GT},G_i^{GT}\right),
$$

而正式发布的 episode 表示还将包含同步 robot states、actions、timestamps、camera metadata、success labels，以及可选 audio/transcript metadata。

Scripted IK 或 motion planning 是第一 expert source，因为它具有明确几何关系、精确抓取目标、较低数据生成成本，并能减少预训练模型误差污染。高质量 Kimodo 或 ARDY rollouts 可以作为 additional demonstration source，但需要单独标记。

### 6.8 【BONUS】可训练视觉语言运动生成器

计划使用的轻量级架构为：

```text
Pretrained Vision Encoder
  + Lightweight Text Encoder
  + Small Multimodal Fusion Transformer
  + Motion Decoder
```

初始配置如下：

| 组件 | 初始配置 |
|---|---|
| Vision encoder | DINOv2 ViT-S/14 或其他轻量 pretrained ViT；初期冻结；保留 spatial patch tokens |
| Text encoder | MiniLM-class pretrained encoder；初期冻结 |
| Shared hidden dimension | 256 |
| Fusion Transformer | 4 layers，8 attention heads，FFN dimension 1024 |
| 预计可训练参数 | 约 5-10M，不含冻结 encoders |
| 主要 decoder | Deterministic Transformer trajectory regression |
| 可选 decoder | 确定性基线稳定后尝试 Flow Matching / DiT-style motion generator |

Representation pipeline 为：

$$
I\rightarrow Z_v,
\qquad
L\rightarrow Z_l,
\qquad
(Z_v,Z_l)\rightarrow Z_{\mathrm{condition}}.
$$

Deterministic decoder 预测：

$$
(Z_v,Z_l)\rightarrow\hat Q_{1:T}.
$$

初始训练目标为：

$$
\mathcal{L}_{\mathrm{pos}}
=
\frac{1}{T}\sum_{t=1}^{T}\left\|\hat q_t-q_t^{GT}\right\|_1,
$$

$$
\mathcal{L}_{\mathrm{vel}}
=
\frac{1}{T-1}\sum_{t=2}^{T}
\left\|
(\hat q_t-\hat q_{t-1})-(q_t^{GT}-q_{t-1}^{GT})
\right\|_1,
$$

$$
\mathcal{L}=\mathcal{L}_{\mathrm{pos}}+\lambda\mathcal{L}_{\mathrm{vel}}.
$$

如果确定性基线可靠，可选 Flow Matching decoder 将学习：

$$
v_\theta(Q_\tau,\tau,Z_{\mathrm{condition}}),
\qquad
\frac{dQ_\tau}{d\tau}
=
v_\theta(Q_\tau,\tau,Z_{\mathrm{condition}}),
$$

从 $Q_{\tau=0}\sim\mathcal{N}(0,I)$ 开始，并生成 $Q_{\tau=1}=Q_{1:T}^{\mathrm{ref}}$。

### 6.9 【BONUS】泛化设计

训练集和测试集将按方块位置分离。对于桌面可达区域：

$$
x\in[x_{\min},x_{\max}],
\qquad
y\in[y_{\min},y_{\max}],
$$

采样的位置集合满足：

$$
\mathcal{P}_{\mathrm{train}}\cap\mathcal{P}_{\mathrm{test}}=\varnothing.
$$

主要泛化比较将分别报告 seen-position 和 unseen-position performance。如果使用多个彩色方块，也将明确区分目标身份并记录 split，从而在避免数据泄漏的前提下计算 target-selection accuracy。

## 7. Archon 监督参观计划

小组将至少提前两天预约，并在监督下参加 session。报告将准确记录：

- 机器人和传感器配置；
- demonstration-recording 的输入和操作者接口；
- 被记录的 observation、robot state、action、timestamp 和 episode boundary；
- 数据保存方式和质量控制流程；
- policy-inference 输入与预处理；
- 模型输出及其表示方式；
- 模型输出到机器人控制命令的转换过程；
- 低层控制器、hand/gripper branch、安全过滤、紧急停止和恢复流程；
- 至少一个成功流程，以及一个实际观察或工作人员说明的失败模式；
- Archon workflow 与本组仿真/SONIC pipeline 的相同点和不同点。

只保留被允许记录的笔记、图片、视频和非受限 metadata。未经许可，不公开 credentials、受限机器人数据、内部代码或第三方材料。

## 8. 评估计划

### 8.1 实验控制

Kimodo/ARDY 核心比较将使用：

- 相同的 G1 模型、simulator、scene assets、桌面和物体几何；
- 相同的 SONIC 版本、控制器配置、standing reference 和 gripper logic；
- 相同的指令语义和抓取成功定义；
- 匹配的初始条件和 evaluation seeds；
- 适用时相同的轨迹时长与 resampling 规则；
- 可比的算力和推理预算；
- 每个 condition 相同数量的重复 trials。

Pilot testing 完成后，目标是每个报告 condition 至少进行 20 次 trial。如果运行时间或算力要求必须改变数量，所有被比较方法仍使用相同次数，并在报告中明确说明。

### 8.2 核心比较矩阵

| 因素 | 核心取值 | 扩展取值 |
|---|---|---|
| Motion method | Kimodo、ARDY | 条件允许时加入可训练视觉语言生成器 |
| Instruction input | 键盘文本 | 语音转文字并支持文本纠正 |
| Scene | 固定机器人、桌面、相机和方块位置 | 随机方块位置；可选多个可区分方块 |
| Controller | 相同 SONIC 配置 | 相同 SONIC 配置 |
| Evaluation seeds | 共享 held-out seeds | 分离的 seen/unseen position sets |

### 8.3 评估指标

| 指标 | 定义或测量方式 | 适用范围 |
|---|---|---|
| Grasp success rate | 目标方块被成功抓取，并在预设时间内抬至预设高度的 trial 比例 | 全部运动方法 |
| Target-selection accuracy | 多物体实验中抓取指令指定目标的比例 | 语言/视觉扩展 |
| Instruction-following accuracy | 是否完成指定目标和动作顺序 | 全部方法 |
| Response time | 指令提交至运动生成完成；同时分开报告 ASR 和 motion-generation 延迟 | 全部方法与 STT |
| User corrections | 执行被接受前重复或修改指令的次数 | 文本与语音输入 |
| Speech recognition quality | Word error rate，以及目标词和动作词的 task-level intent/slot accuracy | STT 扩展 |
| Motion precision | 可测量时计算 end-effector 或 grasp-pose error，$E_{EE}=\|p_{EE}-p_{target}\|_2$ | 全部运动方法 |
| SONIC tracking quality | 可获取时计算 reference-to-executed joint error，并统计 tracking failure | 全部运动方法 |
| Physical feasibility | 关节越界、碰撞、不稳定运动、foot/root instability 和不可行接触行为 | 全部运动方法 |
| Generalization | 在分离的位置集合上报告 seen-position 与 unseen-position success rate | 可训练扩展 |
| Failure analysis | 对 perception、ASR、instruction、generation、adaptation、controller、grasp/contact 和 stability failure 分类与计数 | 整个系统 |

### 8.4 计划分析

- 固定条件下、键盘文本输入的 Kimodo vs. ARDY。
- 每种稳定方法上的键盘文本 vs. 语音识别文本。
- 支持时，加入空间约束或交互式纠正前后的表现。
- 可训练扩展的 seen vs. unseen block positions。
- 数据支持多目标时，Vision-only vs. Vision-Language conditioning。
- 算力允许时，global visual embedding vs. spatial patch tokens。
- 算力允许时，frozen vs. partially fine-tuned visual backbone。
- 只有 deterministic training baseline 完成后，才比较 Deterministic Regression vs. Flow Matching。

高成功率本身不足以代表高质量工作。分析将重点关注公平条件、重复实验、不确定性、集成权衡、代表性失败和有技术依据的解释。

## 9. 团队结构与职责

小组将按功能模块分组，而不是拆成两个相互独立的端到端方法团队。四个功能组分别由 Fu Yuhan、Meng Guanlin、Li Jingyao 和 Hao Hao 担任 lead。共享基础设施只实现一次，并为 Kimodo、ARDY 和可选可训练模型提供明确接口。每个小组必须先完成表中的 **CORE** 职责；**BONUS** 职责只有在对应核心 exit criteria 达成后启动。

### 9.1 功能小组

| 小组 | Lead 与成员 | **CORE** 主要职责 | **BONUS** 职责（核心完成后） |
|---|---|---|---|
| Team 1：Simulation、SONIC 与 Grasp Control | **Lead: Fu Yuhan**；Luo Mingdi；Tu Chengyuan | 仿真场景、G1 配置、canonical motion contract、SONIC 集成、固定站姿/下半身稳定、hand/gripper control 和 scripted grasp 验证 | 位置随机化、expert IK/planner 批量 rollouts、同步数据采集与 LeRobot 转换 |
| Team 2：Kimodo | **Lead: Meng Guanlin**；Tang Zichun；Zhang Kunqi | Kimodo 部署、文本/kinematic constraints、G1 output adaptation、共享 SONIC 接口、方法专属测试与失败分析 | 视觉/文本编码、multimodal fusion，以及可训练模型的数据接口支持 |
| Team 3：ARDY | **Lead: Li Jingyao**；Huang Xinxuan；Zhang Yuanzhuo | ARDY 部署、streaming/interactive behavior、约束、G1 output adaptation、共享 SONIC 接口、方法专属测试与失败分析 | Deterministic trajectory decoder 与 SONIC adapter；算力和进度允许时进行 Diffusion/Flow Matching ablation |
| Team 4：Evaluation、Speech 与 Release | **Lead: Hao Hao**；Mi Siyuan；Zhang Yixin | 实验设计、共享 seeds/logs、指标、失败分类、统计汇总、视频证据、报告/展示整合和仓库可复现性 | 语音转文字与命令标准化；STT 影响、seen/unseen 泛化、数据质量和端到端训练模型评估 |

### 9.2 暂定个人职责

以下分工用于定义初始 owner。最终 contribution statement 将以实际完成的工作和支持证据为准。

| 成员 | 初始职责 |
|---|---|
| Fu Yuhan | **Team 1 lead**；共享 simulation/SONIC architecture、canonical interface、下半身稳定策略和跨组集成 |
| Luo Mingdi | **CORE：**scene assets、camera setup、fixed reset 和 observation hooks；**BONUS：**位置随机化和训练数据 hooks |
| Tu Chengyuan | **CORE：**hand/gripper controller、grasp state machine 和 scripted grasp；**BONUS：**expert IK/planner 与数据采集执行 |
| Meng Guanlin | **Team 2 lead**；Kimodo 技术路线、constraints、canonical-motion adapter 和 SONIC 集成协调 |
| Tang Zichun | **CORE：**Kimodo inference reproduction、output adaptation 和接口测试；**BONUS：**multimodal fusion 支持 |
| Zhang Kunqi | **CORE：**Kimodo 专属测试、失败记录和复现文档；**BONUS：**visual/text encoder 与数据接口支持 |
| Li Jingyao | **Team 3 lead**；ARDY 技术路线、官方推理复现、共享接口和跨组协调 |
| Huang Xinxuan | **CORE：**ARDY 部署、constraints、方法专属测试和失败分析；**BONUS：**trajectory-decoder 支持 |
| Zhang Yuanzhuo | **CORE：**ARDY streaming/interactive interface、canonical-motion adapter 和 SONIC 调试；**BONUS：**训练模型 inference adapter |
| Hao Hao | **Team 4 lead**；核心评估协议、结果表、跨组实验协调，以及 bonus 评估 gate |
| Mi Siyuan | **CORE：**公共日志与实验记录；**BONUS：**speech-to-text、命令标准化、置信度/重试逻辑和 STT 评估 |
| Zhang Yixin | **CORE：**统计汇总、失败分类、视频与报告/展示整合；**BONUS：**seen/unseen、数据质量和 ablation 评估 |

### 9.3 共享工程规则

- 全组使用统一的 simulator version、G1 model、SONIC revision、坐标约定和配置格式。
- 在各方法独立开发前先完成接口文档。
- 每个功能必须有 owner、reviewer、test case、configuration 和 evidence link。
- 共享接口和评估代码通过 pull request 或等价流程进行 review。
- 每周 integration check 都要让两种方法运行当前公共 pipeline。
- 个人工作记录包含任务、commits 或文件、实验、结果、review 和会议决定。

## 10. 工作计划与里程碑

| 里程碑 | 主要工作 | 完成标准 |
|---|---|---|
| M0：Requirements 与 Archon workflow | 确认课程范围，参加 Archon session，记录 data-collection/inference workflow，并冻结初始接口方案 | 范围记录得到确认；Archon workflow 记录完整；安全和公开限制已记录 |
| M1：共享平台 | 构建 G1/桌面/方块仿真、scripted grasp、canonical motion contract、SONIC execution、standing reference 和 gripper state machine | 一条 scripted reference motion 能通过 SONIC 可复现地抓取并抬起方块 |
| M2：独立方法基线 | 复现 Kimodo 和 ARDY inference，并把输出映射到 canonical representation | 官方示例复现；两种方法均能生成可检查的 G1 reference motion |
| M3：核心端到端集成 | 使用键盘指令，让 Kimodo 和 ARDY 分别通过共享 SONIC/gripper pipeline 运行 | 两条必做 pipeline 均至少完成一次端到端 grasp-and-lift trial |
| M4：核心受控评估 | 冻结指令、seeds、成功标准、trial budget 和 logging；采集成功与失败实验 | 公平重复比较，拥有完整 logs、metrics、videos 和 failure labels |
| M5：**BONUS** 语音扩展 | 加入语音采集、ASR、命令标准化、置信度处理、文本 fallback 和延迟/错误日志 | 语音指令可以控制至少一个稳定基线方法；报告 STT 准确率和延迟 |
| M6：**BONUS** 数据与训练扩展 | 自动采集仿真数据、导出 LeRobot episodes、训练选定的 deterministic vision-language trajectory model | 数据集和质量检查有文档；得到训练 checkpoint；可通过共享 adapter 推理 |
| M7：**BONUS** 泛化与可选 ablations | 评估分离的 unseen positions 和选定 ablations；只有前序完成才尝试 Diffusion/Flow Matching | 得到 seen/unseen 结果、代表性失败和任何已完成 ablation 证据 |
| M8：最终材料 | 完成公开 GitHub、报告、展示、demo videos、contribution statement 和 LLM/外部资源声明 | 通过可复现性检查；所有必做及已完成扩展证据均已链接 |

## 11. 交付物与可复现性

### 11.1 必做交付物

- **报告：**5-8 页，不含参考文献，包含 Archon session、仿真系统、Kimodo 与 ARDY、SONIC 集成、评估、失败分析和已完成扩展。
- **展示：**10 分钟，必须包含 demo；随后进行 5 分钟 Q&A。
- **视频：**显示文本指令和对应机器人行为，包含 Kimodo 与 ARDY 的成功和失败实验；扩展证据单独展示。
- **公开 GitHub 仓库：**实现代码、配置、安装说明、评估代码和复现指引。
- **Contribution statement：**说明每位成员的实际工作并提供支持证据。

### 11.2 【BONUS】扩展交付物

- speech-to-text interface 与命令标准化代码；
- 在允许公开时提供匿名或获得同意的语音测试输入；
- 仿真 recording 和 LeRobot conversion scripts；
- 在权限允许时提供数据集或可访问链接；
- 模型训练/推理代码、配置和 checkpoints；
- seen/unseen split 定义和评估脚本；
- 扩展成功与失败视频；
- 任何已完成可选比较的 ablation 结果。

### 11.3 仓库结构

```text
configs/
docs/
  archon_workflow/
  interfaces/
simulation/
sonic_adapter/
gripper_control/
methods/
  kimodo/
  ardy/
speech_interface/
data_collection/
lerobot_conversion/
bonus_model/
evaluation/
scripts/
videos_or_links/
```

仓库将尽可能锁定 dependencies，说明 hardware/software requirements，提供 sample inputs 和小规模测试配置，并避免公开 credentials、受限机器人数据或未经许可的第三方材料。

## 12. 可行性、风险与缓解措施

| 风险 | 潜在影响 | 缓解措施 |
|---|---|---|
| Kimodo/ARDY representation mismatch | 生成运动无法公平接入 SONIC | 尽早冻结 canonical motion contract；用小规模测试验证关节顺序、单位、坐标系、频率和轨迹连续性 |
| SONIC 或 G1 集成不稳定 | Tracking failure、平衡问题或不安全动作 | 从固定站姿和上半身动作开始；限制关节范围；先验证慢速 scripted motion，再运行生成轨迹 |
| 抓取/接触不稳定 | 视觉上合理的动作不能可靠接触、闭合或抬起 | 使用明确 pre-grasp/grasp/lift 状态、精确 object pose、独立 hand control 和 contact-aware failure logging |
| 并行实现不兼容 | 各团队方法无法共享 pipeline | 共享 configs、接口测试、每周 integration run 和跨组 code review |
| STT 识别错误 | 目标/动作错误、纠正次数增加或出现不安全指令 | 限制命令语法、使用置信度阈值、低置信度确认、拒绝无效命令并保留文本 fallback |
| STT 服务延迟或隐私 | 交互过慢或语音数据不能公开 | 比较 offline/online 方案，分项记录延迟，获得同意，未经许可不发布语音数据 |
| 训练数据质量问题 | 模型学习不准确或不稳定轨迹 | 优先使用 scripted IK/planner experts，自动检查成功，抽样检查，记录失败原因并报告数据统计 |
| Train/test leakage | 泛化结果虚高 | 训练前定义分离的位置集合，保存 split manifests，调参时不使用测试位置 |
| 算力限制 | 训练或大规模评估无法完成 | 初期冻结 encoders，使用小型 fusion model，优先 deterministic regression，提前 profiling，baseline 完成后再考虑 Flow Matching |
| Scope expansion | Bonus 工作拖延必做 Kimodo/ARDY 比较 | 使用 milestone gates；保持文本基线独立运行；必做交付物受风险时立即暂停扩展 |
| 受限 Archon 或第三方数据 | 学术诚信、安全或 license 问题 | 获得明确许可，记录限制，只公开允许内容并确认全部外部资源 |

## 13. 安全、数据管理与学术诚信

- 所有真机交互均在 Archon 监督和实验室安全流程下进行。
- 在提出任何可选部署计划前，仿真动作需检查 joint limits、collision、instability 和 abnormal commands。
- 语音记录需要参与者知情并同意；对隐私敏感的测试始终可使用文本指令。
- 公开仓库中不得包含 credentials、受限机器人数据、未公开内部材料或未获授权的第三方资产。
- 对外部代码、模型、checkpoints、datasets 和 assets 记录来源和 license。
- 诚实报告实验失败和负面结果；视频选择不得故意隐藏代表性失败模式。
- 任何 sim-to-real 尝试都必须提前向 TAs 提交仿真证据和部署方案，获得明确批准后再进行监督预约。

## 14. LLM Usage Statement

ChatGPT 被用于项目构思和 proposal 撰写，帮助整理课程要求、整合基线与扩展方案、定义功能模块和分工，并改进本文档的结构与措辞。小组将在提交前审查并验证所有技术论述、公式、模型接口、参考资料、代码和实验结果。后续若使用 LLM 或 VLM 辅助编码、分析、写作或系统开发，将在最终报告中说明受影响的组件和具体辅助方式。

## 15. 预期贡献与最终范围说明

必做贡献是在仿真中对 Kimodo 和 ARDY 的 Unitree G1 桌面抓取能力进行受控、可复现的比较。两种方法将使用相同的 SONIC 低层控制器、hand/gripper logic、指令、实验条件、指标和 trial budget。项目将完整记录 motion-to-control pipeline，不仅分析成功案例，也分析集成和物理交互失败。

一体化扩展加入自然语音接口和可训练的 perception-to-motion 路径：

```text
语音 + 图像
  -> 识别后的指令 + 视觉特征
  -> 可训练 G1 reference motion
  -> SONIC
  -> 泛化抓取与抬起
```

其技术贡献是把 speech-conditioned interaction、同步仿真数据采集、LeRobot 格式导出、可训练视觉语言轨迹生成、SONIC-compatible execution 和未见方块位置泛化结合起来。基线比较将优先完成；只有已实现、经过重复实验评估并具有可复现证据的扩展组件，才会在最终项目中被正式宣称为贡献。
