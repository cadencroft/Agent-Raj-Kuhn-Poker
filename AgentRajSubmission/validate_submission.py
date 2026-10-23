#!/usr/bin/env python3
"""Run every student-visible submission check with one command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent

CHECKS = (
    (
        "Code quality",
        (
            sys.executable,
            "-m",
            "ruff",
            "check",
            ".",
        ),
    ),
    ("Public tests", (sys.executable, "-m", "pytest")),
    (
        "Arena submission contract",
        (
            sys.executable,
            "-m",
            "arena.cli",
            "test",
            ".",
            "--hands",
            "30",
            "--timeout-ms",
            "100",
        ),
    ),
)


def main() -> int:
    """Run checks in order and return a shell-friendly status code."""
    print("Validating poker agent submission...", flush=True)

    for name, command in CHECKS:
        print(f"\n==> {name}", flush=True)
        completed = subprocess.run(command, cwd=REPOSITORY_ROOT, check=False)
        if completed.returncode != 0:
            print(f"\nValidation failed during: {name}", file=sys.stderr)
            return completed.returncode

    print("\nAll submission checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
