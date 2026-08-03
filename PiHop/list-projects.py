#!/usr/bin/env python3
"""list-projects.py — Auto-discover projects from pi & Claude session directories

Output: arg = <project_dir>
"""

import datetime
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
# All configuration comes from Alfred workflow environment variables
# (Alfred → workflow → [x] → Variables). No config files on disk.
_DEFAULT_AGENTS = {
    "pi": {"name": "pi", "icon": "🟢", "launch": "pi"},
    "claude": {"name": "Claude Code", "icon": "🟣", "launch": "claude"},
}


def _load_config():
    cfg = {"defaultAgent": "pi", "agents": dict(_DEFAULT_AGENTS)}
    if os.environ.get("DEFAULT_AGENT"):
        cfg["defaultAgent"] = os.environ["DEFAULT_AGENT"]
    agents_json = os.environ.get("AGENT_AGENTS", "").strip()
    if agents_json:
        try:
            user = json.loads(agents_json)
            if isinstance(user, dict):
                cfg["agents"] = {**cfg["agents"], **user}
        except Exception:
            pass
    return cfg


def _agent_name(agent_id: str) -> str:
    return _load_config()["agents"].get(agent_id, {}).get("name", agent_id)


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


def _parse_ts(ts: str) -> float | None:
    """Parse an ISO timestamp (with optional Z / offset) to local epoch seconds."""
    if not ts:
        return None
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        try:
            dt = datetime.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None
    if dt.tzinfo:
        dt = dt.astimezone()
    return dt.timestamp()


def reltime(ts: str) -> str:
    t = _parse_ts(ts)
    if t is None:
        return "never"
    try:
        diff = int(time.time() - t)
    except (OSError, OverflowError):
        return "?"
    if diff < 60:
        return f"{diff}s"
    elif diff < 3600:
        return f"{diff // 60}m"
    elif diff < 86400:
        return f"{diff // 3600}h"
    else:
        return f"{diff // 86400}d"


def to_epoch(ts: str) -> float:
    return _parse_ts(ts) or 0.0


def latest_ts_jsonl(d: Path) -> str:
    """Newest timestamp among a project's session files.

    Claude Code v2 jsonl files start with metadata lines that carry no
    timestamp, so fall back to the file's mtime (last activity) there.
    """
    best_epoch = 0.0
    best = ""
    if not d.is_dir():
        return best
    for f in sorted(d.glob("*.jsonl"), reverse=True):
        try:
            obj = json.loads(f.open().readline())
            ts = obj.get("timestamp", "")
        except Exception:
            ts = ""
        if not ts:
            ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(f.stat().st_mtime))
        t = _parse_ts(ts)
        if t is not None and t > best_epoch:
            best_epoch = t
            best = ts
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

    # Resume-last-view item on top, when a session was browsed before.
    lower_data_var = "alfred_workflow" + "_data"
    data_dir = os.environ.get("ALFRED_WORKFLOW_DATA") or os.environ.get(
        lower_data_var, ""
    )
    last_viewed = ""
    if data_dir:
        lv = Path(data_dir) / "last_viewed.txt"
        if lv.is_file():
            try:
                last_viewed = lv.read_text(encoding="utf-8").strip()
            except OSError:
                last_viewed = ""
    if last_viewed and Path(last_viewed).is_file():
        items.append(
            {
                "title": "恢复上次浏览的会话",
                "subtitle": f"{Path(last_viewed).name[:70]}",
                "arg": f"__view__|{last_viewed}",
                "icon": {"path": "icons/resume.png"},
            }
        )

    for dir_path, p in sorted_projects:
        name = Path(dir_path).name
        pi_c, pi_l = p["pi_count"], p["pi_last"]
        cc_c, cc_l = p["cc_count"], p["cc_last"]

        if QUERY and not QUERY.startswith("__"):
            # withspace=false passes the query with a possible leading space
            q = QUERY.strip().lower()
            if q and q not in name.lower() and q not in dir_path.lower():
                continue

        sub_parts = []
        if pi_c > 0:
            sub_parts.append(f"{_agent_name('pi')}: {pi_c}s, {reltime(pi_l)}")
        if cc_c > 0:
            sub_parts.append(f"{_agent_name('claude')}: {cc_c}s, {reltime(cc_l)}")
        flags = " ⚡" if p["active"] else ""
        subtitle = " | ".join(sub_parts) + f"  →  {dir_path}{flags}"

        items.append(
            {
                "title": name,
                "subtitle": subtitle,
                "arg": dir_path,
                "autocomplete": name,
                "type": "file",
                "icon": {"type": "fileicon", "path": dir_path},
                # PROJECT_DIR env var flows down the PID-PROJ → PID-SESS connection,
                # letting the sessions filter know the project while the user types
                "variables": {"PROJECT_DIR": dir_path},
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
