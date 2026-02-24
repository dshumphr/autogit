#!/usr/bin/env python3
"""
Installs autogitlog as a macOS launchd user agent so it runs in the background
and survives reboots.
"""

import argparse
import os
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

    label = f"com.autogitlog.{watch_dir.replace('/', '-').strip('-')}"
    plist_path = LAUNCH_AGENTS_DIR / f"{label}.plist"
    log_path = Path.home() / ".autogitlog" / "daemon.log"
    python = sys.executable


    home = os.environ.get('HOME', str(Path.home()))
    path = os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin')
    # Ensure homebrew paths are included
    if '/opt/homebrew/bin' not in path:
        path = f"/opt/homebrew/bin:{path}"
    
    # Get Anthropic API key if available (needed for crush to generate commit messages)
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
    
    # Build environment variables dict
    env_vars = f"""    <key>HOME</key>
    <string>{home}</string>
    <key>PATH</key>
    <string>{path}</string>"""
    
    if anthropic_key:
        env_vars += f"""
    <key>ANTHROPIC_API_KEY</key>
    <string>{anthropic_key}</string>"""

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

  <key>WorkingDirectory</key>
  <string>{home}</string>

  <key>StandardOutPath</key>
  <string>{log_path}</string>

  <key>StandardErrorPath</key>
  <string>{log_path}</string>

  <key>EnvironmentVariables</key>
  <dict>
{env_vars}
  </dict>
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
    parser = argparse.ArgumentParser(description="Install autogitlog as a macOS launchd agent")
    parser.add_argument("--dir", required=True, help="The watched directory (must already be configured)")
    args = parser.parse_args()
    watch_dir = str(Path(args.dir).expanduser().resolve())
    install(watch_dir)


if __name__ == "__main__":
    main()
