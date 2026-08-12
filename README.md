# deepseek-history-organizer

> 🌐 English version: [README.en.md](README.en.md)（中文为主要语言 / Chinese is the primary language）

把 DeepSeek 对话记录整理成便于快速查看与检索的本地成果：可搜索网页查看器、Markdown 摘要目录、归纳 Word/PDF 文档；支持分享链接批量抓取、附件正文提取、参考文献提取与可靠性核查标记。

> ⚠️ 本工具是"整理 + 核查"工具，**不保证 AI 回答与文献的真实性**。AI 生成的文献可能存在编造、拼接或信息错误，引用前务必以权威数据库逐条核对。详见 [免责声明](免责声明.md)。

## 功能

- **可搜索网页查看器**：按日期分组、关键词搜索高亮、日期范围/附件筛选、检索结果导出 JSON，单文件离线可用。
- **Markdown 摘要目录**：每段对话一个文件 + 总目录。
- **归纳文档**：Markdown → Word（规范排版）/ PDF，便于打印与传阅。
- **速览卡片与登记表**：每段对话一张速览卡，归档文件夹自动生成登记表。
- **分享链接批量抓取**：DeepSeek 下载页无法筛选指定对话时，按分享链接批量获取并合并。
- **本地关键词检索**：整包导出后本地检索筛选，命中对话可导出子集。
- **附件正文提取**：读取 Word/PDF/Excel 等附件文档正文（支持开放获取论文补全）。
- **参考文献核查**：半自动调用 Crossref 解析 DOI / 书目检索，输出"倾向"标记候选表，供人工复核后定稿。

## 环境要求

- Python 3（推荐 python-docx、pypdf/pdfplumber、openpyxl）
- 生成 PDF 需要本机安装 Microsoft Edge
- 可选：OfficeCLI（`officecli view <file> text`，Office 文档优先用它提取）

## 快速开始

```bash
# 1. 抓取分享链接（可选；也可直接解析 DeepSeek 导出文件/文件夹）
python scripts/fetch_share.py <分享链接或share_id> [...] -o share_data

# 2. 解析归一化
python scripts/parse_deepseek.py <zip/JSON/文件夹> -o conversations.normalized.json

# 3. 生成查看成果
python scripts/build_html.py conversations.normalized.json -o index.html
python scripts/build_markdown.py conversations.normalized.json -o digests
python scripts/build_cards.py cards conversations.normalized.json -o .

# 4. 归纳并生成 Word/PDF
python scripts/extract_references.py conversations.normalized.json --append 归纳.md
python scripts/build_docx.py 归纳.md -o 归纳.docx
python scripts/build_pdf.py 归纳.md -o 归纳.pdf
```

详细说明见 [使用说明](使用说明.md)。

## 测试记录

已完成 8 段真实对话测试（场景覆盖：全流程、附件提取、文献核查、多段合并、新工具、去重、无文献、附件补全）。测试内容已脱敏，仅以编号与场景类型列出，见 [测试记录](测试记录.md)。

## 免责声明

AI 检索/生成的文献可能编造或不准确；本工具的核查标记为自动化"倾向"结果，仅供人工复核参考；归纳分析内容由 AI 生成，仅作参考，请对照原始对话。完整条款见 [免责声明](免责声明.md)。

## 许可证

MIT（发布前请确认作者署名与许可证条款，见 [LICENSE](LICENSE)）。
