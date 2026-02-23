#!/usr/bin/env python3
"""
auto-git-log setup script
Initializes a directory for automatic git tracking.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_AGENT_CMD   = 'crush run --small_model "{prompt}"'
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

# Auto-git-log internal config
.autogit

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


def setup(args):
    watch_dir = Path(args.dir).expanduser().resolve()

    if not watch_dir.exists():
        print(f"Directory does not exist: {watch_dir}")
        sys.exit(1)

    print(f"Setting up auto-git-log for: {watch_dir}")

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

    # Add .gitignore if missing
    gitignore_path = watch_dir / ".gitignore"
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
        if args.ignore:
            print(f"Appending custom ignore patterns: {', '.join(args.ignore)}")
            existing = gitignore_path.read_text()
            if not existing.endswith('\n'):
                existing += '\n'
            existing += "\n# Custom patterns (added by auto-git-log)\n"
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
            run(["git", "commit", "-m", "initial commit (auto-git-log setup)"], cwd=watch_dir)
        else:
            print("Nothing to commit for initial commit.")

    # Save config to local .autogit file
    config = {
        "remote":               args.remote,
        "branch":               args.branch,
        "idle_minutes":         args.idle,
        "max_interval_minutes": args.max_interval,
        "poll_seconds":         args.poll,
        "agent_cmd":            args.agent_cmd,
    }
    if args.agent_model:
        config["agent_model"] = args.agent_model
    
    save_local_config(watch_dir, config)

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
    parser = argparse.ArgumentParser(description="Set up auto-git-log for a directory")
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
                             "as --small_model=<model>. Ignored if --agent-cmd is fully custom.")
    parser.add_argument("--ignore", nargs='*',
                        help="Additional file patterns to ignore (e.g., *.log *.tmp)")
    args = parser.parse_args()
    setup(args)


if __name__ == "__main__":
    main()
