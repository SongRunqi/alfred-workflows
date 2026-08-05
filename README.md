# Alfred Workflows

Collection of [Alfred](https://www.alfredapp.com/) workflows for macOS.

Each workflow has its own folder containing the source (`info.plist` + scripts).
The `.alfredworkflow` files at the repo root are packaged, installable builds —
double-click one to import into Alfred.

## Workflows

| Workflow | Keyword | What it does | Download |
| --- | --- | --- | --- |
| [Homebrew Manager](Homebrew%20Manager/) | `brew` | Manage Homebrew packages: search, install, uninstall, update, cleanup | [⬇️](https://github.com/SongRunqi/alfred-workflows/raw/main/Homebrew%20Manager.alfredworkflow) |
| [NetEase Music Controls](netease-music-controls/) | — | Control NetEase Cloud Music (play/pause/next/like/volume) from Alfred | [⬇️](https://github.com/SongRunqi/alfred-workflows/raw/main/NetEase%20Music%20Controls.alfredworkflow) |
| [Glide](Glide/) | `maximize` `reasonable` `center` `topleft` … + `window` list | Maximize / reasonable / center / quarter tiles via keywords (add your own hotkeys — triggers ship unbound) | [⬇️](https://github.com/SongRunqi/alfred-workflows/raw/main/Glide.alfredworkflow) |
| [PiHop](PiHop/) | `hop` | Hop into pi / Claude Code agent sessions by project — resume in your terminal (iTerm / kitty / ghostty…), ⌥ browse a session in a Text View, restore the last-viewed session | [⬇️](https://github.com/SongRunqi/alfred-workflows/raw/main/PiHop.alfredworkflow) |
| [System Settings](System%20Settings/) | — | Search and open macOS System Settings panes | [⬇️](https://github.com/SongRunqi/alfred-workflows/raw/main/Settings.alfredworkflow) |
| [Application Shortcuts](ApplicationShortcuts/) | `app` | Hyper-key app launcher: 36 hotkey slots, configurable terminal/browser, `app` menu | [⬇️](https://github.com/SongRunqi/alfred-workflows/raw/main/Application%20Shortcuts.alfredworkflow) |
| [Pulse](Pulse/) | `update` | Check installed workflows against the repo manifest and update them via Alfred's import flow (Hyper+U for a silent check) | [⬇️](https://github.com/SongRunqi/alfred-workflows/raw/main/Pulse.alfredworkflow) |

> ⬇️ 点击下载 `.alfredworkflow`，双击导入 Alfred。

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
