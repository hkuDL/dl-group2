# Source attribution

This directory restores the Group 2 integration and research workspace, including compatibility modules needed by its existing callers. Individual file headers are retained. SOURCE_MANIFEST.json records each recovered file's source location and SHA-256. Original robot, simulator and model dependencies remain external.

- Kimodo: NVIDIA motion-generation runtime and released model; the already-published minimal runtime is under `deployment/g1_replay/third_party/kimodo` in the repository root. Follow its Apache-2.0 source notice and the separate model terms. No model weights are included here.
- ARDY: `nv-tlabs/ardy`, source dependency pinned by the existing deployment manifest to `693f74d13b3d04a0a22ce127ee79c929dd89756b`; Apache-2.0 license retained in `patches/ARDY_LICENSE`. The team’s staged generation and G1 integration live under `research/ardy`.
- SONIC / GR00T-WholeBodyControl: `NVlabs/GR00T-WholeBodyControl`; Apache-2.0 license retained in `patches/SONIC_LICENSE`. Patches identify their upstream baseline and purpose. Model terms remain separate.
- Unitree SDK2 and G1/Dex3 descriptions: external dependencies; no SDK binaries or additional robot mesh copies are included in this source recovery.
- Qwen VLM integration: team orchestration code under `research/ardy/online/qwen`; hosted API credentials are read from the environment and are not included. Any locally installed Qwen/LLM2Vec assets require their original licenses and acquisition process.

This notice does not grant additional rights to third-party model weights, restricted robot recordings or other excluded artifacts. It does not replace individual source-file license headers.
