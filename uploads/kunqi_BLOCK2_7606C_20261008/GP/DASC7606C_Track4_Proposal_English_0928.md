# DASC7606C Group Project Proposal

## Speech- and Vision-Language-Conditioned Motion Generation for Unitree G1 Tabletop Grasping with SONIC

### A Controlled Comparison of Kimodo and ARDY with an Integrated Data-Collection and Training Extension

| Item | Description |
|---|---|
| Track | Track 4: Humanoid-Robot Motion Generation Deployment |
| Group size | 12 students |
| Robot and environment | Unitree G1 in simulation, with a supervised Archon real-robot session |
| Required low-level controller | SONIC |
| Core motion-generation methods | Kimodo and ARDY |
| Core task | Text-driven tabletop block grasping and lifting |
| Integrated extension | Speech-to-text input plus simulation data collection, trainable vision-language-conditioned motion generation, and unseen-position generalization |

### Group Members

Fu Yuhan; Hao Hao; Huang Xinxuan; Li Jingyao; Luo Mingdi; Meng Guanlin; Mi Siyuan; Tang Zichun; Tu Chengyuan; Zhang Kunqi; Zhang Yixin; Zhang Yuanzhuo.

## 1. Executive Summary

This project will build and evaluate a natural-language-controlled tabletop manipulation system for a Unitree G1 humanoid robot in simulation. The required baseline will compare two distinct pretrained motion-generation methods, Kimodo and ARDY, under matched conditions. Both methods will use the same simulation scene, instruction set, motion-adaptation interface, SONIC low-level controller, hand/gripper controller, and evaluation protocol. The target behavior is to make the G1 reach toward, grasp, and lift a block from a table in response to typed natural-language instructions.

The project will also include one coherent optional extension rather than several disconnected bonus ideas. The extension combines two capabilities:

1. a speech-to-text interface that converts spoken commands into the same textual instruction representation used by the baseline; and
2. a trainable vision-language-conditioned motion generator that uses a simulated head-camera image and the recognized instruction to generate a SONIC-compatible G1 upper-body reference trajectory.

The extension will be supported by automated simulation data collection, LeRobot-format export, model training, and generalization tests on block positions not seen during training. The typed-input Kimodo/ARDY baseline will remain independently runnable, so the required Track 4 deliverables do not depend on completion of the optional extension.

## 2. Background and Motivation

Track 4 asks how natural-language instructions can control a Unitree G1 humanoid robot. The main technical challenge is not only generating a plausible human-like motion, but also adapting that motion to the G1 embodiment, executing it through SONIC, coordinating a separate hand or gripper controller, maintaining lower-body stability, and interacting successfully with an object.

Kimodo and ARDY provide two distinct motion-generation approaches suitable for a controlled comparison. Using the same downstream controller and scene will allow the group to study differences in instruction following, grasp-pose accuracy, physical feasibility, response time, correction requirements, and integration complexity.

The integrated extension addresses two limitations of a text-only fixed-scene baseline. First, spoken commands offer a more natural interaction channel but introduce recognition errors and additional latency. Second, a fixed text-to-motion model may not use current visual information to adapt to new block locations. By combining speech-to-text with a trainable vision-language-conditioned motion generator, the extension studies the complete path from spoken intent and visual observation to executable robot motion.

## 3. Project Scope and Course Requirement Alignment

### 3.1 Required Core Scope

The core project will deliver all required Track 4 components:

- attend and document the supervised Archon demonstration-recording and policy-inference session;
- build a Unitree G1 tabletop simulation with a table and graspable block;
- use SONIC as the low-level controller;
- accept typed natural-language instructions;
- implement Kimodo and ARDY as two distinct motion-generation methods;
- adapt both methods to one shared G1/SONIC execution interface;
- implement any required separate hand or gripper control;
- demonstrate grasping and lifting in simulation;
- evaluate both methods with shared instructions, comparable initial conditions, repeated trials, clear success criteria, and representative failures; and
- explain lower-body stabilization when upper-body motion is controlled.

### 3.2 [BONUS] Integrated Optional Extension

The optional extension has two linked layers:

- **Speech interaction layer:** spoken command -> automatic speech recognition -> validated textual instruction.
- **Trainable visual-motion layer:** simulated head-camera image + textual instruction -> trainable motion generator -> SONIC-compatible G1 reference motion.

Speech-to-text alone is not claimed as the complete extra-credit contribution. The substantive extension is the end-to-end combination of simulation data collection, trainable visual-language motion generation, SONIC execution, and unseen-position generalization. The group will confirm the extension scope with the teaching team before presenting it as formal bonus work.

### 3.3 Scope Boundaries

- The required baseline uses pretrained Kimodo and ARDY checkpoints and does not require project-specific fine-tuning.
- Typed text remains the required and reliable input mode; speech input is an optional layer with a typed fallback.
- The first stable scene will use a fixed robot pose, table pose, and block pose.
- Position randomization, multiple distinguishable blocks, dataset generation, and model training belong to the extension.
- The required Archon session is for understanding the real-robot data-collection and inference workflows. The project does not depend on deploying the group's own system on the physical robot.
- Sim-to-real deployment will only be considered after TA review, approval, and completion of the required simulation evidence.

### 3.4 Requirement Traceability

| Track 4 requirement | Planned evidence |
|---|---|
| Archon session and workflow understanding | Attendance record, permitted photos or notes, and a report section explaining inputs, recorded data, model outputs, control flow, safety, and observed failure/recovery behavior |
| SONIC integration | Shared canonical motion interface, G1 adapter, SONIC configuration, controller diagram, tracking logs, and lower-body stabilization explanation |
| Text-driven grasping | Typed instruction demo showing reach, grasp, and lift; step-by-step commands supported where needed |
| Two distinct methods | Independent Kimodo and ARDY implementations using the same SONIC controller and scene |
| Evaluation and analysis | Repeated trials, shared instructions and seeds, success rate, response time, correction count, precision, feasibility, and failure taxonomy |
| Demo and reproducibility | Successful and failed videos for both methods, public GitHub repository, setup instructions, configurations, and evaluation scripts |
| Report and presentation | 5-8 page report excluding references; 10-minute presentation with required demo; 5-minute Q&A |

## 4. Objectives and Research Questions

### 4.1 Core Objectives

1. Build a reproducible G1 tabletop simulation and integrate SONIC as the shared low-level controller.
2. Reproduce and deploy the available G1-oriented Kimodo and ARDY inference pipelines.
3. Define a canonical motion representation so both methods can be adapted fairly to the same G1/SONIC interface.
4. Implement reliable grasp sequencing and separate hand/gripper control where required.
5. Compare Kimodo and ARDY under matched instructions, initial conditions, compute budgets, and evaluation criteria.
6. Produce clear demonstrations, failure analysis, and reproducible code and configurations.

### 4.2 Core Research Questions

- How do Kimodo and ARDY differ in instruction following and their ability to reach a specified grasp pose?
- Do spatial constraints or interactive text corrections improve grasp success?
- What trade-offs exist among motion quality, response time, physical feasibility, and ease of SONIC integration?
- Which failure modes originate in motion generation, embodiment adaptation, SONIC tracking, hand control, contact dynamics, or instruction interpretation?

### 4.3 [BONUS] Extension Research Questions

- How accurately and quickly can speech-to-text convert spoken manipulation commands into task-valid instructions?
- How do speech-recognition errors affect user corrections, total response time, and grasp success compared with typed input?
- Can a lightweight vision-language-conditioned motion generator produce SONIC-compatible grasp trajectories from a single head-camera image and a textual instruction?
- Can the trained model generalize to block positions excluded from the training set?
- If time permits, how do deterministic Transformer regression and Flow Matching differ in motion quality, inference speed, and generalization?

## 5. Overall System Design

### 5.1 Required Baseline Pipeline

```text
Typed natural-language instruction
  -> instruction validation and task parsing
  -> Kimodo or ARDY
  -> method-specific output adapter
  -> canonical G1 reference motion
  -> SONIC low-level controller
  -> separate hand/gripper controller
  -> simulated grasp and lift
```

### 5.2 [BONUS] Speech-Enabled Pipeline

```text
Spoken command
  -> speech-to-text
  -> confidence check and command normalization
  -> the same textual instruction interface
  -> Kimodo or ARDY
  -> G1 motion adapter
  -> SONIC and hand/gripper control
```

If recognition confidence is low or the parsed command is invalid, the interface will request repetition or allow typed correction. The recognized transcript, confidence, latency, correction count, and final accepted command will be logged.

### 5.3 [BONUS] Trainable Vision-Language Extension Pipeline

```text
Audio ----------------> speech-to-text ----------------> instruction L
                                                              |
Head-camera image I -> vision-language-conditioned model -----+
                              |
                              v
                    upper-body trajectory Q_upper
                              |
fixed standing reference -> complete G1 reference motion Q_ref
                              |
                       SONIC + gripper control
                              |
                       generalized grasp and lift
```

The extension model is defined as:

$$
f_\theta(I,L) \rightarrow Q_{1:T}^{\mathrm{upper}},
\qquad
I \in \mathbb{R}^{H \times W \times 3}.
$$

The lower body initially uses a fixed standing reference:

$$
Q_{1:T}^{\mathrm{lower}}=Q^{\mathrm{standing}},
$$

and the complete motion is:

$$
Q_{1:T}^{\mathrm{ref}}
=
\left[Q_{1:T}^{\mathrm{lower}},Q_{1:T}^{\mathrm{upper}}\right]
\in \mathbb{R}^{T\times29}.
$$

Joint velocities can be derived by finite differences:

$$
\dot q_t^{\mathrm{ref}}
=
\frac{q_t^{\mathrm{ref}}-q_{t-1}^{\mathrm{ref}}}{\Delta t}.
$$

For stationary grasping, the root position and orientation will use the standing reference unless the selected SONIC interface requires another representation. Hand/gripper commands will be represented by a separate sequence $G_{1:T}$ and synchronized with the arm trajectory.

## 6. Functional Modules and Technical Plan

### 6.1 Module Overview

The following scope labels are used throughout this section: **CORE** denotes functionality required for the Track 4 deliverables; **BONUS** denotes optional work that begins only after the core baseline is stable and must not block the required submission; **CORE + BONUS** denotes shared infrastructure used to evaluate both the required baseline and any completed extensions.

| ID | Scope | Functional module | Main functions | Outputs and acceptance criteria | Primary owner |
|---|---|---|---|---|---|
| M1 | **CORE**; position randomization, multiple blocks, and training-camera data are **BONUS** | Simulation scene and task definition | Configure G1, table, block assets, the core camera, fixed initial states, reset logic, and success conditions; reserve randomization and data hooks for bonus work | Core: deterministic reset and fixed-scene grasping; Bonus: reachable-region randomization, multi-target settings, and training observations | Team 1 |
| M2 | **CORE** | Canonical motion interface and SONIC integration | Define motion schema, map joint order and units, resample trajectories, compute velocity references, configure standing/root reference, and execute through SONIC | Both Kimodo and ARDY can send comparable reference motions through the same tested interface | Team 1, with Teams 2 and 3 |
| M3 | **CORE** | Grasp and hand control | Implement open, pre-grasp, approach, close, lift, release, and recovery states; synchronize hand commands with reference motion | Block can be grasped and lifted; hand/gripper behavior is logged separately | Team 1 |
| M4 | **CORE** | Kimodo pipeline | Reproduce official inference, define inputs and constraints, generate motion, adapt output, and document method-specific limitations | End-to-end Kimodo -> SONIC -> G1 grasp pipeline with reproducible configuration | Team 2 |
| M5 | **CORE** | ARDY pipeline | Reproduce official G1 inference, investigate interactive/streaming generation, adapt output, and document correction behavior | End-to-end ARDY -> SONIC -> G1 grasp pipeline with reproducible configuration | Team 3 |
| M6 | **BONUS** | Speech-to-text and instruction interface | Capture audio, run ASR, normalize commands, validate task syntax, handle confidence and retries, and provide typed fallback | Spoken commands reliably reach the same text interface; transcript, confidence, latency, and corrections are logged | Team 4 |
| M7 | **BONUS** | Simulation data collection and LeRobot export | Generate expert trajectories, capture synchronized images/states/actions, store instructions and timestamps, mark episode boundaries, perform quality checks, and convert to LeRobot format | Reusable dataset with scripts, schema, metadata, quality report, and accessible storage or link | Team 1, with Team 4 quality control |
| M8 | **BONUS** | Trainable vision-language motion model | Implement visual/text encoders, multimodal fusion, a deterministic Transformer trajectory decoder, losses, training, checkpointing, and a SONIC inference adapter; retain Diffusion/Flow Matching only as a later optional ablation | Trained model generates SONIC-compatible upper-body trajectories and runs in the shared scene | Teams 2 and 3 |
| M9 | **CORE + BONUS** | Evaluation, logging, and failure analysis | Evaluate Kimodo and ARDY in the core phase; add STT, dataset-quality, trained-model, and generalization evaluation only for completed extensions | Fair and reproducible core comparison; separate extension results for any completed bonus work | Team 4 |
| M10 | **CORE** | Archon, safety, documentation, and release | Record supervised workflow, maintain setup guides and contribution evidence, review licenses/data restrictions, and assemble report/demo/repository | Accurate Archon section, public repository without restricted materials, complete contribution statement | Team 4, with all teams contributing |

### 6.2 Shared Motion Contract

To prevent incompatible pipelines, all motion methods will export a common representation before entering SONIC:

```text
CanonicalMotion
  joint_names
  q_ref[T, 29]
  qdot_ref[T, 29] or derivation rule
  timestamps[T]
  root_position[T]
  root_orientation[T]
  optional_hand_command[T]
  metadata: method, instruction, seed, object pose, checkpoint
```

The interface specification will define joint order, units, coordinate frames, sampling frequency, trajectory duration, missing-joint policy, clipping rules, and interpolation. Kimodo and ARDY will keep their method-specific representations internally but must pass through this common contract for evaluation.

### 6.3 Simulation and Task State Machine

The initial task state machine will be:

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
  -> END or RECOVER
```

Core experiments will fix the robot start pose, table pose, block pose, and camera pose. After both baseline methods are stable, the extension will randomize block positions within a documented reachable region. If multiple blocks are used, color or identity will be included in the instruction to make language conditioning meaningful.

### 6.4 Kimodo Method

The Kimodo team will:

- reproduce the available G1-oriented pretrained inference example;
- document text inputs, kinematic constraints, motion representation, checkpoint, preprocessing, and compute requirements;
- generate reaching, grasp-approach, and lifting reference motions;
- determine whether object-derived hand or end-effector constraints can improve precision;
- map Kimodo output to the canonical motion contract;
- integrate with the common SONIC and gripper interfaces; and
- log method-specific failures, including unreachable constraints, discontinuities, joint-limit issues, and contact failures.

### 6.5 ARDY Method

The ARDY team will:

- reproduce the pretrained G1 configuration and official inference examples;
- document model inputs, outputs, checkpoints, preprocessing, and compute requirements;
- investigate its interactive or streaming generation capability where technically feasible;
- implement equivalent reaching, grasp-approach, and lifting behavior under the same task definition;
- map ARDY output to the canonical motion contract;
- integrate with the same SONIC and gripper interfaces; and
- log method-specific failures and any effects of interactive correction.

### 6.6 [BONUS] Speech-to-Text Interface

The speech module will not directly control the robot. It will produce a validated textual command for the same instruction interface used by typed input. The initial command grammar will support target identity and manipulation stages, for example:

```text
Pick up the red block.
Reach toward the blue block.
Adjust the right hand above the block.
Grasp the block.
Lift the block.
```

The module will include:

- audio capture and explicit start/stop controls;
- a selected offline or online ASR engine, chosen after latency, privacy, and deployment testing;
- text normalization for object names, colors, and action verbs;
- confidence thresholding and rejection of out-of-scope commands;
- confirmation or retry when confidence is low;
- typed correction and typed fallback;
- logs of raw transcript, normalized command, confidence, latency, and number of corrections; and
- a privacy rule that no participant voice recording is published without permission.

### 6.7 [BONUS] Simulation Data Collection

For the training extension, each episode will:

1. reset the G1 to a fixed standing pose;
2. sample a block position in the reachable tabletop region;
3. render a head-camera RGB image;
4. assign a typed or speech-derived instruction;
5. use scripted inverse kinematics or a motion planner to generate an expert pre-grasp, grasp, and lift trajectory;
6. execute the trajectory in simulation;
7. verify success and flag failure reasons;
8. save synchronized observations, robot states, actions, joint references, hand commands, timestamps, and episode boundaries; and
9. convert accepted episodes to LeRobot format.

The compact training target can be written as:

$$
D_i=\left(I_i,L_i,Q_i^{GT},G_i^{GT}\right),
$$

while the released episode representation will additionally contain synchronized robot states, actions, timestamps, camera metadata, success labels, and optional audio/transcript metadata.

Scripted IK or motion planning is the first expert source because it provides explicit geometry, accurate grasp targets, low data-generation cost, and limited contamination from pretrained model errors. High-quality Kimodo or ARDY rollouts may be retained as an additional demonstration source, but will be labeled separately.

### 6.8 [BONUS] Trainable Vision-Language Motion Generator

The proposed lightweight architecture is:

```text
Pretrained Vision Encoder
  + Lightweight Text Encoder
  + Small Multimodal Fusion Transformer
  + Motion Decoder
```

The initial configuration is:

| Component | Initial configuration |
|---|---|
| Vision encoder | DINOv2 ViT-S/14 or another lightweight pretrained ViT; frozen initially; spatial patch tokens retained |
| Text encoder | MiniLM-class pretrained encoder; frozen initially |
| Shared hidden dimension | 256 |
| Fusion Transformer | 4 layers, 8 attention heads, FFN dimension 1024 |
| Estimated trainable parameters | Approximately 5-10M, excluding frozen encoders |
| Primary decoder | Deterministic Transformer trajectory regression |
| Optional decoder | Flow Matching / DiT-style motion generator after the deterministic baseline is stable |

The representation pipeline is:

$$
I\rightarrow Z_v,
\qquad
L\rightarrow Z_l,
\qquad
(Z_v,Z_l)\rightarrow Z_{\mathrm{condition}}.
$$

The deterministic decoder predicts:

$$
(Z_v,Z_l)\rightarrow\hat Q_{1:T}.
$$

The initial training objective is:

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

If the deterministic baseline is reliable, the optional Flow Matching decoder will learn:

$$
v_\theta(Q_\tau,\tau,Z_{\mathrm{condition}}),
\qquad
\frac{dQ_\tau}{d\tau}
=
v_\theta(Q_\tau,\tau,Z_{\mathrm{condition}}),
$$

starting from $Q_{\tau=0}\sim\mathcal{N}(0,I)$ and generating $Q_{\tau=1}=Q_{1:T}^{\mathrm{ref}}$.

### 6.9 [BONUS] Generalization Design

The train and test sets will be separated by block position. For a reachable tabletop region:

$$
x\in[x_{\min},x_{\max}],
\qquad
y\in[y_{\min},y_{\max}],
$$

the sampled position sets will satisfy:

$$
\mathcal{P}_{\mathrm{train}}\cap\mathcal{P}_{\mathrm{test}}=\varnothing.
$$

The main generalization comparison will report seen-position and unseen-position performance. If multiple colored blocks are used, target identities will also be separated and documented so target-selection accuracy can be measured without leakage.

## 7. Archon Supervised Session Plan

The group will book the session at least two days in advance and attend under supervision. The report will accurately document:

- the robot and sensor configuration;
- demonstration-recording inputs and operator interface;
- recorded observations, robot states, actions, timestamps, and episode boundaries;
- data storage and quality-control procedures;
- policy-inference inputs and preprocessing;
- model outputs and their representation;
- the transformation from model output to robot control command;
- the low-level controller, hand/gripper branch, safety filters, emergency stop, and recovery procedure;
- at least one successful workflow and one observed or described failure mode; and
- similarities and differences between the Archon workflow and the group's simulation/SONIC pipeline.

Only permitted notes, images, videos, and non-restricted metadata will be retained. The group will not publish credentials, restricted robot data, internal code, or third-party material without permission.

## 8. Evaluation Plan

### 8.1 Experimental Controls

The core Kimodo/ARDY comparison will use:

- the same G1 model, simulator, scene assets, table and object geometry;
- the same SONIC version, controller configuration, standing reference, and gripper logic;
- the same instruction semantics and grasp success definition;
- matched initial conditions and evaluation seeds;
- the same trajectory duration and resampling rules where applicable;
- comparable compute and inference budgets; and
- the same number of repeated trials per condition.

The target is at least 20 trials per reported condition after pilot testing. If runtime or compute constraints require a different count, the final count will be identical across compared methods and explicitly reported.

### 8.2 Core Comparison Matrix

| Factor | Core levels | Extension levels |
|---|---|---|
| Motion method | Kimodo, ARDY | Trainable vision-language generator when available |
| Instruction input | Typed text | Speech-to-text with typed correction |
| Scene | Fixed robot, table, camera, and block pose | Randomized block positions; optionally multiple distinguishable blocks |
| Controller | Same SONIC configuration | Same SONIC configuration |
| Evaluation seeds | Shared held-out seeds | Disjoint seen/unseen position sets |

### 8.3 Metrics

| Metric | Definition or measurement | Applies to |
|---|---|---|
| Grasp success rate | Fraction of trials in which the target block is grasped and lifted above a predefined height for a predefined duration | All motion methods |
| Target-selection accuracy | Fraction of multi-object trials in which the instructed object is selected | Language/vision extension |
| Instruction-following accuracy | Completion of the requested target and action sequence | All methods |
| Response time | Instruction submission to motion availability; also report ASR and motion-generation components separately | All methods and STT |
| User corrections | Number of repeated or corrected commands before accepted execution | Typed and speech input |
| Speech recognition quality | Word error rate plus task-level intent/slot accuracy for target and action words | STT extension |
| Motion precision | End-effector or grasp-pose error, $E_{EE}=\|p_{EE}-p_{target}\|_2$, where measurable | All motion methods |
| SONIC tracking quality | Reference-to-executed joint error and tracking failures where available | All motion methods |
| Physical feasibility | Joint-limit violations, collisions, unstable motion, foot/root instability, and infeasible contact behavior | All motion methods |
| Generalization | Seen-position and unseen-position success rates under disjoint position sets | Trainable extension |
| Failure analysis | Counts and representative cases for perception, ASR, instruction, generation, adaptation, controller, grasp/contact, and stability failures | Entire system |

### 8.4 Planned Analyses

- Kimodo vs. ARDY under typed instructions and fixed conditions.
- Typed vs. speech-derived instructions for each stable method.
- Performance before and after spatial constraints or interactive corrections, where supported.
- Seen vs. unseen block positions for the trainable extension.
- Vision-only vs. vision-language conditioning, if the dataset supports multiple targets.
- Global visual embedding vs. spatial patch tokens, if compute permits.
- Frozen vs. partially fine-tuned visual backbone, if compute permits.
- Deterministic regression vs. Flow Matching, only after the deterministic training baseline is complete.

High success rate alone will not be treated as sufficient. The analysis will emphasize fair conditions, repeated trials, uncertainty, integration trade-offs, representative failures, and technically grounded interpretation.

## 9. Team Structure and Responsibilities

The group will be organized by functional module rather than by two independent end-to-end method teams. The four functional teams will be led by Fu Yuhan, Meng Guanlin, Li Jingyao, and Hao Hao, respectively. Shared infrastructure will be implemented once, with explicit interfaces for Kimodo, ARDY, and the optional trainable model. Each team must finish its **CORE** responsibilities before starting its **BONUS** responsibilities.

### 9.1 Functional Teams

| Team | Lead and members | **CORE** primary ownership | **BONUS** responsibility after the core gate |
|---|---|---|---|
| Team 1: Simulation, SONIC, and Grasp Control | **Lead: Fu Yuhan**; Luo Mingdi; Tu Chengyuan | Simulation scene, G1 configuration, canonical motion contract, SONIC integration, fixed standing/lower-body stabilization, hand/gripper control, and scripted-grasp validation | Position randomization, expert IK/planner batch rollouts, synchronized data collection, and LeRobot conversion |
| Team 2: Kimodo | **Lead: Meng Guanlin**; Tang Zichun; Zhang Kunqi | Kimodo deployment, text/kinematic constraints, G1 output adaptation, shared SONIC interface, method-specific tests, and failure analysis | Visual/text encoding, multimodal fusion, and dataset-interface support for the trainable model |
| Team 3: ARDY | **Lead: Li Jingyao**; Huang Xinxuan; Zhang Yuanzhuo | ARDY deployment, streaming/interactive behavior, constraints, G1 output adaptation, shared SONIC interface, method-specific tests, and failure analysis | Deterministic trajectory decoder and SONIC adapter; Diffusion/Flow Matching ablation only if compute and schedule permit |
| Team 4: Evaluation, Speech, and Release | **Lead: Hao Hao**; Mi Siyuan; Zhang Yixin | Experiment design, common seeds/logs, metrics, failure taxonomy, statistical summaries, video evidence, report/presentation integration, and repository reproducibility | Speech-to-text and command normalization; evaluation of STT effects, seen/unseen generalization, dataset quality, and the end-to-end trained model |

### 9.2 Provisional Member-Level Responsibilities

These assignments define initial ownership. The final contribution statement will describe actual completed work and supporting evidence.

| Member | Initial responsibility |
|---|---|
| Fu Yuhan | **Team 1 lead**; shared simulation/SONIC architecture, canonical interface, lower-body stabilization strategy, and cross-team integration |
| Luo Mingdi | **CORE:** scene assets, camera setup, fixed reset, and observation hooks; **BONUS:** position randomization and training-data hooks |
| Tu Chengyuan | **CORE:** hand/gripper controller, grasp state machine, and scripted grasp; **BONUS:** expert IK/planner and data-collection execution |
| Meng Guanlin | **Team 2 lead**; Kimodo technical direction, constraints, canonical-motion adapter, and SONIC integration coordination |
| Tang Zichun | **CORE:** Kimodo inference reproduction, output adaptation, and interface tests; **BONUS:** multimodal-fusion support |
| Zhang Kunqi | **CORE:** Kimodo-specific testing, failure logging, and reproduction documentation; **BONUS:** visual/text encoder and dataset-interface support |
| Li Jingyao | **Team 3 lead**; ARDY technical direction, official inference reproduction, shared interface, and cross-team coordination |
| Huang Xinxuan | **CORE:** ARDY deployment, constraints, method-specific testing, and failure analysis; **BONUS:** trajectory-decoder support |
| Zhang Yuanzhuo | **CORE:** ARDY streaming/interactive interface, canonical-motion adapter, and SONIC debugging; **BONUS:** trained-model inference adapter |
| Hao Hao | **Team 4 lead**; core evaluation protocol, result tables, cross-team experiment coordination, and bonus evaluation gate |
| Mi Siyuan | **CORE:** common logging and experiment records; **BONUS:** speech-to-text, command normalization, confidence/retry logic, and STT evaluation |
| Zhang Yixin | **CORE:** statistical summaries, failure taxonomy, videos, and report/presentation integration; **BONUS:** seen/unseen, dataset-quality, and ablation evaluation |

### 9.3 Shared Engineering Rules

- All teams will use one agreed simulator version, G1 model, SONIC revision, coordinate convention, and configuration format.
- Interfaces will be documented before independent method development.
- Each feature will have an owner, reviewer, test case, configuration, and evidence link.
- Pull requests or equivalent reviews will be used for shared interfaces and evaluation code.
- Weekly integration checks will run both methods through the current common pipeline.
- Individual contribution records will include tasks, commits or files, experiments, results, reviews, and meeting decisions.

## 10. Work Plan and Milestones

| Milestone | Main work | Exit criteria |
|---|---|---|
| M0: Requirements and Archon workflow | Confirm course scope, attend the Archon session, record data-collection/inference workflows, and freeze the initial interface plan | Approved scope notes; complete Archon workflow record; safety and publication restrictions documented |
| M1: Shared platform | Build G1/table/block simulation, scripted grasp, canonical motion contract, SONIC execution, standing reference, and gripper state machine | A scripted reference motion grasps and lifts the block reproducibly through SONIC |
| M2: Independent method baselines | Reproduce Kimodo and ARDY inference and map outputs to the canonical representation | Official examples reproduced; both methods generate inspectable G1 reference motions |
| M3: Core end-to-end integration | Run Kimodo and ARDY through the shared SONIC and gripper pipeline using typed instructions | Both required pipelines complete at least one end-to-end grasp-and-lift trial |
| M4: Controlled core evaluation | Freeze instructions, seeds, success criteria, trial budget, and logging; collect successful and failed trials | Fair repeated-trial comparison with complete logs, metrics, videos, and failure labels |
| M5: **BONUS** speech extension | Add speech capture, ASR, normalization, confidence handling, typed fallback, and latency/error logging | Spoken commands control at least one stable baseline method; STT accuracy and latency reported |
| M6: **BONUS** data and training extension | Automate simulation collection, export LeRobot episodes, and train the selected deterministic vision-language trajectory model | Documented dataset and quality checks; trained checkpoint; inference through the shared adapter |
| M7: **BONUS** generalization and optional ablations | Evaluate disjoint unseen positions and selected ablations; attempt Diffusion/Flow Matching only if earlier gates are complete | Seen/unseen results, representative failures, and any completed ablation evidence |
| M8: Final artifacts | Finalize public GitHub repository, report, presentation, demo videos, contribution statement, and LLM/external-resource disclosures | Reproduction review passed; all required and completed extension evidence linked |

## 11. Deliverables and Reproducibility

### 11.1 Required Deliverables

- **Report:** 5-8 pages excluding references, covering the Archon session, simulation system, Kimodo and ARDY, SONIC integration, evaluation, failure analysis, and completed extensions.
- **Presentation:** 10 minutes including the required demonstration, followed by 5 minutes of Q&A.
- **Videos:** typed instructions and corresponding robot behavior, including successful and failed trials for both Kimodo and ARDY; completed extension evidence will be included separately.
- **Public GitHub repository:** implementation, configurations, setup instructions, evaluation code, and reproducibility guidance.
- **Contribution statement:** each member's actual work with supporting evidence.

### 11.2 [BONUS] Extension Artifacts

- speech-to-text interface and command-normalization code;
- anonymized or consented speech-test inputs where publishable;
- simulation recording and LeRobot conversion scripts;
- dataset or accessible dataset link, subject to permissions;
- model training and inference code, configurations, and checkpoints;
- seen/unseen split definitions and evaluation scripts;
- successful and failed extension videos; and
- ablation results for any completed optional comparisons.

### 11.3 Repository Structure

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

The repository will pin dependencies where possible, provide hardware/software requirements, include sample inputs and small test configurations, and avoid publishing credentials, restricted robot data, or third-party materials without permission.

## 12. Feasibility, Risks, and Mitigation

| Risk | Potential impact | Mitigation |
|---|---|---|
| Kimodo/ARDY representation mismatch | Generated motion cannot be executed fairly through SONIC | Freeze a canonical motion contract early; validate joint order, units, frames, rates, and trajectory continuity with small tests |
| SONIC or G1 integration instability | Tracking failure, balance problems, or unsafe motion | Begin with fixed standing and upper-body motion; constrain joint ranges; validate slow scripted motions before generated trajectories |
| Grasp/contact instability | Plausible motion fails to contact, close, or lift | Use explicit pre-grasp/grasp/lift states, accurate object pose, separate hand control, and contact-aware failure logging |
| Incompatible parallel implementations | Teams produce methods that cannot share the pipeline | Shared configs, interface tests, weekly integration runs, and cross-team code review |
| STT recognition errors | Wrong target/action, added corrections, or unsafe instruction | Restrict command grammar, apply confidence thresholds, confirm low-confidence commands, reject invalid commands, and retain typed fallback |
| STT service latency or privacy | Slow interaction or non-publishable audio | Compare offline/online options, log component latency, obtain consent, and avoid releasing voice data without permission |
| Training-data quality problems | Model learns inaccurate or unstable trajectories | Prefer scripted IK/planner experts, enforce automatic success checks, inspect samples, track failure reasons, and report dataset statistics |
| Train/test leakage | Inflated generalization results | Define disjoint position sets before training, save split manifests, and avoid using test positions during tuning |
| Compute constraints | Training or large-scale evaluation cannot finish | Keep encoders frozen initially, use a small fusion model, prioritize deterministic regression, profile early, and defer Flow Matching until baseline completion |
| Scope expansion | Required Kimodo/ARDY comparison is delayed by bonus work | Use milestone gates; maintain independently runnable typed baselines; stop extension work if required deliverables are at risk |
| Restricted Archon or third-party data | Academic-integrity, safety, or licensing violation | Obtain explicit permission, document restrictions, publish only allowed artifacts, and acknowledge all external resources |

## 13. Safety, Data Governance, and Academic Integrity

- All real-robot interaction will occur under Archon supervision and laboratory safety procedures.
- Simulation motions will be checked for joint limits, collisions, instability, and abnormal commands before any optional deployment proposal.
- Speech recordings will require participant awareness and permission; typed commands will remain available for privacy-sensitive testing.
- Credentials, restricted robot data, unpublished internal material, and unlicensed third-party assets will not be placed in the public repository.
- External code, models, checkpoints, datasets, and assets will be acknowledged with their licenses and sources.
- Experimental failures and negative results will be reported honestly; videos will not be selected in a way that hides representative failure modes.
- Any sim-to-real attempt will require advance submission of simulation evidence and a deployment plan to the TAs, followed by explicit approval and a supervised booking.

## 14. LLM Usage Statement

ChatGPT was used during project ideation and proposal drafting to help organize the course requirements, integrate the baseline and extension plans, define functional work packages, and improve the structure and wording of this proposal. The group will review and verify all technical claims, equations, model interfaces, references, code, and experimental results before submission. Any later use of LLMs or VLMs for coding, analysis, writing, or system development will be documented in the final report with the affected components and the nature of the assistance.

## 15. Expected Contributions and Final Scope Statement

The required contribution is a controlled and reproducible comparison of Kimodo and ARDY for Unitree G1 tabletop grasping in simulation, using the same SONIC low-level controller, hand/gripper logic, instructions, conditions, metrics, and trial budget. The project will document the complete motion-to-control pipeline and analyze not only successes but also integration and physical-interaction failures.

The integrated extension adds a natural speech interface and a trainable perception-to-motion path:

```text
Speech + Image
  -> recognized instruction + visual features
  -> trainable G1 reference motion
  -> SONIC
  -> generalized grasp and lift
```

Its technical contribution is the combination of speech-conditioned interaction, synchronized simulation data collection, LeRobot-format export, trainable vision-language trajectory generation, SONIC-compatible execution, and generalization to unseen block positions. The baseline comparison will be completed first, and extension claims will be made only for components that are implemented, evaluated with repeated trials, and supported by reproducible evidence.
