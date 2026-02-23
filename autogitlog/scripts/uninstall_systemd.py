#!/usr/bin/env python3
"""
Uninstalls autogitlog systemd service for a directory.
"""

import argparse
import subprocess
import sys
from pathlib import Path

SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"


def uninstall(watch_dir: str):
    watch_dir = str(Path(watch_dir).expanduser().resolve())
    safe_name = watch_dir.replace("/", "-").strip("-")
    service_name = f"autogitlog-{safe_name}"
    service_file = SYSTEMD_USER_DIR / f"{service_name}.service"

    # Stop and disable service if exists
    if service_file.exists():
        print(f"Stopping and disabling service: {service_name}")
        subprocess.run(["systemctl", "--user", "stop", service_name], capture_output=True)
        subprocess.run(["systemctl", "--user", "disable", service_name], capture_output=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        
        print(f"Removing service file: {service_file}")
        service_file.unlink()
        print(f"✓ Uninstalled service for {watch_dir}")
    else:
        print(f"No systemd service found for {watch_dir}")
        print(f"(Expected service: {service_name})")


def main():
    parser = argparse.ArgumentParser(description="Uninstall autogitlog for a directory")
    parser.add_argument("--dir", required=True, help="The watched directory to uninstall")
    args = parser.parse_args()
    uninstall(args.dir)


if __name__ == "__main__":
    main()
