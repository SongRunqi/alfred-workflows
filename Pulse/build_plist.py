#!/usr/bin/env python3
"""Generate info.plist for the Pulse workflow.

Pulse checks installed workflows against the repo's versions.json manifest
and hands updates to Alfred's own import flow.

Objects (4): `update` script filter → update.sh; Hyper+U hotkey → notify.sh.
Config: Configure Workflow… exposes the repo override (PULSE_REPO env).

    python3 build_plist.py     # writes info.plist next to this script
"""

import plistlib
import uuid
from pathlib import Path

HERE = Path(__file__).parent

HYPER = 1966080  # ⌃⌥⇧⌘ — Karabiner Hyper chord
KEYCODE_U = 32  # ANSI 'u'


def uid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"com.songyitian.pulse:{name}")).upper()


sf_uid = uid("filter")
update_uid = uid("update")
hk_uid = uid("hotkey")
notify_uid = uid("notify")
notif_uid = uid("notification")

objects = [
    # `update` script filter
    {
        "config": {
            "alfredfiltersresults": True,
            "alfredfiltersresultsmatchmode": 2,
            "argumenttreatemptyqueryasnil": True,
            "argumenttrimmode": 0,
            "argumenttype": 1,
            "escaping": 102,
            "keyword": "update",
            "queuedelaycustom": 3,
            "queuedelayimmediatelyinitially": True,
            "queuedelaymode": 0,
            "queuemode": 1,
            "runningsubtext": "检查更新…",
            "scriptargtype": 0,
            "scriptfile": "filter.sh",
            "subtext": "检查并更新已安装的工作流 · 回车更新 · ⌘回车仅下载",
            "text": "Pulse",
            "type": 8,
            "withspace": False,
        },
        "type": "alfred.workflow.input.scriptfilter",
        "uid": sf_uid,
        "version": 3,
    },
    # updater (item arg: name|url|sha256 | all | dl|…)
    {
        "config": {
            "concurrently": False,
            "escaping": 102,
            "script": "",
            "scriptargtype": 0,
            "scriptfile": "update.sh",
            "type": 8,
        },
        "type": "alfred.workflow.action.script",
        "uid": update_uid,
        "version": 2,
    },
    # Hyper+U → silent check + notification summary
    {
        "config": {
            "action": 0,
            "argument": 0,
            "focusedappvariable": False,
            "focusedappvariablename": "",
            "hotkey": KEYCODE_U,
            "hotmod": HYPER,
            "hotstring": "U",
            "leftcursor": False,
            "modsmode": 0,
            "relatedAppsMode": 0,
        },
        "type": "alfred.workflow.trigger.hotkey",
        "uid": hk_uid,
        "version": 2,
    },
    {
        "config": {
            "concurrently": False,
            "escaping": 102,
            "script": "",
            "scriptargtype": 0,
            "scriptfile": "notify.sh",
            "type": 8,
        },
        "type": "alfred.workflow.action.script",
        "uid": notify_uid,
        "version": 2,
    },
    # Alfred's own notification (script stdout → {query}); fed by both
    # the updater and the Hyper+U check, shown only when there is output.
    {
        "config": {
            "lastpathcomponent": False,
            "onlyshowifquerypopulated": True,
            "removeextension": False,
            "text": "{query}",
            "title": "Pulse",
        },
        "type": "alfred.workflow.output.notification",
        "uid": notif_uid,
        "version": 1,
    },
]


def edge(dest):
    return {
        "destinationuid": dest,
        "modifiers": 0,
        "modifiersubtext": "",
        "vitoclose": False,
    }


connections = {
    sf_uid: [edge(update_uid)],
    hk_uid: [edge(notify_uid)],
    update_uid: [edge(notif_uid)],
    notify_uid: [edge(notif_uid)],
}

uidata = {
    sf_uid: {"xpos": 40, "ypos": 40},
    update_uid: {"xpos": 280, "ypos": 40},
    hk_uid: {"xpos": 40, "ypos": 200},
    notify_uid: {"xpos": 280, "ypos": 200},
    notif_uid: {"xpos": 560, "ypos": 120},
}

README = """## Pulse

给 Alfred 工作流号脉：检查 `SongRunqi/alfred-workflows` 仓库里**已安装**的
工作流是否有新版本，有就下载、校验并交给 Alfred 导入替换。

### 用法

| 操作 | 效果 |
| --- | --- |
| `update` | 检查并列出：可更新 / 已最新 |
| 回车 | 下载 → sha256 校验 → 交给 Alfred 确认替换 |
| ⌘回车 | 仅下载，不导入 |
| `全部更新` | 逐个下载并交给 Alfred 确认 |
| Hyper+U | 静默检查 → 通知摘要（几个可更新 / 全部最新） |

### 规则

- **只检查已安装的工作流**（本机按 bundle id 扫描 ∩ 仓库清单）。
  未安装的不会出现——更新是更新，搜索是搜索。
- 安装走 Alfred 官方导入流程：每次更新需在 Alfred 弹窗点一次「替换」，
  用户配置（prefs.plist）由 Alfred 保留。
- 版本比较支持 `v1.2.3`、`1.10` 等常见格式（数字段数值比较）。

### 配置

- Configure Workflow… 里的 **PULSE_REPO**（默认 `SongRunqi/alfred-workflows`）
  和 PULSE_BRANCH 可指向其他仓库——Pulse 的清单机制是通用的，
  其他仓库只要提供同格式的 `versions.json` 即可。
- 数据文件（Workflow Data）：`cache.json`（上次检查结果）、
  `downloads/`（下载的安装包）。

### 发布侧

仓库 `scripts/package-all.sh` 打包后自动生成根目录 `versions.json`
（name / bundleid / version / sha256 / url），随提交进 main；
Pulse 更新时先更新自己：新版发布后 `update` 里同样会出现 Pulse 条目。
"""

plist = {
    "bundleid": "com.songyitian.pulse",
    "name": "Pulse",
    "description": "给工作流号脉：检查并更新已安装的 Alfred workflows",
    "createdby": "Songyitian",
    "webaddress": "",
    "version": "1.0.0",
    "category": "Tools",
    "disabled": False,
    "readme": README,
    "variables": {},
    "variablesdontexport": [],
    "userconfigurationconfig": [
        {
            "type": "textfield",
            "variable": "PULSE_REPO",
            "label": "仓库 (owner/repo)",
            "description": "versions.json 所在仓库，默认 SongRunqi/alfred-workflows",
            "config": {
                "default": "",
                "placeholder": "SongRunqi/alfred-workflows",
                "required": False,
                "trim": True,
            },
        },
        {
            "type": "textfield",
            "variable": "PULSE_BRANCH",
            "label": "分支",
            "description": "默认 main",
            "config": {
                "default": "",
                "placeholder": "main",
                "required": False,
                "trim": True,
            },
        },
    ],
    "objects": objects,
    "connections": connections,
    "uidata": uidata,
}

out = HERE / "info.plist"
out.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_XML))
print(f"wrote {out} ({len(objects)} objects)")
