from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from communication.sonic_wire import pack_pose_message
from contracts.reference import ReferenceBundle, validate_reference


def frame_message(bundle: ReferenceBundle, index: int) -> bytes:
    arrays = bundle.arrays
    return pack_pose_message(
        {
            "joint_pos": np.asarray(arrays["body_ref_q"][index : index + 1], dtype=np.float32),
            "joint_vel": np.asarray(arrays["body_ref_dq"][index : index + 1], dtype=np.float32),
            "body_quat": np.asarray(arrays["root_ref_quat"][index : index + 1], dtype=np.float32),
            "frame_index": np.asarray([index], dtype=np.int64),
            "left_hand_joints": np.asarray(arrays["hand_ref_q"][index : index + 1, :7], dtype=np.float32),
            "right_hand_joints": np.asarray(arrays["hand_ref_q"][index : index + 1, 7:], dtype=np.float32),
        },
        version=1,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate, then publish one canonical reference at 50 Hz")
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("--bind", default="tcp://127.0.0.1:5556")
    parser.add_argument("--send", action="store_true", help="actually bind and publish; omission is a dry run")
    parser.add_argument("--countdown", type=int, default=5)
    args = parser.parse_args()
    if not args.bind.startswith("tcp://"):
        parser.error("--bind must be a tcp:// endpoint")
    bundle = ReferenceBundle.load(args.reference_dir)
    report = validate_reference(bundle, mode="dry-run")
    if report.overall != "PASS":
        raise SystemExit("reference validation failed")
    print(f"validated {len(bundle.arrays['time_s'])} frames; robot safety remains NOT_EVALUATED")
    if not args.send:
        print("dry run only; no socket opened and no data sent")
        return 0

    import zmq
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.setsockopt(zmq.SNDHWM, 3)
    socket.bind(args.bind)
    try:
        for remaining in range(args.countdown, 0, -1):
            print(f"publishing starts in {remaining}s")
            time.sleep(1)
        deadline = time.perf_counter()
        for index in range(len(bundle.arrays["time_s"])):
            socket.send(frame_message(bundle, index))
            deadline += 0.02
            time.sleep(max(0.0, deadline - time.perf_counter()))
    finally:
        socket.close(linger=0)
        context.term()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

