#!/usr/bin/env python3
"""Script Filter: manage Homebrew packages.

Type `brew`:
  <empty>   — menu: Installed | Search | quick actions
  !i <qry>  — browse installed packages (filtered by <qry>)
  !s <qry>  — search all packages (installed + available)
  <qry>     — same as !s <qry>
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from alfred import Items, cache_dir, data_dir, log

# --- paths & TTLs ------------------------------------------------------------
INSTALLED_CACHE = Path(cache_dir()) / "brew-installed.json"
OUTDATED_CACHE = Path(data_dir()) / "brew-outdated.json"
FORMULAE_CACHE = Path(data_dir()) / "brew-formulae.txt"
CASKS_CACHE = Path(data_dir()) / "brew-casks.txt"

INSTALLED_TTL = 3600
OUTDATED_TTL = 10800
AVAILABLE_TTL = 86400 * 7

MODE_INSTALLED = "!i"
MODE_SEARCH = "!s"


# --- helpers ------------------------------------------------------------------
def find_brew() -> str | None:
    for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
        if os.path.isfile(p):
            return p
    r = subprocess.run(["which", "brew"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def stale(p: Path, ttl: int) -> bool:
    return not p.exists() or (time.time() - p.stat().st_mtime) >= ttl


# --- data loaders -------------------------------------------------------------
def load_installed(brew: str) -> list[dict]:
    if not stale(INSTALLED_CACHE, INSTALLED_TTL):
        try:
            data = json.loads(INSTALLED_CACHE.read_text())
            if isinstance(data, list):
                return data
        except Exception:
            INSTALLED_CACHE.unlink(missing_ok=True)

    try:
        r = subprocess.run(
            [brew, "info", "--json", "--installed"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            packages = json.loads(r.stdout)
            INSTALLED_CACHE.write_text(json.dumps(packages, ensure_ascii=False))
            return packages
    except Exception as exc:
        log(f"load_installed error: {exc}")

    try:
        data = json.loads(INSTALLED_CACHE.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def load_outdated(brew: str) -> set[str]:
    if not stale(OUTDATED_CACHE, OUTDATED_TTL):
        try:
            raw = json.loads(OUTDATED_CACHE.read_text())
            if isinstance(raw, dict) and "names" in raw:
                return set(raw["names"])
        except Exception:
            OUTDATED_CACHE.unlink(missing_ok=True)

    outdated: set[str] = set()
    ok = False
    for args in (["outdated", "--formula"], ["outdated", "--cask"]):
        try:
            r = subprocess.run(
                [brew] + args,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if r.returncode == 0:
                ok = True
                for line in r.stdout.splitlines():
                    name = line.strip().split()[0] if line.strip() else ""
                    if name:
                        outdated.add(name)
        except Exception as exc:
            log(f"outdated error ({args}): {exc}")

    # Only refresh the cache when at least one query succeeded — a failure
    # must not silently wipe the previous (possibly stale but real) state.
    if ok:
        OUTDATED_CACHE.write_text(
            json.dumps(
                {
                    "names": sorted(outdated),
                    "updated": time.time(),
                }
            )
        )
    return outdated


def load_available_names(brew: str) -> tuple[list[str], list[str]]:
    formulae: list[str] = []
    casks: list[str] = []

    for cp, cmd, target in [
        (FORMULAE_CACHE, ["formulae"], formulae),
        (CASKS_CACHE, ["casks"], casks),
    ]:
        if not stale(cp, AVAILABLE_TTL):
            try:
                target.extend(cp.read_text().splitlines())
                continue
            except Exception:
                cp.unlink(missing_ok=True)
        try:
            r = subprocess.run([brew] + cmd, capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                names = [n.strip() for n in r.stdout.splitlines() if n.strip()]
                target.extend(names)
                cp.write_text("\n".join(names))
        except Exception as exc:
            log(f"load_available({cmd}) error: {exc}")
            if cp.exists():
                with contextlib.suppress(Exception):
                    target.extend(cp.read_text().splitlines())
    return formulae, casks


# --- item builders ------------------------------------------------------------
def make_installed_item(pkg: dict, outdated: set[str]) -> dict:
    name = pkg["name"]
    desc = pkg.get("desc", "")
    version = pkg.get("versions", {}).get("stable", "?")
    is_old = name in outdated
    tap = pkg.get("tap", "")
    tap_label = f" [{tap}]" if tap and tap != "homebrew/core" else ""
    keg = "🔒" if pkg.get("keg_only") else ""
    homepage = pkg.get("homepage", "") or f"https://formulae.brew.sh/formula/{name}"

    sub = (
        f"{keg}{version}{tap_label}  |  {desc}"
        if desc
        else f"{keg}version {version}{tap_label}"
    )
    if is_old:
        sub = "⬆️ UPDATE AVAILABLE — " + sub

    return {
        "title": f"📦 {name}{' ⬆️' if is_old else ''}",
        "subtitle": sub,
        "arg": f"info:{name}",
        "uid": name,
        "valid": True,
        "mods": {
            "cmd": {
                "valid": True,
                "arg": f"upgrade:{name}",
                "subtitle": f"⌘↵ Upgrade {name}",
            },
            "alt": {
                "valid": True,
                "arg": f"uninstall:{name}",
                "subtitle": f"⌥↵ Uninstall {name}",
            },
            "ctrl": {
                "valid": True,
                "arg": f"openurl:{homepage}",
                "subtitle": "\u2303\u21b5 Open homepage",
            },
        },
    }


def match_rank(name: str, query: str) -> int:
    nl, ql = name.lower(), query.lower()
    if nl == ql:
        return 0
    if nl.startswith(ql):
        return 10
    if ql in nl:
        return 20
    return 30


# --- main builder --------------------------------------------------------------
def build(query: str) -> Items:
    items = Items()
    brew = find_brew()
    if not brew:
        items.add(
            title="Homebrew not found",
            subtitle="Install from https://brew.sh",
            valid=False,
        )
        return items

    installed = load_installed(brew)
    outdated = load_outdated(brew) if installed else set()
    inst_by_name = {p["name"]: p for p in installed}
    installed_names = set(inst_by_name.keys())

    query = query.strip()
    ql = query.lower()

    # ── mode detection ─────────────────────────────────────────────────────
    mode: str | None = None
    rest_query = ""

    if ql == MODE_INSTALLED:
        mode = MODE_INSTALLED
        rest_query = ""
    elif ql.startswith(MODE_INSTALLED + " "):
        mode = MODE_INSTALLED
        rest_query = query[len(MODE_INSTALLED) :].strip()
    elif ql == MODE_SEARCH:
        mode = MODE_SEARCH
        rest_query = ""
    elif ql.startswith(MODE_SEARCH + " "):
        mode = MODE_SEARCH
        rest_query = query[len(MODE_SEARCH) :].strip()
    elif query:
        # bare query → treat as search
        mode = MODE_SEARCH
        rest_query = query

    # ── MENU (no mode, no query) ───────────────────────────────────────────
    if mode is None:
        n_out = len(outdated)
        installed_count = len(installed)

        items.add(
            title="📋 Installed Packages",
            subtitle=f"{installed_count} packages installed"
            + (f" · {n_out} outdated" if n_out else ""),
            valid=False,
            autocomplete=MODE_INSTALLED + " ",
        )
        items.add(
            title="🔍 Search Packages",
            subtitle="Search all Homebrew formulae & casks",
            valid=False,
            autocomplete=MODE_SEARCH + " ",
        )

        # Quick actions
        items.add(
            title="🔄 Update Homebrew",
            subtitle="brew update",
            arg="action:update",
            valid=True,
        )
        if n_out > 0:
            items.add(
                title=f"⬆️  Upgrade All ({n_out} outdated)",
                subtitle=f"{n_out} package{'s' if n_out > 1 else ''} can be upgraded",
                arg="action:upgrade-all",
                valid=True,
            )
        items.add(
            title="🧹 Cleanup",
            subtitle="brew cleanup",
            arg="action:cleanup",
            valid=True,
        )
        items.add(
            title="🏥 Doctor",
            subtitle="brew doctor",
            arg="action:doctor",
            valid=True,
        )
        return items

    # ── INSTALLED VIEW ─────────────────────────────────────────────────────
    if mode == MODE_INSTALLED:
        # "Back" hint
        items.add(
            title="← Back to menu",
            subtitle="Clear search to go back",
            valid=False,
            autocomplete="",
            icon={"path": "icon.png"},
        )

        if not rest_query:
            # Show all installed, sorted alphabetically
            pkgs = sorted(installed, key=lambda p: p["name"].lower())
        else:
            # Filter by query
            rq = rest_query.lower()
            pkgs = sorted(
                [
                    p
                    for p in installed
                    if rq
                    in f"{p['name']} {p.get('full_name', '')} {p.get('desc', '')}".lower()
                ],
                key=lambda p: p["name"].lower(),
            )

        for pkg in pkgs:
            items.append(make_installed_item(pkg, outdated))

        if not pkgs:
            items.add(
                title=f"No installed packages matching “{rest_query}”",
                subtitle="Try a different search",
                valid=False,
            )

        return items

    # ── SEARCH VIEW ────────────────────────────────────────────────────────
    if mode == MODE_SEARCH:
        rq = rest_query.lower()
        count = 0
        MAX = 200

        if rq:
            # Search installed
            inst_matches = []
            for pkg in installed:
                name = pkg["name"]
                full = pkg.get("full_name", name)
                desc = pkg.get("desc", "")
                if rq in f"{name} {full} {desc}".lower():
                    inst_matches.append((pkg, match_rank(name, rq)))
            inst_matches.sort(key=lambda x: (x[1], x[0]["name"].lower()))

            for pkg, _ in inst_matches:
                if count >= MAX:
                    break
                items.append(make_installed_item(pkg, outdated))
                count += 1

            # Search available
            if count < MAX and len(rq) >= 1:
                formulae, casks = load_available_names(brew)
                avail = []
                for name in formulae:
                    if name in installed_names:
                        continue
                    r = match_rank(name, rq)
                    if r <= 20:
                        avail.append((name, "formula", r))
                for name in casks:
                    if name in installed_names:
                        continue
                    r = match_rank(name, rq)
                    if r <= 20:
                        avail.append((name, "cask", r))
                avail.sort(key=lambda x: (x[2], x[0].lower()))

                for name, kind, _ in avail:
                    if count >= MAX:
                        break
                    emoji = "🍺" if kind == "cask" else "⬇️"
                    page = f"https://formulae.brew.sh/{'cask' if kind == 'cask' else 'formula'}/{name}"
                    items.add(
                        title=f"{emoji} {name}",
                        subtitle=f"Not installed · {kind}  ⏎ install  ⌃⏎ homepage",
                        arg=f"install:{kind}:{name}",
                        valid=True,
                        mods={
                            "ctrl": {
                                "valid": True,
                                "arg": f"openurl:{page}",
                                "subtitle": f"⌃↵ Open {kind} page",
                            },
                        },
                    )
                    count += 1
        else:
            items.add(
                title="Start typing to search",
                subtitle="Search installed & available Homebrew packages",
                valid=False,
            )

        if not items:
            items.add(
                title=f'🔍 Search Homebrew for "{rest_query}"',
                subtitle="⏎ to run brew search",
                arg=f"search:{rest_query}",
                valid=True,
            )
            items.add(
                title=f'📦 Install "{rest_query}"',
                subtitle="⏎ to install directly",
                arg=f"install:formula:{rest_query}",
                valid=True,
            )

        return items

    return items


# --- entry point --------------------------------------------------------------
def main() -> None:
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    log(f"brew query={query!r}")

    items = build(query)
    if not items:
        items.add(
            title="No results",
            subtitle=f"No packages matching “{query}”",
            valid=False,
        )
    items.emit(skip_knowledge=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"fatal: {exc!r}")
        items = Items()
        items.add(title="Something went wrong", subtitle=str(exc), valid=False)
        items.emit()
