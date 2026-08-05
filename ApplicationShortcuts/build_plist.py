#!/usr/bin/env python3
"""Generate info.plist for the reworked "application shortcuts" workflow.

v2 keeps every working hotkey of the original workflow, drops the dead
nodes (unset triggers, empty Launch targets, orphan scripts), and adds:

  • two configurable slots — Hyper+2 (terminal) and Hyper+B (browser) —
    wired through Configure Workflow… popups (TERMINAL_APP / BROWSER_APP)
  • one shared launch script (launch.sh) with launch-or-toggle behaviour
  • an `app` script filter listing exactly what each hotkey does

Object configs follow the verified shapes from the alfred-workflow skill
(Glide workflow + Alfred 5.7.3 live tests).

    python3 build_plist.py     # writes info.plist next to this script
"""

import plistlib
import uuid
from pathlib import Path

HERE = Path(__file__).parent

HYPER = 1966080    # ⌃⌥⇧⌘ — Karabiner Hyper chord
EASYMOD = 655360   # ⌥⇧ — selected-text trigger

KEYCODE = {  # ANSI layout
    "1": 18, "2": 19, "b": 11, "c": 8, "d": 2, "f": 3, "m": 46, "n": 45,
    "w": 13, "z": 6, "s": 1,
}


def uid() -> str:
    return str(uuid.uuid4()).upper()


def hotkey_uid(k): return uid()
def lf_uid(k): return uid()
def scr_uid(k): return uid()

launch_uid = uid()
sf_uid = uid()

objects = []


def add_hotkey(key: str, mod: int, arg: int = 0, argumenttext: str = "") -> str:
    u = hotkey_uid(key)
    cfg = {
        "action": 0,
        "argument": arg,
        "focusedappvariable": False,
        "focusedappvariablename": "",
        "hotkey": KEYCODE[key],
        "hotmod": mod,
        "hotstring": key.upper(),
        "leftcursor": False,
        "modsmode": 0,
        "relatedAppsMode": 0,
    }
    if arg == 3:
        cfg["argumenttext"] = argumenttext
    objects.append({
        "config": cfg,
        "type": "alfred.workflow.trigger.hotkey",
        "uid": u,
        "version": 2,
    })
    return u


def add_launchfiles(app_path: str) -> str:
    u = lf_uid(app_path)
    objects.append({
        "config": {"paths": [app_path], "toggle": True},
        "type": "alfred.workflow.action.launchfiles",
        "uid": u,
        "version": 1,
    })
    return u


def add_script(script: str) -> str:
    u = scr_uid(script[:20])
    objects.append({
        "config": {
            "concurrently": False,
            "escaping": 102,
            "script": script,
            "scriptargtype": 1,  # stdin (AppleScript reads argv from stdin)
            "scriptfile": "",
            "type": 11,          # osascript
        },
        "type": "alfred.workflow.action.script",
        "uid": u,
        "version": 2,
    })
    return u


# --- hotkeys ---------------------------------------------------------------
hk = {k: add_hotkey(k, HYPER) for k in ("1", "c", "d", "f", "m", "n", "w", "z")}
hk["2"] = add_hotkey("2", HYPER, arg=3, argumenttext="terminal")
hk["b"] = add_hotkey("b", HYPER, arg=3, argumenttext="browser")
hk["s"] = add_hotkey("s", EASYMOD, arg=1)  # ⌥⇧S, selection → Easydict

# --- launch targets ----------------------------------------------------------
lf = {
    "1": add_launchfiles("/Applications/ChatGPT.app"),
    "c": add_launchfiles("/Applications/Claude.app"),
    "d": add_launchfiles("/Applications/Discord.app"),
    "f": add_launchfiles("/System/Library/CoreServices/Finder.app"),
    "m": add_launchfiles("/Applications/WeChat.app"),
    "n": add_launchfiles("/Applications/Obsidian.app"),
    "z": add_launchfiles("/Applications/Zed.app"),
}

# --- inline scripts -----------------------------------------------------------
EASYDICT = (
    'on run argv\n'
    '  set queryText to item 1 of argv\n'
    '  tell application "Easydict"\n'
    '    launch\n'
    '    open location "easydict://query?text=" & queryText\n'
    '  end tell\n'
    'end run'
)
scr = {
    "w": add_script('open -a "Obsidian" ~/data/note/workbook'),
    "s": add_script(EASYDICT),
}

# --- shared launch node (terminal / browser / app menu) ------------------------
objects.append({
    "config": {
        "concurrently": False,
        "escaping": 102,
        "script": "",
        "scriptargtype": 0,  # argv → $1
        "scriptfile": "launch.sh",
        "type": 8,           # bash
    },
    "type": "alfred.workflow.action.script",
    "uid": launch_uid,
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
        "runningsubtext": "加载快捷键清单…",
        "scriptargtype": 0,
        "scriptfile": "filter.py",
        "subtext": "每个快捷键对应什么 · 终端/浏览器可配置",
        "text": "application shortcuts",
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


connections = {
    hk["2"]: [edge(launch_uid)],
    hk["b"]: [edge(launch_uid)],
    hk["s"]: [edge(scr["s"])],
    hk["w"]: [edge(scr["w"])],
    sf_uid: [edge(launch_uid)],
}
for k, target in lf.items():
    connections[hk[k]] = [edge(target)]

# --- Canvas layout: one column per category -------------------------------------
CATS = [  # (x, [keys])
    (40, ["1", "c"]),      # AI
    (300, ["2", "b"]),     # 终端 / 浏览器
    (560, ["m", "d"]),     # 聊天
    (820, ["n", "w"]),     # 笔记
    (1080, ["z", "f"]),    # 开发 / 系统
    (1340, ["s"]),         # 查询
]
uidata = {}
for x, keys in CATS:
    for i, k in enumerate(keys):
        y = 40 + i * 110
        uidata[hk[k]] = {"xpos": x, "ypos": y}
        if k in lf:
            uidata[lf[k]] = {"xpos": x + 150, "ypos": y}
        if k in scr:
            uidata[scr[k]] = {"xpos": x + 150, "ypos": y}
uidata[launch_uid] = {"xpos": 1700, "ypos": 60}
uidata[sf_uid] = {"xpos": 40, "ypos": 420}

# --- Metadata ---------------------------------------------------------------------
README = """## application shortcuts · v2

分类整理后的应用快捷键。每个热键只做一件事：**启动或切换**（应用在前台时
再按一次则隐藏）。

### 快捷键

| 按键 | 分类 | 打开 |
| --- | --- | --- |
| Hyper+1 | AI | ChatGPT |
| Hyper+2 | 终端 | 可配置（默认 iTerm） |
| Hyper+B | 浏览器 | 可配置（默认 Google Chrome） |
| Hyper+C | AI | Claude |
| Hyper+D | 聊天 | Discord |
| Hyper+F | 系统 | Finder |
| Hyper+M | 聊天 | WeChat |
| Hyper+N | 笔记 | Obsidian |
| Hyper+W | 笔记 | Obsidian（工作笔记 vault） |
| Hyper+Z | 开发 | Zed |
| ⌥⇧S | 查询 | Easydict（选中文本查询） |

### 配置

- **终端 / 浏览器**：Workflows → application shortcuts →
  Configure Workflow… 里的下拉框切换（iTerm / kitty / Alacritty /
  WezTerm / Ghostty / Warp / Terminal；Chrome / Safari / Arc / Edge /
  Firefox / Brave / Orion）。
- 想改某个热键：双击画布上的热键触发块重新录制即可。

### 查看

输入 `app` 查看每个快捷键对应的应用（终端/浏览器显示当前配置值），
回车直接启动。所有对象都在画布上按分类排列，没有隐藏的配置。
"""

plist = {
    "bundleid": "com.srq.application",
    "name": "application shortcuts",
    "description": "分类管理的应用快捷键：Hyper+键启动，终端/浏览器可配置",
    "createdby": "songyitian",
    "webaddress": "",
    "version": "2.0.0",
    "category": "Tools",
    "disabled": False,
    "readme": README,
    "variables": {
        "TERMINAL_APP": "iTerm",
        "BROWSER_APP": "Google Chrome",
    },
    "variablesdontexport": [],
    "userconfigurationconfig": [
        {
            "type": "popupbutton",
            "variable": "TERMINAL_APP",
            "label": "终端应用 (Hyper+2)",
            "description": "Hyper+2 打开的终端",
            "config": {
                "default": "iTerm",
                "pairs": [
                    ["iTerm", "iTerm"],
                    ["kitty", "kitty"],
                    ["Alacritty", "Alacritty"],
                    ["WezTerm", "WezTerm"],
                    ["Ghostty", "Ghostty"],
                    ["Warp", "Warp"],
                    ["Terminal", "Terminal"],
                ],
            },
        },
        {
            "type": "popupbutton",
            "variable": "BROWSER_APP",
            "label": "浏览器应用 (Hyper+B)",
            "description": "Hyper+B 打开的浏览器",
            "config": {
                "default": "Google Chrome",
                "pairs": [
                    ["Google Chrome", "Google Chrome"],
                    ["Safari", "Safari"],
                    ["Arc", "Arc"],
                    ["Microsoft Edge", "Microsoft Edge"],
                    ["Firefox", "Firefox"],
                    ["Brave", "Brave"],
                    ["Orion", "Orion"],
                    ["Vivaldi", "Vivaldi"],
                ],
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
