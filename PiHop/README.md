# PiHop

Hop into pi / Claude Code agent sessions grouped by project, straight from
Alfred.

## Usage

- `agent` — project list (auto-discovered from `~/.pi/agent/sessions` and
  `~/.claude`)
- ↩ on a project — its sessions
- ↩ on a session — resume it in the terminal · ⌘↵ on "Start new session" —
  pick the agent

## Development

- `info.plist` is the node graph; scripts are plain Python + bash.
- Package: `zip -r ../"PiHop.alfredworkflow" . -x "__pycache__" "*.pyc" ".DS_Store"`
