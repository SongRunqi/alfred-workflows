#!/usr/bin/env python3
"""Run Script action: execute Homebrew commands.

Receives the selected arg (format: "action:...") and runs the appropriate brew command.
Prints the result for the notification.
"""

from __future__ import annotations

import os
import subprocess
import sys

from alfred import log, pass_along


def find_brew() -> str | None:
    for candidate in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
        if os.path.isfile(candidate):
            return candidate
    try:
        result = subprocess.run(["which", "brew"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def run_brew(*args: str) -> tuple[int, str, str]:
    """Run brew and return (returncode, stdout, stderr)."""
    brew = find_brew()
    if not brew:
        return (1, "", "Homebrew not found")
    try:
        result = subprocess.run(
            [brew] + list(args),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return (result.returncode, result.stdout.strip(), result.stderr.strip())
    except subprocess.TimeoutExpired:
        return (1, "", "Command timed out")
    except OSError as exc:
        return (1, "", str(exc))


def main() -> None:
    arg = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    log(f"action arg={arg!r}")

    if not arg or ":" not in arg:
        pass_along("Nothing to do")
        return

    parts = arg.split(":", 2)
    action = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    target = parts[2] if len(parts) > 2 else ""

    # --- global actions (no target package) -----------------------------------
    if action == "action":
        cmd_map = {
            "update": (["update"], "🔄 Homebrew updated"),
            "upgrade-all": (["upgrade"], "⬆️ All packages upgraded"),
            "cleanup": (["cleanup"], "🧹 Cleanup complete"),
            "doctor": (["doctor"], "🏥 brew doctor finished"),
        }
        if rest in cmd_map:
            brew_args, ok_msg = cmd_map[rest]
            rc, stdout, stderr = run_brew(*brew_args)
            if rc == 0:
                pass_along(ok_msg)
            else:
                pass_along(f"Failed: {stderr or stdout}")
        else:
            pass_along(f"Unknown action: {rest}")
        return

    if action == "search":
        rc, stdout, stderr = run_brew("search", rest)
        if rc == 0:
            pass_along(f"🔍 brew search {rest}\n{stdout[:500]}")
        else:
            pass_along(f"Search failed: {stderr}")
        return

    if action == "openurl":
        url = ":".join([rest, target]) if target else rest
        log(f"opening URL: {url}")
        subprocess.run(["open", url], check=False)
        pass_along(f"🌐 Opened {url}")
        return

    # --- package actions -------------------------------------------------------
    pkg_name = target if target else rest
    # Determine if it's a cask (install:cask:xxx)
    is_cask = rest == "cask"

    if action == "install":
        cmd = ["install", "--cask", pkg_name] if is_cask else ["install", pkg_name]
        rc, stdout, stderr = run_brew(*cmd)
        if rc == 0:
            pass_along(f"✅ Installed {pkg_name}")
        else:
            pass_along(f"❌ Failed to install {pkg_name}: {stderr or stdout}")

    elif action == "uninstall":
        cmd = ["uninstall", "--cask", pkg_name] if is_cask else ["uninstall", pkg_name]
        rc, stdout, stderr = run_brew(*cmd)
        if rc == 0:
            pass_along(f"🗑️ Uninstalled {pkg_name}")
        else:
            # Try without --cask
            if is_cask:
                rc2, stdout2, _ = run_brew("uninstall", pkg_name)
                if rc2 == 0:
                    pass_along(f"🗑️ Uninstalled {pkg_name}")
                    return
            pass_along(f"❌ Failed to uninstall {pkg_name}: {stderr or stdout}")

    elif action == "upgrade":
        rc, stdout, stderr = run_brew("upgrade", pkg_name)
        if rc == 0:
            pass_along(f"⬆️ Upgraded {pkg_name}")
        else:
            pass_along(f"❌ Failed to upgrade {pkg_name}: {stderr or stdout}")

    elif action == "info":
        rc, stdout, stderr = run_brew("info", pkg_name)
        if rc == 0:
            # Show just the first few lines for notification
            lines = stdout.splitlines()
            summary = "\n".join(lines[:5])
            if len(lines) > 5:
                summary += f"\n… ({len(lines)} lines total)"
            pass_along(summary)
        else:
            pass_along(f"❌ No info for {pkg_name}: {stderr}")

    else:
        pass_along(f"Unknown action: {action}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"unhandled error: {exc!r}")
        sys.stdout.write(f"Error: {exc}")
