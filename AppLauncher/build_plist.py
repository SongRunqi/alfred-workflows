#!/usr/bin/env python3
"""Generate info.plist for the App Launcher workflow.

The workflow ships with 36 static hotkey triggers — Hyper+0-9 / Hyper+A-Z
(hotmod 1966080 = ⌃⌥⇧⌘, the user's Karabiner Hyper chord) plus the
selected-text trigger ⌥⇧S (hotmod 655360) for Easydict. Every trigger passes
its own key via argumenttext, so all of them fire the SAME launch script;
the key→app mapping lives in a JSON registry that can be edited at runtime
without touching this plist.

    python3 build_plist.py     # writes info.plist next to this script
"""

import plistlib
import uuid
from pathlib import Path

HERE = Path(__file__).parent

HYPER = 1966080      # ⌃⌥⇧⌘ — the user's Karabiner Hyper chord
EASYMOD = 655360     # ⌥⇧ — selected-text trigger

# keycode for each grid key (ANSI layout)
KEYCODE = {
    "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26, "8": 28,
    "9": 25, "0": 29,
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4,
    "i": 34, "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31, "p": 35,
    "q": 12, "r": 15, "s": 1, "t": 17, "u": 32, "v": 9, "w": 13, "x": 7,
    "y": 16, "z": 6,
}
GRID = "1234567890abcdefghijklmnopqrstuvwxyz"


def uid() -> str:
    return str(uuid.uuid4()).upper()


launch_uid = uid()    # shared launch node (all grid hotkeys + management)
launchq_uid = uid()   # selected-text query node (⌥⇧S)
sf_uid = uid()        # `app` script filter
hotkey_uids = {k: uid() for k in GRID}
easy_uid = uid()

objects = []

# --- 36 grid hotkeys: Hyper + key, passing the key as argumenttext ----------
for k in GRID:
    objects.append({
        "config": {
            "action": 0,
            "argument": 3,  # text argument = the grid key
            "argumenttext": k,
            "focusedappvariable": False,
            "focusedappvariablename": "",
            "hotkey": KEYCODE[k],
            "hotmod": HYPER,
            "hotstring": k.upper(),
            "leftcursor": False,
            "modsmode": 0,
            "relatedAppsMode": 0,
        },
        "type": "alfred.workflow.trigger.hotkey",
        "uid": hotkey_uids[k],
        "version": 2,
    })

# --- selected-text trigger: ⌥⇧S → Easydict query ----------------------------
objects.append({
    "config": {
        "action": 0,
        "argument": 1,  # selection in macOS → passed as the query
        "focusedappvariable": False,
        "focusedappvariablename": "",
        "hotkey": 1,
        "hotmod": EASYMOD,
        "hotstring": "S",
        "leftcursor": False,
        "modsmode": 0,
        "relatedAppsMode": 0,
    },
    "type": "alfred.workflow.trigger.hotkey",
    "uid": easy_uid,
    "version": 2,
})

# --- shared launch node -------------------------------------------------------
objects.append({
    "config": {
        "concurrently": False,
        "escaping": 102,
        "script": "",
        "scriptargtype": 0,
        "scriptfile": "launch.sh",
        "type": 8,
    },
    "type": "alfred.workflow.action.script",
    "uid": launch_uid,
    "version": 2,
})

# --- selected-text query node --------------------------------------------------
objects.append({
    "config": {
        "concurrently": False,
        "escaping": 102,
        "script": "",
        "scriptargtype": 0,
        "scriptfile": "launchq.sh",
        "type": 8,
    },
    "type": "alfred.workflow.action.script",
    "uid": launchq_uid,
    "version": 2,
})

# --- `app` script filter --------------------------------------------------------
objects.append({
    "config": {
        "alfredfiltersresults": True,
        "alfredfiltersresultsmatchmode": 2,
        "argumenttreatemptyqueryasnil": True,
        "argumenttrimmode": 0,
        "argumenttype": 1,
        "escaping": 102,
        "keyword": "app",
        "queuedelaycustom": 3,
        "queuedelayimmediatelyinitially": True,
        "queuedelaymode": 0,
        "queuemode": 1,
        "runningsubtext": "读取注册表…",
        "scriptargtype": 0,
        "scriptfile": "filter.sh",
        "subtext": "app add <键> <应用> · app rm <键|名称> · app <应用>",
        "text": "App Launcher",
        "type": 8,
        "withspace": False,
    },
    "type": "alfred.workflow.input.scriptfilter",
    "uid": sf_uid,
    "version": 3,
})

# --- Connections ---------------------------------------------------------------
def edge(dest):
    return {
        "destinationuid": dest,
        "modifiers": 0,
        "modifiersubtext": "",
        "vitoclose": False,
    }


connections = {uid_: [edge(launch_uid)] for uid_ in hotkey_uids.values()}
connections[easy_uid] = [edge(launchq_uid)]
connections[sf_uid] = [edge(launch_uid)]

# --- Canvas layout ---------------------------------------------------------------
uidata = {}
for i, k in enumerate(GRID):
    uidata[hotkey_uids[k]] = {"xpos": 40.0, "ypos": 40.0 + i * 64.0}
easy_y = 40.0 + len(GRID) * 64.0 + 40.0
uidata[easy_uid] = {"xpos": 40.0, "ypos": easy_y}
uidata[launch_uid] = {"xpos": 360.0, "ypos": 40.0 + len(GRID) * 32.0}
uidata[launchq_uid] = {"xpos": 360.0, "ypos": easy_y}
uidata[sf_uid] = {"xpos": 40.0, "ypos": easy_y + 140.0}

# --- Metadata -----------------------------------------------------------------
README = """## App Launcher

Hyper-key app launcher: 36 static hotkey triggers (**Hyper+0-9 / Hyper+A-Z**)
all fire one shared launch script, which resolves the pressed key against a
JSON registry you edit at runtime — adding an app takes one command, no
workflow editing, no Alfred restart.

### Install & first run

1. Import `App Launcher.alfredworkflow`.
2. **Stop the old "application shortcuts" workflow first** (Preferences →
   Workflows → disable it): it claims the same Hyper hotkeys and wins the
   conflict, which makes the new hotkeys appear dead. The first run warns
   you if it is still enabled.
3. Press any Hyper+key (or run `app` in Alfred). On first use the registry
   is imported automatically from the old workflow if it is still installed
   (Hyper+1/2/3, Hyper+B/C/D/F/M/N/W/Z → your apps, plus ⌥⇧S → Easydict).

### Usage

| You type | What happens |
| --- | --- |
| `app add 4 Slack` | bind Hyper+4 to Slack (path auto-resolved) |
| `app add w Obsidian ~/data/note/workbook` | bind with launch args |
| `app rm 4` / `app rm Slack` | unbind |
| `app slack` | fuzzy search + launch anything, registered or not |
| `app 4 slack` | bind Slack to Hyper+4 in one step |
| press Hyper+<unbound> | hint notification with the exact add command |
| ⌥⇧S | Easydict query with the selected text |

The `app` script filter shows the full registry with live app icons; Alfred's
built-in fuzzy filtering narrows it as you type.

### Behaviour

- **Toggle**: entries default to launch-or-toggle — pressing the hotkey while
  the app is frontmost hides it (same as the old workflow). Frontmost
  detection uses `lsappinfo` (no permission); hiding uses System Events —
  grant the one-time Automation prompt, or turn Toggle off in
  Configure Workflow… to get plain launch-or-focus.
- **Query mode**: the ⌥⇧S trigger and any entry with `"mode": "query"` passes
  the selected text through its URL scheme.

### Registry

`apps.json` lives in Alfred's Workflow Data folder for this bundle id.
Schema: `{"1": {"name": "ChatGPT", "path": "/Applications/ChatGPT.app",
"toggle": true}, "s": {"name": "Easydict", "mode": "query",
"scheme": "easydict://query?text={query}"}}`

### Conflicts

**Hyper+R and Hyper+S are claimed by the "Writing Assistant" workflow** —
they are intentionally left unbound in the grid (add will warn). If you
rebind Writing Assistant, the keys become available here automatically.

### Rebuilding

The plist is generated: `python3 build_plist.py` regenerates `info.plist`
(change the grid, hotmod, keyword…), `./pack.sh` repackages
`App Launcher.alfredworkflow`. Runtime scripts: `app.py` (engine),
`launch.sh` / `launchq.sh` / `filter.sh` (entry points).
"""

plist = {
    "bundleid": "com.yitiansong.applauncher",
    "name": "App Launcher",
    "description": "Hyper-key app launcher: 36 hotkeys, dynamic JSON registry",
    "createdby": "Yitiansong",
    "webaddress": "",
    "version": "1.1.0",
    "category": "Tools",
    "disabled": False,
    "readme": README,
    "variables": {},
    "variablesdontexport": [],
    "userconfigurationconfig": [
        {
            "type": "checkbox",
            "variable": "toggle_default",
            "label": "Toggle",
            "description": "Launch-or-toggle: pressing the hotkey again hides the app",
            "config": {
                "default": True,
                "required": False,
                "text": "Toggle frontmost app (hide when already in front)",
            },
        },
        {
            "type": "checkbox",
            "variable": "notify_unassigned",
            "label": "Unassigned hint",
            "description": "Notify when an unregistered hotkey is pressed",
            "config": {
                "default": True,
                "required": False,
                "text": "Hint when an unbound hotkey is pressed",
            },
        },
    ],
    "objects": objects,
    "connections": connections,
    "uidata": uidata,
}

out = HERE / "info.plist"
out.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_XML))
print(f"wrote {out} ({len(objects)} objects)")
