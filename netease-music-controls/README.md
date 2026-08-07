# NetEase Music Controls for Alfred

Control the macOS **NetEase Music** (网易云音乐) app directly from Alfred —
no Node.js required. Actions click the app's menu bar via AppleScript
(System Events), the same mechanism as the original
[Raycast extension](https://github.com/yitiansong/raycast-netease-music-controls).

## Requirements

- **NetEase Music** for macOS installed
- **Accessibility permission** for Alfred
  (*System Settings → Privacy & Security → Accessibility*) so the workflow can
  click menu-bar items

## Usage

Type one of the direct keywords in Alfred:

| Keyword  | Action          | Keyword  | Action            |
| -------- | --------------- | -------- | ----------------- |
| `play`   | Play (resume)   | `volup`  | Volume up         |
| `pause`  | Pause           | `voldn`  | Volume down       |
| `next`   | Next track      | `like`   | Like / toggle     |
| `prev`   | Previous track  | `dislike`| Dislike / unmark  |
| `shuffle`| Toggle shuffle  |          |                   |
| `repeat1`| Repeat one      |          |                   |

Notes:

- `play` and `pause` are strict, not a toggle: `play` only resumes
  (silently no-ops while already playing) and `pause` only pauses
  (silently no-ops while already paused) — each can be bound to its own
  hotkey without fighting over one toggle.
- `like` doubles as a toggle: if the current track is already liked, the menu
  shows the unlike entry and it gets clicked instead.
- `dislike` prefers dislike/unlike entries (`不喜欢`, `取消喜欢`, `取消红心`, …)
  and only falls back to like entries so it never silently no-ops.
- If an action cannot find the menu item, a notification shows the error
  instead of failing silently.
- The app is launched automatically (without stealing focus) if it isn't
  running. Menu names are matched against English and Chinese variants.

## How It Works

`scripts/runner.sh` uses AppleScript (System Events) to locate the NetEase
Music menu bar and click the right menu item. No browser automation, no
private APIs, no injection.

## Customising

The keywords are plain Keyword triggers in Alfred — double-click any one in
the workflow editor to change it, or add more keywords and wire them to the
corresponding Run Script action (e.g. `repeat-off`, `repeat-all`,
`toggle-lyrics` are already supported by `runner.sh`).

## Troubleshooting

| Symptom | Fix |
| ---------------------------- | ---------------------------------------------------------------- |
| Action does nothing, no notification | Grant Alfred **Accessibility** permission in System Settings |
| "menu item not found" notification | Your NetEase Music language differs — open an issue with the exact menu names |
| NetEase Music doesn't launch | Make sure the app is installed in `/Applications` |

## License

MIT
