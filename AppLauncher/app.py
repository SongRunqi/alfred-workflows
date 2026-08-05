#!/usr/bin/env python3
"""App Launcher — hyper-key app launcher with a dynamic JSON registry.

Architecture
------------
36 static Alfred hotkey triggers (Hyper+0-9 / Hyper+A-Z) all fire the SAME
launch script; the pressed key arrives as the trigger's argumenttext. The
script resolves the key against apps.json (Alfred Workflow Data), so adding
an app is a plain registry write — no plist surgery, no Alfred restart.

Commands (argv):
    <key>                  hotkey path: launch the app bound to KEY
    launch <key> [query]   same, with optional query text (argv 3)
    run <name...>          launch an unregistered app by name
    add <key> <name> [args...]   register app (key must be a grid key)
    remove <key|name>      unregister
    list                   print the registry
    query [text]           script-filter JSON for the `app` keyword
    migrate [--force]      import the old "application shortcuts" workflow
    help                   usage (as a notification)
"""

import json
import os
import plistlib
import re
import subprocess
import sys
import time
import urllib.parse
from contextlib import suppress
from pathlib import Path
from typing import Any

BUNDLE_ID = "com.yitiansong.applauncher"
OLD_WF_NAME = "application shortcuts"

# Grid of assignable keys: digits then letters (matches the 36 static triggers)
GRID = "1234567890abcdefghijklmnopqrstuvwxyz"

# macOS keycodes for the grid keys (ANSI layout)
KEYCODE = {
    "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26, "8": 28,
    "9": 25, "0": 29,
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4,
    "i": 34, "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31, "p": 35,
    "q": 12, "r": 15, "s": 1, "t": 17, "u": 32, "v": 9, "w": 13, "x": 7,
    "y": 16, "z": 6,
}
KEY_TO_CHAR = {v: k for k, v in KEYCODE.items()}

APP_DIRS = [
    Path("/Applications"),
    Path("/System/Applications"),
    Path("/Applications/Utilities"),
    Path("/System/Applications/Utilities"),
]

TITLE = "App Launcher"


# ---------------------------------------------------------------- helpers ---

def data_dir() -> Path:
    """Workflow data dir: Alfred's, an override, or the standard fallback."""
    for env in ("APP_LAUNCHER_DATA", "alfred_workflow_data"):
        v = os.environ.get(env)
        if v:
            return Path(v)
    return Path.home() / "Library/Application Support/Alfred/Workflow Data" / BUNDLE_ID


def registry_path() -> Path:
    return data_dir() / "apps.json"


def _bool_env(name: str, default: bool = True) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() not in ("0", "false", "no", "off")


def notify_unassigned_enabled() -> bool:
    return _bool_env("notify_unassigned", True)


def toggle_default() -> bool:
    return _bool_env("toggle_default", True)


def load_registry() -> dict:
    p = registry_path()
    if not p.exists():
        return {"version": 1, "apps": {}}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "apps": {}}


def save_registry(reg: dict) -> None:
    p = registry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=2))
    os.replace(tmp, p)


def apps() -> dict:
    return load_registry().get("apps", {})


def notify(msg: str, title: str = TITLE) -> None:
    """User notification via osascript (no TCC permission needed)."""
    esc = msg.replace("\\", "\\\\").replace('"', '\\"')
    esc_t = title.replace("\\", "\\\\").replace('"', '\\"')
    with suppress(Exception):
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{esc}" with title "{esc_t}"'],
            capture_output=True, timeout=5)


def _notify_or_print(msg: str) -> None:
    """Notify the user; print instead under APP_LAUNCHER_DRY (tests)."""
    if os.environ.get("APP_LAUNCHER_DRY"):
        print(f"[notify] {msg}")
    else:
        notify(msg)


_OLD_STATUS_CACHE: dict = {"t": 0.0, "v": None}


def old_workflow_status() -> str:
    """Is the old "application shortcuts" workflow still enabled?

    Returns "enabled" / "disabled" / "missing" (read-only scan, 30s cache).
    """
    now = time.time()
    if now - _OLD_STATUS_CACHE["t"] < 30 and _OLD_STATUS_CACHE["v"]:
        return _OLD_STATUS_CACHE["v"]
    old = find_old_plist()
    status = "missing"
    if old is not None:
        try:
            with old.open("rb") as f:
                disabled = plistlib.load(f).get("disabled", False)
            status = "disabled" if disabled else "enabled"
        except Exception:
            status = "missing"
    _OLD_STATUS_CACHE.update(t=now, v=status)
    return status


def sh(args: list, timeout: float = 5) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def resolve_app(name: str) -> str | None:
    """Resolve an app name to an absolute .app path."""
    name = name.strip()
    if not name:
        return None
    if "/" in name:
        p = Path(name).expanduser()
        return str(p) if p.is_dir() else None
    if not name.lower().endswith(".app"):
        name += ".app"
    # exact / prefix match in the standard dirs
    hits = []
    for d in APP_DIRS:
        for child in sorted(d.iterdir()) if d.is_dir() else []:
            if child.name.lower() == name.lower():
                return str(child)
            if child.name.lower().startswith(name.lower()):
                hits.append(str(child))
    if hits:
        return hits[0]
    # Spotlight fallback
    out = sh(["mdfind", "-name", name[:-4]])
    for line in out.splitlines():
        if line.lower().endswith(".app"):
            return line
    return None


def app_bundle_id(app_path: str) -> str | None:
    """Bundle id of an app via mdls (fast, no permissions)."""
    out = sh(["mdls", "-name", "kMDItemCFBundleIdentifier", "-raw", app_path])
    if not out:
        return None
    return out.strip().strip('"') or None


def frontmost_bundle_id() -> str | None:
    """Bundle id of the frontmost app via lsappinfo (no permissions)."""
    asn = sh(["lsappinfo", "front"])
    if not asn:
        return None
    out = sh(["lsappinfo", "info", "-only", "bundleid", asn])
    m = re.search(r'"CFBundleIdentifier"="([^"]+)"', out)
    return m.group(1) if m else None


def hide_app(bundle_id: str, app_name: str) -> bool:
    """Hide the app. System Events first, direct hide as fallback."""
    e1 = (f'tell application "System Events" to set visible of '
          f'(first process whose bundle identifier is "{bundle_id}") to false')
    if sh(["osascript", "-e", e1], timeout=3):
        return True
    e2 = f'tell application id "{bundle_id}" to hide'
    return bool(sh(["osascript", "-e", e2], timeout=3))


def launch_app(entry: dict, query: str = "") -> None:
    """Launch (or toggle) one registry entry."""
    if entry.get("mode") == "query":
        scheme = entry.get("scheme", "")
        url = scheme.replace("{query}", urllib.parse.quote(query, safe=""))
        subprocess.Popen(["open", url])
        return

    name = entry.get("name", "")
    path = entry.get("path", "")
    if not path or "/" not in path:
        resolved = resolve_app(name)
        path = resolved or path or name

    if entry.get("toggle", toggle_default()):
        front = frontmost_bundle_id()
        bid = app_bundle_id(path) if "/" in path else None
        if front and bid and front == bid and hide_app(bid, name):
            return  # hidden; nothing else to do

    args = [str(Path(a).expanduser()) for a in entry.get("args", [])]
    cmd = ["open", "-a", path] + args
    subprocess.Popen(cmd)


# ---------------------------------------------------------------- commands --

def cmd_launch(key: str, query: str = "") -> None:
    ensure_registry()
    reg_apps = apps()
    entry = reg_apps.get(key)
    if not entry:
        if notify_unassigned_enabled():
            _notify_or_print(f"Hyper+{key.upper()} 未绑定应用\n在 Alfred 输入: app add {key} <应用名>")
        return
    if os.environ.get("APP_LAUNCHER_DRY"):
        print(f"[dry] launch key={key} entry={json.dumps(entry, ensure_ascii=False)} query={query!r}")
        return
    launch_app(entry, query)


def cmd_run(names: list) -> None:
    name = " ".join(names)
    if not name:
        _notify_or_print("用法: app run <应用名>")
        return
    path = resolve_app(name)
    if not path:
        _notify_or_print(f"找不到应用: {name}")
        return
    if os.environ.get("APP_LAUNCHER_DRY"):
        print(f"[dry] run {name} -> {path}")
        return
    subprocess.Popen(["open", "-a", path])


def cmd_add(args: list) -> None:
    if len(args) < 2:
        _notify_or_print("用法: app add <键> <应用名> [参数…]\n例: app add o Obsidian ~/data/note/notebook")
        return
    key = args[0].lower()

    # multi-word app names win when the whole string resolves ("Google Chrome");
    # otherwise the first token is the name and the rest are launch args
    name_join = " ".join(args[1:])
    if resolve_app(name_join):
        name, rest = name_join, []
    else:
        name, rest = args[1], args[2:]

    if key not in GRID:
        _notify_or_print(f"无效按键: {key}\n可用按键: {GRID}")
        return
    reg = load_registry()
    reg_apps = reg.setdefault("apps", {})
    if key in reg_apps:
        _notify_or_print(f"Hyper+{key.upper()} 已被 {reg_apps[key].get('name')} 占用\n先 app rm {key}")
        return
    path = resolve_app(name)
    if not path:
        _notify_or_print(f"找不到应用: {name}")
        return

    entry: dict[str, Any] = {"name": Path(path).stem, "path": path}
    if rest:
        entry["args"] = list(rest)
    entry["toggle"] = toggle_default()
    reg_apps[key] = entry
    save_registry(reg)
    _notify_or_print(f"✓ Hyper+{key.upper()} → {Path(path).stem}")


def cmd_remove(target: str) -> None:
    target = target.lower()
    reg = load_registry()
    reg_apps = reg.get("apps", {})
    key = target if target in reg_apps else next(
        (k for k, e in reg_apps.items() if e.get("name", "").lower() == target), None)
    if not key:
        _notify_or_print(f"未注册: {target}")
        return
    name = reg_apps[key].get("name", key)
    del reg_apps[key]
    save_registry(reg)
    _notify_or_print(f"✕ 已移除 Hyper+{key.upper()} → {name}")


def cmd_list() -> None:
    reg_apps = apps()
    if not reg_apps:
        print("（空 — 用 `app add <键> <应用>` 添加）")
        return
    for key in GRID:
        if key in reg_apps:
            e = reg_apps[key]
            extra = f" args={e.get('args')}" if e.get("args") else ""
            print(f"Hyper+{key.upper()}  {e.get('name')}  {e.get('path', '')}{extra}")


# ------------------------------------------------------------------ migrate --

def old_workflow_dirs() -> list:
    env = os.environ.get("APP_LAUNCHER_SCAN_DIRS")
    if env:
        return [Path(p) for p in env.split(",") if p]
    return [
        Path.home() / "data/sync/alfred/Alfred.alfredpreferences/workflows",
        Path.home() / "Library/Application Support/Alfred/Alfred.alfredpreferences/workflows",
    ]


def find_old_plist() -> Path | None:
    for base in old_workflow_dirs():
        if not base.is_dir():
            continue
        for plist in sorted(base.glob("*/info.plist")):
            try:
                with plist.open("rb") as f:
                    data = plistlib.load(f)
            except Exception:
                continue
            if data.get("name") == OLD_WF_NAME:
                return plist
    return None


def migrate(force: bool = False) -> list:
    """Import the old workflow's hotkey→app mapping. Returns migrated entries."""
    p = registry_path()
    if p.exists() and not force:
        return []

    old = find_old_plist()
    reg = {"version": 1, "apps": {}}
    if old is None:
        save_registry(reg)
        return []

    try:
        with old.open("rb") as f:
            data = plistlib.load(f)
    except Exception:
        save_registry(reg)
        return []

    objs = {o["uid"]: o for o in data.get("objects", [])}
    conns = data.get("connections", {})
    migrated = []

    for src, dests in conns.items():
        trig = objs.get(src, {})
        if trig.get("type") != "alfred.workflow.trigger.hotkey":
            continue
        cfg = trig.get("config", {})
        hotkey = cfg.get("hotkey", 0)
        hotstring = cfg.get("hotstring", "")
        if not hotkey or not hotstring:
            continue  # unbound leftover trigger
        char = KEY_TO_CHAR.get(hotkey)
        if not char:
            continue  # not a grid key — can't migrate to the grid

        for d in dests:
            target = objs.get(d.get("destinationuid"), {})
            ttype = target.get("type", "")
            tcfg = target.get("config", {})

            if ttype == "alfred.workflow.action.launchfiles":
                paths = tcfg.get("paths") or []
                if not paths:
                    continue
                entry = {
                    "name": Path(paths[0]).stem,
                    "path": paths[0],
                    "toggle": bool(tcfg.get("toggle", True)),
                }
            elif ttype == "alfred.workflow.action.script":
                script = tcfg.get("script", "")
                if "easydict://query" in script:
                    entry = {
                        "name": "Easydict",
                        "mode": "query",
                        "scheme": "easydict://query?text={query}",
                    }
                else:
                    m = re.match(r'\s*open\s+-a\s+"?([^"\s]+)"?(?:\s+(.*))?$', script)
                    if not m:
                        continue
                    entry = {"name": m.group(1), "path": m.group(1)}
                    if m.group(2):
                        entry["args"] = m.group(2).split()
            else:
                continue

            reg["apps"][char] = entry
            migrated.append((char, entry.get("name")))
            break  # first real target wins

    save_registry(reg)
    return migrated


def ensure_registry() -> bool:
    """Auto-migrate on first run, with an onboarding + conflict warning.

    Returns True if a fresh registry was created.
    """
    if registry_path().exists():
        return False
    migrated = migrate(force=True)
    if migrated:
        lines = [f"✓ 已导入 {len(migrated)} 个快捷键映射（来自旧工作流）"]
        if old_workflow_status() == "enabled":
            lines.append("⚠ 旧的 application shortcuts 仍在启用，会抢占热键")
            lines.append("  请先在 Alfred → Workflows 里停用它")
        keys = [k for k, _n in migrated]
        sample = "1" if "1" in keys else keys[0]
        lines.append(f"按 Hyper+{sample.upper()} 启动 · 添加应用: app add 4 Slack")
        _notify_or_print("\n".join(lines))
    return True


# ------------------------------------------------------------- script filter --

def item(uid: str, title: str, subtitle: str, arg: str, match: str = "",
         icon: str | None = None, valid: bool = True) -> dict:
    it = {"uid": uid, "title": title, "subtitle": subtitle, "arg": arg,
          "match": match, "valid": valid}
    if icon:
        it["icon"] = {"path": icon}
    return it


def free_key(reg_apps: dict) -> str | None:
    return next((k for k in GRID if k not in reg_apps), None)


def query_filter(text: str) -> None:
    ensure_registry()
    reg_apps = apps()
    tokens = text.strip().split()
    items = []

    def emit(its: list) -> None:
        """Print items, prefixed with a banner while the old workflow is active."""
        banner = []
        if old_workflow_status() == "enabled":
            banner.append(item("old-wf", "⚠ 旧的 application shortcuts 仍在启用",
                               "它的热键会抢占 — 先在 Alfred → Workflows 停用它",
                               "", "", valid=False))
        print(json.dumps({"items": banner + its}, ensure_ascii=False))

    def launch_items_for(key: str):
        e = reg_apps[key]
        sub = e.get("path", "")
        if e.get("args"):
            sub += "  args: " + " ".join(e["args"])
        items.append(item(f"launch-{key}", f"Hyper+{key.upper()}  {e.get('name')}",
                          sub, f"launch {key}", f"{key} {e.get('name')}",
                          e.get("path")))
        if e.get("mode") == "query":
            items.append(item(f"q-{key}", "查询模式（⌥⇧S 传选中文本）",
                              e.get("scheme", ""), f"launch {key}", ""))

    if not tokens:
        for key in GRID:
            if key in reg_apps:
                launch_items_for(key)
        free = free_key(reg_apps)
        hint = "app add <键> <应用>  添加 · app rm <键|名称>  移除"
        if free:
            hint += f" · 空闲键示例: Hyper+{free.upper()}"
        items.append(item("help", "用法提示", hint, "help", ""))
        emit(items)
        return

    first = tokens[0].lower()

    # remove
    if first in ("rm", "remove", "del", "delete"):
        if len(tokens) < 2:
            items.append(item("rm-hint", "app rm <键|名称>", "例: app rm 3 / app rm Chrome", "help", ""))
        else:
            target = tokens[1].lower()
            key = target if target in reg_apps else next(
                (k for k, e in reg_apps.items() if e.get("name", "").lower() == target), None)
            if key:
                items.append(item("rm", f"移除 Hyper+{key.upper()} {reg_apps[key].get('name')}？",
                                  "回车确认", f"remove {key}", ""))
            else:
                items.append(item("rm-miss", f"未注册: {tokens[1]}", "", "", valid=False))
        emit(items)
        return

    # help / list
    if first in ("help", "h", "list", "ls"):
        items.append(item("help", "App Launcher 用法",
                          "app add <键> <应用> · app rm <键|名称> · app <应用> 启动 · app <键> <应用> 绑定",
                          "help", ""))
        for key in GRID:
            if key in reg_apps:
                launch_items_for(key)
        emit(items)
        return

    # `add` prefix or key-first two-token form
    add_mode = first == "add"
    rest = tokens[1:] if add_mode else tokens
    if add_mode or (len(rest) >= 2 and rest[0].lower() in GRID):
        key = rest[0].lower() if rest else ""
        name_parts = rest[1:] if len(rest) >= 2 else []
        if not rest:
            items.append(item("add-hint", "app add <键> <应用名> [参数…]",
                              "例: app add 4 Slack · app add w Obsidian ~/data/note/notebook",
                              "help", ""))
        elif not name_parts:
            items.append(item("add-hint", f"绑定 Hyper+{key.upper()}",
                              f"输入应用名: app add {key} <应用名>", "help", ""))
        elif key not in GRID:
            items.append(item("bad-key", f"无效按键: {key}", f"可用按键: {GRID}", "", valid=False))
        elif key in reg_apps:
            items.append(item("taken", f"Hyper+{key.upper()} 已被 {reg_apps[key].get('name')} 占用",
                              "先 app rm " + key, "", valid=False))
        else:
            # multi-word name wins when it resolves; else first token = name,
            # remaining tokens = launch args
            name_join = " ".join(name_parts)
            path = resolve_app(name_join)
            if not path and len(name_parts) > 1:
                path = resolve_app(name_parts[0])
            if path:
                display = Path(path).stem
                name_words = [display]
                if not resolve_app(name_join) and len(name_parts) > 1:
                    name_words += list(name_parts[1:])
                arg = "add " + key + " " + " ".join(name_words)
                items.append(item(f"add-{key}", f"绑定 {display} → Hyper+{key.upper()}",
                                  f"回车添加 · {path}", arg, f"{key} {display}",
                                  path))
            else:
                items.append(item("no-app", f"找不到应用: {name_join}", "", "", valid=False))
        emit(items)
        return

    # single token: key or app name
    if len(tokens) == 1:
        tok = tokens[0].lower()
        if tok in GRID:
            if tok in reg_apps:
                launch_items_for(tok)
                items.append(item(f"rm-{tok}", f"移除 Hyper+{tok.upper()} {reg_apps[tok].get('name')}",
                                  "回车确认", f"remove {tok}", ""))
            else:
                items.append(item(f"un-{tok}", f"Hyper+{tok.upper()} 未绑定",
                                  "输入: app add <键> <应用>，或继续输入应用名", f"add {tok}", ""))
            emit(items)
            return

        # app-name form
        name = tokens[0]
        key = next((k for k, e in reg_apps.items() if e.get("name", "").lower() == name.lower()), None)
        if key:
            launch_items_for(key)
        else:
            path = resolve_app(name)
            if path:
                free = free_key(reg_apps)
                items.append(item(f"run-{name}", f"打开 {Path(path).stem}（未注册）",
                                  f"{path}", f"run {Path(path).stem}", Path(path).stem, path))
                if free:
                    items.append(item(f"add-{name}", f"绑定 {Path(path).stem} → Hyper+{free.upper()}",
                                      f"回车添加 · {path}", f"add {free} {Path(path).stem}",
                                      f"{free} {Path(path).stem}", path))
            else:
                items.append(item("no-app", f"找不到应用: {name}",
                                  "试试全名（如 Google Chrome）", "", valid=False))
        emit(items)
        return

    # two+ tokens, first not a key: `app <名称> <多余>…` → treat as name lookup
    name = tokens[0]
    path = resolve_app(name)
    if path:
        free = free_key(reg_apps)
        items.append(item(f"run-{name}", f"打开 {Path(path).stem}（未注册）",
                          f"{path}", f"run {Path(path).stem}", Path(path).stem, path))
        if free:
            items.append(item(f"add-{name}", f"绑定 {Path(path).stem} → Hyper+{free.upper()}",
                              f"回车添加 · {path}", f"add {free} {Path(path).stem}",
                              f"{free} {Path(path).stem}", path))
    else:
        items.append(item("no-app", f"找不到应用: {name}", "", "", valid=False))
    emit(items)


# ------------------------------------------------------------------- main ---

def main() -> None:
    argv = sys.argv[1:]

    if len(argv) > 1:
        cmd, rest = argv[0], list(argv[1:])
    elif argv:
        tokens = argv[0].split()
        if not tokens:
            cmd, rest = "query", []
        elif tokens[0] in ("launch", "run", "add", "remove", "list", "query",
                           "migrate", "help"):
            cmd, rest = tokens[0], tokens[1:]
        else:
            cmd, rest = "launch", tokens  # bare key from a hotkey trigger
    else:
        cmd, rest = "query", []

    if cmd == "launch":
        cmd_launch(rest[0] if rest else "", rest[1] if len(rest) > 1 else "")
    elif cmd == "run":
        cmd_run(rest)
    elif cmd == "add":
        cmd_add(rest)
    elif cmd == "remove":
        cmd_remove(rest[0] if rest else "")
    elif cmd == "list":
        cmd_list()
    elif cmd == "query":
        query_filter(rest[0] if rest else "")
    elif cmd == "migrate":
        migrated = migrate(force="--force" in rest)
        if migrated:
            print(f"imported {len(migrated)}: " + ", ".join(f"{k}->{n}" for k, n in migrated))
        else:
            print("nothing to import (registry exists or old workflow not found)")
    elif cmd == "help":
        _notify_or_print("App Launcher\napp add <键> <应用> [参数…] · app rm <键|名称>\napp <应用> 启动 · app <键> <应用> 绑定")
    else:
        cmd_launch(cmd)


if __name__ == "__main__":
    main()
