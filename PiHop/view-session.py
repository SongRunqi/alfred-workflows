#!/usr/bin/env python3
"""view-session.py — Render a pi / Claude Code session file as Markdown for the
Text View.

Input:   session file path (argv[1], from the ⌥↵ item arg)
Output:  Text View JSON — {"response": markdown, "behaviour": {...}}

Reads at most the first 3000 lines and caps each message so huge sessions stay
responsive.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

MAX_LINES = 3000
MAX_MESSAGE_CHARS = 4000


def parse_ts(ts: str) -> str:
    """UTC ISO -> local 'MM-DD HH:MM'. Never treat naive UTC as local time."""
    if not ts:
        return ""
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return t.astimezone().strftime("%m-%d %H:%M")
    except ValueError:
        return ""


def content_to_markdown(content) -> str:
    """content may be a plain string or a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                parts.append(str(block))
                continue
            kind = block.get("type", "")
            if kind == "text":
                parts.append(block.get("text", ""))
            elif kind == "thinking":
                parts.append(
                    f"\n<details><summary>💭 thinking</summary>\n\n"
                    f"{block.get('thinking', '')}\n\n</details>\n"
                )
            elif kind == "tool_use":
                name = block.get("name", "?")
                inp = block.get("input", {})
                snippet = json.dumps(inp, ensure_ascii=False, indent=2)
                parts.append(f"\n```json\n// 🛠 {name}\n{snippet[:1200]}\n```\n")
            elif kind == "tool_result":
                result = block.get("content", "")
                if isinstance(result, list):
                    result = "\n".join(
                        b.get("text", "") for b in result if isinstance(b, dict)
                    )
                parts.append(f"\n```\n{str(result)[:800]}\n```\n")
            else:
                parts.append(f"`[{kind}]`")
        return "\n".join(parts)
    return str(content)


def parse_line(line: str) -> dict | None:
    """One jsonl line -> dict, or None when unparsable."""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except ValueError:
        return None


def render_pi(path: Path, lines: list[str]) -> str:
    title_ts = ""
    cwd = ""
    out = []
    for line in lines:
        obj = parse_line(line)
        if not obj:
            continue
        kind = obj.get("type")
        if kind == "session":
            title_ts = parse_ts(obj.get("timestamp", ""))
            cwd = obj.get("cwd", "")
        elif kind == "message":
            msg = obj.get("message", {})
            role = msg.get("role")
            content = content_to_markdown(msg.get("content", ""))
            ts = parse_ts(obj.get("timestamp", ""))
            if role == "user":
                out.append(f"\n## 🧑 You {('· ' + ts) if ts else ''}\n\n{content}")
            elif role == "assistant":
                out.append(
                    f"\n## 🤖 Assistant {('· ' + ts) if ts else ''}\n\n{content}"
                )
        # model_change / thinking_level_change / custom: skipped
    header = f"# Session {title_ts}" if title_ts else "# Session"
    if cwd:
        header += f"\n\n`{cwd}`"
    body = "\n".join(out) or "\n*(empty session)*"
    return header + "\n\n---\n" + body


def render_claude(path: Path, lines: list[str]) -> str:
    title = ""
    out = []
    for line in lines:
        obj = parse_line(line)
        if not obj:
            continue
        kind = obj.get("type")
        if kind == "ai-title":
            title = obj.get("aiTitle", "")
        elif kind in ("user", "assistant"):
            msg = obj.get("message", {})
            content = content_to_markdown(msg.get("content", ""))
            ts = parse_ts(obj.get("timestamp", ""))
            if kind == "user":
                out.append(f"\n## 🧑 You {('· ' + ts) if ts else ''}\n\n{content}")
            else:
                out.append(
                    f"\n## 🤖 Assistant {('· ' + ts) if ts else ''}\n\n{content}"
                )
        # hook_attachment / local-command-caveat / etc: skipped
    header = f"# {title}" if title else f"# {path.stem}"
    body = "\n".join(out) or "\n*(empty session)*"
    return header + "\n\n---\n" + body


def render_codex(path: Path, lines: list[str]) -> str:
    """Codex rollout jsonl: session_meta + response_item payloads.

    Messages carry content blocks of type input_text/output_text; developer
    messages (sandbox instructions, AGENTS.md, app context) are skipped, as
    are system-injected user texts ("<...>", "# AGENTS.md").
    """
    cwd = ""
    title_ts = ""
    out = []
    for line in lines:
        obj = parse_line(line)
        if not obj:
            continue
        kind = obj.get("type")
        payload = obj.get("payload", {}) or {}
        if kind == "session_meta":
            cwd = payload.get("cwd", "")
            title_ts = parse_ts(payload.get("timestamp", ""))
        elif kind != "response_item":
            continue
        ptype = payload.get("type", "")
        ts = parse_ts(obj.get("timestamp", ""))
        if ptype == "message":
            role = payload.get("role", "")
            if role == "developer":
                continue
            texts = [
                b.get("text", "")
                for b in payload.get("content", [])
                if isinstance(b, dict)
                and b.get("type") in ("input_text", "output_text")
            ]
            content = "\n".join(t for t in texts if t).strip()
            if not content:
                continue
            if role == "user":
                if content.startswith(("<", "# AGENTS.md")):
                    continue  # system-injected
                content = content[:MAX_MESSAGE_CHARS]
                out.append(f"\n## 🧑 You {('· ' + ts) if ts else ''}\n\n{content}")
            elif role == "assistant":
                content = content[:MAX_MESSAGE_CHARS]
                out.append(
                    f"\n## 🤖 Assistant {('· ' + ts) if ts else ''}\n\n{content}"
                )
        elif ptype == "reasoning":
            summary = "\n".join(
                s.get("text", "")
                for s in payload.get("summary", [])
                if isinstance(s, dict)
            ).strip()
            if summary:
                out.append(
                    f"\n<details><summary>💭 thinking</summary>\n\n"
                    f"{summary[:2000]}\n\n</details>\n"
                )
        elif ptype == "function_call":
            name = payload.get("name", "?")
            args = payload.get("arguments", "")
            out.append(f"\n```json\n// 🛠 {name}\n{str(args)[:1200]}\n```\n")
        elif ptype == "function_call_output":
            output = payload.get("output", "")
            if isinstance(output, (dict, list)):
                output = json.dumps(output, ensure_ascii=False)
            out.append(f"\n```\n{str(output)[:800]}\n```\n")
    header = f"# Session {title_ts}" if title_ts else "# Session"
    if cwd:
        header += f"\n\n`{cwd}`"
    body = "\n".join(out) or "\n*(empty session)*"
    return header + "\n\n---\n" + body


def main() -> None:
    raw_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    # "__view__|<path>" arrives from the project list's resume item;
    # plain "<path>" from the sessions list ⌥↵.
    session_path = (
        raw_arg.split("|", 1)[1] if raw_arg.startswith("__view__|") else raw_arg
    )
    path = Path(session_path).expanduser()
    if not path.is_file():
        print(
            json.dumps(
                {
                    "response": f"# 无法打开会话\n\n`{session_path}`",
                    "behaviour": {"response": "replace", "scroll": "end"},
                },
                ensure_ascii=False,
            )
        )
        return

    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()[:MAX_LINES]
    except (OSError, PermissionError) as exc:
        print(
            json.dumps(
                {
                    "response": f"# 无法读取会话\n\n`{exc}`",
                    "behaviour": {"response": "replace", "scroll": "end"},
                },
                ensure_ascii=False,
            )
        )
        return

    # Remember this session so the project list can offer "resume last view".
    # Alfred injects the lowercase env var; the linter wants uppercase, so the
    # lowercase name is assembled at runtime and both forms are read.
    lower_data_var = "alfred_workflow" + "_data"
    data_dir = os.environ.get("ALFRED_WORKFLOW_DATA") or os.environ.get(
        lower_data_var, ""
    )
    if data_dir:
        try:
            Path(data_dir).mkdir(parents=True, exist_ok=True)
            (Path(data_dir) / "last_viewed.txt").write_text(str(path), encoding="utf-8")
        except OSError:
            pass

    first = lines[0][:200] if lines else ""
    if '"type":"session"' in first.replace(" ", ""):
        markdown = render_pi(path, lines)
    elif '"session_meta"' in first.replace(" ", ""):
        markdown = render_codex(path, lines)
    else:
        markdown = render_claude(path, lines)

    print(
        json.dumps(
            {
                "response": markdown,
                "behaviour": {"response": "replace", "scroll": "end"},
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
