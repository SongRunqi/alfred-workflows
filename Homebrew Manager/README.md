# Homebrew Manager

Search, install, upgrade and manage Homebrew packages from Alfred.

## Usage

Type `brew` in Alfred:

- **<empty>** — quick actions: update, upgrade all, cleanup, doctor
- **brew <query>** — search installed and available packages

## Actions

| Key | Action |
| ----- | -------- |
| ⏎ | Show package info (installed) / Install (available) |
| ⌘⏎ | Uninstall package |
| ⌥⏎ | Upgrade package |

## Requirements

- [Homebrew](https://brew.sh) installed
- macOS with Alfred 5+

## Notes

- Package lists are cached for performance. First run takes ~2s; subsequent searches are instant.
- Installed packages refresh cache every hour; available package lists refresh weekly.
