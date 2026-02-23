#!/usr/bin/env python3
"""
Installs autogitlog as a systemd user service on Linux.
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"


def install(watch_dir: str):
    # Verify .autogit config exists
    config_file = Path(watch_dir) / ".autogit"
    if not config_file.exists():
        print(f"No .autogit config found in {watch_dir}. Run setup.py first.")
        sys.exit(1)

    safe_name = watch_dir.replace("/", "-").strip("-")
    service_name = f"autogitlog-{safe_name}"
    service_file = SYSTEMD_USER_DIR / f"{service_name}.service"
    python = sys.executable
    log_path = Path.home() / ".autogitlog" / "daemon.log"

    unit_content = f"""[Unit]
Description=autogitlog watcher for {watch_dir}
After=network.target

[Service]
Type=simple
ExecStart={python} {SCRIPTS_DIR}/daemon.py --dir {watch_dir}
Restart=on-failure
RestartSec=30
StandardOutput=append:{log_path}
StandardError=append:{log_path}

[Install]
WantedBy=default.target
"""

    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    service_file.write_text(unit_content)
    print(f"Wrote service file: {service_file}")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", service_name], check=True)

    print(f"\n✓ Installed and started systemd user service: {service_name}")
    print(f"  Logs: {log_path}")
    print(f"  Or:   journalctl --user -u {service_name} -f")
    print(f"\nTo stop:    systemctl --user stop {service_name}")
    print(f"To disable: systemctl --user disable {service_name}")


def main():
    parser = argparse.ArgumentParser(description="Install autogitlog as a systemd user service")
    parser.add_argument("--dir", required=True, help="The watched directory (must already be configured)")
    args = parser.parse_args()
    watch_dir = str(Path(args.dir).expanduser().resolve())
    install(watch_dir)


if __name__ == "__main__":
    main()
