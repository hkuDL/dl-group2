# DASC7606C Track 4 Proposal and Bonus Training Extension

> Editorial note: This document consolidates `DASC7606C_Track4_Proposal.docx` and `Bonus_Proposal.pdf`. Part II has been translated into English for consistency with the main proposal. The original content has been retained as fully as possible; only the Markdown heading hierarchy, tables, lists, equations, and pipeline formatting have been standardized.

## Part I DASC7606C Group Project Proposal

### Track 4 Humanoid-Robot Motion Generation Deployment

#### Comparing Kimodo and ARDY for Text-Driven Tabletop Grasping with SONIC

| Item | Description |
|---|---|
| **Group Size** | 12 students |
| **Primary Platform** | Unitree G1 in simulation; SONIC as the mandatory low-level controller |
| **Core Methods** | Method A: Kimodo-G1 \| Method B: ARDY-G1 |

### 1. Chosen Track, Topic, and Objectives

We select Track 4: Humanoid-Robot Motion Generation Deployment. The project will build a text-to-motion manipulation pipeline for a Unitree G1 humanoid robot in simulation. The robot will receive natural-language instructions and grasp and lift a block from a tabletop scene. SONIC will be used as the common low-level motion controller, while two distinct pretrained motion-generation methods—Kimodo and ARDY—will be implemented and compared under matched conditions.

The project has four primary objectives:

- Build a reproducible G1 tabletop simulation containing a table and graspable block, and integrate SONIC as the low-level controller.
- Deploy pretrained Kimodo-G1 and ARDY-G1 without requiring project-specific model fine-tuning for the baseline.
- Connect both motion generators to the same grasping task and SONIC execution pipeline, including separate hand/gripper control where required.
- Evaluate both methods using repeated trials and a shared instruction set, focusing on grasp success, response time, user corrections, motion precision, physical feasibility, instruction following, and representative failure cases.

### 2. Proposed System and Technical Approach

#### 2.1 Baseline pipeline

The baseline is intentionally deployment-first. We will first establish a minimum working pipeline before attempting optional extensions. No new training dataset or model fine-tuning is required for the baseline; pretrained motion-generation checkpoints will be used.

```text
Natural-language instruction
  → Kimodo / ARDY
  → reference motion
  → G1 adaptation
  → SONIC
  → hand/gripper control
  → simulated grasp and lift
```

#### 2.2 Method A — Kimodo

Kimodo will be used as the first motion-generation method. The team will deploy the available G1-oriented pretrained model, study its text and kinematic-constraint interfaces, generate reference motions for reaching and lifting, and adapt the generated representation to the SONIC execution interface. Spatial constraints such as a target hand/end-effector pose may be derived from the known object pose in simulation.

#### 2.3 Method B — ARDY

ARDY will be used as the second, distinct motion-generation method. The team will deploy its pretrained G1 configuration and construct an equivalent grasping pipeline using the same tabletop scene, grasp targets, SONIC controller, and evaluation protocol. ARDY's interactive/streaming motion-generation capability will also be examined where technically feasible.

#### 2.4 SONIC and manipulation integration

Both methods will use SONIC as the common low-level controller. A central integration task is to determine how each generated motion is represented, how it must be adapted to the G1 embodiment, and how SONIC tracks that reference while maintaining stable whole-body behavior. Hand or gripper actuation will be implemented as a separate control component if it is not covered by the motion representation. For the initial milestone, the table, block, robot start pose, and block pose will be fixed to reduce confounding factors.

### 3. Evaluation Plan

Kimodo and ARDY will be tested using the same instruction set and comparable simulation initial conditions. Each condition will be repeated multiple times. The exact number of trials will be finalized after runtime profiling so that both methods receive a comparable evaluation budget.

| Metric | Definition / Measurement | Purpose |
|---|---|---|
| Grasp success rate | Block is successfully grasped and lifted above a predefined height. | Primary task success |
| Response time | Time from instruction submission to motion availability / task response. | Efficiency |
| User corrections | Number of additional text corrections needed before successful execution. | Interactivity |
| Motion precision | End-effector / grasp-target error where measurable. | Accuracy |
| Physical feasibility | Stability, collisions, joint-limit or visibly infeasible behavior. | Execution quality |
| Failure analysis | Representative reach, grasp, contact, stability, and instruction-following failures. | Technical understanding |

A secondary generalization test may vary the block position after the fixed-scene baseline is stable. This will be treated as an extension rather than a prerequisite for the core comparison.

### 4. Optional Extension / Bonus Direction: VLM/LLM-Guided Instruction Generation

In parallel with the baseline, we propose an optional perception-and-language extension. A simulated head-mounted camera image will be provided to an external vision-language model (VLM), optionally combined with a large language model (LLM), to interpret the scene and generate a structured textual command or motion-level instruction for the downstream motion generator. The resulting text will then be passed to Kimodo or ARDY, followed by the same SONIC execution pipeline.

```text
Simulated camera image + user goal
  → VLM/LLM
  → structured text / spatial instruction
  → Kimodo or ARDY
  → SONIC
  → G1
```

Example: given an image containing a red block and a user request such as “pick up the red block,” the VLM may convert visual context into a more explicit instruction such as “reach the right hand toward the red block on the table, align above it, grasp, then lift.” If reliable geometric information is available from the simulator, it may also be used to form motion constraints rather than asking the VLM to estimate precise coordinates.

This extension is intended to improve interaction and demonstrate a richer perception-to-motion pipeline. It is not assumed to be an automatic formal bonus category; we will confirm with the teaching team that it qualifies as an original extension aligned with Track 4 before presenting it as bonus work. The baseline Kimodo/ARDY comparison will remain independently runnable if the VLM/LLM extension is incomplete.

### 5. Archon Supervised Session

The group will book and attend the required supervised Archon visit. During the session, we will go through the provided real-humanoid demonstration-recording and policy-inference workflows and document the system inputs, recorded data, model outputs, and robot-control flow. The baseline proposal does not depend on training a new policy or deploying our own text-to-motion system on the physical robot.

### 6. Team Organization and Responsibilities

The 12-person team will be organized into two six-person method teams. Each team is responsible for an end-to-end method rather than only one isolated module. This allows Kimodo and ARDY to progress in parallel while enforcing a common interface, simulation scene, SONIC controller, grasp definition, and evaluation protocol.

| Team | Members | Primary responsibilities | Parallel extension responsibility |
|---|---|---|---|
| Team A — Kimodo | Li Jingyao; Meng Guanlin; Hao Hao; Zhang Wenqi; Yuhan; Member 6 (to confirm) | Kimodo-G1 deployment; G1/table/block simulation; Kimodo→SONIC adaptation; grasp/hand control; method-specific evaluation; demo recording. | Implement one branch of the VLM/LLM→text→Kimodo interface and contribute to shared evaluation/reporting. |
| Team B — ARDY | Chen Jianyu; Huang Xinxuan; Zhang Yuanzhuo; Tang Zichun; Zhang Yixin; Member 12 (to confirm) | ARDY-G1 deployment; matched simulation setup; ARDY→SONIC adaptation; grasp/hand control; method-specific evaluation; demo recording. | Implement one branch of the VLM/LLM→text→ARDY interface and contribute to shared evaluation/reporting. |

The meeting minutes identify ten members by name; the remaining two names were not present in the available minutes and are therefore left as placeholders rather than guessed. The final submission will replace these placeholders and specify each member's exact contribution.

#### 6.1 Suggested internal roles within each six-person team

| Role | Responsibility |
|---|---|
| **1. Method lead / integration** | Own the method pipeline, interfaces, schedule, and cross-team compatibility. |
| **2. Model deployment** | Set up the pretrained motion generator and reproduce official inference examples. |
| **3. Simulation + SONIC** | Maintain G1 scene, SONIC execution, and motion-format adaptation. |
| **4. Grasp / hand control** | Define pre-grasp, grasp, lift behavior and separate hand/gripper control. |
| **5. Evaluation + logging** | Implement metrics, repeated-trial scripts, failure logging, and matched comparisons. |
| **6. VLM/LLM extension + documentation** | Build the optional visual-to-text interface and maintain setup/report/demo artifacts. |

### 7. Work Plan and Milestones

| Milestone | Target outcome | Dependency / risk control |
|---|---|---|
| M1 — Independent baselines | Official Kimodo and ARDY inference runs; G1+SONIC simulation operational; simple scripted grasp validated. | Prioritize minimum viable pipeline; avoid fine-tuning. |
| M2 — End-to-end integration | Kimodo→SONIC→G1 grasp and ARDY→SONIC→G1 grasp both runnable. | Use shared motion/grasp interfaces and fixed scene. |
| M3 — Controlled comparison | Repeated trials, metrics, failure taxonomy, successful and failed videos. | Same instructions and comparable conditions. |
| M4 — Optional extension | VLM/LLM converts simulated visual context into downstream text/spatial instruction for both methods. | Keep extension decoupled from baseline. |
| M5 — Final artifacts | Public GitHub, setup/configuration/evaluation code, report, presentation, videos, contribution statement. | Reproducibility review before submission. |

### 8. Expected Deliverables

- A 5–8 page final report describing the Archon session, simulation system, both methods, evaluation, failures, and completed extensions.
- A 10-minute presentation including a required demonstration, followed by Q&A.
- Videos showing the text instructions and corresponding G1 behavior, including successful and failed trials for both Kimodo and ARDY.
- A public GitHub repository containing implementation, configurations, setup instructions, and evaluation code, without credentials or restricted materials.
- A contribution statement documenting each member’s actual work.
- If completed, evidence and code for the VLM/LLM-guided extension.

### 9. Feasibility, Resources, and Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Motion representation mismatch | Kimodo/ARDY output may not directly match SONIC/G1 input. | Validate interfaces early; define a shared adapter and canonical motion format. |
| Grasping/contact instability | Good-looking motion may still fail to grasp or lift. | Start with fixed cube pose; use explicit pre-grasp/grasp/lift stages and separate hand control. |
| Compute constraints | Only limited high-end NVIDIA GPU resources may be available. | Use pretrained inference; avoid baseline fine-tuning; profile before scaling experiments. |
| VLM/LLM API or latency | Extension may be costly, slow, or inconsistent. | Treat as optional and keep baseline independent; confirm available API quota. |
| Integration delay | Two teams may produce incompatible pipelines. | Share simulation, SONIC version, evaluation scripts, interfaces, and weekly integration checkpoints. |

### 10. LLM Usage Statement

ChatGPT was used during project ideation and proposal drafting to help organize the course requirements, meeting decisions, technical work packages, and wording of this proposal. The group will review and verify all technical claims, model interfaces, references, code, and experimental results before submission. Any subsequent use of LLMs or VLMs for coding, analysis, writing, or the proposed system extension will be documented in the final report with the affected components and the nature of the assistance.

### 11. Proposal Scope Summary

The core scope is a controlled comparison of two pretrained text-to-motion methods, Kimodo and ARDY, for Unitree G1 tabletop block grasping in simulation using the same SONIC low-level controller. The team will work as two parallel six-person method groups. The project prioritizes an end-to-end, reproducible baseline over unnecessary training. In parallel, an optional VLM/LLM perception-to-text extension will be explored so that simulated visual observations can be converted into richer instructions for Kimodo and ARDY. Fine-tuning, simulation data collection, and sim-to-real deployment are not baseline dependencies and may only be attempted after the required pipeline and evaluation are stable.

---

## Part II Bonus Training Proposal

### Vision-Language-Conditioned Motion Generation for Tabletop Grasping

### 1. Project Objective

Beyond the core Track 4 task, we plan to add a Bonus Extension that genuinely includes **simulation data collection, model training, and generalization evaluation**.

The baseline task remains unchanged:

> Grasp and lift a block from the table.

The robot does not perform locomotion and remains standing; the table, camera position, and robot initial pose are fixed. The main change introduced by the Bonus Extension is:

> The block position varies randomly.

Based on the current camera image and a natural-language instruction, the model must autonomously generate a G1 motion trajectory that can be executed by SONIC.

The central research question is:

> Can we train a lightweight Vision-Language-Conditioned Motion Generator that uses a single-frame visual observation and a text instruction to generate a SONIC-compatible G1 grasping trajectory and generalize to block positions not seen in the training set?

### 2. Task Definition

The model is defined as:

$$
f_\theta(I,L) \rightarrow Q_{1:T}^{\mathrm{upper}}
$$

where:

$$
I \in \mathbb{R}^{H \times W \times 3}
$$

represents one RGB image captured by the simulated head-mounted camera;

$$
L
$$

represents a natural-language instruction, for example:

```text
Pick up the red block.
```

The model output is:

$$
Q_{1:T}^{\mathrm{upper}}
$$

which is the reference joint trajectory for the G1 upper body over a future time horizon.

The lower-body motion is not generated by the network; instead, it uses a fixed standing reference:

$$
Q_{1:T}^{\mathrm{lower}} = Q^{\mathrm{standing}}
$$

The final complete trajectory is:

$$
Q_{1:T}^{\mathrm{ref}}
=
\left[Q_{1:T}^{\mathrm{lower}},Q_{1:T}^{\mathrm{upper}}\right]
$$

The complete inference pipeline is therefore:

```text
(I, L) → Qᵘᵖᵖᵉʳ₁:ₜ → Qʳᵉᶠ₁:ₜ → SONIC → G1
```

### 3. Model Inputs

The first version of the model uses only two primary inputs.

#### 3.1 RGB Image

The input is one head-camera RGB image at the current time step:

$$
I_t \in \mathbb{R}^{H \times W \times 3}
$$

The visual information is mainly used to determine:

> The position of the target block and its spatial relationship to the robot.

Because the robot initial pose is fixed, the first version does not need to explicitly include the robot state as an input.

If the robot initial pose is randomized in a later stage, the model can be extended to:

$$
f_\theta(I,L,q_t,\dot q_t)
$$

#### 3.2 Language Instruction

The text input specifies the current manipulation goal, for example:

```text
Pick up the red block.
```

If the scene always contains only one block and the instruction is always:

```text
Pick up the block.
```

then the language is effectively constant, and the model could completely ignore the text input.

Therefore, to make the Vision-Language conditioning meaningful, the scene can contain two distinguishable blocks, for example:

```text
red block    blue block
```

The corresponding instruction is:

```text
Pick up the red block.
```

or:

```text
Pick up the blue block.
```

The task itself remains:

> grasp + lift

However, the output trajectory genuinely depends on:

$$
p(Q \mid I,L)
$$

### 4. Model Output and SONIC Interface

The network primarily predicts the upper-body joint trajectory:

$$
Q_{1:T}^{\mathrm{upper}}
$$

The lower body uses a fixed standing motion:

$$
Q_{1:T}^{\mathrm{lower}} = Q^{\mathrm{standing}}
$$

The two components are combined to obtain:

$$
Q_{1:T}^{\mathrm{ref}} \in \mathbb{R}^{T \times 29}
$$

This is the complete G1 29-DoF reference joint position trajectory.

The corresponding joint velocity can be computed by finite differences of the joint positions:

$$
\dot q_t^{\mathrm{ref}}
=
\frac{q_t^{\mathrm{ref}}-q_{t-1}^{\mathrm{ref}}}{\Delta t}
$$

For stationary grasping, the root position and root orientation can use a fixed standing reference.

The reference motion passed to SONIC can therefore be represented uniformly as:

$$
\left(Q^{\mathrm{ref}},\dot Q^{\mathrm{ref}},R^{\mathrm{root}},P^{\mathrm{root}}\right)
$$

where:

$$
Q^{\mathrm{ref}} \in \mathbb{R}^{T \times 29},
\qquad
\dot Q^{\mathrm{ref}} \in \mathbb{R}^{T \times 29}
$$

Hand/gripper control can be implemented as a separate output branch:

$$
G_{1:T}
$$

The final execution pipeline is:

```text
Network → SONIC reference motion → SONIC → G1 grasp
```

### 5. Network Architecture

Because the scene contains only a table, a small number of blocks, and the robot arms, the visual-understanding problem is much simpler than complex environments such as autonomous driving. A heavy perception backbone or BEV architecture is therefore unnecessary.

The proposed architecture is:

```text
Pretrained Vision Encoder
  + Text Encoder
  + Small Fusion Transformer
  + Motion Decoder
```

#### 5.1 Vision Encoder

Candidate model:

> DINOv2 ViT-S/14

or another lightweight pretrained ViT.

Recommended settings:

- Approximately 20–25M parameters;
- Freeze the Vision Backbone in the first stage;
- Do not rely only on the global CLS token;
- Retain the spatial patch tokens.

That is:

$$
I \xrightarrow{\text{Vision Encoder}} Z_v
$$

where:

$$
Z_v \in \mathbb{R}^{N \times D}
$$

The patch-level representation is retained because grasping requires the model to know not only:

> “There is a block in the image.”

but also:

> “Where the block is located.”

#### 5.2 Text Encoder

The text component does not require a large LLM.

A lightweight pretrained text encoder, such as a MiniLM-class model, can be used:

$$
L \xrightarrow{\text{Text Encoder}} Z_l
$$

The pretrained text encoder is also frozen in the first stage.

#### 5.3 Multimodal Fusion

The visual tokens and text tokens are projected into a shared dimension:

$$
d_{\mathrm{model}} = 256
$$

A small Transformer is then used for multimodal fusion.

The recommended initial configuration is:

| Module | Configuration |
|---|---|
| Vision Encoder | DINOv2 ViT-S/14, Frozen |
| Text Encoder | MiniLM-class, Frozen |
| Hidden Dimension | 256 |
| Fusion Transformer | 4 Layers |
| Attention Heads | 8 |
| FFN Dimension | 1024 |
| Trainable Parameters | Approximately 5–10M |

The complete representation pipeline is:

$$
I \rightarrow Z_v
$$

$$
L \rightarrow Z_l
$$

$$
(Z_v,Z_l) \rightarrow Z_{\mathrm{condition}}
$$

### 6. Motion Decoder

The Motion Decoder can be implemented in two stages.

#### 6.1 Option A: Deterministic Transformer Regression

The first version uses the simplest and lowest-risk Transformer trajectory decoder.

The model directly predicts:

$$
(Z_v,Z_l) \rightarrow \hat Q_{1:T}
$$

A set of learned trajectory queries can be defined:

$$
e_1,e_2,\ldots,e_T
$$

Each query corresponds to one future timestep.

The joint position loss is:

$$
\mathcal{L}_{\mathrm{pos}}
=
\frac{1}{T}\sum_{t=1}^{T}
\left\|\hat q_t-q_t^{GT}\right\|_1
$$

To improve trajectory smoothness, a velocity consistency loss can be added:

$$
\mathcal{L}_{\mathrm{vel}}
=
\frac{1}{T-1}\sum_{t=2}^{T}
\left\|
(\hat q_t-\hat q_{t-1})
-(q_t^{GT}-q_{t-1}^{GT})
\right\|_1
$$

The total loss is:

$$
\mathcal{L}
=
\mathcal{L}_{\mathrm{pos}}+\lambda\mathcal{L}_{\mathrm{vel}}
$$

#### 6.2 Option B: Flow Matching Motion Generation

If the deterministic baseline works reliably, the motion decoder can be further replaced with a Flow Matching / DiT-style generator.

The model learns:

$$
v_\theta(Q_\tau,\tau,Z_{\mathrm{condition}})
$$

The trajectory-generation process is:

$$
\frac{dQ_\tau}{d\tau}
=
v_\theta(Q_\tau,\tau,Z_{\mathrm{condition}})
$$

Generation starts from a simple noise distribution:

$$
Q_{\tau=0}\sim\mathcal{N}(0,I)
$$

and produces:

$$
Q_{\tau=1}=Q_{1:T}^{\mathrm{ref}}
$$

This makes it possible to compare:

> Deterministic Transformer Regression

with:

> Flow-Matching Motion Generation

to determine whether they differ in motion quality, generalization, and inference speed.

The first version does not require a Proposal Transformer. For the current single tabletop grasping task, direct conditional trajectory generation is simpler and makes the experimental variables easier to control.

### 7. Simulation Data Collection

The training data are generated automatically in simulation.

Each episode can be constructed using the following procedure:

1. Reset the G1 to a fixed standing initial pose;
2. Randomly sample a block position within the reachable area of the table;
3. Render the current head-camera RGB image;
4. Use an expert controller to generate a grasp-and-lift trajectory;
5. Execute the trajectory in simulation;
6. Check whether the block is successfully grasped and lifted;
7. Save the successful episode.

A single training sample can be represented as:

$$
D_i = \left(I_i,L_i,Q_i^{GT},G_i^{GT}\right)
$$

where:

- $I_i$: head-camera RGB image;
- $L_i$: language instruction;
- $Q_i^{GT}$: expert joint trajectory;
- $G_i^{GT}$: hand/gripper command.

### 8. Expert Trajectory Generation

The Ground Truth trajectories required for training can be generated automatically in simulation.

The first choice is:

> Scripted IK / Motion Planner

For example:

```text
initial pose → pre-grasp pose → grasp pose → lift pose
```

Scripted IK trajectories are preferred because:

- The geometric relationships are explicit;
- The grasp target is precise;
- Data-generation cost is low;
- Large training datasets can be generated automatically;
- They do not introduce additional errors from a pretrained motion generator.

If Kimodo or ARDY can reliably generate high-quality grasp motions, they can also be used as additional demonstration sources.

### 9. Generalization-Oriented Dataset Design

The training and test sets must be separated by block position.

For example, the reachable workspace on the table can be defined as:

$$
x\in[x_{\min},x_{\max}],
\qquad
y\in[y_{\min},y_{\max}]
$$

A set of positions is randomly sampled for training:

$$
\mathcal{P}_{\mathrm{train}}
$$

Different positions are used for testing:

$$
\mathcal{P}_{\mathrm{test}}
$$

such that:

$$
\mathcal{P}_{\mathrm{train}}\cap\mathcal{P}_{\mathrm{test}}=\varnothing
$$

The evaluation therefore measures whether the model can use visual input to generalize to unseen block positions, rather than merely memorizing a fixed trajectory.

### 10. Evaluation

The primary evaluation metrics include:

#### 10.1 Grasp Success Rate

Defined as:

$$
\text{Success Rate}
=
\frac{\text{number of episodes successfully grasped and lifted}}
{\text{total number of episodes}}
$$

#### 10.2 Target Selection Accuracy

If multiple blocks are present, this metric checks whether the robot grasps the target specified by the language instruction.

#### 10.3 Motion Precision

Compute the error between the end-effector and the desired grasp pose:

$$
E_{\mathrm{EE}}
=
\left\|p_{\mathrm{EE}}-p_{\mathrm{target}}\right\|_2
$$

#### 10.4 Physical Feasibility

Record the following failure modes:

- joint-limit violation;
- collision;
- unstable motion;
- SONIC tracking failure;
- grasp/contact failure.

#### 10.5 Inference Latency

Measure the time required from:

```text
camera input → complete motion available
```

This is the end-to-end inference latency.

#### 10.6 Generalization

Report separately:

- Seen-position Success Rate;
- Unseen-position Success Rate.

### 11. Optional Ablation Study

If time and compute resources permit, the following controlled experiments can be conducted:

1. Vision backbone frozen vs. partial fine-tuning;
2. global visual embedding vs. spatial patch tokens;
3. Vision-only vs. Vision-Language conditioning;
4. Transformer Regression vs. Flow Matching;
5. seen block positions vs. unseen block positions.

Completing all ablations is not required. Priority should be given to a complete:

```text
data → training → SONIC execution → evaluation
```

pipeline.

### 12. Expected Contributions

The main contribution of this Bonus Extension is not to add a new robot task, but to augment the fixed grasp-and-lift task with:

1. simulation dataset generation;
2. vision-conditioned motion generation;
3. language-conditioned target selection;
4. trainable trajectory generation;
5. unseen object position generalization;
6. SONIC-compatible motion execution.

The complete pipeline is:

```text
Simulation Data Collection
  → Vision-Language Encoding
  → Motion Generator Training
  → SONIC
  → Generalized Grasping
```

The final objective can be summarized as:

> **Vision-Language Conditioned Motion Generation for Generalized Tabletop Grasping**

That is:

```text
Image + Text → G1 Reference Motion → SONIC → Grasp and Lift
```
