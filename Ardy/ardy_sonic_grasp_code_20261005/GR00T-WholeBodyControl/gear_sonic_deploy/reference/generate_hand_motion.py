#!/usr/bin/env python3
"""Create 50 Hz Dex3 targets from simple English action/hand rules."""
import argparse
import json
import re
from pathlib import Path
import numpy as np

FPS = 50
LEFT_CLOSED = np.array([0., .2, 1., -.9, -1., -.9, -1.])
RIGHT_CLOSED = -LEFT_CLOSED
JOINTS = ["thumb_0", "thumb_1", "thumb_2", "middle_0", "middle_1", "index_0", "index_1"]


def smooth_transition(times, start, end):
    if not 0 <= start < end:
        raise ValueError("Transition requires 0 <= start < end (seconds)")
    p = np.clip((times - start) / (end - start), 0., 1.)
    return p * p * (3. - 2. * p)


def generate_hand_motion(prompt, output_dir, hand="auto", close_start=None, close_end=None):
    output_dir = Path(output_dir)
    body = np.loadtxt(output_dir / "joint_pos.csv", delimiter=",", skiprows=1, ndmin=2)
    frames = len(body)
    times = np.arange(frames) / FPS
    duration = frames / FPS
    text = prompt.lower()
    grasp = bool(re.search(r"\b(grasp\w*|grab\w*|grip\w*|hold\w*|pick(?:s|ing)?\s+up)\b", text))
    release = bool(re.search(r"\b(releas\w*|let(?:s|ting)?\s+go|open(?:s|ing)?\s+(?:the\s+)?(?:left\s+|right\s+|both\s+)?hands?)\b", text))
    if hand == "auto":
        if re.search(r"\bboth\b|\btwo hands\b|\bleft and right\b|\bright and left\b", text):
            hand = "both"
        elif re.search(r"\bleft\b", text):
            hand = "left"
        else:
            hand = "right"
    start = duration * .4 if close_start is None else close_start
    end = duration * .6 if close_end is None else close_end
    if end > times[-1]:
        raise ValueError("Hand transition must finish within the motion")
    if grasp:
        amount = smooth_transition(times, start, end)
        action = "grasp"
        if release:
            release_start, release_end = max(end, duration * .8), duration * .95
            amount *= 1. - smooth_transition(times, release_start, release_end)
            action = "grasp_then_release"
    elif release:
        amount = 1. - smooth_transition(times, start, end)
        action = "release"
    else:
        amount = np.zeros(frames)
        action = "open"
    for side, pose in [("left", LEFT_CLOSED), ("right", RIGHT_CLOSED)]:
        selected = hand in (side, "both")
        values = amount[:, None] * pose[None, :] if selected else np.zeros((frames, 7))
        np.savetxt(output_dir / f"{side}_hand_pos.csv", values, delimiter=",", fmt="%.9f",
                   header=",".join(f"{side}_{joint}" for joint in JOINTS), comments="")
    plan = {"prompt": prompt, "generator": "rule_based_dex3", "hand": hand,
            "action": action, "fps": FPS, "frames": frames, "duration": duration,
            "transition_start": start, "transition_end": end,
            "timing": "fixed fractions of clip duration; not object-aware"}
    if grasp and release:
        plan.update(release_start=release_start, release_end=release_end)
    (output_dir / "hand_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(f"Dex3: {hand} hand, {action}; {frames} frames @ {FPS} FPS")
    print(f"Hand transition: {start:g} -> {end:g} s")
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt")
    parser.add_argument("--output-dir", required=True, type=Path, help="Existing SONIC motion folder")
    parser.add_argument("--hand", choices=["auto", "left", "right", "both"], default="auto")
    parser.add_argument("--close-start", type=float, help="Transition start in seconds (default: 40%% of clip)")
    parser.add_argument("--close-end", type=float, help="Transition end in seconds (default: 60%% of clip)")
    args = parser.parse_args()
    generate_hand_motion(args.prompt, args.output_dir, args.hand, args.close_start, args.close_end)


if __name__ == "__main__":
    main()
