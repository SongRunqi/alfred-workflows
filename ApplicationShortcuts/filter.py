#!/usr/bin/env python3
"""Curated `app` menu for the application shortcuts workflow.

Shows exactly what every hotkey does — no app browsing, no registry, no
black box. The terminal / browser rows reflect the configured values from
Configure Workflow… (workflow variables TERMINAL_APP / BROWSER_APP arrive
as environment variables). Alfred does the filtering (alfredfiltersresults),
so every item carries a `match` combining hotkey + name + category.
"""

import json
import os
from pathlib import Path

term = os.environ.get("TERMINAL_APP", "") or "iTerm"
brow = os.environ.get("BROWSER_APP", "") or "Google Chrome"

APP_DIRS = ("/Applications", "/System/Applications", "/Applications/Utilities")


def icon(name: str) -> str:
    for base in APP_DIRS:
        p = Path(base) / f"{name}.app"
        if p.is_dir():
            return str(p)
    return "icon.png"


# (hotkey, category, title, subtitle, arg, icon-name)
ROWS = [
    ("Hyper+1", "AI",   "ChatGPT",      "启动或切换",            "ChatGPT", "ChatGPT"),
    ("Hyper+2", "终端", term,           "可配置 · Configure Workflow…", "terminal", term),
    ("Hyper+B", "浏览器", brow,          "可配置 · Configure Workflow…", "browser", brow),
    ("Hyper+C", "AI",   "Claude",       "启动或切换",            "Claude", "Claude"),
    ("Hyper+D", "聊天", "Discord",      "启动或切换",            "Discord", "Discord"),
    ("Hyper+F", "系统", "Finder",       "启动或切换",            "Finder", "Finder"),
    ("Hyper+M", "聊天", "WeChat",       "启动或切换",            "WeChat", "WeChat"),
    ("Hyper+N", "笔记", "Obsidian",     "启动或切换",            "Obsidian", "Obsidian"),
    ("Hyper+W", "笔记", "Obsidian · 工作笔记", "~/data/note/workbook", "Obsidian|~/data/note/workbook", "Obsidian"),
    ("Hyper+Z", "开发", "Zed",          "启动或切换",            "Zed", "Zed"),
    ("⌥⇧S",    "查询", "Easydict",     "选中文本查询",          "Easydict", "Easydict"),
]

items = [
    {
        "uid": f"row-{i}",
        "title": f"{hk} · {name}",
        "subtitle": f"{cat} · {sub}",
        "arg": arg,
        "match": f"{hk} {name} {cat} {sub}",
        "icon": {"path": icon(icon_name)},
    }
    for i, (hk, cat, name, sub, arg, icon_name) in enumerate(ROWS)
]

items.append({
    "uid": "config-hint",
    "title": "切换终端 / 浏览器",
    "subtitle": "Workflows → application shortcuts → Configure Workflow… · 双击任意热键可重新录制",
    "arg": "",
    "match": "config 配置 终端 浏览器",
    "valid": False,
    "icon": {"path": "icon.png"},
})

print(json.dumps({"items": items}, ensure_ascii=False))
