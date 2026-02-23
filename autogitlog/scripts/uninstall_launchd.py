#!/usr/bin/env python3
"""
Uninstalls autogitlog launchd service for a directory.
"""

import argparse
import subprocess
import sys
from pathlib import Path

LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"


def uninstall(watch_dir: str):
    watch_dir = str(Path(watch_dir).expanduser().resolve())
    label = f"com.autogitlog.{watch_dir.replace('/', '-').strip('-')}"
    plist_path = LAUNCH_AGENTS_DIR / f"{label}.plist"

    # Unload service if exists
    if plist_path.exists():
        print(f"Unloading launchd service: {label}")
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        print(f"Removing plist: {plist_path}")
        plist_path.unlink()
        print(f"✓ Uninstalled service for {watch_dir}")
    else:
        print(f"No launchd service found for {watch_dir}")
        print(f"(Expected plist: {plist_path})")


def main():
    parser = argparse.ArgumentParser(description="Uninstall autogitlog for a directory")
    parser.add_argument("--dir", required=True, help="The watched directory to uninstall")
    args = parser.parse_args()
    uninstall(args.dir)


if __name__ == "__main__":
    main()
