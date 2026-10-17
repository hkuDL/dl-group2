# Security and real-robot boundary

- Never commit tokens, SSH keys, `.env` files, checkpoints, datasets, videos, or site IP addresses.
- The checked-in golden reference is an integration fixture, not an automatic safety approval.
- The Jetson owns SONIC, Unitree DDS, stale-data handling, CRC checking, and emergency-stop behavior.
- Do not enable real motion without an on-site operator, physical E-stop, cleared workspace, first-pose check, and robot-owner approval.
- Report a suspected credential leak privately to the repository owner; rotate the credential before rewriting history.

