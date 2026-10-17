# SONIC packed-ZMQ subset

Messages are `[topic bytes][1280-byte NUL-padded compact JSON header][little-endian payloads]`.

- v1 motion: `joint_pos [N,29] f32`, `joint_vel [N,29] f32`, `body_quat [N,4] f32` in `wxyz`, `frame_index [N] i64`, optional one-frame left/right hand `[1,7] f32`.
- v4 token: `token_state [1,64] f32`, `frame_index [1] i64`, optional one-frame left/right hand `[1,7] f32`.

The inspected upstream docstring still says 1024 bytes, but its executable constant and receiver use 1280 bytes. This project follows the executable constant. Passing byte-level unit tests establishes format compatibility, not real-robot qualification.

