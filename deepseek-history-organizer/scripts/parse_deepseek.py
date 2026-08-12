#!/usr/bin/env python3
"""Parse DeepSeek exported chat data into a normalized JSON file.

Input may be:
  - a .zip archive from DeepSeek "导出所有历史对话"
  - a JSON file (conversations.json, conversation.json, or a single conversation)
  - a directory containing such JSON files

Usage:
  python parse_deepseek.py <input> [-o output.json]
"""

import argparse
import datetime as dt
import json
import random
import shutil
import string
import sys
import zipfile
from pathlib import Path


def find_json_files(source):
    """Return (tempdir_or_None, list_of_json_paths)."""
    if source.is_dir():
        return None, sorted(p for p in source.rglob("*.json"))
    if source.suffix.lower() == ".zip":
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        tmp = source.parent / f"{source.stem}_extracted_{suffix}"
        tmp.mkdir()
        with zipfile.ZipFile(source) as zf:
            zf.extractall(tmp)
        return tmp, sorted(tmp.rglob("*.json"))
    return None, [source]


def load_data(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def extract_conversations(data):
    """Yield conversation dicts from a parsed JSON document."""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(data, dict):
        return
    if "conversations" in data and isinstance(data["conversations"], list):
        for item in data["conversations"]:
            if isinstance(item, dict):
                yield item
        return
    if "mapping" in data or "messages" in data or "title" in data:
        yield data
        return
    # Unrecognized wrapper: scan values for lists of conversation-like dicts.
    for value in data.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and ("mapping" in item or "messages" in item or "title" in item):
                    yield item


def normalize_time(value):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value > 1e12:  # milliseconds -> seconds
        value /= 1000.0
    return value


def extract_text(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        for key in ("text", "content", "value"):
            if isinstance(content.get(key), str):
                return content[key]
        return json.dumps(content, ensure_ascii=False)
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = extract_text(part.get("text")) or extract_text(part.get("content"))
                if text:
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


def extract_attachments(content):
    """Extract image/file attachment metadata from message content parts."""
    if not isinstance(content, list):
        return []
    attachments = []
    seen = set()

    def push(item):
        key = (item["type"], item["url"], item["name"])
        if key not in seen:
            seen.add(key)
            attachments.append(item)

    for part in content:
        if not isinstance(part, dict):
            continue
        ptype = str(part.get("type", "")).lower()
        if ptype in ("image", "image_url"):
            src = part.get("image") or part.get("image_url") or {}
            if isinstance(src, dict):
                url = src.get("url") or src.get("data") or ""
            else:
                url = src if isinstance(src, str) else ""
            if url:
                push({"type": "image", "name": part.get("name") or "", "url": url})
        elif ptype == "files":
            files = part.get("files")
            if isinstance(files, list):
                for f in files:
                    if isinstance(f, dict):
                        url = f.get("url") or f.get("data") or ""
                        if url or f.get("name"):
                            push({"type": "file", "name": f.get("name") or "", "url": url})
        elif ptype in ("file", "attachment", "upload"):
            src = part.get("file") or part.get("attachment") or part
            if isinstance(src, dict):
                name = src.get("name") or part.get("name") or part.get("file_name") or ""
                url = src.get("url") or part.get("url") or src.get("data") or part.get("data") or ""
            else:
                name = part.get("name") or part.get("file_name") or ""
                url = src if isinstance(src, str) else ""
            if url or name:
                push({"type": "file", "name": name, "url": url})
    return attachments


def normalize_message(item):
    msg = item
    if isinstance(item, dict) and isinstance(item.get("message"), dict):
        msg = item["message"]
    role = msg.get("role", "unknown")
    content = extract_text(msg.get("content"))
    attachments = extract_attachments(msg.get("content"))
    created = normalize_time(
        msg.get("create_time") or msg.get("createTime") or msg.get("timestamp") or msg.get("created_at")
    )
    mid = msg.get("id") or msg.get("uuid") or ""
    return {"id": mid, "role": role, "content": content, "create_time": created, "attachments": attachments}


def flatten_mapping(mapping):
    """Flatten a DeepSeek mapping tree into messages in conversation order."""
    if not isinstance(mapping, dict):
        return []
    nodes = [n for n in mapping.values() if isinstance(n, dict)]
    node_by_id = {str(n.get("id")): n for n in nodes}
    children = {}
    for node in nodes:
        parent = node.get("parent")
        if parent is not None:
            children.setdefault(str(parent), []).append(node)

    ordered = []
    visited = set()

    def walk(node):
        key = str(node.get("id"))
        if key in visited:
            return
        visited.add(key)
        msg = node.get("message")
        if isinstance(msg, dict) and msg.get("content") is not None:
            ordered.append(msg)
        for child in children.get(key, []):
            walk(child)

    roots = [n for n in nodes if n.get("parent") is None or str(n.get("parent")) not in node_by_id]
    for root in roots or nodes:
        walk(root)
    if not ordered:
        ordered = [n["message"] for n in nodes if isinstance(n.get("message"), dict)]
        ordered.sort(key=lambda m: normalize_time(m.get("create_time")) or 0)
    return ordered


def normalize_conversation(conv, index):
    cid = conv.get("id") or conv.get("conversation_id") or conv.get("uuid") or f"conv-{index + 1}"
    title = (conv.get("title") or "").strip() or "未命名对话"
    create_time = normalize_time(conv.get("create_time") or conv.get("createTime") or conv.get("created_at"))
    update_time = normalize_time(conv.get("update_time") or conv.get("updateTime") or conv.get("updated_at"))

    raw_messages = []
    mapping = conv.get("mapping")
    if isinstance(mapping, dict):
        raw_messages = flatten_mapping(mapping)
    elif isinstance(conv.get("messages"), list):
        raw_messages = conv["messages"]
    elif isinstance(conv.get("message_list"), list):
        raw_messages = conv["message_list"]

    messages = [normalize_message(m) for m in raw_messages]
    messages = [m for m in messages if m["content"].strip()]

    times = [m["create_time"] for m in messages if m["create_time"]]
    if create_time is None and times:
        create_time = min(times)
    if update_time is None and times:
        update_time = max(times)

    attachments = []
    for m in messages:
        attachments.extend(m.get("attachments") or [])

    return {
        "id": cid,
        "title": title,
        "create_time": create_time,
        "update_time": update_time,
        "message_count": len(messages),
        "char_count": sum(len(m["content"]) for m in messages),
        "attachments_count": len(attachments),
        "messages": messages,
    }


def format_time(value):
    if not value:
        return "未知时间"
    return dt.datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="DeepSeek 导出 zip、JSON 文件或文件夹路径")
    parser.add_argument("-o", "--output", default=None, help="输出归一化 JSON 路径")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"输入路径不存在: {input_path}")

    tmpdir, json_files = find_json_files(input_path)
    if not json_files:
        sys.exit("未找到任何 JSON 文件")

    conversations = []
    errors = []
    for jf in json_files:
        try:
            data = load_data(jf)
            for conv in extract_conversations(data):
                conversations.append(normalize_conversation(conv, len(conversations)))
        except Exception as exc:  # noqa: BLE001 - report and continue
            errors.append(f"{jf.name}: {exc}")

    if tmpdir is not None:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if not conversations:
        detail = "\n".join(errors) if errors else ""
        sys.exit("未能从输入中解析出任何对话" + (f"\n错误:\n{detail}" if detail else ""))

    conversations.sort(key=lambda c: (c["create_time"] is None, c["create_time"] or 0))

    output = Path(args.output) if args.output else input_path.parent / "conversations.normalized.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "source": str(input_path),
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "conversations": conversations,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    total_msgs = sum(c["message_count"] for c in conversations)
    dates = [c["create_time"] for c in conversations if c["create_time"]]
    date_range = f"{format_time(min(dates))} ~ {format_time(max(dates))}" if dates else "未知"
    print(f"对话总数: {len(conversations)}")
    print(f"消息总数: {total_msgs}")
    print(f"时间范围: {date_range}")
    if errors:
        print(f"跳过文件: {len(errors)} 个")
        for err in errors:
            print(f"  - {err}")
    print(f"已保存: {output}")


if __name__ == "__main__":
    main()
