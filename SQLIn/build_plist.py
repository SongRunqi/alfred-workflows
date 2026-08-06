#!/usr/bin/env python3
"""Generate info.plist for the SQL In workflow.

Selected / copied IDs → SQL `IN (...)` clause. Two triggers, one pipeline:

- `in` keyword: reads the clipboard, or uses `in 1,2,3` as typed
- Universal Action (Text Action): selected text in any app → ⌘/ → "SQL In"

Both feed sql_in.py → notification; the clause is copied back to the
clipboard.

Objects (4): keyword + universal action → sql_in.py → notification.

    python3 build_plist.py     # writes info.plist next to this script
"""

import plistlib
import uuid
from pathlib import Path

HERE = Path(__file__).parent


def uid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"com.songyitian.sqlin:{name}")).upper()


kw_uid = uid("keyword")
act_uid = uid("universalaction")
run_uid = uid("run")
notif_uid = uid("notification")

objects = [
    # `in` keyword — optional argument: empty → read clipboard
    {
        "config": {
            "argumenttype": 1,
            "keyword": "in",
            "subtext": "剪贴板里的 ID 生成 SQL IN 子句 · 可跟参数如 in 1,2,3",
            "text": "SQL In",
            "withspace": False,
        },
        "type": "alfred.workflow.input.keyword",
        "uid": kw_uid,
        "version": 1,
    },
    # Universal Action (Text Action): selected text in any app
    {
        "config": {
            "acceptsfiles": False,
            "acceptsmulti": False,
            "acceptstext": True,
            "acceptsurls": False,
            "name": "SQL In",
        },
        "type": "alfred.workflow.trigger.universalaction",
        "uid": act_uid,
        "version": 1,
    },
    # generator: query (or clipboard) → IN (...) → pbcopy + stdout summary
    {
        "config": {
            "concurrently": False,
            "escaping": 102,
            "script": "",
            "scriptargtype": 0,
            "scriptfile": "sql_in.py",
            "type": 8,
        },
        "type": "alfred.workflow.action.script",
        "uid": run_uid,
        "version": 2,
    },
    # Alfred's own notification (script stdout → {query})
    {
        "config": {
            "lastpathcomponent": False,
            "onlyshowifquerypopulated": True,
            "removeextension": False,
            "text": "{query}",
            "title": "SQL In",
        },
        "type": "alfred.workflow.output.notification",
        "uid": notif_uid,
        "version": 1,
    },
]


def edge(dest, vitoclose=False):
    return {
        "destinationuid": dest,
        "modifiers": 0,
        "modifiersubtext": "",
        "vitoclose": vitoclose,
    }


connections = {
    kw_uid: [edge(run_uid)],
    act_uid: [edge(run_uid)],
    run_uid: [edge(notif_uid)],
}

uidata = {
    kw_uid: {"xpos": 40, "ypos": 40},
    act_uid: {"xpos": 40, "ypos": 200},
    run_uid: {"xpos": 280, "ypos": 120},
    notif_uid: {"xpos": 560, "ypos": 120},
}

README = """## SQL In

把选中的文本 / 剪贴板（或关键词后直接粘贴）里的一堆 ID 变成 SQL `IN (...)` 子句，
自动复制回剪贴板，方便粘贴进查询语句。

### 用法

| 操作 | 效果 |
| --- | --- |
| 选中 ID 文本 → ⌘/ → 选 **SQL In** | 选中的文本 → 生成 `IN (…)` → 复制回剪贴板 + 通知 |
| 复制 ID 后输入 `in` | 读取剪贴板 → 生成 `IN (…)` → 复制回剪贴板 + 通知 |
| `in 1 2 3` / `in 1,2,3` | 直接使用输入的 ID（优先于剪贴板） |

**Text Action（推荐）**：在任意应用里选中 ID（Excel、网页、SQL 编辑器都行），
按 Universal Actions 热键（默认 ⌘/）→ 选 SQL In 即生成，不需要切到 Alfred。
若热键无效，先到 Alfred → Features → Universal Actions 里确认设置。

ID 之间的分隔符随意：空格、换行、逗号、分号、制表符都行。
重复 ID 自动去重，顺序保留。

### 自动识别类型

- 全部是纯数字 → `IN (1, 2, 3)`（不加引号）
- 含有非数字（如 `ord123`、`uuid`）→ 全部加单引号 `IN ('a', 'b')`
  （字符串里的单引号自动转义为 `''`）
- 从 SQL 里复制出来的带引号 ID 会先剥掉引号再处理

### 自定义

想换关键词：Alfred → Workflows → SQL In → 双击 Keyword 对象改 `in` 即可。
"""

plist = {
    "bundleid": "com.songyitian.sqlin",
    "name": "SQL In",
    "description": "选中的文本 / 剪贴板里的 ID 列表 → SQL IN 子句",
    "createdby": "Songyitian",
    "webaddress": "",
    "version": "1.1.0",
    "category": "Tools",
    "disabled": False,
    "readme": README,
    "variables": {},
    "variablesdontexport": [],
    "userconfigurationconfig": [],
    "objects": objects,
    "connections": connections,
    "uidata": uidata,
}

out = HERE / "info.plist"
out.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_XML))
print(f"wrote {out} ({len(objects)} objects)")
