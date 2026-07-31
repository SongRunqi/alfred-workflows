#!/usr/bin/env python3
"""list-projects.py — Auto-discover projects from pi & Claude session directories

Output: arg = <project_dir>
"""

import json
import os
import sys
import time
from pathlib import Path

HOME = Path.home()
QUERY = sys.argv[1] if len(sys.argv) > 1 else ""

PI_SESSIONS = HOME / ".pi" / "agent" / "sessions"
CLAUDE_SESSIONS = HOME / ".claude" / "sessions"
CLAUDE_PROJECTS = HOME / ".claude" / "projects"

# ---- Config ----
CONFIG_PATH = HOME / ".pi-agent-config.json"
_DEFAULT_AGENTS = {
    "pi": {"name": "pi", "icon": "🟢", "launch": "pi"},
    "claude": {"name": "Claude Code", "icon": "🟣", "launch": "claude"},
}


def _load_config():
    cfg = {"defaultAgent": "pi", "agents": dict(_DEFAULT_AGENTS)}
    # 1. JSON config file (lower priority)
    if CONFIG_PATH.is_file():
        try:
            with open(CONFIG_PATH) as f:
                user = json.load(f)
            if "defaultAgent" in user:
                cfg["defaultAgent"] = user["defaultAgent"]
            if "agents" in user:
                cfg["agents"] = {**cfg["agents"], **user["agents"]}
        except Exception:
            pass
    # 2. Alfred config env var (highest priority)
    if os.environ.get("DEFAULT_AGENT"):
        cfg["defaultAgent"] = os.environ["DEFAULT_AGENT"]
    return cfg


def _agent_name(agent_id: str) -> str:
    return _load_config()["agents"].get(agent_id, {}).get("name", agent_id)


def _agent_icon(agent_id: str) -> str:
    return _load_config()["agents"].get(agent_id, {}).get("icon", "📁")


# ---- Encode/decode ----


def decode_path(encoded: str) -> str | None:
    """Try to decode a session directory name back to a real path.

    Encoding: / → -, wrapped with --...-- (pi) or -... (claude).
    Because hyphens in names are ambiguous, try multiple splits,
    return the first that exists on disk.
    """
    # Strip wrappers
    s = encoded
    if s.startswith("--") and s.endswith("--"):
        s = s[2:-2]
    elif s.startswith("-"):
        s = s[1:]

    if not s:
        return None

    # Split by -, try progressively merging from the right
    parts = s.split("-")
    for i in range(len(parts), 0, -1):
        candidate = "/" + "/".join(parts[:i]) + "-" + "-".join(parts[i:])
        candidate = candidate.rstrip("-")  # in case i==len(parts)
        # Try WITHOUT merging first
        candidate2 = "/" + "/".join(parts)
        # Try both
        for c in {candidate, candidate2}:
            if Path(c).is_dir():
                return c

    return None


def reltime(ts: str) -> str:
    if not ts:
        return "never"
    try:
        t = time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
        diff = int(time.time() - t)
    except ValueError:
        return "?"
    if diff < 60:
        return f"{diff}s"
    elif diff < 3600:
        return f"{diff // 60}m"
    elif diff < 86400:
        return f"{diff // 3600}h"
    else:
        return f"{diff // 86400}d"


def to_epoch(ts: str) -> int:
    if not ts:
        return 0
    try:
        return int(time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")))
    except ValueError:
        return 0


def latest_ts_jsonl(d: Path) -> str:
    best = ""
    if not d.is_dir():
        return best
    for f in sorted(d.glob("*.jsonl"), reverse=True):
        try:
            obj = json.loads(f.open().readline())
            ts = obj.get("timestamp", "")
            if ts and ts > best:
                best = ts
        except Exception:
            continue
    return best


def count_jsonl(d: Path) -> int:
    if not d.is_dir():
        return 0
    return len(list(d.glob("*.jsonl")))


def main():
    projects: dict[str, dict] = {}

    # --- Scan pi sessions ---
    if PI_SESSIONS.is_dir():
        for pd in sorted(PI_SESSIONS.iterdir()):
            if not pd.is_dir():
                continue
            real = decode_path(pd.name)
            if not real:
                continue
            pi_c = count_jsonl(pd)
            pi_l = latest_ts_jsonl(pd)
            projects[real] = {
                "pi_count": pi_c,
                "pi_last": pi_l,
                "cc_count": 0,
                "cc_last": "",
                "active": False,
            }

    # --- Scan claude projects ---
    if CLAUDE_PROJECTS.is_dir():
        for pd in sorted(CLAUDE_PROJECTS.iterdir()):
            if not pd.is_dir():
                continue
            real = decode_path(pd.name)
            if not real:
                continue
            cc_c = count_jsonl(pd)
            cc_l = latest_ts_jsonl(pd)
            if real in projects:
                projects[real]["cc_count"] = cc_c
                projects[real]["cc_last"] = cc_l
            else:
                projects[real] = {
                    "pi_count": 0,
                    "pi_last": "",
                    "cc_count": cc_c,
                    "cc_last": cc_l,
                    "active": False,
                }

    # --- Check active claude sessions ---
    if CLAUDE_SESSIONS.is_dir():
        for sf in sorted(CLAUDE_SESSIONS.glob("*.json")):
            try:
                data = json.loads(sf.read_text())
            except Exception:
                continue
            cwd = data.get("cwd", "")
            if cwd in projects and data.get("status") == "busy":
                projects[cwd]["active"] = True
            elif cwd not in projects and Path(cwd).is_dir():
                projects[cwd] = {
                    "pi_count": 0,
                    "pi_last": "",
                    "cc_count": 1,
                    "cc_last": "",
                    "active": data.get("status") == "busy",
                }

    # --- Sort ---
    sorted_projects = sorted(
        projects.items(),
        key=lambda kv: max(to_epoch(kv[1]["pi_last"]), to_epoch(kv[1]["cc_last"])),
        reverse=True,
    )

    # --- Build items ---
    items = []
    for dir_path, p in sorted_projects:
        name = Path(dir_path).name
        pi_c, pi_l = p["pi_count"], p["pi_last"]
        cc_c, cc_l = p["cc_count"], p["cc_last"]

        if QUERY and not QUERY.startswith("__"):
            q = QUERY.lower()
            if q not in name.lower() and q not in dir_path.lower():
                continue

        sub_parts = []
        if pi_c > 0:
            sub_parts.append(f"{_agent_name('pi')}: {pi_c}s, {reltime(pi_l)}")
        if cc_c > 0:
            sub_parts.append(f"{_agent_name('claude')}: {cc_c}s, {reltime(cc_l)}")
        flags = " ⚡" if p["active"] else ""
        subtitle = " | ".join(sub_parts) + f"  →  {dir_path}{flags}"

        if pi_c > 0 and cc_c > 0:
            icon = "🔀"
        elif pi_c > 0:
            icon = _agent_icon("pi")
        else:
            icon = _agent_icon("claude")

        items.append(
            {
                "title": f"{icon}  {name}",
                "subtitle": subtitle,
                "arg": dir_path,
                "autocomplete": name,
                "type": "file",
                "icon": {"type": "fileicon", "path": dir_path},
            }
        )

    if not items:
        items.append(
            {
                "title": "No projects with sessions found",
                "subtitle": "Run pi or claude in a project directory to create sessions",
                "arg": "none",
                "valid": False,
            }
        )

    print(json.dumps({"items": items}, indent=2))


if __name__ == "__main__":
    main()
