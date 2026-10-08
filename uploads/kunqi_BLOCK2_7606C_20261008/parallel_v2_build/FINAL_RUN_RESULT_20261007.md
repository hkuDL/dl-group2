# Kimodo Final Grasp — Single-Shot Integration Result

Date: 2026-10-07 CST  
Contract: `kimodo_grasp_final_v1_20261007`  
Remote run directory: `/workspace/group2/handoffs/kimodo_parallel_v2/final_integration_20261007T174100_CST`

## Outcome

- `physical_success`: **false**
- `expert_valid`: **false**
- Classification: `failed_pre_playback_initialization_instability`
- The run is complete as a single-shot pipeline attempt, but it is not a successful or complete SONIC episode.

## What ran successfully

1. A's final grasp prompt and matrix constraints were consumed by the real Kimodo model.
2. Kimodo ran on physical S4000 GPU 1 using `Kimodo-G1-RP-v1`.
3. One native generation call produced 487 frames at 30 Hz, covering 16.2 seconds.
4. Phase-1 conversion produced 811 body/root frames at 50 Hz.
5. The assembler produced the frozen 810-frame SONIC reference and removed only the 16.20-second surplus endpoint.
6. The real C++ SONIC loader accepted the final six-CSV reference.
7. Canonical MuJoCo execution and independent evidence validation were invoked.

## Generation timing

- Model loading: `19.563801534008235 s`
- Inference: `34.46114263101481 s`
- Total generator wall time: `55.15628255001502 s`
- Denoising steps: `100`
- Segmentation: not used
- Padding, tail repetition, extrapolation and smoothing: not used

## Replay failure

The canonical runner stopped at simulation time `1.365 s` with:

```text
Nan, Inf or huge value in QACC at DOF 0.
RuntimeError: MuJoCo physics warning
```

SONIC playback had not started:

- `actual_playing_duration`: `0.0 s`
- `playing_start_step`: `null`
- Evidence rows recorded: `273`
- Complete replay: `false`
- Synchronized replay: `false`

The run used no band, support or weld, and kept the frozen Kp/Kd, hand PD, physics timestep and gravity.

## Independent validation

- Maximum cube lift observed: `0.09418982638254603 m`
- Required lift: `0.10 m`
- Longest qualifying grasp hold: `0.0 s`
- Terminal qualifying grasp hold: `0.0 s`
- `physical_success`: `false`
- `expert_valid`: `false`

The recorded lift occurred during the unstable pre-playback initialization and does not qualify as a grasp.

## Motion diagnostics

- Generated first root position was close to the canonical plan: delta approximately `[0.00125, -0.00256, 0.00134] m`.
- Generated first body pose differed from the planned initial body pose by as much as `0.925278 rad`.
- Phase-1 detected a maximum adjacent body-joint step of `3.625217 rad`, greater than pi; it preserved the model output without smoothing or unwrapping.

These are diagnostics, not a proven root-cause attribution. The observed failure mode is pre-playback physical initialization instability.

## Integration defects found and fixed

Two plumbing defects prevented the first two replay launches. They were fixed without modifying upstream controller code:

1. The Role-C wrapper now explicitly supplies the contract-frozen activated-finger robot XML instead of relying on an unpopulated pinned submodule.
2. The assembled case metadata now uses canonical `block_xy` and `block_yaw_deg` keys rather than `cube_xy` and `cube_yaw`.

After both fixes, Role C passed 24/24 tests and its checksum set passed. The third replay reached actual MuJoCo execution and produced the result above.

## Evidence hashes

- Raw Kimodo motion: `c7394669595f8e4d957ed8752d1d34d5f52af7ac749a1136701a8a4823fcc718`
- Packed Phase-1 body reference: `4b7ca7832285bf5a83952952f375eb4e7008ee49c38fc723b154eeaa69b52536`
- Final SONIC reference: `2ffe77292c5d65e4d7328b41182ce8eff33d37b0ebe06fb73033ec53d78a08c8`
- Replay evidence: `d3b5caa3dc36991e0c04cb91c3c694ed941ff69984512288fac36b3275c1d81e`
- Integrity metadata: `1e032e7de4fecbb1a18a671c926ab1f3ef8e7a45d90a813f439f2436dc3e178a`
- Independent validation: `65fd534f0508e58fe0fd0e68b2c589dbe5685b4aac2d7663202d72f2c6f31b1b`

## Correct next step

Do not silently regenerate until a successful sample appears. First diagnose why the generated initial body state cannot survive the unassisted startup, and inspect the greater-than-pi trajectory discontinuity. Any altered seed, constraint, controller setting or retry must be labeled as a separate development run unless the evaluation protocol explicitly permits it.
