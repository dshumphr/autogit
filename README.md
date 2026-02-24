# autogitlog

A **Crush/Claude Code skill** that automatically tracks changes in a directory, committing and pushing them to GitHub with LLM-powered commit messages. Designed for LLM-readable **non-code files** — notes, journals, research, drafts, configs — where you want a searchable git history without touching git manually.

> **Note:** This is an agent skill designed to be installed in your agent's skill directory (e.g., `~/.config/crush/skills/autogitlog/`). The scripts run from the skill directory itself.

## Features

- 🤖 **AI-powered commit messages** via configurable agent CLI (default: [crush](https://github.com/charmbracelet/crush))
- ⏱️ **Two Commit Triggers:**
  - **Quiescence:** Commit after X minutes without further changes (default: 5 min)
  - **Max interval:** Force commit after Y minutes even if changes keep coming (default: 60 min)
  - Both are only triggered if there are changes since the previous commit.
- 🔄 **Cross-platform:** macOS, Linux, Windows
- 📦 **Few dependencies:** Python, Git, and your favorite tool-calling agent cli
- 🔌 **Flexible agent integration:** Works with any CLI that reads prompts and writes to stdout

## Prerequisites

- **Python** (tested with 3.12.7)
- **Git**
- **Agent CLI** (one of):
  - [crush](https://github.com/crushsh/crush) (default) — `brew install crush` or see crush docs
  - [claude-cli](https://github.com/anthropics/claude-cli) — `npm install -g @anthropic-ai/claude-cli`
  - Any other Anthropic Skill compatible agent cli

## Installation

### Quick Install (Recommended)

```bash
git clone https://github.com/yourusername/autogitlog.git
cd autogitlog
./install.sh
```

This installs the skill to the default Crush skills directory (`~/.config/crush/skills/autogitlog`).

### Custom Installation Directory

To install to a specific location (e.g., for a single agent):

```bash
./install.sh --dir /path/to/your/agent/skills
```

### Manual Installation

Alternatively, copy the `autogitlog` directory to your agent's skills directory:

```bash
cp -r autogitlog ~/.config/crush/skills/
```

## Usage

Once installed, simply ask your agent to set up auto git log for a directory:

```
Set up auto git log for ~/Documents/notes
```

If there are files that should be ignored, let the agent know and it will update `.gitignore` appropriately.

## Configuration Options
You can ask the agent to configure a given directory's auto git log behavior in several ways. Since it is an agent skill, no precise format is required, though they are listed as flags here for convenience.

| Option | Default | Description |
|--------|---------|-------------|
| `--dir` | *(required)* | Directory to watch |
| `--remote` | inferred from dir and git configuration | Git remote URL (SSH or HTTPS) |
| `--branch` | `main` | Branch to commit and push to |
| `--idle` | `5` | Minutes of inactivity before committing |
| `--max-interval` | `60` | Max minutes between commits (force commit even if changes keep coming) |
| `--poll` | `30` | Seconds between change checks |
| `--agent-cmd` | `crush run --small-model "{prompt}"` | Agent CLI command template (see below) |
| `--ignore` | *(none)* | Additional file patterns to ignore (space-separated, e.g., `*.log *.tmp secret.txt`) |

### Agent CLI Configuration

The `--agent-cmd` option controls how commit messages are generated. The default uses [crush](https://github.com/crushsh/crush):

```bash
--agent-cmd 'crush run --small-model "{prompt}"'
```

The `{prompt}` placeholder gets replaced with the full prompt (diff + instructions). If you omit `{prompt}`, the prompt is sent via stdin instead.

#### Using Different Agent CLIs

**Claude CLI:**
```bash
--agent-cmd 'claude -p "{prompt}"'
```

**Custom script:**
```bash
--agent-cmd '/usr/local/bin/my-commit-agent'
```

#### Agent CLI Requirements

Your agent CLI must:
1. Accept a prompt (via command-line argument with `{prompt}` or stdin)
2. Write a single commit message line to stdout
3. Exit with code 0 on success

**Fallback behavior:** If the agent CLI fails, times out (60s), or produces no output, autogitlog falls back to a stat-based message like `auto: 3 files changed, 42 insertions(+)`. Commits are never silently skipped.

## How It Works

1. **Polling:** Every `poll_seconds`, daemon runs `git status --porcelain` to check for changes
2. **Trigger detection:** Commits are triggered when:
   - No further changes for `idle_minutes` (quiescence), OR
   - `max_interval_minutes` since last push (force commit)
3. **Commit message generation:**
   - Daemon stages all changes with `git add -A`
   - Calls `commit_message.py` which shells out to agent CLI
   - Agent receives the diff and writes a commit message
   - Falls back to stat-based message if agent fails
4. **Push:** Commits are immediately pushed to `origin/<branch>`