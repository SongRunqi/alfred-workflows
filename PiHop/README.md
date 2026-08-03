# PiHop

Hop into pi / Claude Code agent sessions grouped by project, straight from
Alfred.

Requires **Alfred 5.5+** (the session browser uses the Text View).

## Usage

- `hop` — project list (auto-discovered from `~/.pi/agent/sessions` and
  `~/.claude`)
- ↩ on a project — its sessions
- ↩ on a session — resume it in the terminal
- ⌥ on a session — browse the conversation in a Text View (markdown-rendered,
  opens at the latest message)
- ⌘↵ in the Text View — back to the session list (Esc closes)
- `hop` again later — the project list shows "恢复上次浏览的会话" on top,
  restoring the last browsed session even after Alfred was closed
- ⌘↵ on "Start new session" — pick the agent

## Terminal support

Configure in Alfred → Configure Workflow… → **Terminal** (`AGENT_TERMINAL`):

| Value | Behavior | Notes |
| --- | --- | --- |
| System Default | `open` the session script | macOS default terminal |
| `iTerm` | new **tab** in the running app, brought to front | no setup needed |
| `Terminal` | new tab via ⌘T | needs **Accessibility** permission for Alfred |
| `kitty` | new tab via remote control | needs `kitty.conf`: `listen_on unix:/tmp/kitty-{kitty_pid}.sock` + `allow_remote_control yes`, then restart kitty once; falls back to a fresh window with the same flags |
| `ghostty` | new **window** (`open -a ghostty --args -e zsh …`) | no tab API yet |
| any app name | `open -a <app> <script>` | new window |
| any template with `{file}` | run as-is; `{file}` = session script | e.g. `wezterm start zsh {file}` |

kitty without remote control shows a notification with the exact config
steps. Sessions resumed from a Claude background agent (`claude agents`)
are detected and automatically **forked** (`--fork-session`) with a notice,
instead of claude exiting with a cryptic message.

## Behavior notes

- Resuming a session opens the terminal (frontmost when the app supports
  it) and runs `claude --resume <sid>` / `pi --session <file>` in the
  project directory.
- The Text View renders pi and Claude Code v2 jsonl (tool calls and
  thinking collapsed into details blocks, UTC timestamps converted to
  local) and opens scrolled to the latest message.
- Icons: official pi P-mark (green), official Anthropic starburst for
  Claude (orange), grey cpu for custom agents — all rendered on
  terminal-dark badges in `icons/`.

## Development

- `info.plist` is the node graph; scripts are plain Python + bash.
- `list-projects.py` / `list-project-sessions.py` — the two Script Filters.
- `launch.sh` — terminal dispatch and session resume (see its header for
  the input formats and terminal logic).
- `view-session.py` — session jsonl → markdown for the Text View; persists
  the last-viewed session to `alfred_workflow_data/last_viewed.txt`.
- `make_icons.swift` — renders the SF-Symbol icons (claude.png and pi.png
  are composited from official marks; steps documented in the file).
- Package: `zip -r ../"PiHop.alfredworkflow" . -x "make_icons.swift" "__pycache__" "*.pyc" ".DS_Store"`
