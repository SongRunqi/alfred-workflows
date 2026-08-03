# PiHop

Hop into pi / Claude Code agent sessions grouped by project, straight from
Alfred.

Requires **Alfred 5.5+** (the session browser uses the Text View).

## Usage

- `hop` — project list (auto-discovered from `~/.pi/agent/sessions` and
  `~/.claude`)
- ↩ on a project — its sessions
- ↩ on a session — resume it in the terminal
- ⌥ on a session — browse the conversation in a Text View (markdown-rendered)
- ⌘↵ on "Start new session" — pick the agent

## Development

- `info.plist` is the node graph; scripts are plain Python + bash.
- `view-session.py` renders a session jsonl as markdown for the Text View
  (handles both pi and Claude Code v2 formats, UTC timestamps converted).
- Package: `zip -r ../"PiHop.alfredworkflow" . -x "__pycache__" "*.pyc" ".DS_Store"`
