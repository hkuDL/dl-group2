# Model installation

Weights are intentionally outside Git. Copy them into the relative paths listed in `model_requirements.json`, then run `python -m scripts.verify_models`. Never put credentials in a download URL or configuration file.

Kimodo/ARDY local text encoding may additionally require the LLM2Vec Meta-Llama-3 8B base and PEFT weights. For a strict single-GPU benchmark, the model and text encoder must run in the same process on the same selected GPU; alternatively provide a precomputed prompt embedding and report that benchmark mode explicitly.

