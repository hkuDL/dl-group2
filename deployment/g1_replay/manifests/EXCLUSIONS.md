# S4000 exclusion decisions

The inventory deliberately excludes:

- all training datasets, trainers, optimizers, experiment trackers, videos, logs and rollouts;
- every checkpoint and model weight (tracked by hash in `models/model_requirements.json` only);
- simulation launchers including `execution/sonic_mujoco` and the existing VA MuJoCo rollout path;
- server-specific conda environments, absolute paths, IP addresses and credentials;
- native SONIC binaries and Unitree SDK binaries;
- dirty or unlicensed research wrappers copied verbatim.

Kimodo and ARDY use a class named `MujocoQposConverter`, but the inspected implementations only parse the packaged G1 XML and perform tensor/matrix conversion. They do not import or launch MuJoCo. The independent runners may therefore use this kinematic converter while remaining simulator-free.

The S4000 GPU is an MTT S4000, not an NVIDIA H100. S4000 measurements must not be labeled H100 results.

