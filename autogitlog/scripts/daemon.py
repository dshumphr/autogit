#!/usr/bin/env python3
"""
autogitlog daemon
Watches a directory and commits+pushes changes on a schedule.

Commit triggers:
  1. Quiescence: no new changes for --idle minutes
  2. Max interval: --max-interval minutes since last push (even if changes keep coming)

When a commit fires, a one-shot agent CLI subprocess is spawned to read the
staged diff and write a meaningful commit message (via commit_message.py).
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from commit_message import generate_commit_message, DEFAULT_AGENT_CMD, DEFAULT_AGENT_MODEL

# Set up logging (will create ~/.autogitlog/daemon.log for consolidated logs)
LOG_DIR = Path.home() / ".autogitlog"
LOG_FILE = LOG_DIR / "daemon.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("autogitlog")


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def has_changes(repo_dir: str) -> bool:
    r = run(["git", "status", "--porcelain"], cwd=repo_dir)
    return bool(r.stdout.strip())


def commit_and_push(repo_dir: str, branch: str, agent_cmd: str, agent_model: str, push_remote: bool = True) -> bool:
    """Stage all changes, ask the agent CLI for a commit message, commit, and optionally push."""
    r = run(["git", "add", "-A"], cwd=repo_dir)
    if r.returncode != 0:
        log.error(f"git add failed: {r.stderr}")
        return False

    # Bail out early if nothing was actually staged
    r = run(["git", "diff", "--cached", "--quiet"], cwd=repo_dir)
    if r.returncode == 0:
        log.info("Nothing staged to commit.")
        return False

    log.info("Invoking agent CLI for commit message...")
    msg = generate_commit_message(repo_dir, agent_cmd=agent_cmd, agent_model=agent_model)
    log.info(f"Commit message: {msg}")

    r = run(["git", "commit", "-m", msg], cwd=repo_dir)
    if r.returncode != 0:
        log.error(f"git commit failed: {r.stderr}")
        return False

    if not push_remote:
        log.info("Local-only mode: skipping push.")
        return True

    log.info(f"Pushing to origin/{branch}...")
    r = run(["git", "push", "origin", branch], cwd=repo_dir)
    if r.returncode != 0:
        log.error(f"git push failed: {r.stderr}")
        log.error("Will retry next cycle. Check remote auth.")
        return False

    log.info("Push successful.")
    return True


def load_local_config(watch_dir: str) -> dict:
    """Load config from .autogit in the watched directory"""
    config_file = Path(watch_dir) / ".autogit"
    if config_file.exists():
        with open(config_file) as f:
            return json.load(f)
    return None


def run_daemon(
    watch_dir: str,
    idle_minutes: float,
    max_interval_minutes: float,
    branch: str,
    poll_seconds: int,
    agent_cmd: str,
    agent_model: str,
    push_remote: bool = True,
):
    idle_secs        = idle_minutes * 60
    max_interval_secs = max_interval_minutes * 60

    log.info("Starting autogitlog daemon")
    log.info(f"  Watching:     {watch_dir}")
    log.info(f"  Idle trigger: {idle_minutes} min")
    log.info(f"  Max interval: {max_interval_minutes} min")
    log.info(f"  Poll interval:{poll_seconds} sec")
    log.info(f"  Branch:       {branch}")
    log.info(f"  Push remote:  {push_remote}")
    log.info(f"  Agent cmd:    {agent_cmd}")
    if agent_model:
        log.info(f"  Agent model:  {agent_model}")

    last_change_time = None
    last_push_time   = time.time()   # treat startup as a pseudo-push baseline
    pending_changes  = False

    def handle_signal(sig, frame):
        log.info("Received shutdown signal. Exiting.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    while True:
        now = time.time()
        changes_exist = has_changes(watch_dir)

        if changes_exist:
            if not pending_changes:
                log.info("Changes detected.")
                last_change_time = now
            pending_changes  = True

        should_commit = False
        reason        = ""

        if pending_changes:
            if last_change_time and (now - last_change_time) >= idle_secs:
                should_commit = True
                reason = f"idle for {idle_minutes} min"

            if (now - last_push_time) >= max_interval_secs:
                should_commit = True
                reason = f"max interval ({max_interval_minutes} min) reached"

        if should_commit:
            log.info(f"Commit trigger: {reason}")
            success = commit_and_push(watch_dir, branch, agent_cmd, agent_model, push_remote)
            if success:
                last_push_time   = time.time()
                last_change_time = None
                pending_changes  = False

        time.sleep(poll_seconds)


def main():
    parser = argparse.ArgumentParser(description="autogitlog daemon")
    parser.add_argument("--dir",          required=True, help="Directory to watch")
    parser.add_argument("--idle",         type=float,    help="Idle timeout in minutes (overrides config)")
    parser.add_argument("--max-interval", type=float,    help="Max interval in minutes (overrides config)")
    parser.add_argument("--poll",         type=int,      help="Poll interval in seconds (overrides config)")
    parser.add_argument("--branch",                      help="Branch to push to (overrides config)")
    parser.add_argument("--agent-cmd",                   help="Agent CLI command template (overrides config)")
    parser.add_argument("--agent-model",                 help="Model hint passed to the agent (overrides config)")
    parser.add_argument("--no-push",      action="store_true", help="Local-only mode: commit but do not push to remote")
    args = parser.parse_args()

    watch_dir = str(Path(args.dir).expanduser().resolve())

    # Load config from local .autogit file
    watch_cfg = load_local_config(watch_dir)
    
    if watch_cfg:
        idle         = args.idle         or watch_cfg.get("idle_minutes", 5)
        max_interval = args.max_interval or watch_cfg.get("max_interval_minutes", 60)
        poll         = args.poll         or watch_cfg.get("poll_seconds", 15)
        branch       = args.branch       or watch_cfg.get("branch", "main")
        agent_cmd    = args.agent_cmd    or watch_cfg.get("agent_cmd", DEFAULT_AGENT_CMD)
        agent_model  = args.agent_model  or watch_cfg.get("agent_model", DEFAULT_AGENT_MODEL)
        push_remote  = not args.no_push  and watch_cfg.get("push_remote", True)
    else:
        log.warning(f"No .autogit config found in {watch_dir}. Using CLI args or defaults.")
        idle         = args.idle or 5
        max_interval = args.max_interval or 60
        poll         = args.poll or 15
        branch       = args.branch or "main"
        agent_cmd    = args.agent_cmd or DEFAULT_AGENT_CMD
        agent_model  = args.agent_model or DEFAULT_AGENT_MODEL
        push_remote  = not args.no_push

    run_daemon(watch_dir, idle, max_interval, branch, poll, agent_cmd, agent_model, push_remote)


if __name__ == "__main__":
    main()
