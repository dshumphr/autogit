#!/usr/bin/env python3
"""
Installs auto-git-log as a macOS launchd user agent so it runs in the background
and survives reboots.
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"


def install(watch_dir: str):
    # Verify .autogit config exists
    config_file = Path(watch_dir) / ".autogit"
    if not config_file.exists():
        print(f"No .autogit config found in {watch_dir}. Run setup.py first.")
        sys.exit(1)

    label = f"com.auto-git-log.{watch_dir.replace('/', '-').strip('-')}"
    plist_path = LAUNCH_AGENTS_DIR / f"{label}.plist"
    log_path = Path.home() / ".auto-git-log" / "daemon.log"
    python = sys.executable

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label}</string>

  <key>ProgramArguments</key>
  <array>
    <string>{python}</string>
    <string>{SCRIPTS_DIR}/daemon.py</string>
    <string>--dir</string>
    <string>{watch_dir}</string>
  </array>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>{log_path}</string>

  <key>StandardErrorPath</key>
  <string>{log_path}</string>
</dict>
</plist>
"""

    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(plist_content)
    print(f"Wrote plist: {plist_path}")

    # Load it
    subprocess.run(["launchctl", "load", str(plist_path)], check=True)
    print(f"✓ Loaded launchd agent: {label}")
    print(f"  Logs: {log_path}")
    print(f"\nTo stop:   launchctl unload {plist_path}")
    print(f"To remove: rm {plist_path} && launchctl unload {plist_path}")


def main():
    parser = argparse.ArgumentParser(description="Install auto-git-log as a macOS launchd agent")
    parser.add_argument("--dir", required=True, help="The watched directory (must already be configured)")
    args = parser.parse_args()
    watch_dir = str(Path(args.dir).expanduser().resolve())
    install(watch_dir)


if __name__ == "__main__":
    main()
