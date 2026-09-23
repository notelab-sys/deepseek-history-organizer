#!/usr/bin/env python3
"""Search and filter conversations locally by keywords.

The full DeepSeek export contains every conversation; instead of manually
searching in the web page (which cannot open several conversations at once),
parse the export once and search it locally here. Matching conversations can
then be exported as a subset and analyzed one by one.

Usage:
python search_conversations.py <conversations.normalized.json> --keywords "代谢,调控"
  python search_conversations.py <conversations.normalized.json> --keywords "Turing" --export selected.json
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path


def fmt_ts(value):
    if not value:
        return "未知时间"
    return dt.datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")


def conv_text(c):
    parts = [c.get("title") or ""]
    for m in c.get("messages", []):
        parts.append(m.get("content") or "")
        for a in m.get("attachments") or []:
            parts.append(a.get("name") or "")
    return "\n".join(parts)


def search(conversations, keywords, match_all=False):
    kw = [k.strip().lower() for k in keywords if k.strip()]
    results = []
    for c in conversations:
        text = conv_text(c)
        low = text.lower()
        if not kw:
            continue
        hits = []
        present = []
        for k in kw:
            if k in low:
                present.append(k)
                pos = 0
                while True:
                    idx = low.find(k, pos)
                    if idx == -1:
                        break
                    s = max(0, idx - 30)
                    e = min(len(text), idx + len(k) + 50)
                    snippet = text[s:e].replace("\n", " ").strip()
                    hits.append(snippet)
                    pos = idx + len(k)
        if present and (len(present) == len(kw) if match_all else True):
            results.append((c, hits))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="归一化对话 JSON（parse_deepseek.py 的输出，可含全部对话）")
    parser.add_argument("--keywords", default="", help="关键词，逗号分隔（多个关键词时命中的对话都列出）")
    parser.add_argument("--date-from", default="", help="可选：起始日期 YYYY-MM-DD")
    parser.add_argument("--date-to", default="", help="可选：结束日期 YYYY-MM-DD")
    parser.add_argument("--match", choices=["any", "all"], default="any", help="多关键词匹配方式：any=任一命中，all=全部命中（默认 any）")
    parser.add_argument("--export", default=None, help="可选：把命中的对话导出为子集 JSON，供后续步骤直接使用")
    parser.add_argument("--all", action="store_true", help="不按关键词过滤，列出全部对话")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"输入文件不存在: {input_path}")
    with open(input_path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    conversations = data.get("conversations") if isinstance(data, dict) else data
    if not isinstance(conversations, list):
        sys.exit("输入 JSON 格式不正确，请先运行 parse_deepseek.py")

    keywords = [k for k in args.keywords.replace("，", ",").split(",") if k.strip()]
    if args.all or not keywords:
        results = [(c, []) for c in conversations]
        if not args.all:
            print("未提供 --keywords，列出全部对话（可用 --keywords 关键词过滤）")
    else:
        results = search(conversations, keywords, args.match == "all")

    if args.date_from or args.date_to:
        filtered = []
        for c, hits in results:
            d = fmt_ts(c.get("create_time"))[:10]
            if d == "未知时间":
                continue
            if args.date_from and d < args.date_from:
                continue
            if args.date_to and d > args.date_to:
                continue
            filtered.append((c, hits))
        results = filtered

    print(f"共 {len(conversations)} 段对话，命中 {len(results)} 段")
    for i, (c, hits) in enumerate(results, 1):
        print(f"\n[{i}] {fmt_ts(c.get('create_time'))}  {c.get('title')}")
        print(f"    消息数 {len(c.get('messages', []))}   对话id {c.get('id')}")
        if hits:
            seen = set()
            shown = 0
            for s in hits:
                key = s[:40]
                if key in seen:
                    continue
                seen.add(key)
                print(f"    · {s[:90]}")
                shown += 1
                if shown >= 3:
                    break

    if args.export:
        selected = [c for c, _ in results]
        out = Path(args.export)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"conversations": selected}, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"\n已导出命中对话: {out}（{len(selected)} 段）")


if __name__ == "__main__":
    main()
