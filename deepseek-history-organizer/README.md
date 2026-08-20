# DeepSeek History Organizer ｜ DeepSeek 对话记录整理

> Organize, search, summarize and export your DeepSeek chat history — from **share links** or **official exports** — into a searchable HTML viewer, Markdown, Word (Chinese journal style) and PDF, with multi-conversation analysis and reference reliability checking (Crossref + PubMed for English literature, CNKI / Wanfang / VIP routing for Chinese literature).
>
> 把 DeepSeek 历史对话整理成可搜索网页、Markdown、Word（中文期刊规范排版）与 PDF；支持分享链接批量抓取、多条对话综合分析、附件正文提取，以及参考文献可靠性核查（英文走 Crossref + PubMed，中文提示走知网 / 万方 / 维普 / 期刊官网）。

## 功能 Features

- **分享链接批量抓取**：把 DeepSeek 分享链接（或 share_id）批量抓取为标准 JSON，合并成一次整理；支持链接文件批量输入。
  **Share-link fetching**: batch-fetch DeepSeek share links into standard JSON and merge them into one archive.
- **本地检索对话框**：对官方导出（zip / conversations.json）在本地按关键词检索，命中对话直接导出子集，无需手动翻网页。
  **Local conversation search**: keyword-search all exported conversations locally and export the matched subset.
- **多条对话综合分析**：每条对话独立、完整归纳；相近主题可合并、不同主题单独分析；主题相近自动提示（suggest_similar），按时间连续编号归档并生成登记表。
  **Multi-conversation analysis**: each conversation is summarized independently and completely; similar topics can be merged, different topics stay separate, with similarity hints, numbered archiving and a catalog.
- **可搜索 HTML 查看器**：离线单文件，支持关键词搜索、日期范围筛选、附件筛选、导出检索结果。
  **Searchable HTML viewer**: offline single file with keyword search, date-range/attachment filters and result export.
- **多格式输出 + 语言自适应**：Markdown / Word / PDF；中文用户输出中文期刊规范排版（黑体标题、宋体正文、页脚页码），英文用户以 `--lang en` 输出英文期刊格式（Times New Roman 12pt、加粗标题、APA 悬挂缩进、Page X of Y 页码）。
  **Multi-format output with language adaptation**: Markdown / Word / PDF. Chinese users get Chinese journal typography; English users can pass `--lang en` for English journal formatting (Times New Roman 12 pt, bold headings, APA hanging indent, "Page X of Y").
- **附件正文提取**：读取对话附件的 Word / PDF / Excel / PPT 等正文，供归纳参考。
  **Attachment text extraction**: read text from attached Word / PDF / Excel / PPT files.
- **参考文献可靠性核查（中英文）**：自动提取对话中的网页链接与疑似文献引用；英文文献经 Crossref + PubMed 双通道核查（带 PMID），中文文献提示经知网 CNKI、万方、维普、期刊官网人工核对；输出 ✅/⚠️/❌ 倾向标记表。
  **Reference reliability checking (EN & ZH)**: extract links and citation-like fragments; verify English literature via Crossref + PubMed (with PMID), route Chinese literature to CNKI / Wanfang / VIP / journal sites, and output a ✅/⚠️/❌ candidate table.

## 快速开始 Quick Start

**方式 A：分享链接（推荐，无需下载整包）** / *A. Share links (no full archive download needed)*

```bash
python scripts/fetch_share.py https://chat.deepseek.com/share/<share_id> [...] -o share_data
# 或把多个链接写入 links.txt（每行一个）
python scripts/fetch_share.py -i links.txt -o share_data
python scripts/parse_deepseek.py share_data -o conversations.normalized.json
```

**方式 B：官方导出 / 本地检索** / *B. Official export & local search*

```bash
# 下载 DeepSeek「导出所有历史对话」zip 并解压到某文件夹
python scripts/parse_deepseek.py <导出文件夹> -o conversations.normalized.json
python scripts/search_conversations.py conversations.normalized.json --keywords "关键词"
python scripts/search_conversations.py conversations.normalized.json --keywords "关键词" --export selected.json
```

**生成成果** / *Build outputs*

```bash
python scripts/build_html.py conversations.normalized.json -o index.html          # 可搜索网页
python scripts/build_markdown.py conversations.normalized.json -o digests        # Markdown 摘要目录
python scripts/build_docx.py 归纳.md -o 归纳.docx                                 # Word（中文期刊规范）
python scripts/build_pdf.py 归纳.md -o 归纳.pdf                                   # PDF（需本机 Edge）
python scripts/extract_references.py conversations.normalized.json --append 归纳.md
python scripts/verify_references.py references.md -o references.check.md          # 参考文献核查候选表
```

## 完整工作流 Workflow

1. 定位输入：分享链接批量抓取，或官方导出 zip / conversations.json。
2. 解析归一化：`parse_deepseek.py` 统一为 conversations.normalized.json。
3. 生成一句话摘要与速览卡片（可选）。
4. 提取附件文档正文（可选）。
5. 每条对话独立、完整归纳；相近主题合并、不同主题单独成文，按时间编号归档。
6. 生成 HTML / Markdown / Word / PDF 成果。
7. 提取参考文献与网页链接，逐条核查可靠性（英文 Crossref+PubMed，中文知网/万方/维普路径），给出倾向标记供人工复核。

## 验证记录 Verified Examples

已用 9 组真实 DeepSeek 对话验证，覆盖全流程、附件提取、文献核查（可靠/不可靠）、多段合并、去重、无文献、附件补全、组学分析选型等场景。测试例已脱敏、仅以编号列出，不展示具体对话内容。

## 与社区同类对比 Comparison

GitHub 上已有 DeepSeek 对话导出/备份工具（导出 JSON/MD/HTML/Word/PDF）与聊天历史语义分析 Skill（如 CHATDRILL，输出结构化知识库），以及独立的参考文献核查 Skill（如 reference-checker-skill）。本 Skill 的差异化在于把**分享链接获取 → 对话归纳分析 → 中英文期刊规范 Word/PDF 交付 → 中英文文献可靠性核查**组合成完整闭环，并支持多条对话的独立分析与合并决策。

## 许可 License

MIT License。See [LICENSE](LICENSE).

## 免责声明 Disclaimer

DeepSeek 对话中的文献引用与网页链接可能由 AI 检索或生成，存在编造、拼接或不准确的可能；核查表仅为“倾向”结论，引用前务必与权威数据库（PubMed / Crossref / Web of Science / 知网 / 万方 / 维普 / 期刊官网）核对原文。分享链接有效期约 7 天，失效后需重新生成。本工具仅处理你本地或你已获授权的对话数据，请注意数据隐私。
