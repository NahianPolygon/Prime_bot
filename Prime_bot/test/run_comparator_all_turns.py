import argparse
import os
import subprocess
import sys


def run(cmd):
    print("\n$ " + " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        raise SystemExit(rc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run comparator tests turn 1->N")
    parser.add_argument("--max-turn", type=int, default=3, help="Maximum turn number to run")
    parser.add_argument("--reset-first", action="store_true", help="Reset CSV/session before running")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_script = os.path.join(base_dir, "test_comparator.py")

    if args.reset_first:
        run([sys.executable, test_script, "--reset"])

    for turn in range(1, args.max_turn + 1):
        run([sys.executable, test_script, "--turn", str(turn)])

    run([sys.executable, test_script, "--summary"])
