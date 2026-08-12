# DeepSeek 导出格式与归一化说明

## DeepSeek 官方导出

「导出所有历史对话」生成 zip 压缩包，常见文件：conversations.json、conversation.json、user.json。

## 常见结构

顶层可能是：

- 数组，元素为对话对象
- 包装对象，含 "conversations" 数组
- 单个对话对象（含 "mapping" 或 "messages"）

### 对话对象常见字段

| 字段 | 说明 |
| --- | --- |
| id | 对话 ID |
| title | 标题 |
| create_time / createTime / created_at | 创建时间（秒或毫秒时间戳） |
| update_time / updateTime | 更新时间 |
| mapping | 消息树：node_id → {id, parent, children, message} |
| messages / message_list | 部分导出为扁平消息数组 |

### 消息对象

| 字段 | 说明 |
| --- | --- |
| id | 消息 ID |
| role | user / assistant / system / tool |
| content | 字符串、{"text": ...} 或分块数组（如 [{"type":"text","text":"..."}]） |
| create_time | 时间戳（秒或毫秒） |

### 附件（content 为分块数组时）

常见分块类型：

| type | 说明 | 解析结果 |
| --- | --- | --- |
| image / image_url | 图片（url 或 data URL） | {"type":"image","name","url"} |
| file / attachment / upload | 文件 | {"type":"file","name","url"} |
| files | 多个文件 | 每项一条 file 附件 |

附件统一存入消息的 attachments 字段，并汇总为对话级 attachments_count。

## 解析策略（parse_deepseek.py）

1. zip 自动解压到临时目录并查找所有 *.json；文件夹递归查找。
2. 递归提取对话对象；mapping 树按 parent/children 做 DFS，保证对话顺序正确。
3. content 归一化为纯文本：字符串原样；dict 取 text/content/value；数组拼接各分块文本。
4. 时间戳大于 1e12 视为毫秒，统一转换为秒。
5. 输出 conversations.normalized.json，按创建时间升序排列。
6. 附件从 content 分块中提取（图片 / 文件），不混入正文文本。

## 归一化 JSON 结构

```json
{
  "schema_version": 1,
  "source": "输入路径",
  "generated_at": "生成时间",
  "conversations": [
    {
      "id": "...",
      "title": "...",
      "create_time": 1712345678.0,
      "update_time": 1712345678.0,
      "message_count": 12,
      "char_count": 1234,
      "messages": [
        {"id": "...", "role": "user", "content": "文本", "create_time": 1712345678.0, "attachments": [{"type": "image", "name": "...", "url": "..."}]}
      ],
      "attachments_count": 1
    }
  ]
}
```

## summaries.json

对话 id → 一句话中文摘要的映射，供 build_html.py / build_markdown.py 使用。

## 输出格式

- build_html.py：单文件 index.html，内嵌数据，无网络依赖；左侧按日期分组排列对话主题（日期内按时间排序），支持关键词搜索（标题、正文、附件名、文档正文）、时间排序、命中高亮；对话底部单独显示附件栏（图片直接预览，文件可点击）；传入 --documents 时左侧出现「附件文档」区。
- build_markdown.py：digests/ 下 index.md（目录表格）+ 每段对话一个 Markdown 文件。
- build_docx.py：Markdown → Word（.docx）。支持 `#` 标题、`-`/`1.` 列表、`|` 表格、`**加粗**`、`*斜体*`、`` `代码` ``、`>` 引用；中文默认微软雅黑。

## 参考文献与链接提取（extract_references.py）

扫描归一化 JSON 中助手消息：

- 网页链接：`https?://...`，去重后列出，标注来源对话与消息序号。
- 疑似文献引用片段：含"参考文献 / 参考来源 / 来源 / 引自 / DOI / doi.org / PubMed / Web of Science / 知网 / 万方 / ScienceDirect"等关键词的短行。

输出 Markdown 附录"参考文献与网页链接（供核对）"，固定包含可靠性提示：AI 检索/生成的文献可能编造或不准确，须与权威数据库核对，对话讨论分析与结论仅供参考。可用 `--append 归纳.md` 直接追加到归纳文档，再经 build_docx.py 转 Word。

## 参考文献可靠性核查标记

提取后由使用该 Skill 的智能体逐条用权威数据库（PubMed / Crossref / Web of Science / 期刊官网 / 知网等）核实，并在附录中标记：

| 标记 | 含义 | 判定要点 |
| --- | --- | --- |
| ✅ | 可靠 | 权威数据库可检索到，作者/年份/标题/期刊/卷期页码一致（标注 DOI/PMID 等依据） |
| ⚠️ | 不确定 | 只能检索到部分吻合信息，或存在同名/年份/主题混淆 |
| ❌ | 存疑/不可靠 | 权威数据库检索不到，或关键信息与原文明显不符，很可能为 AI 编造 |

输出为 参考文献.verified.md：每行保留原引用文本 + 标记 + 一句核对说明（含核对来源）。网络不可用时跳过核查，仅保留"供核对"附录。

## 附件文档正文提取（extract_documents.py）

输入为文档文件或文件夹，输出 docs_extracted.json：

```json
[
  {"name": "育种试验方案.docx", "path": "C:/.../育种试验方案.docx", "text": "正文...", "char_count": 107}
]
```

提取策略：

- .docx（Word，主要目标）：优先 `officecli view <file> text`，表格内容用 python-docx 补全；OfficeCLI 不可用时回退 python-docx。
- .xlsx：优先 officecli text（按行输出各单元格值），回退 openpyxl。
- .pptx：officecli text。
- .pdf：pypdf，失败回退 pdfplumber。
- .txt / .md / .csv：直接按 UTF-8 / GBK 读取。

OfficeCLI 的 `view <file> text` 输出会去掉路径前缀（如 `[/body/p[1]]`），表格摘要 `[Table: N rows]` 会被替换为真实表格行文本。
