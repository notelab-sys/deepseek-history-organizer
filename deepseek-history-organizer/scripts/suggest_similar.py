#!/usr/bin/env python3
"""Suggest which conversations may share a similar topic (for merge decisions).

Compares conversations by token overlap (English words + Chinese bigrams) of
their titles, summaries and user messages, then lists pairs above a threshold.
This is only a hint: whether to merge (相近主题可合并) or analyze separately is
decided by the user.

Usage:
  python suggest_similar.py <conversations.normalized.json> [--summaries summaries.json] [--min-score 0.3] [-o report.md]
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

STOP_EN = {"the", "and", "of", "in", "on", "for", "with", "from", "to", "a", "an",
           "via", "by", "at", "its", "their", "his", "her", "this", "that", "are",
           "is", "was", "were", "be", "been", "not", "or", "as", "but", "deepseek",
           "share", "chat", "对话", "分享", "记录", "请", "如何", "哪些", "什么",
           "进行", "分析", "归纳", "整理", "相关", "可以", "需要", "主要", "提供"}


def fmt_date(value):
    if not value:
        return "未知时间"
    return dt.datetime.fromtimestamp(value).strftime("%Y-%m-%d")


def tokens_of(text):
    text = (text or "").lower()
    en = {w for w in re.findall(r"[a-z][a-z0-9'\-]{2,}", text) if w not in STOP_EN}
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    zh = set()
    for i in range(len(cjk) - 1):
        bigram = cjk[i] + cjk[i + 1]
        if bigram not in STOP_EN:
            zh.add(bigram)
    return en | zh


def conv_text(c, summaries):
    title = re.sub(r"（DeepSeek\s*分享对话）", "", c.get("title") or "")
    parts = [title, summaries.get(c.get("id")) or ""]
    for m in c.get("messages", []):
        parts.append((m.get("content") or "")[:500])
    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="归一化对话 JSON")
    parser.add_argument("--summaries", default=None, help="可选：summaries.json")
    parser.add_argument("--min-score", type=float, default=0.3, help="相似度阈值（默认 0.3）")
    parser.add_argument("-o", "--output", default=None, help="可选：输出报告 Markdown")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"输入文件不存在: {input_path}")
    with open(input_path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    convs = data.get("conversations") if isinstance(data, dict) else data
    if not isinstance(convs, list):
        sys.exit("输入 JSON 格式不正确，请先运行 parse_deepseek.py")

    summaries = {}
    if args.summaries:
        with open(args.summaries, encoding="utf-8-sig") as fh:
            summaries = json.load(fh)

    toks = {c.get("id"): tokens_of(conv_text(c, summaries)) for c in convs}
    ids = [c.get("id") for c in convs]
    pairs = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = toks[ids[i]], toks[ids[j]]
            if not a or not b:
                continue
            inter = a & b
            # 重叠系数：共同词 / 较小对话的词数，避免长对话稀释相似度
            score = len(inter) / min(len(a), len(b))
            if score >= args.min_score:
                shared = sorted(inter, key=len, reverse=True)[:8]
                pairs.append((score, ids[i], ids[j], shared))
    pairs.sort(key=lambda x: -x[0])
    by_id = {c.get("id"): c for c in convs}

    print(f"共 {len(convs)} 段对话，相似度 ≥ {args.min_score} 的对：{len(pairs)} 组")
    lines = ["# 主题相近提示（供合并决策参考）", "",
             f"> 基于标题/摘要/用户提问的字词重合度；仅作提示，是否合并由用户确认。", ""]
    if not pairs:
        lines.append("未发现相似度达到阈值的对话对。")
    for score, ida, idb, shared in pairs:
        a, b = by_id[ida], by_id[idb]
        print(f"  {score:.2f}  {fmt_date(a.get('create_time'))} {a.get('title')[:20]}  <->  "
              f"{fmt_date(b.get('create_time'))} {b.get('title')[:20]}")
        lines.append(f"- 相似度 **{score:.2f}**：{fmt_date(a.get('create_time'))}《{a.get('title')}》"
                     f" ↔ {fmt_date(b.get('create_time'))}《{b.get('title')}》")
        lines.append(f"  - 共同关键词：{'、'.join(shared) if shared else '（无显著共同词）'}")
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
        print(f"已生成: {out}")


if __name__ == "__main__":
    main()
