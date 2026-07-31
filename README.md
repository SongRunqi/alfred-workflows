# Alfred Workflows

Collection of [Alfred](https://www.alfredapp.com/) workflows for macOS.

Each workflow has its own folder containing the source (`info.plist` + scripts).
The `.alfredworkflow` files at the repo root are packaged, installable builds —
double-click one to import into Alfred.

## Workflows

| Workflow | Keyword | What it does |
| --- | --- | --- |
| [Homebrew Manager](Homebrew%20Manager/) | `brew` | Manage Homebrew packages: search, install, uninstall, update, cleanup |
| [NetEase Music Controls](netease-music-controls/) | — | Control NetEase Cloud Music (play/pause/next/like/volume) from Alfred |
| [agent-session](agent-session/) | — | Launch pi-coding-agent projects/sessions from Alfred |
| [System Settings](System%20Settings/) | — | Search and open macOS System Settings panes |

## Install

Double-click any `.alfredworkflow` file, or drag a workflow folder into
Alfred → Preferences → Workflows.

## Development

- Workflows are plain folders with an `info.plist` (the node graph) plus scripts.
- Package a workflow by zipping the **contents** of its folder and renaming the
  result to `<Name>.alfredworkflow`.
- `prefs.plist` (user configuration) is gitignored and never committed.

## License

Private/personal use unless noted otherwise.
