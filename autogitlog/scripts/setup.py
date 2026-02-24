#!/usr/bin/env python3
"""
autogitlog setup script
Initializes a directory for automatic git tracking.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_AGENT_CMD   = 'crush run "{prompt}" --small-model=claude-haiku-4-5-20251001'
DEFAULT_AGENT_MODEL = None

DEFAULT_GITIGNORE = """\
# OS cruft
.DS_Store
Thumbs.db
desktop.ini

# Editor temp files
*.tmp
*.swp
*.swo
*~
.#*
\\#*#

# autogitlog internal config
.autogit
.autogitlog/

# Common artifacts
*.pyc
__pycache__/
node_modules/
"""


def run(cmd, cwd=None, check=True):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR running {' '.join(cmd)}:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result


def save_local_config(watch_dir: Path, config: dict):
    """Save config to .autogit in the watched directory"""
    config_file = watch_dir / ".autogit"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)


def test_git_auth(remote_url, cwd):
    """Test if we can authenticate to the remote. Returns (success, message)"""
    print("Testing git authentication...")
    
    # Try ls-remote as a non-destructive auth test
    result = subprocess.run(
        ["git", "ls-remote", "--heads", remote_url],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        return True, "Authentication successful"
    
    # Parse common errors
    error = result.stderr.lower()
    if "permission denied" in error or "authentication failed" in error:
        if remote_url.startswith("git@"):
            return False, "SSH authentication failed. Run: ssh -T git@github.com"
        else:
            return False, "HTTPS authentication failed. Check credentials."
    elif "could not resolve host" in error:
        return False, "Network error: cannot reach GitHub"
    else:
        return False, f"Git remote test failed: {result.stderr[:200]}"


def resolve_agent_cmd_path(agent_cmd):
    """Resolve relative paths in agent command to absolute paths"""
    # Extract the command name (first token)
    parts = agent_cmd.split()
    if not parts:
        return agent_cmd
    
    cmd_name = parts[0]
    
    # If it's already an absolute path, return as-is
    if cmd_name.startswith('/'):
        return agent_cmd
    
    # Try to find the full path
    full_path = shutil.which(cmd_name)
    if full_path:
        parts[0] = full_path
        return ' '.join(parts)
    
    # Couldn't resolve, return original with warning
    print(f"WARNING: Could not find '{cmd_name}' in PATH. "
          f"Service may fail if PATH is not available.")
    return agent_cmd


def setup(args):
    watch_dir = Path(args.dir).expanduser().resolve()

    if not watch_dir.exists():
        print(f"Directory does not exist: {watch_dir}")
        sys.exit(1)

    print(f"Setting up autogitlog for: {watch_dir}")
    
    # Detect if this is a config update
    config_file = watch_dir / ".autogit"
    is_update = config_file.exists()

    # Init git if needed
    if not (watch_dir / ".git").exists():
        print("Initializing git repository...")
        run(["git", "init", "-b", args.branch], cwd=watch_dir)
    else:
        print("Git repo already exists, skipping init.")

    run(["git", "checkout", "-B", args.branch], cwd=watch_dir, check=False)

    # Set remote
    existing_remotes = run(["git", "remote"], cwd=watch_dir, check=False).stdout.split()
    if "origin" in existing_remotes:
        print(f"Updating remote origin to {args.remote}")
        run(["git", "remote", "set-url", "origin", args.remote], cwd=watch_dir)
    else:
        print(f"Adding remote origin: {args.remote}")
        run(["git", "remote", "add", "origin", args.remote], cwd=watch_dir)
    
    # Test authentication
    auth_ok, auth_msg = test_git_auth(args.remote, watch_dir)
    if not auth_ok:
        print(f"\nWARNING: {auth_msg}")
        print("Setup will continue, but pushes will fail until authentication is configured.")
    else:
        print(f"✓ {auth_msg}")

    # Add .gitignore if missing
    gitignore_path = watch_dir / ".gitignore"
    required_patterns = ['.autogit', '.autogitlog/']
    
    if not gitignore_path.exists():
        print("Creating .gitignore...")
        gitignore_content = DEFAULT_GITIGNORE
        if args.ignore:
            print(f"Adding custom ignore patterns: {', '.join(args.ignore)}")
            gitignore_content += "\n# Custom patterns\n"
            for pattern in args.ignore:
                gitignore_content += f"{pattern}\n"
        gitignore_path.write_text(gitignore_content)
    else:
        print(".gitignore already exists.")
        existing = gitignore_path.read_text()
        
        # Ensure required patterns are present
        missing_patterns = []
        for pattern in required_patterns:
            if pattern not in existing:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            print(f"Adding required patterns to .gitignore: {', '.join(missing_patterns)}")
            if not existing.endswith('\n'):
                existing += '\n'
            existing += "\n# autogitlog config (added by setup)\n"
            for pattern in missing_patterns:
                existing += f"{pattern}\n"
            gitignore_path.write_text(existing)
        
        if args.ignore:
            print(f"Appending custom ignore patterns: {', '.join(args.ignore)}")
            existing = gitignore_path.read_text()
            if not existing.endswith('\n'):
                existing += '\n'
            existing += "\n# Custom patterns (added by autogitlog)\n"
            for pattern in args.ignore:
                existing += f"{pattern}\n"
            gitignore_path.write_text(existing)

    # Initial commit if repo is empty
    log_result = run(["git", "log", "--oneline", "-1"], cwd=watch_dir, check=False)
    if not log_result.stdout.strip():
        print("Making initial commit...")
        run(["git", "add", "-A"], cwd=watch_dir)
        status = run(["git", "status", "--porcelain"], cwd=watch_dir)
        if status.stdout.strip():
            run(["git", "commit", "-m", "initial commit (autogitlog setup)"], cwd=watch_dir)
        else:
            print("Nothing to commit for initial commit.")

    # Resolve agent command to absolute path
    resolved_agent_cmd = resolve_agent_cmd_path(args.agent_cmd)
    
    # Save config to local .autogit file
    config = {
        "remote":               args.remote,
        "branch":               args.branch,
        "idle_minutes":         args.idle,
        "max_interval_minutes": args.max_interval,
        "poll_seconds":         args.poll,
        "agent_cmd":            resolved_agent_cmd,
    }
    if args.agent_model:
        config["agent_model"] = args.agent_model
    
    save_local_config(watch_dir, config)
    
    # If this was an update and a service might be running, suggest restart
    if is_update:
        print("\n⚠ Configuration updated. If the watcher service is running, restart it:")
        if sys.platform == "darwin":
            print(f"  launchctl stop com.autogitlog.{watch_dir.name}")
            print(f"  launchctl start com.autogitlog.{watch_dir.name}")
        elif sys.platform == "linux":
            print(f"  systemctl --user restart autogitlog-{watch_dir.name}")
        elif sys.platform == "win32":
            print(f"  Stop and start the 'autogitlog-{watch_dir.name}' task in Task Scheduler")

    print(f"\n✓ Setup complete!")
    print(f"  Dir:          {watch_dir}")
    print(f"  Remote:       {args.remote}")
    print(f"  Branch:       {args.branch}")
    print(f"  Idle timeout: {args.idle} min")
    print(f"  Max interval: {args.max_interval} min")
    print(f"  Poll interval:{args.poll} sec")
    print(f"  Agent cmd:    {args.agent_cmd}")
    if args.agent_model:
        print(f"  Agent model:  {args.agent_model}")
    print(f"  Config saved: {watch_dir}/.autogit")
    print(f"\nStart watching with:")
    print(f"  python3 {Path(__file__).parent}/daemon.py --dir \"{watch_dir}\"")


def main():
    parser = argparse.ArgumentParser(description="Set up autogitlog for a directory")
    parser.add_argument("--dir",    required=True, help="Directory to watch")
    parser.add_argument("--remote", required=True, help="Git remote URL")
    parser.add_argument("--branch", default="main", help="Branch name (default: main)")
    parser.add_argument("--idle",   type=float, default=5.0,
                        help="Minutes of inactivity before committing (default: 5)")
    parser.add_argument("--max-interval", type=float, default=60.0,
                        help="Max minutes between commits (default: 60)")
    parser.add_argument("--poll",   type=int, default=15,
                        help="Seconds between change checks (default: 15)")
    parser.add_argument("--agent-cmd", default=DEFAULT_AGENT_CMD,
                        help='Agent CLI command template. Use {prompt} for inline placement, '
                             'or omit it to receive the prompt via stdin. '
                             f'Default: {DEFAULT_AGENT_CMD!r}')
    parser.add_argument("--agent-model", default=DEFAULT_AGENT_MODEL,
                        help="Optional model name passed to the default crush command "
                             "as --small-model=<model>. Ignored if --agent-cmd is fully custom.")
    parser.add_argument("--ignore", nargs='*',
                        help="Additional file patterns to ignore (e.g., *.log *.tmp)")
    args = parser.parse_args()
    setup(args)


if __name__ == "__main__":
    main()
