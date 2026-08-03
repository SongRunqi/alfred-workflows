#!/usr/bin/env python3
"""Generate info.plist for the Glide workflow.

Every config shape below was verified against installed workflows
(Acidham's "Window Manager" for hotkeys/keywords/Arg&Vars, Alfred Gallery
for the Script Filter).

    python3 build_plist.py     # writes info.plist next to this script
"""

import plistlib
import uuid
from pathlib import Path

HERE = Path(__file__).parent

# --- action ids --------------------------------------------------------------
ACTIONS = [
    # (id, condition label, hotkey keycode, hotstring)
    ("max", "Maximize", 46, "M"),
    ("reasonable", "Reasonable", 15, "R"),
    ("center", "Center", 8, "C"),
    ("tl", "Top Left", 26, "7"),
    ("tr", "Top Right", 28, "9"),
    ("bl", "Bottom Left", 18, "1"),
    ("br", "Bottom Right", 20, "3"),
]

# id -> (keyword trigger, result title, result subtext)
KEYWORDS = {
    "max": ("maximize", "Maximize", "Fill the screen (below menu bar)"),
    "reasonable": ("reasonable", "Reasonable", "Two-thirds size, centered"),
    "center": ("center", "Center", "Keep size, center on screen"),
    "tl": ("topleft", "Top Left", "Top-left quarter"),
    "tr": ("topright", "Top Right", "Top-right quarter"),
    "bl": ("bottomleft", "Bottom Left", "Bottom-left quarter"),
    "br": ("bottomright", "Bottom Right", "Bottom-right quarter"),
}

LIST_KEYWORD = "window"  # "win" is claimed by the installed "Search ALL the docs!"

HOTMOD = 1835008  # ⌃⌥⌘ = 262144 + 524288 + 1048576 (NSEvent bitmask)


def uid() -> str:
    return str(uuid.uuid4()).upper()


sf_uid = uid()
keyword_uids = {a: uid() for a, *_rest in ACTIONS}
argvars_uids = {a: uid() for a, *_rest in ACTIONS}
hotkey_uids = {a: uid() for a, *_rest in ACTIONS}
script_uid = uid()
notify_uid = uid()

objects = []

# --- Script Filter: the action list -----------------------------------------
objects.append(
    {
        "config": {
            "alfredfiltersresults": True,
            "alfredfiltersresultsmatchmode": 2,
            "argumenttreatemptyqueryasnil": True,
            "argumenttrimmode": 0,
            "argumenttype": 1,
            "escaping": 102,
            "keyword": LIST_KEYWORD,
            "queuedelaycustom": 3,
            "queuedelayimmediatelyinitially": True,
            "queuedelaymode": 0,
            "queuemode": 1,
            "runningsubtext": "Resizing window…",
            "scriptargtype": 0,
            "scriptfile": "actions.py",
            "subtext": "Maximize · Reasonable · Center · Quarters",
            "text": "Glide",
            "type": 8,
            "withspace": False,
        },
        "type": "alfred.workflow.input.scriptfilter",
        "uid": sf_uid,
        "version": 3,
    }
)

# --- Keywords: one per action, fire immediately on the bare word ------------
for action_id, *_rest in ACTIONS:
    trigger, title, subtext = KEYWORDS[action_id]
    objects.append(
        {
            "config": {
                "argumenttype": 2,  # no argument — runs on the bare keyword
                "keyword": trigger,
                "subtext": subtext,
                "text": title,
                "withspace": False,
            },
            "type": "alfred.workflow.input.keyword",
            "uid": keyword_uids[action_id],
            "version": 1,
        }
    )

# --- Arg & Vars: keywords carry no argument, so inject the action id ---------
for action_id, *_rest in ACTIONS:
    objects.append(
        {
            "config": {
                "argument": action_id,
                "passthroughargument": False,
                "variables": {},
            },
            "type": "alfred.workflow.utility.argument",
            "uid": argvars_uids[action_id],
            "version": 1,
        }
    )

# --- Hotkeys (pre-assigned ⌃⌥⌘ scheme; rebindable in Alfred) ----------------
for action_id, _label, keycode, hotstring in ACTIONS:
    objects.append(
        {
            "config": {
                "action": 0,
                "argument": 3,  # text argument
                "argumenttext": action_id,
                "focusedappvariable": False,
                "focusedappvariablename": "",
                "hotkey": keycode,
                "hotmod": HOTMOD,
                "hotstring": hotstring,
                "leftcursor": False,
                "modsmode": 0,
                "relatedAppsMode": 0,
            },
            "type": "alfred.workflow.trigger.hotkey",
            "uid": hotkey_uids[action_id],
            "version": 2,
        }
    )

# --- Run Script: forward the action id to the geometry engine ---------------
objects.append(
    {
        "config": {
            "concurrently": False,
            "escaping": 102,
            "script": "",
            "scriptargtype": 0,
            "scriptfile": "run.sh",
            "type": 8,
        },
        "type": "alfred.workflow.action.script",
        "uid": script_uid,
        "version": 2,
    }
)

# --- Notification: shows only when the engine printed an error ---------------
objects.append(
    {
        "config": {
            "lastpathcomponent": False,
            "onlyshowifquerypopulated": True,
            "removeextension": False,
            "text": "{query}",
            "title": "Glide",
        },
        "type": "alfred.workflow.output.notification",
        "uid": notify_uid,
        "version": 1,
    }
)


# --- Connections -------------------------------------------------------------
def edge(dest):
    return {
        "destinationuid": dest,
        "modifiers": 0,
        "modifiersubtext": "",
        "vitoclose": False,
    }


connections = {sf_uid: [edge(script_uid)]}
for action_id, *_rest in ACTIONS:
    connections[keyword_uids[action_id]] = [edge(argvars_uids[action_id])]
    connections[argvars_uids[action_id]] = [edge(script_uid)]
    connections[hotkey_uids[action_id]] = [edge(script_uid)]
connections[script_uid] = [edge(notify_uid)]

# --- Canvas layout -----------------------------------------------------------
uidata = {sf_uid: {"xpos": 40.0, "ypos": 40.0}}
for i, (action_id, *_rest) in enumerate(ACTIONS):
    uidata[keyword_uids[action_id]] = {"xpos": 40.0, "ypos": 200.0 + i * 88.0}
    uidata[argvars_uids[action_id]] = {"xpos": 330.0, "ypos": 200.0 + i * 88.0}
    uidata[hotkey_uids[action_id]] = {"xpos": 620.0, "ypos": 40.0 + i * 88.0}
uidata[script_uid] = {"xpos": 910.0, "ypos": 320.0}
uidata[notify_uid] = {"xpos": 1200.0, "ypos": 320.0}

# --- Metadata -----------------------------------------------------------------
README = """## Glide

Maximize, "reasonable" size (two-thirds, centered), center, and quarter tiles
for the frontmost window — straight from a keyword, or from the action list /
hotkeys. Resizing is done by a small bundled engine (Accessibility API), so
every action lands exactly where the screen allows.

### Requirements

- **Alfred 5** (any recent version)
- Alfred needs **Accessibility** permission:
  System Settings → Privacy & Security → Accessibility → enable Alfred

### Usage — keywords

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
hotkeys (⌃⌥⌘M / R / C / 7 / 9 / 1 / 3 — rebindable: Workflows → Glide
→ double-click a hotkey trigger → record keys).

### Behaviour notes

- Moves animate smoothly (~150 ms ease-out) unless you turn the Animation
  checkbox off in Configure Workflow…, or the system Reduce Motion setting is
  on.
- Quarters are flush against the usable screen edges: below the menu bar on
  top, and — because your Dock is auto-hidden — all the way to the physical
  bottom edge. If you turn Dock auto-hide off, the bottom rows stop above the
  Dock instead.
- Some apps clamp or animate resizes (browsers, IDEs); the engine retries
  gently and lands as close as the app allows.
- Apps that block programmatic resizing entirely simply don't move.

### Notes

- **Disable Acidham's "Window Manager"** if it is installed: it claims the
  `center` / `reasonable` keywords too, and Alfred would show both.
"""

plist = {
    "bundleid": "com.songyitian.glide",
    "name": "Glide",
    "description": "Glide windows: maximize, size, center and quarter tiles",
    "createdby": "Songyitian",
    "webaddress": "",
    "version": "1.7.0",
    "category": "Tools",
    "disabled": False,
    "readme": README,
    "variables": {},
    "variablesdontexport": [],
    "userconfigurationconfig": [
        {
            "type": "checkbox",
            "variable": "animate",
            "label": "Animation",
            "description": "Smoothly animate window moves",
            "config": {
                "default": True,
                "required": False,
                "text": "Animate window moves (uncheck for instant snapping)",
            },
        },
    ],
    "objects": objects,
    "connections": connections,
    "uidata": uidata,
}

out = HERE / "info.plist"
out.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_XML))
print(f"wrote {out}")
