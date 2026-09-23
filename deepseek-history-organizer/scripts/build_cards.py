#!/usr/bin/env python3
"""Build quick-view cards and a folder registry (登记表) for conversation digests.

Subcommand: cards
  Reads normalized conversations and writes:
    - 速览卡片.md  — one card per conversation (编号/日期/主题/摘要/消息数/
                     首条提问/关键词/关键要点/待办占位)
    - 登记表.md    — catalog table (编号 | 日期 | 主题 | 消息数 | 摘要)
  Usage:
    python build_cards.py cards conversations.normalized.json [--summaries summaries.json] [-o outdir]

Subcommand: catalog
  Scans an output folder whose files are named 0001-日期-主题.md/.docx and
  writes 登记表.md (编号 | 日期 | 主题 | MD | Word | 状态).
  Usage:
    python build_cards.py catalog <输出文件夹> [-o 登记表.md]
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def fmt_ts(value):
    if not value:
        return "未知时间"
    return dt.datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")


def date_only(value):
    return fmt_ts(value)[:10]


def first_user_question(conv):
    for m in conv.get("messages", []):
        if m.get("role") == "user" and (m.get("content") or "").strip():
            return (m.get("content") or "").strip().replace("\n", " ")[:80]
    return ""


def keywords_of(title, question, limit=8):
    text = f"{title} {question}"
    en = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text)
    out = []
    for w in en:
        if w.lower() not in {t.lower() for t in out}:
            out.append(w)
    return out[:limit]


def attachments_count(conv):
    return sum(len(m.get("attachments") or []) for m in conv.get("messages", []))


def load_conversations(path):
    with open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    convs = data.get("conversations") if isinstance(data, dict) else data
    if not isinstance(convs, list):
        sys.exit("输入 JSON 格式不正确，请先运行 parse_deepseek.py")
    return convs


def build_cards(conversations, summaries, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    summaries = summaries or {}
    convs = sorted(conversations, key=lambda c: c.get("create_time") or 0)
    cards = ["# 对话速览卡片", "", "> 每段对话一张卡片；关键要点与待办/灵感由归纳时填写。", ""]
    rows = ["| 编号 | 日期 | 主题 | 消息数 | 附件 | 摘要 |", "| --- | --- | --- | --- | --- | --- |"]
    for i, c in enumerate(convs, 1):
        num = f"{i:04d}"
        date = date_only(c.get("create_time"))
        title = c.get("title") or "未命名对话"
        question = first_user_question(c)
        summary = summaries.get(c.get("id")) or "（待补充）"
        n_msgs = len(c.get("messages", []))
        n_att = attachments_count(c)
        kws = ", ".join(keywords_of(title, question)) or "—"
        cards.append(f"## {num}　{title}")
        cards.append("")
        cards.append(f"- 日期：{date}")
        cards.append(f"- 消息数：{n_msgs}　|　附件数：{n_att}　|　对话 id：{c.get('id')}")
        cards.append(f"- 一句话摘要：{summary}")
        cards.append(f"- 首条提问：{question or '—'}")
        cards.append(f"- 关键词：{kws}")
        cards.append(f"- 关键要点：（归纳时填写）")
        cards.append(f"- 待办 / 灵感：（归纳时填写）")
        cards.append("")
        rows.append(f"| {num} | {date} | {title.replace('|', '\\\\|')} | {n_msgs} | {n_att} | {summary.replace('|', '\\\\|')} |")
    (outdir / "速览卡片.md").write_text("\n".join(cards), encoding="utf-8-sig")
    (outdir / "登记表.md").write_text("# 对话登记表\n\n" + "\n".join(rows) + "\n", encoding="utf-8-sig")
    print(f"已生成: {outdir / '速览卡片.md'}")
    print(f"已生成: {outdir / '登记表.md'}（{len(convs)} 段对话）")


NAME_RE = re.compile(r"^(\d{4})[-–](\d{4}-\d{2}-\d{2})[-–](.+)$")


def build_catalog(folder, output):
    folder = Path(folder)
    files = sorted(folder.iterdir()) if folder.is_dir() else []
    entries = {}
    other = []
    for f in files:
        if not f.is_file():
            continue
        stem = f.stem
        m = NAME_RE.match(stem)
        if m:
            num, date, topic = m.group(1), m.group(2), m.group(3)
            entry = entries.setdefault(num, {"date": date, "topic": topic, "md": "", "docx": ""})
            if f.suffix.lower() == ".md":
                entry["md"] = f.name
            elif f.suffix.lower() == ".docx":
                entry["docx"] = f.name
        else:
            other.append(f.name)
    lines = ["# 文件夹登记表", "", f"> 文件夹：{folder}", f"> 登记 {len(entries)} 份文档（按编号排列）", "",
             "| 编号 | 日期 | 主题 | MD | Word |", "| --- | --- | --- | --- | --- |"]
    for num in sorted(entries):
        e = entries[num]
        md = f"[{e['md']}]({e['md']})" if e["md"] else "—"
        docx = f"[{e['docx']}]({e['docx']})" if e["docx"] else "—"
        lines.append(f"| {num} | {e['date']} | {e['topic'].replace('|', '\\\\|')} | {md} | {docx} |")
    if other:
        lines.append("")
        lines.append("### 未按编号命名（未登记）")
        for n in other:
            lines.append(f"- {n}")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"已生成: {output}（{len(entries)} 条登记）")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("cards", help="从归一化对话生成速览卡片与登记表")
    p1.add_argument("input", help="conversations.normalized.json")
    p1.add_argument("--summaries", default=None, help="可选：summaries.json")
    p1.add_argument("-o", "--output", default=".", help="输出目录（默认当前目录）")
    p2 = sub.add_parser("catalog", help="扫描编号文档文件夹生成登记表")
    p2.add_argument("folder", help="包含 0001-日期-主题.md/.docx 的文件夹")
    p2.add_argument("-o", "--output", default="登记表.md", help="输出登记表路径（默认 登记表.md）")
    args = parser.parse_args()

    if args.cmd == "cards":
        summaries = {}
        if args.summaries:
            with open(args.summaries, encoding="utf-8-sig") as fh:
                summaries = json.load(fh)
        build_cards(load_conversations(args.input), summaries, args.output)
    else:
        build_catalog(args.folder, args.output)


if __name__ == "__main__":
    main()
