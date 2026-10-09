# Canonical Tabletop Grasp Experimental Base Contract

**Status:** Required baseline for Rule Generator / Kimodo / ARDY / VA experiments  
**Purpose:** Ensure that all methods are compared under the same robot, MuJoCo scene, SONIC controller, hand controller, physics settings, observation setup, and evaluation contract.

> **Rule:** A method may change the generated motion / policy output, but it must not silently change the robot model, MuJoCo scene, SONIC bundle, hand controller, joint mapping, physics parameters, or evaluation environment.

---

## 1. Canonical Runtime Stack

All experiments must use the following common stack:

```text
G1 robot
+ MuJoCo tabletop scene
+ SONIC release controller
+ canonical hand PD controller
```

The allowed method-specific component is only the high-level motion / action generator:

```text
Rule Generator
Kimodo
ARDY
VA
```

These methods must ultimately connect to the same canonical runtime below.

---

# 2. Fixed Canonical Components

## 2.1 G1 Robot

### Canonical robot XML

```text
/home/group2/GR00T-WholeBodyControl/decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml
```

This exact robot model must be used unless a new canonical version is explicitly approved.

### Base / DoF

```text
Base: free-base
Body DoF: 29
Hand DoF: 14
Total actuated DoF: 43
```

The canonical runtime must not weld the pelvis.

Expected compiled MuJoCo dimensions with the canonical cube scene:

```text
nq = 57
nv = 55
nu = 43
neq = 0
```

### Canonical initial body pose

The experiment initial body pose follows the neutral standing reference:

```text
[-0.15, -0.15, 0,
  0,     0,    0,
  0,     0,    0,
  0.3,   0.3,
  0.7,   0.7,
 -0.15, -0.15,
  0.45, -0.45,
  0,     0,
  0,     0,
  0.4,   0.4,
  0,     0,
  0,     0,
  0,     0]
```

The actual runtime initialization must use the selected reference frame-0 state where applicable.

### Canonical initial hand pose

```text
14D hand q = all zeros
```

### Initial root pose convention

Current runtime initialization is taken from the selected reference frame-0 and overrides the XML default.

Verified reference example:

```text
root position = [0, 0, 0.7846157043688324]
root quaternion (wxyz) = [1, 0, 0, 0]
```

Do not silently replace this with the raw XML root z.

---

# 3. Canonical MuJoCo Scene

## 3.1 Scene files

Canonical tabletop scene:

```text
/home/group2/dl-group2/scenes/tabletop.xml
```

Canonical scene builder:

```text
/home/group2/dl-group2/scripts/scene.py
```

The runtime scene must be constructed through the same canonical builder path.

Do not substitute:

```text
scene_empty.xml
scene_43dof.xml
```

or any IDE/test scene unless the experiment is explicitly labeled as a non-canonical diagnostic.

---

## 3.2 MuJoCo version and physics

Verified current environment:

```text
MuJoCo: 3.14.0
Integrator: implicitfast
Gravity: [0, 0, -9.81] m/s^2
```

Canonical SONIC / VA replay physics timestep:

```text
dt = 0.005 s
physics frequency = 200 Hz
```

Important:

```text
tabletop.xml default timestep = 0.002 s (500 Hz)
```

but the canonical SONIC / VA runtime overrides it to:

```text
0.005 s (200 Hz)
```

Therefore:

```text
200 Hz is the canonical runtime physics frequency.
```

Source-generation-only code that still runs at 500 Hz must not be confused with canonical SONIC/VA replay.

---

# 4. Canonical Table

Canonical table geometry:

```text
table body position = [0.65, 0, 0]
table board center z = 0.72 m
table board size = 0.8 × 1.0 × 0.06 m
table surface z = 0.75 m
front edge x = 0.25 m
```

The canonical table surface height is:

```text
0.75 m
```

Do not use `0.70 m` as the canonical table height.

---

# 5. Canonical Cube

## 5.1 Fixed cube properties

```text
shape: box
edge length: 0.07 m
mass: 0.1 kg
free joint: yes
contype = 1
conaffinity = 1
friction = [0.95, 0.01, 0.001]
```

### Cube initial z

Cube center z must follow the geometric relation:

```text
cube_center_z
= table_surface_z + cube_half_height
= 0.75 + 0.035
= 0.785 m
```

Therefore:

```text
0.785 m = cube center z
0.75 m  = table surface height
```

These values must not be confused.

---

## 5.2 Variable cube parameters

Cube initial XY is **not a fixed canonical value**.

It is a task / sampling parameter.

Runtime source:

```text
metadata["case"]["block_xy"]
```

The XML value is only a placeholder and must not be treated as the actual experimental coordinate.

Cube yaw may also be treated as a task parameter:

```text
metadata["case"]["block_yaw_deg"]
```

### Current common XY ranges

Typical right-arm datasets currently use approximately:

```text
x ∈ [0.38, 0.40] m
y ∈ [-0.17, -0.13] m
```

Some newer datasets expand to approximately:

```text
x ∈ [0.37, 0.41] m
y ∈ [-0.18, -0.12] m
```

For method comparison, all methods must use the **same evaluation XY cases / seeds**.

---

# 6. Canonical SONIC Bundle

All methods must use the **SONIC release** bundle.

## 6.1 Required paths

```text
/home/group2/GR00T-WholeBodyControl/gear_sonic_deploy/policy/release/model_encoder.onnx

/home/group2/GR00T-WholeBodyControl/gear_sonic_deploy/policy/release/model_decoder.onnx

/home/group2/GR00T-WholeBodyControl/gear_sonic_deploy/policy/release/observation_config.yaml
```

Do **not** substitute:

```text
sonic_v1_1
```

or any other SONIC variant.

---

## 6.2 Canonical hashes

Current verified SHA256:

```text
model_encoder.onnx
013ab0287236aa2721e13f1e936d699db982302d0de0bfcdae76d5c3245362d3

model_decoder.onnx
c7241a123eaa36b5d64bad19540efde93cac1ad443bd4572fd12ca99898118ed

observation_config.yaml
466d05947c78af6c76388adfb86e3a2a77b2a1d921a64883ed3d085ebf58de1b
```

A run should be treated as canonical only if these files match, unless a new baseline version is explicitly declared.

---

## 6.3 Encoder contract

Canonical release encoder:

```text
input:
obs_dict [1, 1762]

output:
encoded_tokens [1, 64]
```

Reference/expert replay uses:

```text
encoder mode = 0 / g1
```

The encoder produces the canonical 64D SONIC native token.

---

## 6.4 Decoder contract

Canonical release decoder:

```text
input:
obs_dict [1, 994]

output:
action [1, 29]
```

The decoder input includes:

```text
64D SONIC token
+ angular velocity history
+ body q history
+ body dq history
+ previous action history
+ projected gravity history
```

The output is a 29D SONIC body action.

---

## 6.5 SONIC action post-processing

Canonical body target construction:

```text
q_target[i]
=
default_angles[i]
+
scale[i] * action[permutation[i]]
```

with canonical SONIC permutation, scaling, and default-angle parameters from the release implementation.

Important:

```text
SONIC default_angles != robot initial q
```

`default_angles` are decoder/action offsets and must not be used as the experiment reset pose.

---

# 7. Canonical Body Runtime Chain

For reference-based expert execution:

```text
G1 + MuJoCo tabletop scene
        ↓
reset_case(XY / yaw)
        ↓
reference frame-0 robot initialization
        ↓
motion reference
        ↓
SONIC release encoder (mode 0)
        ↓
64D native SONIC token
        ↓
SONIC release decoder
        ↓
29D body action
        ↓
SONIC permutation / scaling / default-angle offset
        ↓
body PD / torque clipping
        ↓
29 body motors
        ↓
MuJoCo
```

---

# 8. Canonical VA Body Interface

A VA model that directly predicts native SONIC tokens may bypass the encoder:

```text
RGB / proprio
        ↓
VA
        ↓
64D native SONIC token
        ↓
SONIC release decoder
        ↓
same canonical body controller
        ↓
MuJoCo
```

This is valid because VA replaces the **encoder output**, not the SONIC decoder/controller.

Therefore:

```text
VA may bypass the encoder.
VA must not bypass or replace the canonical release decoder/controller
unless the experiment is explicitly declared non-canonical.
```

---

# 9. Canonical Hand Interface

The hand is controlled separately from the SONIC body decoder.

Canonical hand reference:

```text
14D absolute joint-position reference
unit: rad
```

Canonical hand controller:

```text
/home/group2/dl-group2/scripts/hand_trajectory_controller.py
```

Canonical PD law:

```text
tau = 12 * (q_ref - q) - 0.3 * dq
```

Therefore:

```text
kp = 12
kd = 0.3
```

The hand reference velocity is not currently used in this PD formula.

### Torque clipping

Canonical hand torque clipping must remain unchanged.

Approximate limits:

```text
thumb_0: ±2.45 Nm
other hand joints: ±1.4 Nm
```

All methods must output hand references in the same 14D joint order.

---

# 10. Canonical Cameras

## 10.1 Head camera

```text
name: head_rgb
attached to: torso_link
local pos: [0.06, 0, 0.44]
vertical FOV: 75 deg
```

Canonical VA visual camera:

```text
head_rgb
```

---

## 10.2 Right wrist camera

```text
name: wrist_rgb
attached to: right_wrist_yaw_link
local pos: [0.06, -0.09, 0.13]
vertical FOV: 90 deg
```

This is available but is not the canonical default VA image unless explicitly stated.

---

## 10.3 Overview camera

World camera used for evaluation / visualization only.

It must not silently become a training input.

---

# 11. Canonical Timing

The following timing layers must be kept distinct.

```text
MuJoCo physics loop       = 200 Hz
SONIC inference           = 50 Hz
body torque application   = 200 Hz
hand PD application       = 200 Hz
hand reference nominal    = 50 Hz
expert RGB capture        = 10 Hz
```

Method-specific VA/Kimodo/ARDY inference frequency may differ, but it must be logged explicitly.

Do not silently treat method inference frequency as a canonical scene parameter.

---

# 12. Canonical Episode Initialization

Current typical dataset episode:

```text
800 control frames × 20 ms = 16 s
```

Initialization/warm-up must be logged explicitly.

Important distinction:

```text
source WBC generation:
first ~1 s keeps grasp reference from advancing

expert replay:
warmup_frames may be 0

native SONIC:
has its own initialization phase

VA:
may additionally wait for image / preload / inference readiness
```

These are different mechanisms and must not be collapsed into one generic "1 s reset".

---

# 13. Rule Generator / Kimodo / ARDY Contract

## 13.1 What may differ

The method is allowed to change:

```text
trajectory generation algorithm
reach path
body motion
reach speed
grasp timing
hand trajectory
policy architecture
internal latent representation
```

---

## 13.2 What must remain identical

The method must not silently change:

```text
G1 robot XML
free-base configuration
body / hand joint order
MuJoCo tabletop scene
table geometry
cube geometry / mass / friction
physics timestep
gravity
SONIC release model bundle
SONIC decoder/controller
hand PD controller
camera definition
reset convention
evaluation metric
```

---

# 14. Required Interface for Kimodo / ARDY

Kimodo / ARDY must ultimately produce outputs compatible with the canonical runtime.

Preferred body integration path:

```text
Kimodo / ARDY
        ↓
G1 motion reference
(q_ref, dq_ref, root orientation / required motion fields)
        ↓
SONIC release encoder
        ↓
64D native token
        ↓
SONIC release decoder
        ↓
29D body control
        ↓
MuJoCo
```

Alternative direct-token output is allowed only if the method is explicitly designed to output the canonical 64D release-token space and this is verified.

Hand integration:

```text
Kimodo / ARDY hand output
        ↓
canonical 14D absolute hand q reference
        ↓
canonical hand PD
        ↓
MuJoCo
```

---

# 15. Dataset Generation Contract

Every generated expert episode should preserve or record at least:

```text
timestamps
body_q
body_dq
hand_q
hand_dq

body_ref_q
body_ref_dq
hand_ref_q
hand_ref_dq

root_pos
root_quat
root_lin_vel
root_ang_vel

root_ref_pos
root_ref_quat

cube_pos
cube_quat

eef_pos
eef_quat

qpos
qvel
ctrl

native SONIC token logs
native SONIC action logs

RGB
camera metadata
reference/control frame indices
simulation timestamps
```

Native SONIC token logs must come from the canonical `policy/release` stack.

---

# 16. Fixed vs Variable Parameters

## Fixed canonical parameters

```text
G1 model
free-base configuration
joint order
MuJoCo scene
table geometry
cube size / mass / friction
cube z geometry relation
gravity
physics dt
SONIC release bundle
body controller
hand controller
camera geometry
reset convention
```

## Variable task parameters

```text
cube XY
cube yaw (if explicitly enabled)
random seed
trajectory generator
reach path
reach speed
grasp timing
hand trajectory
task arm
episode duration
method inference frequency
```

For formal model comparison, the following must additionally be frozen:

```text
evaluation XY positions
evaluation seeds
task arm
episode duration
success criterion
```

---

# 17. Canonical Comparison Principle

When comparing:

```text
Rule Generator
vs
Kimodo
vs
ARDY
vs
VA
```

the intended experiment is:

```text
different motion / policy generator
+
same G1
+
same MuJoCo
+
same SONIC release controller
+
same hand PD
+
same scene
+
same evaluation cases
```

The experiment must **not** become:

```text
different generator
+
different robot model
+
different physics
+
different controller
```

because that would make performance comparisons uninterpretable.

---

# 18. Runtime Verification Checklist

Before accepting a generated dataset or evaluation run, verify:

- [ ] Robot XML exactly matches the canonical activated-finger G1 XML.
- [ ] Base is free, not welded.
- [ ] Body DoF = 29.
- [ ] Hand DoF = 14.
- [ ] Scene is `tabletop.xml`.
- [ ] Scene is loaded through the canonical builder.
- [ ] Table surface z = 0.75 m.
- [ ] Cube edge = 0.07 m.
- [ ] Cube mass = 0.1 kg.
- [ ] Cube center z = 0.785 m.
- [ ] Cube XY comes from the experiment case, not the XML placeholder.
- [ ] MuJoCo physics dt = 0.005 s.
- [ ] Gravity = `[0, 0, -9.81]`.
- [ ] SONIC encoder is `policy/release/model_encoder.onnx`.
- [ ] SONIC decoder is `policy/release/model_decoder.onnx`.
- [ ] SONIC observation config is `policy/release/observation_config.yaml`.
- [ ] SONIC file hashes match the canonical hashes.
- [ ] No `sonic_v1_1` bundle is used.
- [ ] Body output is routed through the canonical release decoder/controller.
- [ ] Hand output is routed through the canonical 14D hand PD.
- [ ] Hand PD gains remain kp=12, kd=0.3.
- [ ] Head camera is the canonical VA visual input unless explicitly stated otherwise.
- [ ] Reset source and initial robot state are recorded.
- [ ] Cube XY / seed are recorded.
- [ ] Method inference frequency is recorded.
- [ ] Episode duration is recorded.
- [ ] Runtime provenance and model paths are saved with the run.

---

# 19. Known Non-Canonical / Entry-Specific Differences

The following must not be silently treated as canonical constants:

1. **Rule source generation**
   - may use its own WBC before SONIC replay validation;
   - source-generation physics may differ from canonical replay.

2. **VA**
   - may directly predict native SONIC token and bypass the encoder;
   - its own inference frequency / horizon is method-specific.

3. **Kimodo / ARDY**
   - their final integration into this canonical runtime must be verified;
   - their internal simulator/controller must not be used for final comparison unless the experiment is explicitly labeled non-canonical.

4. **Historical executable binaries**
   - identical ONNX/config bundles do not imply the old SONIC executable binary was bitwise identical;
   - current comparisons should preserve runtime provenance.

---

# 20. Source-of-Truth Rule

When a conflict appears between:

```text
XML
config
dataset metadata
old documentation
Git history
runtime
```

use the following priority:

```text
1. actual current runtime behavior
2. actual loaded file path / runtime provenance
3. active config / XML
4. dataset metadata
5. historical notes / old code / commit assumptions
```

Do not resolve conflicting values by guesswork.

Record the conflict explicitly.

---

# 21. Canonical Base Summary

The canonical experimental base is:

```text
Free-base G1
29D body + 14D hand
activated-finger G1 XML
MuJoCo tabletop scene
table surface z = 0.75 m
7 cm / 0.1 kg cube
cube center z = 0.785 m
cube XY variable by case
200 Hz physics
SONIC policy/release stack
64D native token
release decoder → 29D body action
independent 14D hand PD
head_rgb canonical visual input
```

All Rule / Kimodo / ARDY / VA experiments intended for direct comparison must satisfy this contract.
