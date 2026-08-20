---
name: deepseek-history-organizer
description: 整理 DeepSeek 导出的历史对话记录，生成可搜索的本地网页、Markdown 摘要或 Word 文档，便于快速浏览和查找；同时支持读取 Word/PDF/Excel 等附件文档正文、提取对话中的参考文献和网页链接（附可靠性提示供日后核对）。当用户提供 DeepSeek「导出所有历史对话」的 zip 压缩包、conversations.json / conversation.json 文件或包含对话 JSON 的文件夹，并希望整理、搜索、归纳、备份或快速翻看以前的对话、查看对话里的图片和附件、读取附件里的 Word/PDF 文档、把归纳内容生成 Word 文档、核对对话里的参考文献和链接时使用。触发场景示例：「整理我的 DeepSeek 对话记录」「把 DeepSeek 导出的记录做成可搜索网页」「查找以前和 DeepSeek 聊过的内容」「给 DeepSeek 对话做目录和摘要」「读取对话附件里的 Word 文档」「把附件文档正文也放进检索」「把对话归纳生成 Word 文档」「把对话里的参考文献和链接附在文档后面」。
---

# DeepSeek 对话记录整理

把 DeepSeek 导出的对话记录解析、归一化，并输出为方便快速查看的成果。

## 工作流程

### 1. 定位输入

输入可以是以下任意一种：

- DeepSeek「导出所有历史对话」下载的 zip 压缩包
- 解压后的 conversations.json / conversation.json 文件
- 包含上述 JSON 文件的文件夹
- 单次对话的分享链接（下载页无法筛选指定对话时使用）：分享链接有效期约 7 天，把要整理的链接批量抓取到同一文件夹，即可合并成一次整理

下载的完整导出包含全部对话、无法在下载页挑选；如需只整理其中几次对话，可让用户为这几段对话各生成一个分享链接，然后运行：

```bash
python scripts/fetch_share.py <分享链接或share_id> [...] -o share_data
```

链接较多时也可先写入文本文件（每行一个链接），再用 `python scripts/fetch_share.py -i links.txt -o share_data`。脚本会把每段对话保存为标准的 conversations.json 格式文件（`share_data\*.json`），之后照常按第 2 步把整个文件夹作为输入解析合并。

**推荐操作流程 A（本地检索，最省事；无需手动搜索网页、无需分享链接）**：

1. 用户下载一次「导出所有历史对话」的 zip（全量备份）。
2. 由 AI 助手解析后，用关键词在本地检索（search_conversations.py），列出命中对话及上下文片段：

```bash
python scripts/search_conversations.py conversations.normalized.json --keywords "代谢,调控"
```

3. 与用户确认要整理哪几段（或直接按命中结果），导出子集：

```bash
python scripts/search_conversations.py conversations.normalized.json --keywords "代谢" --export selected.json
```

4. 对子集里每段对话独立、完整分析（全部内容整体归纳，不切分），各自生成文档，按时间连续编号归档。

**操作流程 B（分享链接，仅当不想下载整包或只有零星对话时使用）**：

1. 用户在 DeepSeek 网页版检索栏输入关键词定位对话（结果不能同时展开多条，逐条确认即可，无需细读）。
2. 对每段要整理的对话生成分享链接（有效期约 7 天），粘贴给 AI 助手（或写入 links.txt，每行一个）。
3. AI 助手用 fetch_share.py 批量抓取、解析，之后同样每段独立、完整分析，按时间连续编号归档。

### 2. 解析并归一化

运行：

```bash
python scripts/parse_deepseek.py <输入路径> -o conversations.normalized.json
```

脚本会输出对话总数、消息总数、时间范围，并生成归一化 JSON（结构见 references/schema.md）。

### 3. 可选：生成一句话摘要

阅读 conversations.normalized.json，为每段对话写一句话中文摘要（40 字以内），保存为 summaries.json：

```json
{"<对话id>": "一句话概括这段对话", ...}
```

对话很多时可分批进行，或先询问用户是否需要摘要。

写完摘要后，可用速览卡片快速总览（每段一张卡片：编号/日期/主题/摘要/首条提问/关键词，关键要点与待办在归纳时填写）：

```bash
python scripts/build_cards.py cards conversations.normalized.json --summaries summaries.json -o .
```

会生成 速览卡片.md 与 登记表.md（编号 | 日期 | 主题 | 消息数 | 摘要）。

### 4. 可选：提取附件文档正文

如果对话里带 Word/PDF/Excel 等附件文档，先把文档放进一个文件夹（或给出文件路径），运行：

```bash
python scripts/extract_documents.py <文档文件夹或文件> -o docs_extracted.json --txt-dir docs
```

- Word（.docx）为主，同时支持 .pdf、.xlsx、.pptx、.txt、.md、.csv。
- Office 文档优先调用 OfficeCLI 提取，自动补全表格内容；OfficeCLI 不可用时回退 python-docx / openpyxl；PDF 用 pypdf / pdfplumber。
- 生成 docs_extracted.json 供归纳时参考正文（也可用 --with-documents 选择放入网页检索）；--txt-dir 会额外输出可读文本副本。

**附件补全（重要）**：DeepSeek 分享接口只返回附件元数据（文件名/大小），**不提供附件文件下载**。若附件为公开发表的论文，可经合法开放获取渠道（PMC / Unpaywall / 期刊官网 OA 页等）按 DOI 或题名检索下载原文，再运行 extract_documents.py 提取正文；若无法合法获取，如实告知用户"附件不可用"，不要伪造或跳过。下载时遵守期刊许可，仅下载开放获取或用户已获授权的文献。

### 5. 生成查看成果

默认生成可搜索网页（推荐，双击即可在浏览器打开，无需联网）：

```bash
python scripts/build_html.py conversations.normalized.json --summaries summaries.json -o index.html
```

网页支持关键词搜索、按日期排序、**日期范围筛选、仅看含附件对话、导出当前检索结果为 JSON**（左侧筛选栏）。

附件正文默认不放进网页（网页只显示对话内容和附件名称/链接，避免正文零散、不完整影响阅读）；如用户明确需要在网页里检索附件正文，再加：

```bash
python scripts/build_html.py conversations.normalized.json --summaries summaries.json --with-documents --documents docs_extracted.json -o index.html
```

如用户需要 Markdown 版（每段对话一个文件 + index.md 总目录）：

```bash
python scripts/build_markdown.py conversations.normalized.json --summaries summaries.json -o digests
```

没有生成摘要时，省略 --summaries 参数即可。

### 5.5 多段对话时的处理原则：每段独立

输入包含多段对话时：**内容相近的对话可以合并分析**（如同一主题的连续讨论）；**主题不相同的对话必须单独分析、单独生成文档**，互不影响。具体做法：

- 网页版和 Markdown 目录只是总览/检索层：左侧按日期列出全部对话，可逐段点击查看、跨段搜索。
- **每段对话全部内容整体分析**：完整通读该对话的所有轮次，一次性归纳全部内容，不切分、不抽取片段；一段对话对应一份完整文档。
- 归纳文档附录的问答题目：**只列实质讨论主题**——重复提问只保留一条（如"服务器繁忙"导致的重复提问），"谢谢"等简单答复不列入，"请按 HTML/Word/PDF 格式输出"等要求 AI 执行的格式生成类提问不列入（不属于讨论主题）；附录说明统一写「已删除重复提问、简单答复和格式生成类提问」。
- 归纳 Word 文档按段生成：每段对话单独写一份归纳 MD，再各自转成 Word；全部文档输出到同一个文件夹，文件名按时间顺序连续编号（0001-日期-主题、0002-日期-主题、0003-…），一个文件夹一次排开，之后按编号/日期即可快速检索。
- 附件、参考文献等同样按所属对话分别处理，互不混入。

合并/拆分决策可先用主题相近提示辅助（按标题/摘要/消息字词重合度给出相似对话对，仅作参考，是否合并由用户确认）：

```bash
python scripts/suggest_similar.py conversations.normalized.json --summaries summaries.json
```

文档归档后，可在归档文件夹顶部生成登记表（扫描 0001-日期-主题.md/.docx 命名文件）：

```bash
python scripts/build_cards.py catalog <归档文件夹>
```

### 6. 可选：把内容生成 Word 文档

按"文字类文件先转 MD 再处理"的规则，先把归纳/整理内容写成 Markdown（如 归纳.md），再转换为 Word：

```bash
python scripts/extract_references.py conversations.normalized.json --append 归纳.md
python scripts/build_docx.py 归纳.md -o 归纳.docx
```

支持标题、无序/有序列表、表格、加粗/斜体/行内代码、引用等 Markdown 语法。

需要 PDF 版时（MD → 排版 HTML → Edge 无头打印，需本机安装 Microsoft Edge）：

```bash
python scripts/build_pdf.py 归纳.md -o 归纳.pdf
```

Word 排版按照中文期刊规范格式：正文 Times New Roman + 宋体 10.5pt、行距 1.3、段落首行缩进两字符；标题黑体（标题 20pt 居中、一级节题 14pt、二级以下 11pt）；基因名与拉丁学名斜体（蛋白质/酶缩写保持正体）；参考文献区条目用 8pt 悬挂缩进、行距 1.15；页脚自动页码（第 X 页 / 共 Y 页）。编号列表按原文 1、2、3… 依次编号，不跳号。

`extract_references.py` 会把对话中助手消息里的网页链接和疑似文献引用片段提取出来，追加"参考文献与网页链接（供核对）"一节，并附固定可靠性提示：AI 检索/生成的文献可能编造或不准确，须与权威数据库核对，对话分析结论仅供参考。该步骤即使没有提取到链接也会追加提示，便于日后核对。

### 6.5 可选：参考文献可靠性核查与标记

提取参考文献后，用权威数据库逐条核实并标记可靠性：

可先用半自动脚本生成候选核查表（英文文献经 Crossref 解析 DOI / 书目检索 与 PubMed（NCBI E-utilities）双通道核查并带 PMID；中文文献自动提示走知网 CNKI、万方、维普、期刊官网人工核对；输出"倾向"标记与最佳匹配，人工只需复核）：

```bash
python scripts/verify_references.py references.md -o references.check.md
```

然后按候选表逐条复核并标记：

- ✅ **可靠**：在权威数据库（PubMed / Crossref / Web of Science / 期刊官网 / 知网等）检索到，作者、年份、标题、期刊、卷期页码与原文一致（标注核对依据，如 DOI / PMID）。
- ⚠️ **不确定**：检索到部分信息（如同名作者、年份或主题相近）但无法完全确认，或存在疑似混淆。
- ❌ **存疑/不可靠**：权威数据库检索不到，或关键信息与原文明显不符，很可能为 AI 编造或拼接。

把标记结果整理为 参考文献.verified.md（保留原引用文本 + 标记 + 一句核对说明），替换或追加到归纳文档后再转 Word。优先核实明确列出的"参考文献"清单；对话中内嵌引用（括号引用）可抽查重点条目。网络不可用时跳过核查，仅保留"供核对"附录。

**提醒（"假验证"风险）**：AI 声称"已通过 PubMed/数据库逐一核查"并不可信——实测中 AI 给出的"修正后"文献列表可能与上一版完全相同（假验证）。DOI 必须用 Crossref/期刊官网逐条解析并比对标题与作者（verify_references.py 已实现），仅凭 AI 声明不能判定可靠。

### 7. 交付

- 网页版：告知用户双击 index.html 即可打开，支持按关键词搜索、按时间排序、点击查看全文，匹配内容会高亮。
- 网页版左侧按日期分组列出对话主题，日期内按时间排列；对话详情底部单独显示「附件」栏，图片直接预览、文件可点击打开。
- 附件正文默认不放进网页，避免显示零散、不完整的文档内容；如用户明确要求，可加 --with-documents --documents 把附件正文放入网页供检索阅读。
- Markdown 版：index.md 为总目录，其余文件为单段对话内容。
- Word 版：由 Markdown 经 build_docx.py 转换，便于打印、传阅和进一步编辑。
- 输出目录建议放在输入文件旁或用户指定位置；如用户要求，可同时生成两种格式。

**交付清单（每次交付固定核对）**：可搜索网页 index.html、速览卡片.md、登记表.md、Markdown 摘要目录 digests\、归纳 MD/Word（有 PDF 时一并给 PDF）、参考文献核查表 references.verified.md（无文献时注明）、验证记录.md，以及附件原文/正文提取结果（如有）。交付回复中逐项给出文件链接，避免漏列。

## 注意事项

- 解析脚本兼容多种导出结构（mapping 消息树 / 扁平 messages 数组、内容为字符串或分块列表），细节见 references/schema.md。
- 若解析失败或统计异常，先运行 parse 脚本查看报错，再检查输入是否确实为 DeepSeek 导出格式。
- 网页版为单文件、离线可用，不依赖网络。

## 资源

### scripts/

- parse_deepseek.py — 解析导出数据，输出归一化 JSON
- extract_documents.py — 读取 Word/PDF/Excel 等附件文档正文（OfficeCLI 优先，python 库回退）
- fetch_share.py — 批量抓取分享链接（每条保存为对话 JSON，供合并整理）
- search_conversations.py — 本地关键词检索全部对话，命中对话可导出子集（无需手动搜索网页）
- build_html.py — 生成可搜索 HTML 查看器
- build_markdown.py — 生成 Markdown 摘要目录
- build_cards.py — 生成速览卡片（cards）与文件夹登记表（catalog）
- build_pdf.py — Markdown 转 PDF（排版 HTML + Edge 无头打印）
- verify_references.py — 参考文献半自动核查（英文：Crossref + PubMed 双通道；中文：人工核对提示；输出候选表）
- suggest_similar.py — 对话主题相近提示（字词重合度，供合并决策参考）
- build_docx.py — Markdown 转 Word（.docx），支持标题/列表/表格/加粗等语法
- extract_references.py — 提取对话中的网页链接与疑似文献引用，生成带可靠性提示的附录

### references/

- schema.md — DeepSeek 导出格式说明、归一化结构与各脚本输出说明

## 版本与更新记录

- v1.1（2026-08-20）：文献核查升级为英文 Crossref + PubMed 双通道（带 PMID），中文文献自动提示走知网 CNKI / 万方 / 维普 / 期刊官网人工核对；面向国内外 DeepSeek 用户发布，新增中英双语 README。
- v1.0：初版（分享链接抓取、本地检索、HTML/MD/Word/PDF 输出、多条对话综合分析、附件正文提取、参考文献提取与核查标记）。
