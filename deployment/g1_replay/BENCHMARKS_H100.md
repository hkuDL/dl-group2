# H100 batch=1 inference benchmark

Measurement command: `python -m scripts.benchmark_h100 MODEL --config configs/MODEL.h100.yaml --report benchmark_results/MODEL.json`.

The measurement scope is a prepared model forward pass plus conversion to a SONIC-compatible reference. Model loading is reported separately. CUDA is synchronized around every run, and peak allocated/reserved GPU memory is recorded. The script refuses to label a non-H100 GPU as H100.

| Model | H100 GPU | batch | Simulator | Training data | Mean latency | p50 | p95 | Peak allocated VRAM | Status |
|---|---:|---:|---|---|---:|---:|---:|---:|---|
| Kimodo | — | 1 | no | no | — | — | — | — | NOT_RUN_H100 |
| ARDY | — | 1 | no | no | — | — | — | — | NOT_RUN_H100 |
| VA v4.1 | — | 1 | no | no | — | — | — | — | NOT_RUN_H100 |

On 2026-10-17 the configured `hk` host timed out from the current network. S4000 has MTT S4000 48 GB GPUs, not H100s, so its numbers would not answer the requested measurement and have not been substituted.

