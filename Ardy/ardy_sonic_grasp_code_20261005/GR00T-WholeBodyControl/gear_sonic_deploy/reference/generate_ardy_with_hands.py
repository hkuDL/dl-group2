#!/usr/bin/env python3
"""Generate ARDY G1 body motion and rule-based Dex3 motion from one prompt."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from generate_hand_motion import generate_hand_motion


def main():
    deploy_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt")
    parser.add_argument("--output-dir", required=True, type=Path, help="One SONIC motion folder")
    parser.add_argument("--ardy-repo", type=Path, default=deploy_dir.parent.parent / "ardy")
    parser.add_argument("--checkpoints-dir", type=Path)
    parser.add_argument("--model", default="g1", help="G1 model nickname")
    parser.add_argument("--duration", type=float, default=5.)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--gpu", type=int, choices=[4, 5, 6, 7], default=7)
    parser.add_argument("--constraints", type=Path)
    parser.add_argument("--input-npz", type=Path, help="Reuse existing body motion instead of running ARDY")
    parser.add_argument("--hand", choices=["auto", "left", "right", "both"], default="auto")
    parser.add_argument("--close-start", type=float, help="Finger transition start in seconds")
    parser.add_argument("--close-end", type=float, help="Finger transition end in seconds")
    args = parser.parse_args()
    ardy_repo = args.ardy_repo.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.input_npz:
        source = args.input_npz.resolve()
        print(f"Reusing body motion: {source}", flush=True)
    else:
        source = output_dir / "ardy_motion.npz"
        env = os.environ.copy()
        env["MUSA_VISIBLE_DEVICES"] = env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
        env.setdefault("TEXT_ENCODERS_DIR", str(ardy_repo / "text_encoders"))
        env["TEXT_ENCODER_MODE"] = "local"
        env["HF_HUB_OFFLINE"] = env["TRANSFORMERS_OFFLINE"] = "1"
        checkpoints = (args.checkpoints_dir or ardy_repo / "checkpoints").resolve()
        command = [sys.executable, str(ardy_repo / "scripts/generate.py"), args.prompt,
                   "--model", args.model, "--checkpoints_dir", str(checkpoints),
                   "--duration", str(args.duration), "--seed", str(args.seed),
                   "--output", str(source.with_suffix(""))]
        if args.constraints:
            command += ["--constraints", str(args.constraints.resolve())]
        subprocess.run(command, cwd=ardy_repo, env=env, check=True)
    subprocess.run([sys.executable, str(deploy_dir / "reference/convert_ardy.py"), str(source),
                    "--ardy-repo", str(ardy_repo), "--output-dir", str(output_dir)], check=True)
    generate_hand_motion(args.prompt, output_dir, args.hand, args.close_start, args.close_end)
    print(f"Ready: {output_dir}")
    print(f"SONIC reference parent directory: {output_dir.parent}")


if __name__ == "__main__":
    main()
