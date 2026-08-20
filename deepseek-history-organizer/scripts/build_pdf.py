#!/usr/bin/env python3
"""Convert Markdown file(s) to a PDF via a styled HTML + Edge headless print.

The typography follows the same Chinese journal style as build_docx.py
(SimSun body, SimHei headings, first-line indents, hanging-indent numbered items).
Requires Microsoft Edge (headless print-to-pdf).

Usage:
  python build_pdf.py <input.md> [...] [-o output.pdf]
"""

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
@page { size: A4; margin: 20mm 18mm; }
body { font-family: "Times New Roman", "SimSun", serif; font-size: 10.5pt;
       line-height: 1.6; color: #141414; }
h1 { font-family: "SimHei"; font-size: 20pt; text-align: center; margin: 0 0 10pt; }
h2 { font-family: "SimSun"; font-size: 14pt; margin: 14pt 0 6pt; }
h3 { font-family: "SimHei"; font-size: 11pt; margin: 10pt 0 5pt; }
h4, h5, h6 { font-family: "SimHei"; font-size: 10.5pt; margin: 8pt 0 4pt; }
p { margin: 0 0 6pt; }
blockquote { color: #6e6e6e; font-size: 9.5pt; margin: 6pt 0; padding-left: 12pt;
             border-left: 2px solid #ddd; }
ul, ol { margin: 4pt 0 8pt; padding-left: 24pt; }
li { margin-bottom: 2pt; }
table { border-collapse: collapse; margin: 8pt auto; font-size: 9.5pt; }
th, td { border: 1px solid #999; padding: 3pt 6pt; }
th { background: #f2f2f2; }
code { font-family: Consolas, monospace; font-size: 9.5pt; background: #f6f6f6;
       padding: 0 2pt; }
mark { background: #ffe58f; }
.num { margin: 0 0 3pt; padding-left: 24pt; text-indent: -24pt; }
.meta { text-align: center; color: #6e6e6e; font-size: 9pt; margin-bottom: 12pt; }
"""

EN_CSS = """
@page { size: A4; margin: 25mm 25mm; }
body { font-family: "Times New Roman", serif; font-size: 12pt;
       line-height: 1.5; color: #141414; text-align: justify; }
h1 { font-family: "Times New Roman"; font-size: 16pt; font-weight: bold;
     text-align: center; margin: 0 0 12pt; }
h2 { font-family: "Times New Roman"; font-size: 14pt; font-weight: bold;
     margin: 16pt 0 8pt; }
h3 { font-family: "Times New Roman"; font-size: 12pt; font-weight: bold;
     margin: 12pt 0 6pt; }
h4, h5, h6 { font-family: "Times New Roman"; font-size: 12pt; font-weight: bold;
     margin: 10pt 0 5pt; }
p { margin: 0 0 8pt; text-indent: 12pt; }
ul p, ol p, blockquote p { text-indent: 0; }
blockquote { color: #6e6e6e; font-size: 10.5pt; margin: 8pt 0;
             padding-left: 14pt; border-left: 2px solid #ddd; }
ul, ol { margin: 4pt 0 10pt; padding-left: 0; list-style-position: inside; }
li { margin-bottom: 3pt; }
table { border-collapse: collapse; margin: 10pt auto; font-size: 10.5pt; }
th, td { border: 1px solid #999; padding: 4pt 8pt; }
th { background: #f2f2f2; }
code { font-family: Consolas, monospace; font-size: 10.5pt; background: #f6f6f6;
       padding: 0 2pt; }
mark { background: #ffe58f; }
.num { margin: 0 0 4pt; padding-left: 0; text-indent: 0; }
.ref { margin: 0 0 6pt; text-indent: 12pt; }
.meta { text-align: center; color: #6e6e6e; font-size: 10pt; margin-bottom: 14pt; }
"""

INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")
LANG = "zh"
HEAD_CNT = [0, 0, 0, 0, 0, 0]


def numbered_heading(level, text):
    """Add hierarchical numbers (1. / 1.1 / 1.1.1) to English headings."""
    global HEAD_CNT
    if LANG != "en" or level < 2:
        return text
    if level == 2:
        HEAD_CNT[2] += 1
        HEAD_CNT[3] = HEAD_CNT[4] = HEAD_CNT[5] = 0
        prefix = f"{HEAD_CNT[2]}."
    elif level == 3:
        HEAD_CNT[3] += 1
        HEAD_CNT[4] = HEAD_CNT[5] = 0
        prefix = f"{HEAD_CNT[2]}.{HEAD_CNT[3]}"
    elif level == 4:
        HEAD_CNT[4] += 1
        HEAD_CNT[5] = 0
        prefix = f"{HEAD_CNT[2]}.{HEAD_CNT[3]}.{HEAD_CNT[4]}"
    else:
        HEAD_CNT[5] += 1
        prefix = f"{HEAD_CNT[2]}.{HEAD_CNT[3]}.{HEAD_CNT[4]}.{HEAD_CNT[5]}"
    return f"{prefix} {text}"


def inline_html(text):
    parts = []
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            parts.append("<strong>" + html.escape(part[2:-2]) + "</strong>")
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            parts.append("<code>" + html.escape(part[1:-1]) + "</code>")
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            parts.append("<em>" + html.escape(part[1:-1]) + "</em>")
        else:
            parts.append(html.escape(part))
    return "".join(parts)


def is_table_sep(line):
    return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line


def md_to_html(md_text):
    lines = md_text.splitlines()
    out = []
    i = 0
    in_refs = False
    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not is_table_sep(lines[i]):
                    rows.append(cells)
                i += 1
            if rows:
                ncol = max(len(r) for r in rows)
                out.append("<table>")
                for ri, row in enumerate(rows):
                    tag = "th" if ri == 0 else "td"
                    out.append("<tr>" + "".join(f"<{tag}>{inline_html(row[j] if j < len(row) else '')}</{tag}>" for j in range(ncol)) + "</tr>")
                out.append("</table>")
            continue
        if not s:
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            level = len(m.group(1))
            text = inline_html(numbered_heading(level, m.group(2).strip()))
            if level == 1:
                out.append(f"<h1>{text}</h1>")
            elif level == 2:
                out.append(f"<h2>{text}</h2>")
            else:
                out.append(f"<h{level}>{text}</h{level}>")
            if level <= 2:
                in_refs = ("参考文献" in m.group(2)) or (LANG == "en" and "reference" in m.group(2).lower())
            i += 1
            continue
        if re.match(r"^---+$", s) or re.match(r"^\*\*\*+$", s):
            out.append("<hr>")
            i += 1
            continue
        if s.startswith(">"):
            out.append("<blockquote>" + inline_html(s.lstrip(">").strip()) + "</blockquote>")
            i += 1
            continue
        m = re.match(r"^[-*+]\s+(.*)$", s)
        if m:
            items = []
            while i < len(lines):
                sm = re.match(r"^[-*+]\s+(.*)$", lines[i].strip())
                if not sm:
                    break
                if in_refs and LANG == "en":
                    items.append(f'<p class="ref">' + inline_html(sm.group(1).strip()) + "</p>")
                else:
                    items.append("<li>" + inline_html(sm.group(1).strip()) + "</li>")
                i += 1
            if in_refs and LANG == "en":
                out.extend(items)
            else:
                out.append("<ul>" + "".join(items) + "</ul>")
            continue
        m = re.match(r"^(\d+)[.、)]\s+(.*)$", s)
        if m:
            items = []
            while i < len(lines):
                sm = re.match(r"^(\d+)[.、)]\s+(.*)$", lines[i].strip())
                if not sm:
                    break
                prefix = f"{sm.group(1)}.&nbsp;" if (in_refs or LANG != "en") else "•&nbsp;"
                items.append(f'<p class="num">{prefix}' + inline_html(sm.group(2).strip()) + "</p>")
                i += 1
            out.extend(items)
            continue
        out.append("<p>" + inline_html(s) + "</p>")
        i += 1
    return "\n".join(out)


def find_edge():
    for p in EDGE_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def build(md_text, output):
    edge = find_edge()
    if not edge:
        sys.exit("未找到 Microsoft Edge，无法生成 PDF；请安装 Edge 或改用 build_docx.py 生成 Word。")
    body = md_to_html(md_text)
    css = EN_CSS if LANG == "en" else CSS
    lang_attr = "en" if LANG == "en" else "zh-CN"
    html_text = (
        f"<!DOCTYPE html><html lang='{lang_attr}'><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>{body}</body></html>"
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    td = Path(tempfile.mkdtemp(prefix="ds_pdf_"))
    try:
        html_path = td / "doc.html"
        html_path.write_text(html_text, encoding="utf-8")
        user_dir = td / "edge_profile"
        cmd = [
            edge, "--headless", "--disable-gpu", "--disable-extensions",
            "--no-first-run", "--no-pdf-header-footer",
            f"--user-data-dir={user_dir}",
            f"--print-to-pdf={output.resolve()}",
            html_path.as_uri(),
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=120)
        err = (proc.stderr or b"").decode("utf-8", errors="replace")
        if proc.returncode != 0:
            sys.exit(f"Edge 打印失败：{err[-500:]}")
        time.sleep(1.5)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    if not output.exists():
        sys.exit("PDF 未生成（输出文件不存在）")
    print(f"已生成: {output}（{output.stat().st_size} 字节）")


def main():
    global LANG
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="Markdown 文件路径（多个时按顺序合并）")
    parser.add_argument("-o", "--output", default=None, help="输出 PDF 路径（默认与输入同名 .pdf）")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh", help="排版语言：zh=中文期刊规范（默认），en=英文期刊格式")
    args = parser.parse_args()
    LANG = args.lang
    parts = []
    for name in args.inputs:
        input_path = Path(name)
        if not input_path.exists():
            sys.exit(f"输入文件不存在: {input_path}")
        parts.append(input_path.read_text(encoding="utf-8-sig"))
    first = Path(args.inputs[0])
    output = Path(args.output) if args.output else first.with_suffix(".pdf")
    build("\n\n".join(parts), output)


if __name__ == "__main__":
    main()
