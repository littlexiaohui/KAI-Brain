# KAI V3.3 切分策略 (Chunking Strategy)

> 版本：V3.3
> 更新：基于 Markdown 结构的递归切分
> 作者：Claude Code

## 问题背景

❌ **旧策略问题**：只按字符数切分（如每 500 字切一刀），会把完整段落腰斩，导致语义破碎。

✅ **新策略**：基于 Markdown 结构的递归切分，利用标题层级保证每个 Chunk 都是完整的知识点。

---

## 混合切分策略

### 第一层：按标题切分（保证语义完整性）

```python
from langchain.text_splitter import MarkdownHeaderTextSplitter

headers_to_split_on = [
    ("#", "Header 1"),      # 一级标题 = 大章节
    ("##", "Header 2"),     # 二级标题 = 小节
    ("###", "Header 3"),    # 三级标题 = 子节
]

markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
md_header_splits = markdown_splitter.split_text(markdown_text)
```

**效果**：每个 Chunk 开头自带标题元数据，保留层级路径。

### 第二层：递归细切（防止单章过长）

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # 每个块约 300-500 中文字
    chunk_overlap=50,     # 重叠 50 字，防止上下文丢失
    separators=["\n\n", "\n", "。", "！", "？"]  # 优先按段落和句子切
)
```

---

## 配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| CHUNK_SIZE | 500 | 每块约 300-500 中文字 |
| CHUNK_OVERLAP | 50 | 段落间重叠，防止上下文丢失 |
| MAX_HEADER_LEVEL | 3 | 最多识别到三级标题 |

---

## 实现代码

```python
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def intelligent_chunking(markdown_text):
    """
    KAI 智能切分：先按标题切，再递归细切
    """
    # 1. 按标题切分（保留元数据）
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(markdown_text)

    # 2. 递归细切
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？"]
    )

    final_chunks = text_splitter.split_documents(md_header_splits)
    return final_chunks
```

---

## 元数据增强

切分后的每个 Chunk 会自动带上：

```yaml
metadata:
  source: 文件名.md
  filepath: /path/to/file.md
  Header 1: 第一章 标题
  Header 2: 1.1 小节标题
  Header 3: 1.1.1 子节标题
  start_index: 123
```

**优点**：检索结果自带层级路径，方便理解上下文。

---

## 对比效果

### ❌ 旧策略（纯字符切分）
```
Chunk 1: "复盘是联想文化的重要"
Chunk 2: "组成部分复盘是实践"
→ 语义断裂，不知所云
```

### ✅ 新策略（标题+递归切分）
```
Chunk 1: "## 复盘的由来\n- 复盘是中国围棋..."
Chunk 2: "## 为什么复盘？\n- 为了知其然..."
→ 每个块都是完整知识点
```

---

## 调用方式

```bash
# 重新索引知识库
python3 scripts/build_index.py
```

---

## 相关文件

| 文件 | 功能 |
|------|------|
| `scripts/build_index.py` | 向量化脚本（已集成新切分策略） |
| `docs/03_Chunking_Strategy.md` | 本文档 |
