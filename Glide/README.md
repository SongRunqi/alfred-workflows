# Glide

Maximize, "reasonable" size (two-thirds width & height, centered), center, and
quarter tiles for the frontmost window — straight from a keyword, or from the
action list / hotkeys.

Resizing is done by a small bundled Swift engine (`window_control`) using the
Accessibility API: geometry is computed from the window's own screen and lands
exactly where the OS allows (see Behaviour notes). Moves are **animated**:
pure moves glide (~150 ms ease-out), while actions that change size land in a
single motion — Rectangle-style size→position→size, merged by the app into
one visual step. Uncheck the Animation option in Configure Workflow… for
instant snapping, or let the system Reduce Motion setting disable it.

## Requirements

- Alfred 5 (any recent version)
- Alfred needs **Accessibility** permission:
  System Settings → Privacy & Security → Accessibility → enable Alfred
  (this is what lets Alfred resize other apps' windows)

## Usage — keywords

Type any keyword below and press ↩ — the frontmost window moves immediately:

| Keyword | Action |
| --- | --- |
| `maximize` | fill the screen (below the menu bar) |
| `reasonable` | two-thirds width & height, centered |
| `center` | keep size, center on screen |
| `topleft` | top-left quarter |
| `topright` | top-right quarter |
| `bottomleft` | bottom-left quarter |
| `bottomright` | bottom-right quarter |

Also available: type **`window`** for a pickable action list, or use the
hotkeys (all rebindable):

| Action | Hotkey |
| --- | --- |
| Maximize | ⌃⌥⌘M |
| Reasonable | ⌃⌥⌘R |
| Center | ⌃⌥⌘C |
| Top-left quarter | ⌃⌥⌘7 |
| Top-right quarter | ⌃⌥⌘9 |
| Bottom-left quarter | ⌃⌥⌘1 |
| Bottom-right quarter | ⌃⌥⌘3 |

Rebind: Workflows → Glide → double-click a hotkey trigger → record
the keys.

## Behaviour notes

- Moves animate smoothly: pure moves glide (~150 ms ease-out); size-changing
  actions (maximize, reasonable, quarters) fire Rectangle-style
  size→position→size back-to-back so the app renders one motion. Turn the
  Animation checkbox off in Configure Workflow… for instant snapping, or
  rely on the system Reduce Motion setting.
- Placement is Rectangle-style: **size → position → size**, back-to-back —
  apps merge the rapid requests into one visual step, so a window moves to
  its corner and resizes in a single motion (no "move, then resize"). The
  window server is then polled as a safety net so rapid consecutive actions
  never pile onto a busy app.
- Quarters are flush against the usable screen edges: below the menu bar on
  top, and — because your Dock is auto-hidden — all the way to the physical
  bottom edge. If you turn Dock auto-hide off, the bottom rows stop above the
  Dock instead.
- macOS clamps window tops to below the menu bar; the engine reads the menu
  bar height directly from the window list — no probing moves.
- Apps that block programmatic resizing entirely simply don't move.

## Notes

- **Disable Acidham's "Window Manager"** if it is installed: it claims the
  `center` / `reasonable` keywords too, and Alfred would show both workflows.

## Development

- `info.plist` is generated — edit `build_plist.py`, then
  `python3 build_plist.py` and `plutil -lint info.plist`.
- Engine: `swiftc -O -framework AppKit -framework ApplicationServices window_control.swift -o window_control`
- Icon: `icon.png` is the workflow icon (AI-generated, replace freely).
- Icons: `swiftc -O make_icons.swift -o /tmp/mkicons && /tmp/mkicons icons`.
- Package (excludes the dev files, keeps exec bits):
  `zip -r ../"Glide.alfredworkflow" . -x "build_plist.py" "make_icons.swift" ".DS_Store" "*.pyc" ".ruff_cache/*"`
