#!/usr/bin/env python3
"""
Settings — Alfred Script Filter for macOS System Settings panes.

Usage (in Alfred):
    system batt   → Battery
    system wifi   → Wi‑Fi
    system 电池   → Battery
    system login  → Login Items & Extensions
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

CACHE_FILE = (
    Path(os.environ.get("ALFRED_WORKFLOW_DATA", "/tmp")) / "system-settings-panes.json"
)
CACHE_TTL = 86400  # 24 hours


def _cache_valid() -> bool:
    try:
        return (time.time() - CACHE_FILE.stat().st_mtime) < CACHE_TTL
    except FileNotFoundError:
        return False


def _load_cache() -> list[dict]:
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return data
    except Exception:
        pass
    return []


def _save_cache(entries: list[dict]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Icon mapping — each pane uses its Settings extension bundle icon
# ---------------------------------------------------------------------------

_EXT = "/System/Library/ExtensionKit/Extensions"
_APP = "/System/Applications/System Settings.app"

# Each pane → its Settings extension bundle.
# Alfred extracts the native icon via {"type": "fileicon", "path": ...}.
_PANE_BUNDLES: dict[str, str] = {
    "General": _APP,
    "About": _APP,
    "Software Update": f"{_EXT}/SoftwareUpdateSettingsExtension.appex",
    "Storage": _APP,
    "AirDrop & Continuity": f"{_EXT}/AirDropHandoffExtension.appex",
    "Login Items & Extensions": f"{_EXT}/LoginItems.appex",
    "AppleCare & Warranty": f"{_EXT}/CoverageSettings.appex",
    "Language & Region": f"{_EXT}/InternationalSettingsExtension.appex",
    "Date & Time": f"{_EXT}/DateAndTime Extension.appex",
    "Sharing": f"{_EXT}/Sharing.appex",
    "Time Machine": f"{_EXT}/TimeMachineSettings.appex",
    "Transfer or Reset": f"{_EXT}/TransferResetExtension.appex",
    "Startup Disk": f"{_EXT}/StartupDisk.appex",
    "Device Management": f"{_EXT}/ProfilesSettingsExt.appex",
    "Siri": f"{_EXT}/SiriPreferenceExtension.appex",
    "Touch ID & Password": f"{_EXT}/Touch ID & Password.appex",
    "Battery": f"{_EXT}/PowerPreferences.appex",
    "Wallpaper": f"{_EXT}/Wallpaper.appex",
    "Spotlight": f"{_EXT}/SpotlightPreferenceExtension.appex",
    "Notifications": f"{_EXT}/NotificationsSettings.appex",
    "iCloud": f"{_EXT}/AppleIDSettings.appex",
    "Wi‑Fi": f"{_EXT}/Wi-Fi.appex",
    "Bluetooth": f"{_EXT}/Bluetooth.appex",
    "Accessibility": f"{_EXT}/AccessibilitySettingsExtension.appex",
    "Wallet & Apple Pay": f"{_EXT}/WalletSettingsExtension.appex",
    "Internet Accounts": f"{_EXT}/InternetAccountsSettingsExtension.appex",
    "Game Center": f"{_EXT}/GameCenterMacOSSettingsExtension.appex",
    "Printers & Scanners": f"{_EXT}/PrinterScannerSettings.appex",
    "Privacy & Security": f"{_EXT}/SecurityPrivacyExtension.appex",
    "Focus": f"{_EXT}/FocusSettingsExtension.appex",
    "Menu Bar": f"{_EXT}/ControlCenterSettings.appex",
    "Desktop & Dock": f"{_EXT}/DesktopSettings.appex",
    "Keyboard": f"{_EXT}/KeyboardSettings.appex",
    "Appearance": f"{_EXT}/Appearance.appex",
    "Trackpad": f"{_EXT}/TrackpadExtension.appex",
    "Screen Time": f"{_EXT}/ScreenTimePreferencesExtension.appex",
    "Displays": f"{_EXT}/DisplaysExt.appex",
    "Users & Groups": f"{_EXT}/UsersGroups.appex",
    "Lock Screen": f"{_EXT}/LockScreen.appex",
    "Sound": f"{_EXT}/Sound.appex",
    "Network": f"{_EXT}/Network.appex",
    "VPN": _APP,
    "Apple Account": f"{_EXT}/AppleIDSettings.appex",
}


def _icon(entry: dict[str, str]) -> dict:
    """Return an Alfred icon object with the pane's native icon."""
    name = entry["name"]
    if name in _PANE_BUNDLES:
        return {"type": "fileicon", "path": _PANE_BUNDLES[name]}
    name_lower = name.lower()
    for key, path in _PANE_BUNDLES.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return {"type": "fileicon", "path": path}
    return {"type": "fileicon", "path": _APP}


# ---------------------------------------------------------------------------
# Pane discovery via AppleScript
# ---------------------------------------------------------------------------

APPLESCRIPT = r"""
tell application "System Settings"
    set output to ""
    set allPanes to every pane
    repeat with p in allPanes
        try
            set paneName to name of p
        on error
            set paneName to ""
        end try
        try
            set paneID to id of p
        on error
            set paneID to ""
        end try
        set output to output & paneName & ":::" & paneID & "§§§"
    end repeat
    return output
end tell
"""

_ID_TO_NAME: dict[str, str] = {
    "com.apple.systempreferences.GeneralSettings": "General",
    "com.apple.SystemProfiler.AboutExtension": "About",
    "com.apple.Software-Update-Settings.extension": "Software Update",
    "com.apple.settings.Storage": "Storage",
    "com.apple.AirDrop-Handoff-Settings.extension": "AirDrop & Continuity",
    "com.apple.LoginItems-Settings.extension": "Login Items & Extensions",
    "com.apple.Coverage-Settings.extension": "AppleCare & Warranty",
    "com.apple.Localization-Settings.extension": "Language & Region",
    "com.apple.Date-Time-Settings.extension": "Date & Time",
    "com.apple.Sharing-Settings.extension": "Sharing",
    "com.apple.Time-Machine-Settings.extension": "Time Machine",
    "com.apple.Transfer-Reset-Settings.extension": "Transfer or Reset",
    "com.apple.Startup-Disk-Settings.extension": "Startup Disk",
    "com.apple.Profiles-Settings.extension": "Device Management",
    "com.apple.Siri-Settings.extension": "Siri",
    "com.apple.Touch-ID-Settings.extension": "Touch ID & Password",
    "com.apple.Battery-Settings.extension": "Battery",
    "com.apple.Wallpaper-Settings.extension": "Wallpaper",
    "com.apple.Spotlight-Settings.extension": "Spotlight",
    "com.apple.Notifications-Settings.extension": "Notifications",
    "com.apple.systempreferences.AppleIDSettings:icloud": "iCloud",
    "com.apple.systempreferences.AppleIDSettings*AppleIDSettings": "Apple Account",
    "com.apple.wifi-settings-extension": "Wi‑Fi",
    "com.apple.BluetoothSettings": "Bluetooth",
    "com.apple.Accessibility-Settings.extension": "Accessibility",
    "com.apple.WalletSettingsExtension": "Wallet & Apple Pay",
    "com.apple.Internet-Accounts-Settings.extension": "Internet Accounts",
    "com.apple.Game-Center-Settings.extension": "Game Center",
    "com.apple.Print-Scan-Settings.extension": "Printers & Scanners",
    "com.apple.settings.PrivacySecurity.extension": "Privacy & Security",
    "com.apple.Focus-Settings.extension": "Focus",
    "com.apple.ControlCenter-Settings.extension": "Menu Bar",
    "com.apple.Desktop-Settings.extension": "Desktop & Dock",
    "com.apple.Keyboard-Settings.extension": "Keyboard",
    "com.apple.Appearance-Settings.extension": "Appearance",
    "com.apple.Trackpad-Settings.extension": "Trackpad",
    "com.apple.Screen-Time-Settings.extension": "Screen Time",
    "com.apple.Displays-Settings.extension": "Displays",
    "com.apple.Users-Groups-Settings.extension": "Users & Groups",
    "com.apple.Lock-Screen-Settings.extension": "Lock Screen",
    "com.apple.Sound-Settings.extension": "Sound",
    "com.apple.Network-Settings.extension": "Network",
    "com.apple.NetworkExtensionSettingsUI.NESettingsUIExtension": "VPN",
}


def _name_from_id(pane_id: str) -> str:
    if pane_id in _ID_TO_NAME:
        return _ID_TO_NAME[pane_id]
    base = pane_id.split("*")[0].split(":")[0]
    if base in _ID_TO_NAME:
        return _ID_TO_NAME[base]
    parts = pane_id.replace("-", " ").replace(".", " ").split()
    meaningful = [
        p
        for p in parts
        if p not in ("com", "apple", "extension", "settings", "preferences")
    ]
    if meaningful:
        return " ".join(meaningful).title()
    return pane_id


def _discover_panes_via_applescript() -> list[dict]:
    try:
        proc = subprocess.run(
            ["osascript", "-e", APPLESCRIPT],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    raw = proc.stdout.strip()
    if not raw:
        return []

    entries: list[dict] = []
    seen_ids: set[str] = set()

    for chunk in raw.split("§§§"):
        chunk = chunk.strip()
        if not chunk or ":::" not in chunk:
            continue
        name, pane_id = chunk.split(":::", 1)
        name = name.strip()
        pane_id = pane_id.strip()
        if not pane_id:
            continue
        if not name:
            name = _name_from_id(pane_id)
        if name.lower() == "song yitian":
            name = "Apple Account"
        if pane_id in seen_ids:
            continue
        seen_ids.add(pane_id)
        entries.append({"name": name, "id": pane_id})

    return entries


def _get_panes(force_refresh: bool = False) -> list[dict]:
    if not force_refresh and _cache_valid():
        cached = _load_cache()
        if cached and len(cached) >= 30:
            return cached

    # If System Settings isn't running, AppleScript returns only a few
    # panes. Launch it hidden first, then query for the full list.
    entries = _discover_panes_via_applescript()
    if len(entries) >= 30:
        _save_cache(entries)
        return entries

    # Partial or empty — launch System Settings, retry.
    try:
        subprocess.run(
            ["open", "-j", "-a", "System Settings"],
            timeout=3,
            capture_output=True,
        )
        time.sleep(1.0)
        entries = _discover_panes_via_applescript()
        if len(entries) >= 30:
            _save_cache(entries)
            return entries
    except Exception:
        pass

    # Still not enough — use the hard-coded fallback.
    return FALLBACK_PANES


FALLBACK_PANES: list[dict] = [
    {"name": "General", "id": "com.apple.systempreferences.GeneralSettings"},
    {"name": "About", "id": "com.apple.SystemProfiler.AboutExtension"},
    {"name": "Software Update", "id": "com.apple.Software-Update-Settings.extension"},
    {"name": "Storage", "id": "com.apple.settings.Storage"},
    {
        "name": "AirDrop & Continuity",
        "id": "com.apple.AirDrop-Handoff-Settings.extension",
    },
    {
        "name": "Login Items & Extensions",
        "id": "com.apple.LoginItems-Settings.extension",
    },
    {"name": "AppleCare & Warranty", "id": "com.apple.Coverage-Settings.extension"},
    {"name": "Language & Region", "id": "com.apple.Localization-Settings.extension"},
    {"name": "Date & Time", "id": "com.apple.Date-Time-Settings.extension"},
    {"name": "Sharing", "id": "com.apple.Sharing-Settings.extension"},
    {"name": "Time Machine", "id": "com.apple.Time-Machine-Settings.extension"},
    {"name": "Transfer or Reset", "id": "com.apple.Transfer-Reset-Settings.extension"},
    {"name": "Startup Disk", "id": "com.apple.Startup-Disk-Settings.extension"},
    {"name": "Device Management", "id": "com.apple.Profiles-Settings.extension"},
    {"name": "Siri", "id": "com.apple.Siri-Settings.extension"},
    {"name": "Touch ID & Password", "id": "com.apple.Touch-ID-Settings.extension"},
    {"name": "Battery", "id": "com.apple.Battery-Settings.extension"},
    {"name": "Wallpaper", "id": "com.apple.Wallpaper-Settings.extension"},
    {"name": "Spotlight", "id": "com.apple.Spotlight-Settings.extension"},
    {"name": "Notifications", "id": "com.apple.Notifications-Settings.extension"},
    {"name": "iCloud", "id": "com.apple.systempreferences.AppleIDSettings:icloud"},
    {"name": "Wi‑Fi", "id": "com.apple.wifi-settings-extension"},
    {"name": "Bluetooth", "id": "com.apple.BluetoothSettings"},
    {"name": "Accessibility", "id": "com.apple.Accessibility-Settings.extension"},
    {"name": "Wallet & Apple Pay", "id": "com.apple.WalletSettingsExtension"},
    {
        "name": "Internet Accounts",
        "id": "com.apple.Internet-Accounts-Settings.extension",
    },
    {"name": "Game Center", "id": "com.apple.Game-Center-Settings.extension"},
    {"name": "Printers & Scanners", "id": "com.apple.Print-Scan-Settings.extension"},
    {
        "name": "Privacy & Security",
        "id": "com.apple.settings.PrivacySecurity.extension",
    },
    {"name": "Focus", "id": "com.apple.Focus-Settings.extension"},
    {"name": "Menu Bar", "id": "com.apple.ControlCenter-Settings.extension"},
    {"name": "Desktop & Dock", "id": "com.apple.Desktop-Settings.extension"},
    {"name": "Keyboard", "id": "com.apple.Keyboard-Settings.extension"},
    {"name": "Appearance", "id": "com.apple.Appearance-Settings.extension"},
    {"name": "Trackpad", "id": "com.apple.Trackpad-Settings.extension"},
    {"name": "Screen Time", "id": "com.apple.Screen-Time-Settings.extension"},
    {"name": "Displays", "id": "com.apple.Displays-Settings.extension"},
    {"name": "Users & Groups", "id": "com.apple.Users-Groups-Settings.extension"},
    {"name": "Lock Screen", "id": "com.apple.Lock-Screen-Settings.extension"},
    {"name": "Sound", "id": "com.apple.Sound-Settings.extension"},
    {"name": "Network", "id": "com.apple.Network-Settings.extension"},
    {"name": "VPN", "id": "com.apple.NetworkExtensionSettingsUI.NESettingsUIExtension"},
    {
        "name": "Apple Account",
        "id": "com.apple.systempreferences.AppleIDSettings*AppleIDSettings",
    },
]


# ---------------------------------------------------------------------------
# Search aliases — Chinese, pinyin, and common abbreviations
# ---------------------------------------------------------------------------

_MATCH_ALIASES: dict[str, str] = {
    "General": "通用 gen",
    "About": "关于 about 本机 benji ben ji mac info",
    "Software Update": "软件更新 ruan jian geng xin update",
    "Storage": "存储 cun chu disk 磁盘 space 空间",
    "AirDrop & Continuity": "隔空投送 air drop handoff 接力",
    "Login Items & Extensions": "登录项 deng lu xiang login startup 启动 start boot",
    "AppleCare & Warranty": "保修 bao xiu warranty coverage",
    "Language & Region": "语言 地区 yu yan di qu lang region locale 中文",
    "Date & Time": "日期 时间 ri qi shi jian clock 时钟 timezone 时区",
    "Sharing": "共享 gong xiang share",
    "Time Machine": "时间机器 shi jian ji qi backup 备份",
    "Transfer or Reset": "迁移 重置 qian yi chong zhi reset erase 抹掉",
    "Startup Disk": "启动磁盘 qi dong ci pan boot",
    "Device Management": "设备管理 she bei guan li profile 描述文件",
    "Siri": "siri 语音 assistant",
    "Touch ID & Password": "touchid 密码 mi ma password 指纹 zhi wen finger",
    "Battery": "电池 dian chi power 电量 节能 jie neng",
    "Wallpaper": "壁纸 bi zhi wallpaper 桌面背景 background",
    "Spotlight": "spotlight 聚焦 ju jiao search 搜索",
    "Notifications": "通知 tong zhi notification 提醒",
    "iCloud": "icloud cloud 云盘 云 yun",
    "Wi‑Fi": "wifi wi-fi 无线 wu xian wireless 网络",
    "Bluetooth": "蓝牙 lan ya bluetooth bt",
    "Accessibility": "辅助功能 fu zhu gong neng accessibility 视觉 听觉 旁白",
    "Wallet & Apple Pay": "钱包 qian bao wallet pay 支付",
    "Internet Accounts": "互联网账户 hu lian wang zhang hu account email mail 邮件 日历 通讯录",
    "Game Center": "游戏 you xi game",
    "Printers & Scanners": "打印机 扫描仪 da yin ji printer scanner",
    "Privacy & Security": "隐私 安全性 yin si an quan privacy security 权限 firewall 防火墙 文件保险箱",
    "Focus": "专注 zhuan zhu do not disturb 免打扰",
    "Menu Bar": "菜单栏 cai dan lan menubar control center 控制中心",
    "Desktop & Dock": "桌面 程序坞 zhuo mian cheng xu wu desk dock 台前调度 stage manager",
    "Keyboard": "键盘 jian pan key 输入法 输入源",
    "Appearance": "外观 wai guan theme dark 深色 light 浅色 颜色",
    "Trackpad": "触控板 chu kong ban trackpad 触摸板 手势",
    "Screen Time": "屏幕使用时间 ping mu shi yong shi jian screentime",
    "Displays": "显示器 xian shi qi display monitor 分辨率 刷新率",
    "Users & Groups": "用户 群组 yong hu qun zu user group account 账户",
    "Lock Screen": "锁定屏幕 suo ding lock screen 屏保",
    "Sound": "声音 sheng yin audio 音量 输出 输入 耳机 er ji",
    "Network": "网络 wang luo net vpn 代理 firewall",
    "VPN": "vpn 虚拟专用网",
    "Apple Account": "apple id 账户 appleid icloud",
}


def _matches_query(name: str, pane_id: str, query: str) -> bool:
    extra = _MATCH_ALIASES.get(name, "")
    haystack = f"{name} {pane_id} {extra}".lower()
    tokens = query.lower().split()
    return all(t in haystack for t in tokens)


# ---------------------------------------------------------------------------
# Alfred output
# ---------------------------------------------------------------------------


def _emit(items: list[dict], **kwargs) -> None:
    output = {"items": items, **kwargs}
    json.dump(output, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    query = (sys.argv[1] if len(sys.argv) > 1 else "").strip()

    force_refresh = query.lower() == "refresh"
    if force_refresh:
        query = ""

    entries = _get_panes(force_refresh)

    items: list[dict] = []

    # Top-level entry: open System Settings main window.
    if not query or _matches_query("System Settings", "systempreferences", query):
        items.append(
            {
                "title": "System Settings",
                "subtitle": "Open System Settings main window",
                "arg": "com.apple.systempreferences",
                "autocomplete": "System Settings",
                "icon": {"path": _APP},
            }
        )

    for entry in entries:
        name = entry["name"]
        pane_id = entry["id"]

        if query and not _matches_query(name, pane_id, query):
            continue

        is_apple = pane_id.startswith("com.apple.")
        subtitle = (
            ("System Settings → " + name) if is_apple else ("Third-party → " + name)
        )

        items.append(
            {
                "uid": pane_id,
                "title": name,
                "subtitle": subtitle,
                "arg": pane_id,
                "autocomplete": name,
                "icon": _icon(entry),
                "valid": True,
                "mods": {
                    "cmd": {
                        "valid": True,
                        "arg": pane_id,
                        "subtitle": f"Copy ID: {pane_id}",
                    },
                },
            }
        )

    if not items:
        items = [
            {
                "title": "No matching pane",
                "subtitle": f"Nothing matches “{query}”",
                "valid": False,
            }
        ]

    _emit(items)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback

        traceback.print_exc(file=sys.stderr)
        _emit([{"title": "Something went wrong", "subtitle": str(exc), "valid": False}])
