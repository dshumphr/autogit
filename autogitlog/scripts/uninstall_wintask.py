#!/usr/bin/env python3
"""
Uninstalls auto-git-log Windows Task Scheduler task for a directory.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def uninstall(watch_dir: str):
    watch_dir = str(Path(watch_dir).expanduser().resolve())
    safe_name = watch_dir.replace("\\", "-").replace(":", "").replace("/", "-").strip("-")
    task_name = f"auto-git-log-{safe_name}"

    # Delete task if exists
    print(f"Deleting Task Scheduler task: {task_name}")
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✓ Uninstalled task for {watch_dir}")
    else:
        print(f"No task found for {watch_dir} (or already deleted)")
        print(f"(Expected task: {task_name})")


def main():
    parser = argparse.ArgumentParser(description="Uninstall auto-git-log for a directory")
    parser.add_argument("--dir", required=True, help="The watched directory to uninstall")
    args = parser.parse_args()
    uninstall(args.dir)


if __name__ == "__main__":
    main()
