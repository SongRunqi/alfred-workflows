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
| [Glide](Glide/) | `maximize` `reasonable` `center` `topleft` … + `window` list | Maximize / reasonable / center / quarter tiles via keywords (hotkeys ⌃⌥⌘M R C 7 9 1 3 optional) |
| [PiHop](PiHop/) | `hop` | Hop into pi / Claude Code agent sessions by project — resume in your terminal (iTerm / kitty / ghostty…), ⌥ browse a session in a Text View, restore the last-viewed session |
| [System Settings](System%20Settings/) | — | Search and open macOS System Settings panes |

## Install

Double-click any `.alfredworkflow` file, or drag a workflow folder into
Alfred → Preferences → Workflows.

## Development

- Workflows are plain folders with an `info.plist` (the node graph) plus scripts.
- Package a workflow by zipping the **contents** of its folder and renaming the
  result to `<Name>.alfredworkflow`.
- `prefs.plist` (user configuration) is gitignored and never committed.
- **Alfred may run from a synced preferences folder** (`~/data/sync/alfred`
  here): after packaging, also copy the changed files into the installed
  workflow folder there — script changes apply instantly, `info.plist` after
  ~20 s. When re-importing, leave the dialog's migrate/keep option off or old
  keywords silently survive.

## License

Private/personal use unless noted otherwise.
