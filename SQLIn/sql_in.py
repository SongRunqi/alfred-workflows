#!/usr/bin/env python3
"""SQL In — 把一堆 ID 变成 SQL IN 子句，复制回剪贴板。

数据来源（优先级）：argv[1]（关键词后输入的内容）> 剪贴板。
分隔符：空格 / 换行 / 逗号 / 分号 / 制表符，混用都行。
自动类型：全是纯数字 → IN (1, 2, 3)；否则全部加单引号 IN ('a', 'b')。

    python3 sql_in.py "1 2 3"          # → IN (1, 2, 3)
    python3 sql_in.py "a b"            # → IN ('a', 'b')
    python3 sql_in.py                  # 读剪贴板
"""

import re
import subprocess
import sys

# 分隔符：空白、中英文逗号、中英文分号、顿号
SPLIT_RE = re.compile(r"[\s,，;；、]+")
# 纯数字：可选正负号，至少一位
NUM_RE = re.compile(r"[+-]?\d+$")
# 自动剥掉从 SQL 复制出来的外层引号（单/双/反引号）
QUOTE_STRIP = re.compile(r"^(['\"`])(.*)\1$")


def read_clipboard() -> str:
    try:
        out = subprocess.run(["pbpaste"], capture_output=True, check=True, timeout=5)
        return out.stdout.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 — any failure → treat as empty
        print(f"读取剪贴板失败：{e}")
        return ""


def write_clipboard(text: str) -> None:
    try:
        subprocess.run(
            ["pbcopy"],
            input=text.encode("utf-8"),
            check=True,
            timeout=5,
        )
    except Exception as e:  # noqa: BLE001
        print(f"写入剪贴板失败：{e}")


def parse_ids(raw: str) -> list[str]:
    """拆分成 ID 列表：去空、剥外层引号、按序去重。"""
    seen: set[str] = set()
    ids: list[str] = []
    for part in SPLIT_RE.split(raw.strip()):
        m = QUOTE_STRIP.match(part)
        if m:
            part = m.group(2)
        if not part:
            continue
        if part not in seen:
            seen.add(part)
            ids.append(part)
    return ids


def build_in_clause(ids: list[str]) -> str:
    """全部纯数字 → 不加引号；否则全部单引号（内部 ' 转义为 ''）。"""
    if all(NUM_RE.match(i) for i in ids):
        body = ", ".join(ids)
    else:
        body = ", ".join("'" + i.replace("'", "''") + "'" for i in ids)
    return f"IN ({body})"


def main() -> int:
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    raw = query if query else read_clipboard()
    if not raw.strip():
        print("没有找到 ID：先复制 ID，或直接输入 `in 1 2 3`")
        return 1

    ids = parse_ids(raw)
    if not ids:
        print("没有找到 ID：剪贴板/输入内容里没有可用的 ID")
        return 1

    clause = build_in_clause(ids)
    write_clipboard(clause)

    # 通知里预览：太长截断
    preview = clause if len(clause) <= 80 else clause[:77] + "…"
    source = "输入" if query else "剪贴板"
    print(f"已复制（{source}，{len(ids)} 个 ID）：{preview}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
