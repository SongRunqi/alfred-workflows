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

import datetime
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
# All configuration comes from Alfred workflow environment variables
# (Alfred → workflow → [x] → Variables). No config files on disk.
_DEFAULT_AGENTS = {
    "pi": {"name": "pi", "launch": "pi"},
    "claude": {"name": "Claude Code", "launch": "claude"},
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


def _agent_icon(agent_id: str) -> str:
    """Per-agent icon file (relative to the workflow root)."""
    return {"pi": "icons/pi.png", "claude": "icons/claude.png"}.get(
        agent_id, "icons/agent.png"
    )


def _default_agent() -> str:
    return _load_config()["defaultAgent"]


def encode_pi(path: str) -> str:
    return "--" + path.lstrip("/").replace("/", "-") + "--"


def encode_cc(path: str) -> str:
    return "-" + path.lstrip("/").replace("/", "-")


def _parse_ts(ts: str) -> float | None:
    """Parse an ISO timestamp (with optional Z / offset) to local epoch seconds.

    Handles both UTC timestamps ("...Z") and naive local ones; naive inputs are
    interpreted as local time.
    """
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


def fmt_time(ts: str) -> str:
    t = _parse_ts(ts)
    if t is None:
        return "unknown"
    return time.strftime("%b %d %H:%M", time.localtime(t))


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
                "mods": {
                    "alt": {
                        "subtitle": "⌥ 浏览会话内容",
                        "arg": f"{sf}",
                    }
                },
                "ts": ts,
                "agent": "pi",
            }
        )
    return sessions


def claude_meta(sf: Path) -> tuple[str, str, str, str]:
    """Read a Claude Code v2 jsonl in one pass.

    New-format files start with type-tagged metadata lines (ai-title,
    agent-name, mode, ...) instead of a session header, and the first line has
    no timestamp. Returns (ai_title, first_user_message, timestamp, sessionId):
      - ai_title: Claude's own generated title (ai-title entry)
      - first_user: first real user message, skipping system-injected ones
        (<local-command-caveat>, <command-name>, <command-message>...)
      - timestamp: first message timestamp found in the file, else file mtime
    """
    ai_title = ""
    first_user = ""
    ts = ""
    sid = ""
    try:
        with open(sf) as f:
            for i, line in enumerate(f):
                if i > 250:
                    break
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not sid and obj.get("sessionId"):
                    sid = obj["sessionId"]
                if not ts and obj.get("timestamp"):
                    ts = obj["timestamp"]
                if (
                    not ai_title
                    and obj.get("type") == "ai-title"
                    and obj.get("aiTitle")
                ):
                    ai_title = obj["aiTitle"]
                if not first_user and obj.get("type") == "user":
                    m = obj.get("message") or {}
                    content = m.get("content", "")
                    if isinstance(content, str):
                        if content.startswith("<"):
                            continue  # system-injected: local-command-caveat etc.
                        if content.strip():
                            first_user = content.strip()[:80]
                    elif isinstance(content, list):
                        texts = [
                            b.get("text", "")
                            for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        ]
                        combined = " ".join(texts).strip()
                        if combined and not combined.startswith("<"):
                            first_user = combined[:80]
                if ai_title and first_user:
                    break  # title settled; timestamp falls back to mtime if absent
    except OSError:
        return "", "", "", ""
    if not ts:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(sf.stat().st_mtime))
    return ai_title, first_user, ts, sid


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
        ai_title, first_user, ts, sid = claude_meta(sf)
        name = name_lookup.get(sid, "")
        active = " ⚡" if status_lookup.get(sid) == "busy" else ""
        title = ai_title or name or first_user or fmt_time(ts)
        sessions.append(
            {
                "title": title,
                "subtitle": f"claude  ·  {fmt_time(ts)}  ·  {(sf.stat().st_size / 1024):.0f}KB{active}",
                "arg": f"{sf}|claude|{project_dir}",
                "mods": {
                    "alt": {
                        "subtitle": "⌥ 浏览会话内容",
                        "arg": f"{sf}",
                    }
                },
                "ts": ts,
                "agent": "claude",
            }
        )
    return sessions


# ── Agent List mode ──


def show_agent_list(project_dir: str, filter_text: str = ""):
    """Output agent list for starting a new session."""
    project_name = Path(project_dir).name
    agents = _load_config()["agents"]
    q = filter_text.strip().lower()
    items = []

    items.append(
        {
            "title": "←  Back to sessions",
            "subtitle": f"Return to session list for {project_name}",
            "arg": f"__rerun__|sessions|{project_dir}",
        }
    )

    for aid, info in agents.items():
        if q and q not in info.get("name", aid).lower() and q not in aid.lower():
            continue
        items.append(
            {
                "title": info.get("name", aid),
                "subtitle": f"Start a new {info.get('name', aid)} session in {project_name}",
                "arg": f"__new__|{project_dir}|{aid}",
                "icon": {"path": _agent_icon(aid)},
            }
        )

    print(json.dumps({"items": items}, indent=2))


# ── Sessions mode ──


def show_sessions(project_dir: str, filter_text: str = ""):
    """Output session list for a project, optionally client-filtered.

    filter_text: typed by the user while the project dir sits in the input box;
    the project itself travels via the project_dir env var (see main()).
    """
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

    q = filter_text.strip().lower()
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
            "title": f"Start new session (default: {default_name})",
            "subtitle": f"Enter = {default_name}  |  ⌘↵ = choose agent…",
            "arg": f"__new__|{project_dir}|{default_agent}",
            "icon": {"path": "icons/new.png"},
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
        if q and q not in (s["title"] + " " + s["subtitle"]).lower():
            continue
        aid = s["agent"]
        item = {
            "title": s["title"],
            "subtitle": s["subtitle"],
            "arg": s["arg"],
            "icon": {"path": _agent_icon(aid)},
        }
        if s.get("mods"):
            item["mods"] = s["mods"]
        items.append(item)

    if len(items) == 2:
        items.append(
            {
                "title": f"No matching sessions for “{filter_text.strip()}”"
                if q
                else "No previous sessions yet",
                "subtitle": "Use ↑ Start new session to begin",
                "valid": False,
            }
        )

    print(json.dumps({"items": items}, indent=2))


# ── Main ──


def main():
    if INPUT.startswith("__rerun__|"):
        parts = INPUT.split("|", 2)
        if len(parts) >= 3:
            mode = parts[1]
            rest = parts[2]
            # The project dir rides along in the input, but with the sessions
            # filter now re-running on every keystroke (argumenttype=1) the
            # typed filter text is appended after it. PROJECT_DIR is still in
            # the variable stream (Call External Trigger passes variables), so
            # when it matches the embedded dir, treat the tail as the filter
            # — this also keeps dirs containing spaces working.
            env_dir = os.environ.get("PROJECT_DIR", "").strip()
            if env_dir and (rest == env_dir or rest.startswith(env_dir + " ")):
                filter_text = rest[len(env_dir) :].strip()
                if mode == "agents":
                    show_agent_list(env_dir, filter_text)
                else:
                    show_sessions(env_dir, filter_text)
                return
            if mode == "agents":
                show_agent_list(rest)
            else:
                show_sessions(rest)
            return

    # Picked from the project list: the project travels via the PROJECT_DIR env
    # var (connection variables through the external-trigger chain), while the
    # input box stays clean so the user types a filter directly. The query may
    # be the bare filter text, or (legacy path) the dir with the filter appended.
    env_dir = os.environ.get("PROJECT_DIR", "").strip()
    if env_dir:
        rest = INPUT[len(env_dir) :] if INPUT.startswith(env_dir) else INPUT
        show_sessions(env_dir, rest)
        return

    if not INPUT or INPUT == "none":
        print(json.dumps({"items": [{"title": "No project selected", "valid": False}]}))
        return

    show_sessions(INPUT)


if __name__ == "__main__":
    main()
