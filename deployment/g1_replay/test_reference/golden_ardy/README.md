# Golden ARDY integration reference

This is the exact 810-frame, 50 Hz artifact selected on S4000. Its SHA-256 is
`e16dc4b3125a0a611e15a0b555b9164ec268e71d63d44c70aba96d3b7608e053`.

It is **golden only under the recorded ARDY task policy** and is intended for
schema, adapter, transport and dry-run integration tests. It is not a blanket
real-robot approval: the retained replay reports 26 right-thumb/table contact
steps (0.13 s), so the strict no-table-contact gate is false. Before first real
motion, the team must still pass downstream SONIC compilation, current-pose and
joint-order matching, collision/contact review, low-risk supported playback,
physical E-stop checks and robot-owner approval.

