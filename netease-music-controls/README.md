# NetEase Music Controls for Alfred

Control the macOS **NetEase Music** (网易云音乐) app directly from Alfred.
Ported from the [Raycast extension](https://github.com/yitiansong/raycast-netease-music-controls).

## Requirements

- **NetEase Music** for macOS must be installed
- **Node.js** (for the Script Filter and runner — `brew install node`)
- **Accessibility permission** for Alfred (macOS may prompt you; grant it in
  *System Settings → Privacy & Security → Accessibility* so the workflow can
  click menu-bar items)

## Installation

```bash
# 1. Clone or copy into Alfred's workflow directory
cp -r alfred-netease-music-controls \
  "$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows/"

# 2. Or symlink for development
ln -s "$(pwd)/alfred-netease-music-controls" \
  "$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows/"
```

Then open Alfred Preferences → Workflows, find **NetEase Music Controls**, and
make sure it's enabled.

## Usage

1. Open Alfred and type `nc` — the full control panel appears.
2. Start typing to filter (e.g. `nc play`, `nc volume`, `nc repeat`).
3. Press **Enter** on any item to execute that action.

### Available Controls

| Section        | Actions                                |
| -------------- | -------------------------------------- |
| **Playback**   | Play, Stop, Toggle Play/Pause, Next Track, Previous Track |
| **Volume**     | Increase Volume, Decrease Volume       |
| **Favorites**  | Like Track, Dislike Track              |
| **Repeat**     | Repeat Off, Repeat One, Repeat All     |
| **Playback Mode** | Shuffle                             |
| **Other**      | Show/Hide Lyrics, Customize Touch Bar  |

## How It Works

The workflow uses **AppleScript (System Events)** to locate NetEase Music's
menu bar and click menu items via the Accessibility API — the exact same
mechanism as the original Raycast extension. No browser automation, no private
APIs, no injection.

It auto-launches NetEase Music if the app is not already running, and supports
both English and Chinese menu item names.

## Customising the Keyword

The default keyword is `nc`. To change it:

1. Open Alfred Preferences → Workflows → NetEase Music Controls
2. Double-click the **Script Filter** block
3. Change the **Keyword** field to whatever you prefer (e.g. `netease`, `ncm`)

## Troubleshooting

| Symptom                           | Fix                                                                   |
| --------------------------------- | --------------------------------------------------------------------- |
| *"Node.js not found"*             | Install Node.js: `brew install node`                                  |
| Action does nothing / no menubar  | Grant Alfred **Accessibility** permission in System Settings          |
| NetEase Music doesn't launch      | Make sure the app is installed in `/Applications`                     |
| *"Menu not found"* error          | Your NetEase Music language may differ — open an issue with details   |

## License

MIT
