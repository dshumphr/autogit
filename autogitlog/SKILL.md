---
name: auto-git-log
description: "Automatically tracks changes in a directory by committing and pushing them via git on a schedule. Use this skill whenever the user wants to: set up automatic git versioning for notes, text files, journals, or any non-code files; create a searchable revision history for documents; run a 'git watch' or 'auto-commit' daemon; periodically back up a folder to GitHub; or track changes to a directory without manually running git. Trigger this skill for any request involving automatic/periodic git commits, watching a directory for changes, or setting up git logging for notes or documents. Works best with files which are LLM-understable."
---

# Auto-Git-Log

Automatically watches a directory, generates commit messages via an agent CLI, and pushes changes to GitHub when:
- Changes have been idle for **X minutes** (quiescence trigger), OR
- **Y minutes** have passed since the last push (max-interval trigger)

Designed primarily for **non-code files** — notes, journals, research, drafts, configs — where you want a searchable git history without touching git manually.

---

## Quick Start

```bash
# Directory configuration setup
python3 "scripts/setup.py" \
  --dir ~/notes \
  --remote git@github.com:user/notes.git \
  --idle 5 \
  --max-interval 60

# Install watcher as a persistent background service (survives reboots)
python3 "$SKILL_DIR/scripts/install_launchd.py" --dir ~/notes   # macOS
python3 "$SKILL_DIR/scripts/install_systemd.py" --dir ~/notes   # Linux
python3 "$SKILL_DIR/scripts/install_wintask.py" --dir ~/notes   # Windows
```

---

## When the User Asks You to Set This Up

Follow these phases in order:

### Phase 1: Gather Requirements

Ask (or infer from context):
1. **Which directory** to watch?
2. **GitHub remote URL** — Infer from local git config if present. If the directory doesn't have a repo set yet, try to infer a remote URL from context like the directory chosen. If you can't infer, ask the user for the remote URL (SSH or HTTPS). 
3. **Idle timeout** (default: 5 min) — how long with no changes before committing?
4. **Max interval** (default: 60 min) — force-commit even if changes keep rolling in?
5. **Poll interval** (default: 15 sec) — how frequently to check for changes?
6. **Agent CLI** (default: `crush run --small_model "{prompt}"`) — the command used to generate commit messages. See [Agent CLI Configuration](#agent-cli-configuration) below.
7. **Branch** to push to? (default: `main`)
8. **File patterns to ignore?** (e.g., `*.tmp`, `.DS_Store` — sensible defaults apply)

### Phase 2: Check Prerequisites

```bash
git --version     # must be installed
python3 --version # needed for the daemon and scripts
crush --version   # or whichever agent CLI the user wants — verify it's on PATH
```

For SSH remotes, verify: `ssh -T git@github.com`
For HTTPS, note the user may need a personal access token stored in the git credential helper.

### Phase 3: Initialize the Directory

```bash
python3 "scripts/setup.py" \
  --dir "/path/to/dir" \
  --remote "git@github.com:user/repo.git" \
  --branch main \
  --idle 5 \
  --max-interval 60 \
  --poll 15 \
  --agent-cmd 'crush run --small_model "{prompt}"'
  # --agent-model claude-haiku-4-5-20251001   (optional model override)
```

This will:
- `git init` if not already a repo
- Add `.gitignore` with sensible defaults
- Set or update the remote
- Create an initial commit if the repo is empty
- Save config to `~/.auto-git-log/config.json`

### Phase 4: Setup the background service to run the watcher daemon:

#### macOS (launchd)
```bash
SKILL_DIR="$HOME/.config/crush/skills/auto-git-log"
python3 "$SKILL_DIR/scripts/install_launchd.py" --dir ~/notes
```

#### Linux (systemd)
```bash
SKILL_DIR="$HOME/.config/crush/skills/auto-git-log"
python3 "$SKILL_DIR/scripts/install_systemd.py" --dir ~/notes
```

#### Windows (Task Scheduler)
```bash
SKILL_DIR="$HOME/.config/crush/skills/auto-git-log"
python3 "$SKILL_DIR/scripts/install_wintask.py" --dir ~/notes
```

---

## Agent CLI Configuration

When a commit is triggered, the daemon calls `commit_message.py`, which **shells out to the configured agent CLI** and captures its stdout as the commit message.

### Default: crush

```
crush run --small_model "{prompt}"
```

The `{prompt}` placeholder is replaced with the full prompt text (the diff + instructions). `--small_model` tells crush to use its fast/cheap model. To pin a specific model:

```bash
--agent-cmd 'crush run --small_model=claude-haiku-4-5-20251001 "{prompt}"'
# or equivalently, just pass --agent-model:
--agent-model claude-haiku-4-5-20251001
```

### Other agent CLIs

Any CLI that reads a prompt and writes the response to stdout works. Use `{prompt}` for inline placement, or omit it to receive via stdin:

```bash
# claude CLI (inline)
--agent-cmd 'claude -p "{prompt}"'

# Custom wrapper script
--agent-cmd '/usr/local/bin/my-commit-agent'

# Pipe pattern (stdin, no {prompt})
--agent-cmd 'cat | ollama run llama3'
```

**Agent CLI contract:**
- Receives the prompt as a shell argument or via stdin
- Writes a single commit message line to stdout
- Exits 0 on success

**Fallback:** If the agent CLI exits non-zero, times out (60s), or produces no output, the daemon logs the error and falls back to a stat-based message like `auto: 3 files changed, 42 insertions(+)`. Commits are never silently skipped.

---

## Configuration File

Stored at `~/.auto-git-log/config.json`:

```json
{
  "watches": [
    {
      "dir": "/absolute/path/to/dir",
      "remote": "git@github.com:user/repo.git",
      "branch": "main",
      "idle_minutes": 5,
      "max_interval_minutes": 60,
      "poll_seconds": 15,
      "agent_cmd": "crush run --small_model \"{prompt}\"",
      "agent_model": null,
      "last_push": null,
      "pid": null
    }
  ]
}
```

`agent_model` is `null` by default. When set, it's substituted into the default crush command as `--small_model=<model>` — useful if you want to pin a specific model without writing a full custom `agent_cmd`.

Multiple directories can be watched simultaneously with different configs.

---

## Troubleshooting

**Agent CLI not found / command not found**
- Verify it's on PATH: `which crush` or `crush --version`
- Use the full path in `--agent-cmd` if needed: `/usr/local/bin/crush run ...`

**Push fails with auth error**
- SSH: `ssh -T git@github.com`. Add key with `ssh-add ~/.ssh/id_ed25519`.
- HTTPS: `git config --global credential.helper store`, then do one manual push.

**Commit messages are vague / fallback fires every time**
- Check `~/.auto-git-log/daemon.log` for the agent CLI error
- Test the agent command manually: `crush run --small_model "say hello"`

**Too many commits**
- Increase `--idle` so changes must settle longer before triggering
- Increase `--max-interval` to reduce forced commits

**"nothing to commit" but files changed**
- Files may match `.gitignore`. Check: `git status --ignored`

---

## Scripts Reference

| Script | Purpose |
|---|---|
| `scripts/setup.py` | One-time directory initialization |
| `scripts/daemon.py` | The main watcher loop |
| `scripts/commit_message.py` | Shells out to agent CLI for commit messages |
| `scripts/install_launchd.py` | macOS persistent service installer |
| `scripts/install_systemd.py` | Linux persistent service installer |
| `scripts/install_wintask.py` | Windows Task Scheduler installer |

You may read the relevant script before running it to understand its exact behavior.
