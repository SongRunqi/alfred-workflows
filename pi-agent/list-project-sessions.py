#!/usr/bin/env python3
"""list-project-sessions.py — Sessions & Agent List for one project

Input:
  <project_dir>              → show sessions + Start items
  __rerun__|agents|<dir>     → show agent list (from Cmd+Enter on Start)
  __rerun__|sessions|<dir>   → back from agent list to sessions

Output args:
  __back__                          → back to projects (Enter → Conditional)
  __new__|<dir>|<agent>             → start new session
  __rerun__|agents|<dir>            → show agent list (⌘↵ on Start, or Back from agent list)
  <session_file>|<agent>|<dir>      → resume session
"""

import json
import os
import sys
import time
from pathlib import Path

HOME = Path.home()
INPUT = sys.argv[1] if len(sys.argv) > 1 else ""

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
    if os.environ.get("DEFAULT_AGENT"):
        cfg["defaultAgent"] = os.environ["DEFAULT_AGENT"]
    return cfg


def _agent_name(agent_id: str) -> str:
    return _load_config()["agents"].get(agent_id, {}).get("name", agent_id)


def _agent_icon(agent_id: str) -> str:
    return _load_config()["agents"].get(agent_id, {}).get("icon", "📁")


def _default_agent() -> str:
    return _load_config()["defaultAgent"]


def encode_pi(path: str) -> str:
    return "--" + path.lstrip("/").replace("/", "-") + "--"


def encode_cc(path: str) -> str:
    return "-" + path.lstrip("/").replace("/", "-")


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


def fmt_time(ts: str) -> str:
    if not ts:
        return "unknown"
    try:
        t = time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        return time.strftime("%b %d %H:%M", t)
    except ValueError:
        return ts[:16]


def extract_title(filepath: Path) -> str:
    try:
        with open(filepath) as f:
            for i, line in enumerate(f):
                if i > 50:
                    break
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                msg = (
                    obj.get("message", {})
                    if isinstance(obj.get("message"), dict)
                    else {}
                )
                role = msg.get("role", "") or obj.get("role", "")
                content = msg.get("content", "") or obj.get("content", "")
                if role == "user" and content:
                    if isinstance(content, str) and content.strip():
                        return content.strip()[:80]
                    elif isinstance(content, list):
                        texts = [
                            b.get("text", "")
                            for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        ]
                        combined = " ".join(texts).strip()
                        if combined:
                            return combined[:80]
    except (OSError, ValueError, LookupError):
        pass
    return ""


def scan_pi_sessions(project_dir: str) -> list[dict]:
    enc = encode_pi(project_dir)
    d = PI_SESSIONS / enc
    if not d.is_dir():
        return []
    sessions = []
    for sf in sorted(d.glob("*.jsonl"), reverse=True):
        try:
            meta = json.loads(sf.open().readline())
            ts = meta.get("timestamp", "")
        except Exception:
            ts = ""
        title = extract_title(sf) or fmt_time(ts)
        sessions.append(
            {
                "title": title,
                "subtitle": f"pi  ·  {fmt_time(ts)}  ·  {(sf.stat().st_size / 1024):.0f}KB",
                "arg": f"{sf}|pi|{project_dir}",
                "ts": ts,
                "agent": "pi",
            }
        )
    return sessions


def scan_claude_sessions(project_dir: str) -> list[dict]:
    name_lookup: dict[str, str] = {}
    status_lookup: dict[str, str] = {}
    if CLAUDE_SESSIONS.is_dir():
        for sf in sorted(CLAUDE_SESSIONS.glob("*.json")):
            try:
                obj = json.loads(sf.read_text())
                sid = obj.get("sessionId", "")
                if sid:
                    name_lookup[sid] = obj.get("name", "")
                    status_lookup[sid] = obj.get("status", "")
            except Exception:
                pass

    enc = encode_cc(project_dir)
    proj_dir = CLAUDE_PROJECTS / enc
    if not proj_dir.is_dir():
        return []

    sessions = []
    for sf in sorted(proj_dir.glob("*.jsonl"), reverse=True):
        try:
            meta = json.loads(sf.open().readline())
            ts = meta.get("timestamp", "")
            sid = meta.get("sessionId", "")
        except Exception:
            ts, sid = "", ""

        name = name_lookup.get(sid, "")
        active = " ⚡" if status_lookup.get(sid) == "busy" else ""
        title = name or extract_title(sf) or fmt_time(ts)
        sessions.append(
            {
                "title": title,
                "subtitle": f"claude  ·  {fmt_time(ts)}  ·  {(sf.stat().st_size / 1024):.0f}KB{active}",
                "arg": f"{sf}|claude|{project_dir}",
                "ts": ts,
                "agent": "claude",
            }
        )
    return sessions


# ── Agent List mode ──


def show_agent_list(project_dir: str):
    """Output agent list for starting a new session."""
    project_name = Path(project_dir).name
    agents = _load_config()["agents"]
    items = []

    items.append(
        {
            "title": "←  Back to sessions",
            "subtitle": f"Return to session list for {project_name}",
            "arg": f"__rerun__|sessions|{project_dir}",
        }
    )

    for aid, info in agents.items():
        items.append(
            {
                "title": f"{info.get('icon', '📁')}  {info.get('name', aid)}",
                "subtitle": f"Start a new {info.get('name', aid)} session in {project_name}",
                "arg": f"__new__|{project_dir}|{aid}",
            }
        )

    print(json.dumps({"items": items}, indent=2))


# ── Sessions mode ──


def show_sessions(project_dir: str):
    """Output session list for a project."""
    project_path = Path(project_dir)
    if not project_path.is_dir():
        print(
            json.dumps(
                {
                    "items": [
                        {"title": f"Directory not found: {project_dir}", "valid": False}
                    ]
                }
            )
        )
        return

    all_sessions = scan_pi_sessions(project_dir) + scan_claude_sessions(project_dir)
    all_sessions.sort(key=lambda s: s.get("ts", ""), reverse=True)

    default_agent = _default_agent()
    default_name = _agent_name(default_agent)
    items = []

    # Back
    items.append(
        {
            "title": "←  Back to projects",
            "subtitle": "Return to project list",
            "arg": "__back__",
        }
    )

    # Start new session: Enter = default, Cmd+Enter = agent list
    # The Cmd+Enter arg goes through Sessions SF's second connection (mod=1048576)
    # directly to CallExternal → ExtSess → Sessions SF re-run with __rerun__|agents|dir
    items.append(
        {
            "title": f"🎯  Start new session (default: {default_name})",
            "subtitle": f"Enter = {default_name}  |  ⌘↵ = choose agent…",
            "arg": f"__new__|{project_dir}|{default_agent}",
            "icon": {"path": str(project_path)},
            "mods": {
                "cmd": {
                    "arg": f"__rerun__|agents|{project_dir}",
                    "subtitle": "Choose which agent to use…",
                }
            },
        }
    )

    # Sessions
    for s in all_sessions:
        aid = s["agent"]
        items.append(
            {
                "title": f"{_agent_icon(aid)}  {s['title']}",
                "subtitle": s["subtitle"],
                "arg": s["arg"],
                "icon": {"path": str(project_path)},
            }
        )

    if len(items) == 2:
        items.append(
            {
                "title": "No previous sessions yet",
                "subtitle": "Use ↑ Start new session to begin",
                "valid": False,
            }
        )

    print(json.dumps({"items": items}, indent=2))


# ── Main ──


def main():
    if not INPUT or INPUT == "none":
        print(json.dumps({"items": [{"title": "No project selected", "valid": False}]}))
        return

    if INPUT.startswith("__rerun__|"):
        parts = INPUT.split("|", 2)
        if len(parts) >= 3:
            mode = parts[1]
            project_dir = parts[2]
            if mode == "agents":
                show_agent_list(project_dir)
            else:
                show_sessions(project_dir)
            return

    show_sessions(INPUT)


if __name__ == "__main__":
    main()
