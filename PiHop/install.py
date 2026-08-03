#!/usr/bin/env python3
"""install.py — agent-session Alfred workflow 一键安装/同步脚本

用法:
  python3 install.py             安装/同步（代码 → Alfred + kitty 配置 + 布局快照）
  python3 install.py --check     只检查状态，不做任何修改
  python3 install.py --package   同步后打包 .alfredworkflow 到桌面

做的事:
  1. 把 launch.sh / list-projects.py / list-project-sessions.py
     同步到 Alfred 实际运行的 workflow 目录
     （通过 prefs.json 的 current 定位，支持 sync 目录）
  2. 确保 prefs.plist 的 AGENT_TERMINAL = kitty
  3. 确保 ~/.config/kitty/kitty.conf 有 listen_on / startup_session
     （幂等：已存在则不动；改了需要重启 kitty 生效）
  4. 刷新 ~/.config/kitty/restore-session 布局快照
     （有运行中的 kitty 则导出真实布局，否则写默认布局）
  5. --package: 打包 .alfredworkflow（info.plist 在包根目录，可双击安装）
"""

import argparse
import json
import os
import plistlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HOME = Path.home()
SRC = Path(__file__).resolve().parent  # 本脚本所在目录（开发目录）
FILES = ["launch.sh", "list-projects.py", "list-project-sessions.py"]
KITTY_CONF = HOME / ".config" / "kitty" / "kitty.conf"
RESTORE_SESSION = HOME / ".config" / "kitty" / "restore-session"
PACKAGE_OUT = HOME / "Desktop" / "agent-session.alfredworkflow"

GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"


def find_alfred_prefs() -> Path | None:
    """Alfred preferences 目录：优先读 prefs.json 的 current（支持同步目录）。"""
    pj = Path.home() / "Library" / "Application Support" / "Alfred" / "prefs.json"
    try:
        cur = json.loads(pj.read_text()).get("current")
        if cur:
            p = Path(cur)
            if p.is_dir():
                return p
    except Exception:
        pass
    p = (
        Path.home()
        / "Library"
        / "Application Support"
        / "Alfred"
        / "Alfred.alfredpreferences"
    )
    return p if p.is_dir() else None


def find_workflow_dir(prefs: Path) -> Path | None:
    """在 preferences/workflows 下找本 workflow（含 list-project-sessions.py 的目录）。"""
    root = prefs / "workflows"
    if not root.is_dir():
        return None
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "list-project-sessions.py").exists():
            return d
    return None


def sync_files(dst: Path, check_only: bool) -> list[str]:
    report = []
    for name in FILES:
        s, t = SRC / name, dst / name
        if not s.exists():
            report.append(f"{RED}⚠ 源码缺失: {name}{RESET}")
            continue
        if t.exists() and t.read_bytes() == s.read_bytes():
            report.append(f"{GREEN}✓ {name}{RESET} 已是最新")
        elif check_only:
            report.append(f"{YELLOW}→ {name}{RESET} 需要同步")
        else:
            shutil.copy2(s, t)
            report.append(f"{YELLOW}→ {name}{RESET} 已同步")
    return report


def ensure_prefs(dst: Path, check_only: bool) -> str:
    pf = dst / "prefs.plist"
    data = {}
    if pf.exists():
        try:
            with open(pf, "rb") as f:
                data = plistlib.load(f)
        except Exception:
            data = {}
    old = data.get("AGENT_TERMINAL")
    if old in (None, "", "kitty --detach zsh {file}"):
        if check_only:
            return f"{YELLOW}→ AGENT_TERMINAL{RESET} 需要设为 kitty（当前: {old!r}）"
        data["AGENT_TERMINAL"] = "kitty"
        try:
            with open(pf, "wb") as f:
                plistlib.dump(data, f)
        except OSError as e:
            return f"{RED}✗ 写入 prefs.plist 失败: {e}{RESET}"
        return f"{YELLOW}→ AGENT_TERMINAL{RESET} 已设为 kitty（原值: {old!r}）"
    return f"{GREEN}✓ AGENT_TERMINAL{RESET} = {old!r}（保持）"


def ensure_kitty_conf(check_only: bool) -> list[str]:
    if not KITTY_CONF.exists():
        return [f"{RED}⚠ {KITTY_CONF} 不存在，跳过{RESET}"]
    text = KITTY_CONF.read_text()
    lines = text.splitlines()
    keys = {
        "allow_remote_control": any(
            ln.strip().startswith("allow_remote_control") for ln in lines
        ),
        "listen_on": any(ln.strip().startswith("listen_on") for ln in lines),
        "startup_session": any(
            ln.strip().startswith("startup_session") for ln in lines
        ),
    }
    want = {
        "allow_remote_control": "allow_remote_control yes",
        "listen_on": "listen_on unix:/tmp/kitty-$USER-{kitty_pid}.sock",
        "startup_session": f"startup_session {RESTORE_SESSION}",
    }
    report = []
    changed = False
    for k in ("allow_remote_control", "listen_on", "startup_session"):
        if keys[k]:
            report.append(f"{GREEN}✓ {k}{RESET} 已配置")
        elif check_only:
            report.append(f"{YELLOW}→ {k}{RESET} 缺失，需要追加: {want[k]}")
        else:
            text = text.rstrip() + "\n\n" + want[k] + "\n"
            changed = True
            report.append(f"{YELLOW}→ {k}{RESET} 已追加: {want[k]}")
    if changed and not check_only:
        KITTY_CONF.write_text(text)
        report.append(f"{YELLOW}⚠ kitty.conf 已修改，需要重启 kitty 才生效{RESET}")
    return report


def refresh_restore_session(check_only: bool) -> str:
    user = os.environ.get("USER") or ""
    socks = sorted(
        Path("/tmp").glob(f"kitty-{user}-*.sock") if user else [],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    kitten = shutil.which("kitten") or "/opt/homebrew/bin/kitten"
    for s in socks:
        try:
            r = subprocess.run(
                [kitten, "@", "--to", f"unix:{s}", "ls", "--output-format=session"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            continue
        if r.returncode == 0 and r.stdout.strip():
            if check_only:
                return f"{GREEN}✓ 布局快照{RESET} 可更新（来自实例 {s.name}）"
            RESTORE_SESSION.write_text(r.stdout)
            return f"{YELLOW}→ 布局快照{RESET} 已保存（来自实例 {s.name}）"
    if check_only:
        return f"{YELLOW}→ 布局快照{RESET} 缺失（无运行中的 kitty 实例）"
    RESTORE_SESSION.write_text(f"new_tab\ncd {HOME}\nlaunch\n")
    return f"{YELLOW}→ 布局快照{RESET} 已写入默认布局（无运行中的 kitty）"


def package(dst: Path, out: Path) -> str:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(dst.iterdir()):
            if f.name.startswith(".") or f.name == ".DS_Store":
                continue
            z.write(f, f.name)
    return f"{GREEN}✓ 已打包{RESET} {out}"


def main():
    ap = argparse.ArgumentParser(description="agent-session workflow 安装/同步")
    ap.add_argument("--check", action="store_true", help="只检查状态，不做修改")
    ap.add_argument(
        "--package", action="store_true", help="同步后打包 .alfredworkflow 到桌面"
    )
    args = ap.parse_args()
    check = args.check
    print(f"{DIM}{'─' * 46}{RESET}")
    print(
        f"{DIM}agent-session 安装脚本  ({'检查模式' if check else '安装模式'}){RESET}"
    )
    print(f"{DIM}{'─' * 46}{RESET}")

    prefs = find_alfred_prefs()
    if not prefs:
        print(f"{RED}✗ 找不到 Alfred preferences 目录{RESET}")
        sys.exit(1)
    print(f"{DIM}Alfred preferences: {prefs}{RESET}")

    dst = find_workflow_dir(prefs)
    if not dst:
        print(
            f"{RED}✗ 找不到已安装的 agent-session workflow（{prefs / 'workflows'} 下无匹配）{RESET}"
        )
        sys.exit(1)
    print(f"{DIM}workflow 目录: {dst}{RESET}")

    print("\n── 1. 同步代码文件 ──")
    for line in sync_files(dst, check):
        print("  " + line)

    print("\n── 2. Alfred 配置 (prefs.plist) ──")
    print("  " + ensure_prefs(dst, check))

    print("\n── 3. kitty.conf ──")
    for line in ensure_kitty_conf(check):
        print("  " + line)

    print("\n── 4. 布局快照 (restore-session) ──")
    print("  " + refresh_restore_session(check))

    if args.package and not check:
        print("\n── 5. 打包 ──")
        print("  " + package(dst, PACKAGE_OUT))

    print(f"\n{DIM}{'─' * 46}{RESET}")
    if check:
        print(f"{DIM}检查完成（未做任何修改）。不带 --check 运行即可安装。{RESET}")
    else:
        print(f"{YELLOW}完成。提醒:{RESET}")
        print("  • 若 kitty.conf 有改动 → 重启一次 kitty")
        print("  • 若 Alfred 正在运行 → 无需重装，脚本已直接更新运行文件")
    print(f"{DIM}{'─' * 46}{RESET}")


if __name__ == "__main__":
    main()
