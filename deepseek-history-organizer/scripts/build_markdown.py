#!/usr/bin/env python3
"""Build Markdown digests from normalized conversations.

Creates index.md (catalog table) plus one Markdown file per conversation.

Usage:
  python build_markdown.py <conversations.json> [--summaries summaries.json] [-o outdir]
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path


ROLE_NAMES = {"user": "我", "assistant": "DeepSeek", "system": "系统", "tool": "工具"}


def fmt_ts(value):
    if not value:
        return "未知时间"
    return dt.datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")


def slugify(text):
    s = re.sub(r'[\\/:*?"<>|\s]+', "-", text).strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:60] or "untitled"


def build(conversations, summaries, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    summaries = summaries or {}
    convs = sorted(conversations, key=lambda c: c.get("create_time") or 0, reverse=True)
    rows = []
    for i, c in enumerate(convs, 1):
        date = fmt_ts(c.get("create_time"))
        title = c.get("title", "未命名对话")
        fname = f"{i:04d}-{slugify(date[:10] + ' ' + title)}"
        fpath = outdir / (fname + ".md")
        attachments = []
        for m in c.get("messages", []):
            attachments.extend(m.get("attachments") or [])
        lines = [
            f"# {title}",
            "",
            f"- 时间：{date}",
            f"- 消息数：{c.get('message_count', len(c.get('messages', [])))}",
            f"- 附件数：{len(attachments)}",
        ]
        summary = summaries.get(c.get("id"))
        if summary:
            lines.append(f"- 摘要：{summary}")
        lines.append("")
        for m in c.get("messages", []):
            role = ROLE_NAMES.get(m.get("role"), m.get("role", "unknown"))
            lines.append(f"**{role}**：{m.get('content', '')}")
            lines.append("")
        if attachments:
            lines.append("## 附件")
            lines.append("")
            for a in attachments:
                name = a.get("name") or ("图片" if a.get("type") == "image" else "附件")
                url = a.get("url") or ""
                if a.get("type") == "image" and url:
                    lines.append(f"![{name}]({url})")
                elif url:
                    lines.append(f"- [{name}]({url})")
                else:
                    lines.append(f"- {name}")
            lines.append("")
        fpath.write_text("\n".join(lines), encoding="utf-8-sig")
        rows.append((date, title, len(c.get("messages", [])), summary or "", f"[{fname}.md]({fname}.md)"))

    index = ["# 对话目录", "", "| 时间 | 标题 | 消息数 | 摘要 | 文件 |", "| --- | --- | --- | --- | --- |"]
    for date, title, count, summary, link in rows:
        safe_title = title.replace("|", "\\|")
        safe_summary = summary.replace("|", "\\|")
        index.append(f"| {date} | {safe_title} | {count} | {safe_summary} | {link} |")
    (outdir / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8-sig")
    print(f"已生成目录: {outdir / 'index.md'}")
    print(f"已生成 {len(rows)} 个对话文件: {outdir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="归一化对话 JSON（parse_deepseek.py 的输出）")
    parser.add_argument("--summaries", default=None, help="可选：summaries.json（对话 id → 一句话摘要）")
    parser.add_argument("-o", "--output", default="digests", help="输出目录（默认 digests）")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"输入文件不存在: {input_path}")
    with open(input_path, encoding="utf-8") as fh:
        data = json.load(fh)
    conversations = data.get("conversations") if isinstance(data, dict) else data
    if not isinstance(conversations, list):
        sys.exit("输入 JSON 格式不正确，请先运行 parse_deepseek.py")

    summaries = {}
    if args.summaries:
        with open(args.summaries, encoding="utf-8") as fh:
            summaries = json.load(fh)

    build(conversations, summaries, args.output)


if __name__ == "__main__":
    main()
