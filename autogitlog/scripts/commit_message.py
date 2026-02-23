#!/usr/bin/env python3
"""
Agent CLI-powered commit message generator.

Builds a prompt from the staged git diff, then shells out to a configured
agent CLI to produce the commit message. The agent CLI is fully configurable —
defaults to crush with its small/fast model flag.

Default command template:
    crush run --small_model "{prompt}"

The {prompt} placeholder is replaced with the full prompt text.
Alternatively, set agent_cmd to read from stdin, e.g.:
    echo "{prompt}" | my-llm-cli

Agent CLI contract:
    - Receives the prompt (via inline arg or stdin)
    - Writes a single commit message line to stdout
    - Exits 0 on success

Falls back to a heuristic stat-based message if the agent call fails.
"""

import shlex
import subprocess
import sys

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# The default agent command template.
# {prompt} is replaced with the full prompt string.
# Use shell=True so pipes, env vars, etc. all work.
DEFAULT_AGENT_CMD = 'crush run --small_model "{prompt}"'

# Optional: override the model used by crush (e.g. "claude-haiku-4-5-20251001")
# If set, the template becomes: crush run --small_model=<model> "{prompt}"
DEFAULT_AGENT_MODEL = None

# Max characters of diff to send (large diffs get truncated)
MAX_DIFF_CHARS = 12_000

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """\
You are a git commit message writer. Write a single commit message for the diff below.

Rules:
- Output ONLY the commit message — no explanation, no preamble, no quotes
- Start with an imperative verb: add, update, revise, remove, expand, fix, reorganize
- Be specific about content when readable (e.g. "expand async section in rust-notes.md")
- For binary/unreadable files, describe the operation: "add 2 images to assets/"
- For large batches, summarize: "revise meeting notes for March"
- Maximum 72 characters

--- STAT SUMMARY ---
{stat}

--- FULL DIFF ---
{diff}"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_stat(repo_dir: str) -> str:
    r = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        cwd=repo_dir, capture_output=True, text=True
    )
    return r.stdout.strip()


def _get_diff(repo_dir: str) -> str:
    r = subprocess.run(
        ["git", "diff", "--cached"],
        cwd=repo_dir, capture_output=True, text=True
    )
    diff = r.stdout
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n\n[... diff truncated ...]"
    return diff


def _heuristic_message(repo_dir: str) -> str:
    """Stat-based fallback when the agent CLI is unavailable or fails."""
    r = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        cwd=repo_dir, capture_output=True, text=True
    )
    stat = r.stdout.strip()
    if not stat:
        return "update files"
    last = stat.splitlines()[-1]
    return f"auto: {last}"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_commit_message(
    repo_dir: str,
    agent_cmd: str = DEFAULT_AGENT_CMD,
    agent_model: str = DEFAULT_AGENT_MODEL,
) -> str:
    """
    Calls the agent CLI to generate a commit message for the current staged diff.

    agent_cmd: shell command template with optional {prompt} placeholder.
               If {prompt} is absent, the prompt is passed via stdin instead.
    agent_model: if set, substituted into the default crush command as
                 --small_model=<model>. Ignored if agent_cmd is fully custom.
    """
    stat = _get_stat(repo_dir)
    diff = _get_diff(repo_dir)

    if not stat and not diff:
        return "housekeeping: no content changes"

    prompt = PROMPT_TEMPLATE.format(stat=stat, diff=diff)

    # If using the default crush command and a specific model was requested,
    # rewrite the flag to --small_model=<model>
    cmd_template = agent_cmd
    if agent_model and agent_cmd == DEFAULT_AGENT_CMD:
        cmd_template = f'crush run --small_model={shlex.quote(agent_model)} "{{prompt}}"'

    # Decide whether prompt goes inline or via stdin
    use_stdin = "{prompt}" not in cmd_template
    if use_stdin:
        cmd = cmd_template
        input_data = prompt
    else:
        # Escape the prompt for safe shell interpolation
        cmd = cmd_template.replace("{prompt}", prompt.replace('"', '\\"').replace('`', '\\`').replace('$', '\\$'))
        input_data = None

    log_prefix = "[autogitlog]"
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"{log_prefix} agent CLI exited {result.returncode}: {result.stderr.strip()}", file=sys.stderr)
            return _heuristic_message(repo_dir)

        # Take first non-empty line of output as the commit message
        output = result.stdout.strip()
        for line in output.splitlines():
            line = line.strip().strip('"').strip("'")
            if line:
                # Enforce 72-char hard limit
                if len(line) > 72:
                    line = line[:69] + "..."
                return line

        print(f"{log_prefix} agent CLI produced no output, using fallback", file=sys.stderr)
        return _heuristic_message(repo_dir)

    except subprocess.TimeoutExpired:
        print(f"{log_prefix} agent CLI timed out after 60s, using fallback", file=sys.stderr)
        return _heuristic_message(repo_dir)
    except Exception as e:
        print(f"{log_prefix} agent CLI error ({e}), using fallback", file=sys.stderr)
        return _heuristic_message(repo_dir)


# ---------------------------------------------------------------------------
# CLI: python commit_message.py /path/to/repo ["custom agent cmd"]
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    cmd  = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_AGENT_CMD
    print(generate_commit_message(repo, agent_cmd=cmd))
