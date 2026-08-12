#!/usr/bin/env python3
"""Fetch DeepSeek shared conversations by link and save each as a JSON file.

DeepSeek's "导出所有历史对话" contains ALL conversations and the download page
cannot filter to selected ones. Every conversation can still be shared with a
separate link (links are valid about 7 days). This script fetches one or more
share links, converts each into the standard conversations.json format, and
stores them in one folder so the selected conversations can be merged and
organized together:

  python scripts/fetch_share.py <分享链接或share_id> [...] -o share_data
  python scripts/parse_deepseek.py share_data -o conversations.normalized.json

Usage:
  python fetch_share.py [链接或ID ...] [-o 输出文件夹]
  python fetch_share.py -i links.txt -o share_data
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

API = "https://chat.deepseek.com/api/v0/share/content"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://chat.deepseek.com/",
    "Accept": "application/json, text/plain, */*",
}
ROLE_MAP = {"USER": "user", "ASSISTANT": "assistant", "SYSTEM": "system", "TOOL": "tool"}


def share_id(text):
    m = re.search(r"share/([A-Za-z0-9_-]+)", text)
    if m:
        return m.group(1)
    text = text.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{6,}", text):
        return text
    return None


def fetch(share):
    url = f"{API}?share_id={share}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def make_conversation(share, raw):
    data = (raw.get("data") or {})
    biz = (data.get("biz_data") or {})
    msgs = biz.get("messages") or []
    role_map = lambda r: ROLE_MAP.get(r, str(r).lower())
    title = None
    for m in msgs:
        if role_map(m.get("role")) == "user" and (m.get("content") or "").strip():
            title = (m.get("content") or "").strip().replace("\n", " ")[:40]
            break
    title = (title or "DeepSeek 对话") + "（DeepSeek 分享对话）"
    return {
        "id": f"share-{share}",
        "title": title,
        "create_time": msgs[0].get("inserted_at") if msgs else None,
        "update_time": msgs[-1].get("inserted_at") if msgs else None,
        "messages": [
            {
                "id": str(m.get("message_id") or i),
                "role": role_map(m.get("role")),
                "content": m.get("content") or "",
                "create_time": m.get("inserted_at"),
                "files": m.get("files") or [],
            }
            for i, m in enumerate(msgs)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("links", nargs="*", help="分享链接或 share_id（可多个）")
    parser.add_argument("-i", "--input", default=None, help="文本文件，每行一个分享链接或 share_id")
    parser.add_argument("-o", "--outdir", default="share_data", help="输出文件夹（默认 share_data）")
    args = parser.parse_args()

    tokens = list(args.links)
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            sys.exit(f"输入文件不存在: {input_path}")
        tokens += [ln for ln in input_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not tokens:
        sys.exit("未提供分享链接；用法见脚本说明（python scripts/fetch_share.py <链接> [-o 文件夹]）")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, []
    for token in tokens:
        share = share_id(token)
        if not share:
            fail.append((token, "无法识别链接或 ID"))
            continue
        try:
            raw = fetch(share)
            if raw.get("code") != 0:
                fail.append((token, raw.get("msg") or raw.get("biz_msg") or f"接口返回 code={raw.get('code')}"))
                continue
            conv = make_conversation(share, raw)
            count = len(conv["messages"])
            if count == 0:
                fail.append((token, "未取到消息（分享链接可能已失效）"))
                continue
            out = outdir / f"{share}.json"
            out.write_text(json.dumps(conv, ensure_ascii=False, indent=2), encoding="utf-8")
            ok += 1
            print(f"OK  {share}  {count} 条消息  ->  {out}")
        except Exception as exc:  # noqa: BLE001
            fail.append((token, str(exc)))

    print(f"\n成功 {ok} 条，失败 {len(fail)} 条")
    for token, reason in fail:
        print(f"失败  {token}: {reason}")
    if fail:
        print("提示：分享链接有效期约 7 天，失效后需在 DeepSeek 重新生成分享链接。")
        sys.exit(1)


if __name__ == "__main__":
    main()
