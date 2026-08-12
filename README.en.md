# deepseek-history-organizer

Organize DeepSeek chat history into local, searchable deliverables: an offline searchable web viewer, Markdown digests, and Word/PDF summary documents. It also supports batch fetching of share links, attachment text extraction, and reference extraction with reliability checking.

> ⚠️ This tool organizes and *checks* AI output; it does **not** guarantee the accuracy of AI answers or references. AI-generated references may be fabricated, spliced, or contain errors. Always verify against authoritative databases before citing. See [Disclaimer](免责声明.en.md).

## Features

- **Searchable web viewer**: grouped by date, keyword search with highlighting, date-range/attachment filters, and export of search results as JSON. Single offline HTML file.
- **Markdown digests**: one file per conversation plus an index.
- **Summary documents**: Markdown → Word (Chinese journal style) / PDF.
- **Quick-view cards & registry**: one card per conversation; auto-generated folder registry for archived documents.
- **Batch share-link fetching**: when DeepSeek's export page cannot filter specific conversations, fetch them by share links.
- **Local keyword search**: search the full export locally, then export the selected subset.
- **Attachment text extraction**: read Word/PDF/Excel attachment content (open-access papers can be supplemented from legitimate sources).
- **Reference checking**: semi-automated Crossref/DOI resolution producing a candidate table with suggested marks (✅/⚠️/❌) for human review.

## Requirements

- Python 3 (recommended: python-docx, pypdf/pdfplumber, openpyxl)
- Microsoft Edge installed locally for PDF generation
- Optional: OfficeCLI (`officecli view <file> text`) for Office documents

## Quick Start

```bash
# 1. Fetch share links (optional; you can also parse DeepSeek export files/folders)
python scripts/fetch_share.py <share-link-or-id> [...] -o share_data

# 2. Parse & normalize
python scripts/parse_deepseek.py <zip/JSON/folder> -o conversations.normalized.json

# 3. Generate deliverables
python scripts/build_html.py conversations.normalized.json -o index.html
python scripts/build_markdown.py conversations.normalized.json -o digests
python scripts/build_cards.py cards conversations.normalized.json -o .

# 4. Summarize and export Word/PDF
python scripts/extract_references.py conversations.normalized.json --append summary.md
python scripts/build_docx.py summary.md -o summary.docx
python scripts/build_pdf.py summary.md -o summary.pdf
```

See [使用说明.en.md](使用说明.en.md) for details.

## Test Record

Eight real conversations have been tested (full pipeline, attachments, reference checking, multi-conversation merging, new tools, deduplication, no-reference scenario, attachment supplementation). Test content is anonymized and listed only by number and scenario type in [测试记录.en.md](测试记录.en.md).

## Disclaimer

AI-generated references may be unreliable; verification marks are automated "tendency" suggestions for human review only; summaries are AI-generated and should be checked against the original conversations. See [免责声明.en.md](免责声明.en.md) for full terms.

## License

MIT (please confirm authorship attribution before public release; see [LICENSE](LICENSE)).
