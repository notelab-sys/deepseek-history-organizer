#!/usr/bin/env python3
"""Build a self-contained, searchable HTML viewer from normalized conversations.

Usage:
  python build_html.py <conversations.json> [--summaries summaries.json] [-o index.html] [--title "标题"]
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


def fmt_ts(value):
    if not value:
        return "未知时间"
    return dt.datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; background: #f6f7f9; color: #1f2328; }
.app { display: flex; height: 100vh; }
.sidebar { width: 370px; min-width: 260px; background: #fff; border-right: 1px solid #e3e6ea; display: flex; flex-direction: column; }
.sidebar-header { padding: 16px 16px 12px; border-bottom: 1px solid #f0f2f5; }
.sidebar-header h1 { font-size: 17px; margin-bottom: 10px; }
#search { width: 100%; padding: 9px 12px; border: 1px solid #d0d7de; border-radius: 8px; font-size: 14px; outline: none; }
#search:focus { border-color: #1f6feb; }
.sidebar-actions { display: flex; gap: 8px; padding: 10px 16px; align-items: center; justify-content: space-between; }
#sortBtn { border: 1px solid #d0d7de; background: #fff; border-radius: 6px; padding: 5px 10px; font-size: 12px; cursor: pointer; }
#stats { font-size: 12px; color: #57606a; }
.sidebar-filters { display: flex; flex-wrap: wrap; gap: 6px 10px; padding: 8px 16px 10px; border-top: 1px solid #f0f2f5; font-size: 12px; color: #57606a; }
.sidebar-filters label { display: flex; align-items: center; gap: 4px; }
.sidebar-filters input[type="date"] { font-size: 12px; padding: 2px 4px; border: 1px solid #d0d7de; border-radius: 6px; }
#exportBtn { border: 1px solid #1f6feb; background: #eef4ff; color: #1f6feb; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
#convList { flex: 1; overflow-y: auto; }
.conv-item { padding: 12px 16px; border-bottom: 1px solid #f0f2f5; cursor: pointer; }
.conv-item:hover { background: #f6f8fa; }
.conv-item.active { background: #eef4ff; }
.conv-title { font-weight: 600; font-size: 14px; margin-bottom: 4px; word-break: break-all; }
.conv-meta { font-size: 12px; color: #57606a; }
.conv-summary { font-size: 13px; color: #57606a; margin-top: 5px; line-height: 1.45; }
.main { flex: 1; overflow-y: auto; padding: 24px 32px; }
.conv-header { margin-bottom: 18px; }
.conv-header h2 { font-size: 20px; word-break: break-all; }
.conv-header .conv-meta { margin-top: 6px; }
.msg { display: flex; margin: 12px 0; }
.msg.user { justify-content: flex-end; }
.msg.assistant { justify-content: flex-start; }
.msg.system { justify-content: center; }
.bubble { max-width: 74%; padding: 10px 14px; border-radius: 14px; background: #fff; border: 1px solid #e3e6ea; white-space: pre-wrap; word-break: break-word; line-height: 1.6; font-size: 14px; }
.msg.user .bubble { background: #1f6feb; color: #fff; border-color: #1f6feb; }
.msg.system .bubble { background: #eef1f4; border-color: #e3e6ea; color: #57606a; font-style: italic; max-width: 92%; }
.msg .role-label { font-size: 11px; color: #8b949e; margin-bottom: 4px; display: block; }
.msg.user .role-label { text-align: right; color: #aac8ff; }
mark { background: #ffe58f; padding: 0 2px; border-radius: 3px; }
.empty { color: #8b949e; text-align: center; padding: 40px 16px; font-size: 14px; }
.no-result { padding: 24px 16px; color: #8b949e; font-size: 14px; text-align: center; }
.section-title { padding: 10px 16px 6px; font-size: 12px; color: #8b949e; font-weight: 600; background: #fafbfc; position: sticky; top: 0; z-index: 1; }
.doc-item { padding: 12px 16px; border-bottom: 1px solid #f0f2f5; cursor: pointer; }
.doc-item:hover { background: #f6f8fa; }
.doc-item.active { background: #eef4ff; }
.doc-text { white-space: pre-wrap; word-break: break-word; line-height: 1.7; font-size: 14px; background: #fff; border: 1px solid #e3e6ea; border-radius: 10px; padding: 18px 20px; }
.date-group { margin-bottom: 4px; }
.date-header { padding: 8px 16px 6px; font-size: 12px; color: #8b949e; font-weight: 600; background: #fafbfc; position: sticky; top: 0; z-index: 1; }
.attach-badge { font-size: 11px; background: #eef4ff; color: #1f6feb; border-radius: 10px; padding: 1px 7px; margin-left: 6px; font-weight: 400; white-space: nowrap; }
.attachments { margin-top: 24px; padding-top: 16px; border-top: 1px solid #e3e6ea; }
.attachments h3 { font-size: 14px; color: #57606a; margin-bottom: 10px; }
.attachment-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.attachment-card { background: #fff; border: 1px solid #e3e6ea; border-radius: 10px; overflow: hidden; }
.attachment-card a { text-decoration: none; color: inherit; display: block; }
.attachment-card img { width: 100%; height: 120px; object-fit: cover; display: block; background: #f0f2f5; }
.attachment-name { font-size: 12px; padding: 6px 8px; word-break: break-all; }
@media (max-width: 760px) {
  .sidebar { width: 42%; min-width: 0; }
  .main { padding: 16px; }
}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1>__TITLE__</h1>
      <input id="search" type="search" placeholder="搜索标题或对话内容…" autocomplete="off">
    </div>
    <div class="sidebar-actions">
      <span id="stats"></span>
      <button id="sortBtn" type="button">最新在前</button>
    </div>
    <div class="sidebar-filters">
      <label>从 <input id="dateFrom" type="date"></label>
      <label>至 <input id="dateTo" type="date"></label>
      <label><input id="onlyAtt" type="checkbox"> 仅看含附件</label>
      <button id="exportBtn" type="button">导出检索结果(JSON)</button>
    </div>
    <div id="convSection">
      <div class="section-title">对话记录</div>
      <div id="convList"></div>
    </div>
    <div id="docSection" style="display:none">
      <div class="section-title">附件文档</div>
      <div id="docList"></div>
    </div>
  </aside>
  <main class="main" id="main"></main>
</div>
<script type="application/json" id="payload">__PAYLOAD__</script>
<script>
const payload = JSON.parse(document.getElementById("payload").textContent);
let conversations = payload.conversations || [];
let summaries = payload.summaries || {};
let documents = payload.documents || [];
let query = "";
let sortDesc = true;
let activeId = null;
let activeDocId = null;
let dateFrom = "";
let dateTo = "";
let onlyAtt = false;

const $ = (id) => document.getElementById(id);

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function fmt(ts) {
  if (!ts) return "未知时间";
  const d = new Date(ts * 1000);
  const p = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + " " + p(d.getHours()) + ":" + p(d.getMinutes());
}
function convText(c) {
  let text = c.title;
  (c.messages || []).forEach((m) => {
    text += "\\n" + (m.content || "");
    (m.attachments || []).forEach((a) => {
      if (a.name) text += "\\n" + a.name;
    });
  });
  return text;
}
function matches(c) {
  if (!query) return true;
  if (!convText(c).toLowerCase().includes(query.toLowerCase())) return false;
  if (dateFrom || dateTo) {
    const key = dayKey(c.create_time);
    if (key === "未知日期") return false;
    if (dateFrom && key < dateFrom) return false;
    if (dateTo && key > dateTo) return false;
  }
  if (onlyAtt && !((c.attachments_count || 0) > 0)) return false;
  return true;
}
function sorted() {
  const list = conversations.filter(matches);
  list.sort((a, b) => {
    const ta = a.create_time || 0, tb = b.create_time || 0;
    return sortDesc ? tb - ta : ta - tb;
  });
  return list;
}
function highlight(text) {
  if (!query) return esc(text);
  const lower = String(text).toLowerCase();
  const q = query.toLowerCase();
  let out = "", i = 0, idx;
  while ((idx = lower.indexOf(q, i)) !== -1) {
    out += esc(String(text).slice(i, idx));
    out += "<mark>" + esc(String(text).slice(idx, idx + q.length)) + "</mark>";
    i = idx + q.length;
  }
  out += esc(String(text).slice(i));
  return out;
}
function roleLabel(role) {
  const map = { user: "我", assistant: "DeepSeek", system: "系统", tool: "工具" };
  return map[role] || role;
}
function dayKey(ts) {
  if (!ts) return "未知日期";
  const d = new Date(ts * 1000);
  const p = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
}
function convItemHtml(c) {
  const summary = summaries[c.id] ? '<div class="conv-summary">' + esc(summaries[c.id]) + "</div>" : "";
  const attach = (c.attachments_count || 0) > 0 ? '<span class="attach-badge">📎 ' + c.attachments_count + "</span>" : "";
  return '<div class="conv-item' + (c.id === activeId ? " active" : "") + '" data-id="' + esc(c.id) + '">' +
    '<div class="conv-title">' + esc(c.title) + attach + "</div>" +
    '<div class="conv-meta">' + fmt(c.create_time) + " · " + (c.messages || []).length + " 条消息</div>" +
    summary + "</div>";
}
function docMatches(d) {
  if (!query) return true;
  return (d.name + "\\n" + d.text).toLowerCase().includes(query.toLowerCase());
}
function docItemHtml(d) {
  return '<div class="doc-item' + (d.id === activeDocId ? " active" : "") + '" data-id="' + esc(d.id) + '">' +
    '<div class="conv-title">📄 ' + esc(d.name) + "</div>" +
    '<div class="conv-meta">' + (d.char_count || d.text.length) + " 字</div></div>";
}
function renderList() {
  const list = sorted();
  const docs = documents.filter(docMatches);
  const total = conversations.length;
  const totalMsgs = conversations.reduce((n, c) => n + (c.messages || []).length, 0);
  const totalAtts = conversations.reduce((n, c) => n + (c.attachments_count || 0), 0);
  let stats = list.length + " / " + total + " 段 · " + totalMsgs + " 条消息";
  if (documents.length) stats += " · 📄 " + documents.length + " 个文档";
  if (totalAtts) stats += " · 📎 " + totalAtts;
  $("stats").textContent = stats;
  const box = $("convList");
  if (list.length) {
    const groups = {};
    list.forEach((c) => {
      const key = dayKey(c.create_time);
      (groups[key] = groups[key] || []).push(c);
    });
    const keys = Object.keys(groups).sort((a, b) => {
      if (a === "未知日期") return 1;
      if (b === "未知日期") return -1;
      return sortDesc ? b.localeCompare(a) : a.localeCompare(b);
    });
    box.innerHTML = keys.map((k) => {
      return '<div class="date-group"><div class="date-header">' + esc(k) + " · " + groups[k].length + " 段</div>" +
        groups[k].map(convItemHtml).join("") + "</div>";
    }).join("");
  } else {
    box.innerHTML = '<div class="no-result">没有匹配的对话</div>';
  }
  const docSection = $("docSection");
  if (docs.length) {
    docSection.style.display = "";
    $("docList").innerHTML = docs.map(docItemHtml).join("");
  } else {
    docSection.style.display = "none";
  }
  if (!list.length && !docs.length) {
    $("main").innerHTML = '<div class="empty">没有匹配的内容</div>';
  }
}
function convAttachments(conv) {
  const list = [];
  (conv.messages || []).forEach((m) => {
    (m.attachments || []).forEach((a) => list.push(a));
  });
  return list;
}
function renderConversation(id) {
  const conv = conversations.find((c) => c.id === id);
  const main = $("main");
  if (!conv) {
    main.innerHTML = '<div class="empty">选择左侧对话查看内容</div>';
    return;
  }
  const summary = summaries[id] ? '<div class="conv-summary">摘要：' + esc(summaries[id]) + "</div>" : "";
  const msgs = (conv.messages || []).map((m) => {
    const cls = ["user", "assistant", "system"].includes(m.role) ? m.role : "assistant";
    return '<div class="msg ' + cls + '"><div class="bubble"><span class="role-label">' + roleLabel(m.role) + "</span>" + highlight(m.content) + "</div></div>";
  }).join("");
  const atts = convAttachments(conv);
  let attHtml = "";
  if (atts.length) {
    const cards = atts.map((a) => {
      const name = a.name || (a.type === "image" ? "图片" : "附件");
      const img = a.type === "image" && a.url ? '<img src="' + esc(a.url) + '" alt="' + esc(name) + '">' : "";
      const href = a.url ? ' href="' + esc(a.url) + '"' : "";
      const target = a.url ? ' target="_blank" rel="noopener"' : "";
      return '<div class="attachment-card"><a' + href + target + ">" + img + '<div class="attachment-name">' + esc(name) + "</div></a></div>";
    }).join("");
    attHtml = '<div class="attachments"><h3>附件（' + atts.length + '）</h3><div class="attachment-grid">' + cards + '</div></div>';
  }
  main.innerHTML = '<div class="conv-header"><h2>' + esc(conv.title) + "</h2>" +
    '<div class="conv-meta">' + fmt(conv.create_time) + " · " + (conv.messages || []).length + " 条消息" +
    (atts.length ? " · 📎 " + atts.length + " 个附件" : "") + "</div>" + summary + "</div>" + msgs + attHtml;
  main.scrollTop = 0;
}
function renderDocument(id) {
  const d = documents.find((x) => x.id === id);
  if (!d) return;
  $("main").innerHTML = '<div class="conv-header"><h2>📄 ' + esc(d.name) + "</h2>" +
    '<div class="conv-meta">' + (d.char_count || d.text.length) + " 字</div></div>" +
    '<div class="doc-text">' + highlight(d.text) + "</div>";
  $("main").scrollTop = 0;
}
document.addEventListener("click", (e) => {
  const item = e.target.closest(".conv-item");
  if (item) {
    activeId = item.dataset.id;
    activeDocId = null;
    renderList();
    renderConversation(activeId);
    return;
  }
  const docItem = e.target.closest(".doc-item");
  if (docItem) {
    activeDocId = docItem.dataset.id;
    activeId = null;
    renderList();
    renderDocument(activeDocId);
  }
});
$("search").addEventListener("input", (e) => {
  query = e.target.value.trim();
  if (!sorted().some((c) => c.id === activeId)) activeId = null;
  if (!documents.some((d) => d.id === activeDocId && docMatches(d))) activeDocId = null;
  renderList();
  if (activeId) renderConversation(activeId);
  else if (activeDocId) renderDocument(activeDocId);
});
$("sortBtn").addEventListener("click", () => {
  sortDesc = !sortDesc;
  $("sortBtn").textContent = sortDesc ? "最新在前" : "最早在前";
  renderList();
  if (activeId) renderConversation(activeId);
  else if (activeDocId) renderDocument(activeDocId);
});
function bindFilters() {
  const sync = () => {
    dateFrom = $("dateFrom").value;
    dateTo = $("dateTo").value;
    onlyAtt = $("onlyAtt").checked;
    if (!sorted().some((c) => c.id === activeId)) activeId = null;
    renderList();
    if (activeId) renderConversation(activeId);
  };
  $("dateFrom").addEventListener("change", sync);
  $("dateTo").addEventListener("change", sync);
  $("onlyAtt").addEventListener("change", sync);
  $("exportBtn").addEventListener("click", () => {
    const out = { conversations: sorted() };
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "筛选结果.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  });
}
bindFilters();
renderList();
if (conversations.length) {
  const first = sorted()[0];
  activeId = first.id;
  renderConversation(activeId);
} else if (documents.length) {
  activeDocId = documents[0].id;
  renderDocument(activeDocId);
}
</script>
</body>
</html>
"""


def build(conversations, summaries, title, output, documents=None):
    docs_out = []
    for i, d in enumerate(documents or []):
        item = dict(d)
        item.setdefault("id", f"doc-{i}")
        docs_out.append(item)
    data = {"title": title, "conversations": conversations, "summaries": summaries or {}, "documents": docs_out}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html_text = TEMPLATE.replace("__TITLE__", title).replace("__PAYLOAD__", payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_text, encoding="utf-8")
    print(f"已生成: {output}")
    print(f"共 {len(conversations)} 段对话、{len(docs_out)} 个文档，双击该文件即可在浏览器中打开。")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="归一化对话 JSON（parse_deepseek.py 的输出）")
    parser.add_argument("--summaries", default=None, help="可选：summaries.json（对话 id → 一句话摘要）")
    parser.add_argument("--documents", default=None, help="可选：docs_extracted.json（附件文档正文，extract_documents.py 的输出）")
    parser.add_argument(
        "--with-documents",
        action="store_true",
        help="可选：把附件文档正文也放进网页供检索阅读（默认不放入，网页只显示附件名称/链接）",
    )
    parser.add_argument("-o", "--output", default="index.html", help="输出 HTML 路径（默认 index.html）")
    parser.add_argument("--title", default="DeepSeek 对话记录", help="页面标题（默认：DeepSeek 对话记录）")
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

    documents = None
    if args.with_documents:
        if not args.documents:
            sys.exit("--with-documents 需要配合 --documents <docs_extracted.json> 使用")
        with open(args.documents, encoding="utf-8") as fh:
            documents = json.load(fh)
        if not isinstance(documents, list):
            sys.exit("--documents 应为列表格式（extract_documents.py 的输出）")
    elif args.documents:
        print("提示：已忽略 --documents（附件正文默认不放进网页，只显示附件名称/链接；如确需在网页中检索附件正文，请同时加 --with-documents）")

    build(conversations, summaries, args.title, Path(args.output), documents)


if __name__ == "__main__":
    main()
