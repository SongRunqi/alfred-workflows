#!/usr/bin/env python3
"""Pulse — check and update Alfred workflows from the repo manifest.

Commands (argv):
    filter                    script-filter JSON for the `update` keyword
    notify                    silent check → notification summary (Hyper+U)
    check                     plain-text status (debug / tests)
    update <spec|all>         download+verify+open in Alfred: <name>|<url>|<sha256>
    download <spec|all>       download+verify only, no import dialog

Scope rule (per design): only workflows that are INSTALLED locally AND
listed in the manifest are checked. Uninstalled workflows never appear —
update is update, search is search.

Manifest: https://raw.githubusercontent.com/<repo>/<branch>/versions.json
overridable via config.json in the workflow data dir (repo/branch) or the
PULSE_MANIFEST_URL / PULSE_SCAN_DIRS / PULSE_DRY env vars (tests).
"""

import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
import time
import urllib.request
from contextlib import suppress
from itertools import zip_longest
from pathlib import Path
from typing import Any

BUNDLE_ID = "com.songyitian.pulse"
TITLE = "Pulse"

DEFAULT_REPO = "SongRunqi/alfred-workflows"
DEFAULT_BRANCH = "main"


# ---------------------------------------------------------------- helpers ---

def data_dir() -> Path:
    for env in ("PULSE_DATA", "alfred_workflow_data"):
        v = os.environ.get(env)
        if v:
            return Path(v)
    return Path.home() / "Library/Application Support/Alfred/Workflow Data" / BUNDLE_ID


def config() -> dict:
    p = data_dir() / "config.json"
    cfg = {"repo": DEFAULT_REPO, "branch": DEFAULT_BRANCH}
    if p.exists():
        try:
            cfg.update(json.loads(p.read_text()))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Pulse: config.json unreadable: {e}", file=sys.stderr)
    return cfg


def manifest_url(cfg: dict) -> str:
    env = os.environ.get("PULSE_MANIFEST_URL")
    if env:
        return env
    repo = os.environ.get("PULSE_REPO") or cfg.get("repo", DEFAULT_REPO)
    branch = os.environ.get("PULSE_BRANCH") or cfg.get("branch", DEFAULT_BRANCH)
    return f"https://raw.githubusercontent.com/{repo}/{branch}/versions.json"


def cache_path() -> Path:
    return data_dir() / "cache.json"


def load_cache() -> dict:
    if cache_path().exists():
        try:
            return json.loads(cache_path().read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(cache: dict) -> None:
    p = cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
    os.replace(tmp, p)


def notify(msg: str, title: str = TITLE) -> None:
    esc = msg.replace("\\", "\\\\").replace('"', '\\"')
    esc_t = title.replace("\\", "\\\\").replace('"', '\\"')
    with suppress(Exception):
        subprocess.run(
            ["osascript", "-e", f'display notification "{esc}" with title "{esc_t}"'],
            capture_output=True, timeout=5)


def dry() -> bool:
    return bool(os.environ.get("PULSE_DRY"))


# ------------------------------------------------------------ version math ---

def _as_int(tok: str) -> int | None:
    try:
        return int(tok)
    except ValueError:
        return None


def parse_version(s: str) -> list:
    """'v1.2.3-beta' → [1, 2, 3, 'beta'] (numbers numeric, rest lexical)."""
    s = re.sub(r"^v(?=\d)", "", str(s).lower())  # strip leading v/V prefix
    out = []
    for tok in re.findall(r"\d+|[a-zA-Z]+", s):
        n = _as_int(tok)
        out.append(n if n is not None else tok)
    return out


def _tok_cmp(x, y) -> int:
    """Compare two version tokens: -1 / 0 / 1 (ints numerically, else lexical)."""
    if isinstance(x, int) and isinstance(y, int):
        return (x > y) - (x < y)
    sx, sy = str(x), str(y)
    return (sx > sy) - (sx < sy)


def version_newer(remote: str, installed: str) -> bool:
    """True when remote is strictly newer than installed (missing = older)."""
    if not installed:
        return bool(remote)
    for x, y in zip_longest(parse_version(remote), parse_version(installed), fillvalue=""):
        c = _tok_cmp(x, y)
        if c:
            return c > 0
    return False


# ------------------------------------------------------------ installed scan ---

def scan_dirs() -> list:
    env = os.environ.get("PULSE_SCAN_DIRS")
    if env:
        return [Path(p) for p in env.split(",") if p]
    return [
        Path.home() / "data/sync/alfred/Alfred.alfredpreferences/workflows",
        Path.home() / "Library/Application Support/Alfred/Alfred.alfredpreferences/workflows",
    ]


def installed_workflows() -> dict:
    """bundleid → {name, version, icon_dir} for every installed workflow."""
    found: dict[str, dict[str, Any]] = {}
    for base in scan_dirs():
        if not base.is_dir():
            continue
        for plist in sorted(base.glob("*/info.plist")):
            try:
                with plist.open("rb") as f:
                    data = plistlib.load(f)
            except Exception:
                continue
            bid = data.get("bundleid", "")
            if not bid:
                continue
            wdir = plist.parent
            icon = str(wdir / "icon.png") if (wdir / "icon.png").is_file() else ""
            entry = {
                "name": data.get("name", bid),
                "version": str(data.get("version") or ""),
                "icon": icon,
            }
            # The same bundle id can exist in several prefs dirs (a stale
            # copy from before sync, an old import, …). Prefer the entry
            # that carries a version; merge icons so the menu keeps one.
            prev = found.get(bid)
            if prev:
                if prev.get("version") and entry.get("version"):
                    continue  # first (sync dir) wins on a tie
                if prev.get("version"):
                    if not prev.get("icon") and icon:
                        prev["icon"] = icon
                    continue
                if not entry.get("icon"):
                    entry["icon"] = prev.get("icon", "")
            found[bid] = entry
    return found


# ---------------------------------------------------------------- manifest ---

def fetch_manifest() -> dict | None:
    """Fetch the versions.json manifest. None on any failure."""
    url = manifest_url(config())
    if dry():
        return None
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


# ------------------------------------------------------------------ check ---

def check() -> dict:
    """Fresh check: scan installed ∪ manifest, compare, write cache.

    Returns {ok, checked, updates: [{name, installed, remote, url, sha256}],
             latest: [{name, version, icon}]}.
    """
    installed = installed_workflows()
    manifest = fetch_manifest()
    cfg = config()

    if manifest is None:
        cached = load_cache()
        cached["ok"] = False
        cached["checked"] = cached.get("checked", "")
        return cached

    updates, latest = [], []
    for wf in manifest.get("workflows", []):
        bid = wf.get("bundleid", "")
        local = installed.get(bid)
        if not local:
            continue  # not installed → out of scope
        remote = str(wf.get("version") or "")
        icon = local.get("icon") or "icon.png"
        if remote and version_newer(remote, local.get("version", "")):
            updates.append({
                "name": wf.get("name", bid),
                "installed": local.get("version", ""),
                "remote": remote,
                "url": wf.get("url", ""),
                "sha256": wf.get("sha256", ""),
                "icon": icon,
            })
        else:
            latest.append({
                "name": wf.get("name", bid),
                "version": local.get("version") or remote or "?",
                "icon": icon,
            })

    cache = {
        "ok": True,
        "checked": time.strftime("%Y-%m-%d %H:%M"),
        "repo": cfg.get("repo", DEFAULT_REPO),
        "updates": updates,
        "latest": latest,
    }
    save_cache(cache)
    return cache


# ----------------------------------------------------------- script filter ---

def item(uid: str, title: str, subtitle: str, arg: str, icon: str = "",
         valid: bool = True, mods: dict | None = None) -> dict:
    it = {"uid": uid, "title": title, "subtitle": subtitle, "arg": arg,
          "valid": valid, "match": f"{title} {subtitle}"}
    if icon:
        it["icon"] = {"path": icon}
    if mods:
        it["mods"] = mods
    return it


def filter_json() -> None:
    result = check()
    items = []

    if not result.get("ok"):
        items.append(item("err", "⚠ 检查失败（网络或清单不可用）",
                          "回车重试", "refresh", valid=False))
        for u in result.get("updates", []):
            items.append(item(f"cached-{u['name']}", f"{u['name']}  {u['installed']} → {u['remote']}",
                              f"上次结果（{result.get('checked', '?')}）", "update", valid=False))
        print(json.dumps({"items": items}, ensure_ascii=False))
        return

    updates = result.get("updates", [])
    latest = result.get("latest", [])

    if updates:
        names = "、".join(u["name"] for u in updates[:3])
        more = f" 等 {len(updates)} 个" if len(updates) > 3 else ""
        items.append(item("head", f"⚡ {len(updates)} 个工作流可更新",
                          f"{names}{more} · 回车更新 · ⌘回车仅下载", "", valid=False))
        for u in updates:
            arg = f"{u['name']}|{u['url']}|{u['sha256']}"
            items.append(item(
                f"up-{u['name']}",
                f"{u['name']}  {u['installed'] or '?'} → {u['remote']}",
                "回车：更新（Alfred 确认替换）· ⌘回车：仅下载",
                arg, u.get("icon", ""),
                mods={"cmd": {"arg": f"dl|{arg}", "subtitle": "仅下载，不导入"}}))
        items.append(item("all", "全部更新", f"逐个下载并交给 Alfred 确认（{len(updates)} 个）",
                          "all", valid=False))
    else:
        items.append(item("head", "✓ 全部已是最新",
                          f"检查于 {result.get('checked', '?')}", "", valid=False))

    for lf in latest:
        items.append(item(f"ok-{lf['name']}", f"✓ {lf['name']}  {lf['version']}",
                          "已是最新", "", lf.get("icon", ""), valid=False))

    if not updates and not latest:
        items.append(item("none", "没有需要检查的工作流",
                          "清单里没有已安装的工作流", "", valid=False))

    print(json.dumps({"items": items}, ensure_ascii=False))


# -------------------------------------------------------------- notify mode ---

def notify_summary() -> None:
    result = check()
    if not result.get("ok"):
        notify("检查失败（网络或清单不可用），输入 update 重试")
        return
    updates = result.get("updates", [])
    if updates:
        names = "、".join(u["name"] for u in updates)
        notify(f"{len(updates)} 个工作流可更新：{names}\n输入 update 查看并更新")
    else:
        notify(f"✓ 全部已是最新（{result.get('checked', '')}）")


# ---------------------------------------------------------------- updater ---

def _download(name: str, url: str, sha256: str) -> Path | None:
    """Download + verify. Returns the file path, or None on failure."""
    if not url:
        notify(f"{name}: 清单缺少下载地址")
        return None
    dest = data_dir() / "downloads" / Path(url).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dry():
        print(f"[dry] download {url} → {dest}")
        return dest
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as e:
        notify(f"{name}: 下载失败（{e}）")
        return None
    if sha256:
        actual = hashlib.sha256(dest.read_bytes()).hexdigest()
        if actual.lower() != sha256.lower():
            notify(f"{name}: 校验和不匹配，已拒绝安装")
            dest.unlink(missing_ok=True)
            return None
    return dest


def do_update(specs: list, download_only: bool = False) -> None:
    """specs: list of (name, url, sha256) — or [('all',…)] to refresh + take all."""
    if specs and specs[0][0] == "all":
        result = check()
        specs = [(u["name"], u["url"], u["sha256"]) for u in result.get("updates", [])]
        if not specs:
            notify("没有可更新的工作流")
            return

    done, failed = [], []
    for name, url, sha256 in specs:
        path = _download(name, url, sha256)
        if path is None:
            failed.append(name)
            continue
        if not download_only:
            try:
                if dry():
                    print(f"[dry] open -a 'Alfred 5' {path}")
                else:
                    subprocess.run(["open", "-a", "Alfred 5", str(path)], check=True)
            except Exception:
                failed.append(name)
                continue
        done.append(name)

    if done:
        verb = "已下载" if download_only else "已下载并校验，等待确认替换"
        notify(f"{verb}：{'、'.join(done)}\nAlfred 将弹出导入确认")
    if failed:
        notify(f"失败：{'、'.join(failed)}")


# ------------------------------------------------------------------- main ---

def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "filter"

    if cmd == "filter":
        filter_json()
    elif cmd == "notify":
        notify_summary()
    elif cmd == "check":
        result = check()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif cmd in ("update", "download"):
        specs = []
        for part in (argv[1:] or ["all"]):
            fields = part.split("|")
            if len(fields) >= 3:
                specs.append((fields[0], fields[1], fields[2]))
            else:
                specs.append((fields[0], "", ""))
        do_update(specs, download_only=(cmd == "download"))
    else:
        notify("Pulse: filter | notify | check | update | download")


if __name__ == "__main__":
    main()
