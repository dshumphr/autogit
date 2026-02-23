#!/usr/bin/env python3
"""
Installs auto-git-log as a Windows Task Scheduler task.
Run this in an elevated (Administrator) prompt, or use --no-elevate to
register as a user-level task (which may not start at login without elevation).
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
CONFIG_FILE = Path.home() / ".auto-git-log" / "config.json"


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"watches": []}


def install(watch_dir: str):
    config = load_config()
    watch = next((w for w in config["watches"] if w["dir"] == watch_dir), None)
    if not watch:
        print(f"No config found for {watch_dir}. Run setup.py first.")
        sys.exit(1)

    safe_name = watch_dir.replace("\\", "-").replace(":", "").replace("/", "-").strip("-")
    task_name = f"auto-git-log-{safe_name}"
    python = sys.executable
    daemon_script = str(SCRIPTS_DIR / "daemon.py")

    # Build schtasks command
    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'"{python}" "{daemon_script}" --dir "{watch_dir}"',
        "/sc", "ONLOGON",
        "/ru", "SYSTEM",  # runs as system to avoid session issues; adjust if needed
        "/f",             # force overwrite if exists
        "/rl", "HIGHEST",
    ]

    print(f"Registering Task Scheduler task: {task_name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        print("\nTip: Try running this script as Administrator.")
        sys.exit(1)

    print(f"✓ Task registered: {task_name}")
    print(f"  It will start automatically on login.")
    print(f"\nTo start now:   schtasks /run /tn \"{task_name}\"")
    print(f"To stop:        schtasks /end /tn \"{task_name}\"")
    print(f"To delete:      schtasks /delete /tn \"{task_name}\" /f")
    print(f"\nLogs: {Path.home() / '.auto-git-log' / 'daemon.log'}")


def main():
    parser = argparse.ArgumentParser(
        description="Install auto-git-log as a Windows Task Scheduler task"
    )
    parser.add_argument("--dir", required=True, help="The watched directory (must already be configured)")
    args = parser.parse_args()
    install(args.dir)


if __name__ == "__main__":
    main()
