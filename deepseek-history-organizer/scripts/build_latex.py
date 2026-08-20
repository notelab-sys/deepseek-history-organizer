#!/usr/bin/env python3
"""Convert an English summary Markdown into an Elsevier-style LaTeX document and
compile it to PDF with Tectonic (or pdflatex/xelatex if available).

Design:
- H1 (document title) -> \\title{}; H2 -> \\section{}; H3 -> \\subsection{};
  H4 -> \\subsubsection{} (LaTeX auto-numbers 1 / 1.1 / 1.1.1).
- Body paragraphs are separated by blank lines (first-line indent removed to
  match the final English layout); **bold** / *italic* / `code` are converted.
- Lists: "- " -> itemize; "N. " -> enumerate (kept as bullets in EN mode
  already at the MD level, so itemize is the common case).
- Tables (| ... |) -> tabular.
- Blockquotes ("> ") -> quote environment.
- References: entries under a "References" heading are emitted as a
  thebibliography with [1]..[n] numbering in Elsevier author-year style text.

Usage:
  python build_latex.py <input.md> [-o output.tex|output.pdf] [--no-compile]
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_tectonic():
    exe = shutil.which("tectonic")
    if exe:
        return exe
    cands = [
        Path.home() / ".codex" / ".tmp" / "bundled-marketplaces" / "openai-bundled" / "plugins" / "latex" / "bin" / "tectonic.exe",
        Path.home() / ".codex" / "plugins" / "cache" / "openai-bundled" / "latex" / "0.2.6" / "bin" / "tectonic.exe",
    ]
    for c in cands:
        if c.exists():
            return str(c)
    return None


def esc(text):
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("$", r"\$")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("^", r"\textasciicircum{}")
        .replace("~", r"\textasciitilde{}")
    )


INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def inline_latex(text):
    out = []
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append(r"\textbf{" + esc(part[2:-2]) + "}")
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            out.append(r"\texttt{" + esc(part[1:-1]) + "}")
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append(r"\textit{" + esc(part[1:-1]) + "}")
        else:
            out.append(esc(part))
    return "".join(out)


def is_table_sep(line):
    return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line


def table_to_latex(rows):
    ncol = max(len(r) for r in rows)
    head = "l" * ncol
    lines = [r"\begin{table}[h]", r"\centering", r"\caption{}", r"\begin{tabular}{" + head + "}"]
    for ri, row in enumerate(rows):
        cells = [inline_latex(row[j] if j < len(row) else "") for j in range(ncol)]
        sep = r" \\" + ("\n\\hline" if ri == 0 else "") + "\n" if ri < len(rows) - 1 else "\n"
        if ri == 0:
            lines.append(" & ".join(r"\textbf{" + c + "}" for c in cells) + sep)
        else:
            lines.append(" & ".join(cells) + sep)
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


def md_to_latex(md_text, title):
    lines = md_text.splitlines()
    out = []
    i = 0
    in_refs = False
    refs = []

    def flush_refs():
        nonlocal refs
        if refs:
            out.append(r"\begin{thebibliography}{99}")
            for n, ref in enumerate(refs, 1):
                out.append(r"\bibitem{ref" + str(n) + "} " + inline_latex(ref))
            out.append(r"\end{thebibliography}")
            refs = []

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not is_table_sep(lines[i]):
                    rows.append(cells)
                i += 1
            if rows:
                out.append(table_to_latex(rows))
            continue

        if not stripped:
            i += 1
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            text = inline_latex(heading.group(2).strip())
            if level == 1:
                title = heading.group(2).strip()
            elif level == 2:
                if "reference" in heading.group(2).lower() and "verification" not in heading.group(2).lower():
                    in_refs = True
                else:
                    flush_refs()
                    in_refs = False
                out.append(r"\section{" + text + "}")
            elif level == 3:
                flush_refs()
                in_refs = False
                out.append(r"\subsection{" + text + "}")
            else:
                flush_refs()
                in_refs = False
                out.append(r"\subsubsection{" + text + "}")
            i += 1
            continue

        if re.match(r"^---+$", stripped) or re.match(r"^\*\*\*+$", stripped):
            i += 1
            continue

        if stripped.startswith(">"):
            out.append(r"\begin{quote}" + inline_latex(stripped.lstrip(">").strip()) + r"\end{quote}")
            i += 1
            continue

        bullet = re.match(r"^[-*+]\s+(.*)$", stripped)
        if bullet:
            if in_refs:
                refs.append(bullet.group(1).strip())
            else:
                items = []
                while i < len(lines):
                    sm = re.match(r"^[-*+]\s+(.*)$", lines[i].strip())
                    if not sm:
                        break
                    items.append(r"\item " + inline_latex(sm.group(1).strip()))
                    i += 1
                out.append(r"\begin{itemize}" + "\n" + "\n".join(items) + "\n" + r"\end{itemize}")
            i += 1
            continue

        numbered = re.match(r"^(\d+)[.、)]\s+(.*)$", stripped)
        if numbered:
            if in_refs:
                refs.append(numbered.group(2).strip())
            else:
                items = []
                while i < len(lines):
                    sm = re.match(r"^(\d+)[.、)]\s+(.*)$", lines[i].strip())
                    if not sm:
                        break
                    items.append(r"\item " + inline_latex(sm.group(2).strip()))
                    i += 1
                out.append(r"\begin{enumerate}" + "\n" + "\n".join(items) + "\n" + r"\end{enumerate}")
            i += 1
            continue

        out.append(inline_latex(stripped))
        out.append("")
        i += 1

    flush_refs()
    return title, "\n\n".join(out)


def build(md_text, output, compile_pdf=True):
    lines = md_text.splitlines()
    title = "Document"
    for ln in lines:
        m = re.match(r"^#\s+(.*)$", ln.strip())
        if m:
            title = m.group(1).strip()
            break
    title, body = md_to_latex(md_text, title)
    tex = r"""\documentclass[preprint,12pt]{elsarticle}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{hyperref}
\journal{Plant Physiology and Biochemistry}
\begin{document}
\title{""" + esc(title) + r"""}
\author{}
\begin{abstract}
Generated from a DeepSeek conversation summary. See the source Markdown for
details and verification notes.
\end{abstract}
\maketitle
""" + body + r"""
\end{document}
"""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tex_path = output if output.suffix.lower() == ".tex" else output.with_suffix(".tex")
    tex_path.write_text(tex, encoding="utf-8")
    print(f"已生成 LaTeX: {tex_path}")
    if not compile_pdf:
        return str(tex_path)
    exe = find_tectonic()
    if not exe:
        sys.exit("未找到 Tectonic，无法编译 PDF；请安装 Tectonic 或使用 --no-compile 仅生成 .tex")
    pdf_path = output if output.suffix.lower() == ".pdf" else output.with_suffix(".pdf")
    # Tectonic 对非 ASCII 路径支持不佳：在临时 ASCII 目录编译后复制回目标
    with tempfile.TemporaryDirectory(prefix="ds_tex_") as td:
        tmp_tex = Path(td) / tex_path.name
        shutil.copy(tex_path, tmp_tex)
        proc = subprocess.run([exe, str(tmp_tex)], cwd=td, capture_output=True, text=True, errors="replace", timeout=300)
        if proc.returncode != 0:
            sys.exit(f"Tectonic 编译失败：{proc.stderr[-1200:]}")
        tmp_pdf = Path(td) / (tex_path.stem + ".pdf")
        if not tmp_pdf.exists():
            sys.exit("Tectonic 编译未产生 PDF")
        shutil.copy(tmp_pdf, pdf_path)
    print(f"已生成 PDF: {pdf_path}")
    return str(pdf_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="英文归纳 Markdown 文件")
    parser.add_argument("-o", "--output", default=None, help="输出 .tex 或 .pdf 路径（默认与输入同名 .pdf）")
    parser.add_argument("--no-compile", action="store_true", help="仅生成 .tex，不编译 PDF")
    args = parser.parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"输入文件不存在: {input_path}")
    md_text = input_path.read_text(encoding="utf-8-sig")
    out = Path(args.output) if args.output else input_path.with_suffix(".pdf")
    build(md_text, out, compile_pdf=not args.no_compile)


if __name__ == "__main__":
    main()
