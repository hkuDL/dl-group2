# T6 — Kimodo Baseline

Work record for [Issue #6: Kimodo Baseline](https://github.com/hkuDL/dl-group2/issues/6). Scope is the T6 baseline only; this record does not claim T7 deployment or T8 debugging.

## Result

The Kimodo text encoder and baseline generation were exercised in the existing `va-train` container with MUSA. The run produced a 5-second motion NPZ with 150 frames. The saved motion loaded in the Kimodo Demo page and played in the viewer.

- **Rendered preview:** [test_walk_preview.mp4](./test_walk_preview.mp4)
- **Kimodo motion output:** [test_walk.npz](./test_walk.npz)
- Prompt: `A person walks forward.`
- Output: 150 frames at 30 FPS; `posed_joints` shape `(150, 77, 3)`.

The MP4 is a 77-joint skeleton visualization rendered from the saved `posed_joints` array. It is a preview of the generated motion, not a screen recording or a rendered character-mesh export from the browser.

## Environment

| Setting | Verified value |
|---|---|
| Container | `va-train` |
| Python | `3.10.12` |
| PyTorch | `2.9.0` |
| MUSA | Available; 8 devices detected |
| GPU | Moore Threads MTT S4000 |
| Transformers | `5.8.1` (reported in the existing environment handoff; not changed for this work) |

Credentials, server IPs, and login usernames are intentionally not recorded in this public repository.

### Paths

```text
PROJECT_ROOT=/workspace/group2/kimodo-t6
KIMODO_DIR=/workspace/group2/kimodo-t6/kimodo-main
CHECKPOINT_DIR=/workspace/group2/kimodo-t6/models/Kimodo-SOMA-RP-v1
TEXT_ENCODERS_DIR=/workspace/group2/workspace/fuyuhan/ardy/text_encoders
BASE_LLAMA=$TEXT_ENCODERS_DIR/meta-llama/Meta-Llama-3-8B-Instruct
MNTP_ADAPTER=$TEXT_ENCODERS_DIR/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp
SUPERVISED_ADAPTER=$TEXT_ENCODERS_DIR/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised
```

Model weights and the shared text-encoder checkpoints are not included in this branch. They must already be present at the configured paths.

## Verified work

1. Confirmed `torch.musa.is_available() == True` and `torch.musa.device_count() == 8` in `va-train`.
2. Loaded Base Llama as Kimodo's `LlamaBiModel`, applied MNTP, merged it with `merge_and_unload()`, then applied the supervised adapter to the merged model.
3. Moved the encoder to `musa:0` and encoded `A person walks forward.`; output embedding shape was `(1, 4096)`.
4. Ran Kimodo text-to-motion generation and saved `test_walk.npz`.
5. Loaded the saved NPZ through a Demo-compatible example folder; the Demo confirmed the example loaded and displayed a 5-second motion.

The minimal source changes applied in the working Kimodo checkout are recorded in [`patches/llm2vec_musa.patch`](./patches/llm2vec_musa.patch). They cover adapter base-model resolution and routing an explicitly selected MUSA device through the single-device encoder path. The patch is a record; it does not include or replace the upstream Kimodo source tree.

## Reproduce generation

Run inside `va-train`:

```bash
cd /workspace/group2/kimodo-t6/kimodo-main
export CHECKPOINT_DIR=/workspace/group2/kimodo-t6/models/Kimodo-SOMA-RP-v1
export TEXT_ENCODERS_DIR=/workspace/group2/workspace/fuyuhan/ardy/text_encoders
export TEXT_ENCODER_DEVICE=musa
export PYTHONPATH="$PWD/MotionCorrection/python:$PYTHONPATH"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

kimodo_gen "A person walks forward." \
  --model Kimodo-SOMA-RP-v1 \
  --duration 5.0 \
  --output /workspace/group2/kimodo-t6/test_walk
```

The single-sample output is `/workspace/group2/kimodo-t6/test_walk.npz`.

## Rebuild the preview video

The included `render_npz_preview.py` uses the Kimodo SOMA 77-joint hierarchy, NumPy, and the container's existing OpenCV installation. From the Kimodo source directory:

```bash
python /path/to/baseline/render_npz_preview.py \
  /path/to/baseline/test_walk.npz \
  /path/to/baseline/test_walk_preview.mp4
```

No PyTorch, torch_musa, Transformers, or MUSA installation changes were made for this baseline.

## Run the Kimodo Demo

The Demo-compatible example is stored under the lowercase model key:

```text
kimodo/assets/demo/examples/kimodo-soma-rp-v1/test_walk_npz_view/
```

It contains `motion.npz` and `meta.json`. Start the UI from the Kimodo source directory with the same environment variables above:

```bash
kimodo_demo --model Kimodo-SOMA-RP-v1
```

The default UI port is `7860`. Open the browser through the course-approved SSH tunnel, load the model if generating a new sample, then select `test_walk_npz_view` and click **Load Example** to play the saved NPZ.
