# KAI 知识库 RAG 系统

> 版本：v3.3 | 构建日期：2026-01-08

KAI 是一个基于多源内容的本地知识库 RAG 系统，支持多平台文档同步、AI 内容拆解和 PDF 全文提取。

## 功能特性

| 模块 | 功能 | 状态 |
|------|------|------|
| 多平台同步 | 飞书多维表 → KAI_Brain（小红书/公众号/抖音） | ✅ |
| 视频号拆解 | DeepSeek-R1 逐字稿分析 → douyin/ | ✅ |
| PDF 全文提取 | GLM-4.6 排版修复 → library/ | ✅ |
| 向量化 | 本地 Embedding 生成向量 | ✅ |
| 智能问答 | 基于知识库的 RAG 问答 | ✅ |

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

**或一键安装：**
```bash
pip3 install langchain langchain-community chromadb langchain-huggingface sentence-transformers python-dotenv requests markdown
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填写飞书和 LLM 配置：

```bash
cp .env.example .env
```

```env
# 飞书应用配置
FEISHU_APP_ID=你的APP_ID
FEISHU_APP_SECRET=你的APP_SECRET
TARGET_FOLDER_TOKEN=目标文件夹token

# LLM API 配置（用于生成回答）
OPENAI_API_BASE=https://api.minimax.chat/v1
OPENAI_API_KEY=你的API_KEY
CHAT_MODEL=abab6.5s-chat
```

### 3. 同步文档

```bash
# 同步多平台文档（小红书、公众号、抖音）
python3 sync_feishu_final.py

# 旧版飞书云文档同步（已归档）
python3 scripts/sync_all.py
```

### 4. PDF 全文提取

```bash
# 处理 pdf_temp/ 下的所有 PDF
python3 scripts/scan_library.py

# 输出：library/Full_xxx.md（带 # 标题修复的全文）
# 原文件自动归档到 pdf_archive/
```

### 5. 向量化

```bash
python3 scripts/build_index.py
```

### 6. 开始问答

```bash
python3 scripts/ask_kai.py "如何提升个人能力？"
```

## 内容同步工作流 V3.0

### 6.1 飞书多维表同步

```
飞书多维表 → sync_feishu_final.py → KAI_Brain/00-Inbox/{platform}/
     │
     ├── 小红书 → xiaohongshu/ (清洗 + 元数据注入)
     ├── 公众号 → wechat/ (清洗 + 元数据注入)
     └── 抖音 → douyin/ (raw_mode，直接保存)
```

**触发条件：**
- `Sync_Trigger` = true
- `Sync_Status` ≠ "已同步"

### 6.2 视频号逐字稿拆解

```
视频号文案 → 告诉 KAI "处理视频号逐字稿" → 05_Video_Analyze.md
     → DeepSeek-R1 深度拆解 → KAI_Brain/00-Inbox/douyin/

输出结构：
├── 第一部分：🎭 逐字稿复盘（语气标注、金句高光）
└── 第二部分：🧠 知识框架提炼（逻辑结构、行动建议）
```

### 6.3 PDF 全文提取

```
pdf_temp/ → scan_library.py → pdfplumber 提取 → GLM-4.6 排版
     → KAI_Brain/00-Inbox/library/Full_xxx.md
     → pdf_archive/ (原文件归档)

特性：
├── 纯文字 PDF：直接提取，修复断行
├── 扫描版 PDF：OCR 识别（pytesseract）
└── 超过 8 万字：自动截断
```

## API 配置

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   飞书云文档     │────▶│  sync_all.py    │────▶│ knowledge_base/ │
│                 │     │  文档同步        │     │  Markdown 文件  │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   智能问答      │◀────│  ask_kai.py     │◀────│ chroma_db_data/ │
│   KAI 助手      │     │  RAG 检索生成   │     │  向量数据库     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 文件说明

### 核心脚本

| 文件 | 功能 | 使用方式 |
|------|------|----------|
| `sync_feishu_final.py` | 多平台同步（小红书/公众号/抖音） | `python3 sync_feishu_final.py` |
| `scripts/scan_library.py` | PDF 全文提取（GLM-4.6） | `python3 scripts/scan_library.py` |
| `scripts/sync_all.py` | 飞书云文档同步（旧版） | `python3 scripts/sync_all.py` |
| `scripts/gen_index.py` | 生成知识库索引 | `python3 scripts/gen_index.py` |
| `scripts/build_index.py` | 向量化并存储到 Chroma | `python3 scripts/build_index.py` |
| `scripts/ask_kai.py` | 知识库问答 | `python3 scripts/ask_kai.py "问题"` |
| `scripts/legacy/` | 已归档脚本 | 备查 |

### 数据目录

| 目录/文件 | 说明 |
|-----------|------|
| `KAI_Brain/00-Inbox/` | 收件箱（多平台同步内容） |
| `KAI_Brain/00-Inbox/library/` | PDF 全文提取结果 |
| `knowledge_base/` | 飞书云文档同步（归档） |
| `chroma_db_data/` | Chroma 向量数据库 |
| `docs_list.txt` | 飞书文档链接列表 |
| `.sync_state.json` | 同步状态记录 |
| `knowledge_base_index.md` | 知识库文档索引 |

### 配置文件

| 文件 | 说明 |
|------|------|
| `config/.env` | API 配置 |
| `.env.example` | 配置模板 |
| `requirements.txt` | Python 依赖 |

## 飞书多维表同步规范

### 支持平台

| 平台 | 内容字段 | 文件名来源 | 特点 |
|------|----------|------------|------|
| 小红书 | `MD_Content` | title 字段 / 首句提取 | 需清洗格式、注入元数据 |
| 公众号 | `MD_Content` | title 字段 / 首句提取 | 需清洗格式、注入元数据 |
| 抖音 | `Output` | `FileName` 字段 | 直接保存，无需清洗 |

### 同步流程

```
飞书多维表 → Sync_Trigger=True 触发 → 获取记录 → 筛选未同步 → 保存文件 → 更新 Sync_Status=已同步
```

### 触发条件

- `Sync_Trigger` = true（触发同步）
- `Sync_Status` ≠ "已同步"（避免重复）

### Block 类型映射

| block_type | 飞书字段 | Markdown 输出 |
|------------|----------|---------------|
| 2 | text | 普通段落 |
| 3 | heading1 | `## 标题` |
| 4 | heading2 | `### 标题` |
| 5 | heading3 | `#### 标题` |
| 10 | bullet | `- 列表项` |
| 13 | ordered | `- 列表项` |
| 19 | divider | `---` |

### 同步流程

```
docs_list.txt → 提取 token → 去重 → 遍历同步 → 清理格式 → 保存
```

### 常见问题

**Q: 标题提取为空？**
- 原因：飞书文档使用了加粗段落模拟标题
- 解决：在飞书中选中文字 → 格式 → 标题 → 重新同步

**Q: 列表编号全是 `1. 1. 1.`？**
- 原因：飞书 API 返回格式问题
- 解决：`scripts/legacy/clean_markdown.py` 会自动修复

**Q: 抖音内容文件名不对？**
- 确认多维表有 `FileName` 字段
- 检查字段名大小写（飞书 API 返回的字段名是原始名称）

## RAG 系统架构

### Embedding 模型

**写入端 (build_index.py)** 和 **读取端 (ask_kai.py)** 必须使用相同的 Embedding 模型：

```python
# 使用本地 HuggingFace 中文模型
model_name = "shibing624/text2vec-base-chinese"
# 维度: 768
```

### LLM 配置

支持多种 LLM API（通过 `config/.env` 配置）：

```env
# DeepSeek（视频号逐字稿拆解）
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_API_BASE=https://api.deepseek.com

# 智谱 GLM（PDF 全文提取）
ZHIPUAI_API_KEY=xxx

# MiniMax（问答）
OPENAI_API_BASE=https://api.minimax.chat/v1
CHAT_MODEL=abab6.5s-chat
```

### PDF 依赖安装

```bash
# PDF 提取 + OCR 识别
pip3 install pdfplumber zhipuai pytesseract pillow
```

## 项目结构

```
KAI/
├── sync_feishu_final.py    # 多平台同步脚本（小红书/公众号/抖音）
├── prompts/
│   ├── 000_KAI_Menu.md     # KAI 花名册
│   ├── 01_Task_Decompose.md
│   ├── 02_Biz_Hypothesis.md
│   ├── 05_Demand_Verify.md
│   └── 06_Video_Analyze.md # 视频号逐字稿拆解
├── scripts/
│   ├── scan_library.py     # PDF 全文提取（GLM-4.6）
│   ├── sync_all.py         # 飞书云文档同步（归档）
│   ├── gen_index.py        # 索引生成
│   ├── build_index.py      # 向量化脚本
│   ├── ask_kai.py          # RAG 问答脚本
│   └── legacy/             # 已归档脚本
├── config/
│   └── .env                # API 配置
├── requirements.txt        # 依赖列表
├── .env.example            # 配置模板
├── knowledge_base/         # Markdown 文档（飞书云文档）
├── KAI_Brain/              # 知识库主目录
│   ├── 00-Inbox/           # 收件箱
│   │   ├── xiaohongshu/    # 小红书同步
│   │   ├── wechat/         # 公众号同步
│   │   ├── douyin/         # 抖音/视频号
│   │   ├── pdf_temp/       # PDF 待处理
│   │   ├── pdf_archive/    # PDF 归档
│   │   └── library/        # PDF 全文提取结果
│   └── ...
├── chroma_db_data/         # 向量数据库
└── 知识库索引.md           # 文档索引
```

## 知识库统计

- **文档数量**：93 篇
- **向量片段**：805 个
- **Embedding 维度**：768
- **向量数据库**：Chroma

## V3.3 切分策略 (Chunking Strategy)

> 2026-01-08 更新：基于 Markdown 结构的递归切分

### 问题背景

❌ **旧策略问题**：只按字符数切分（如每 500 字切一刀），会把完整段落腰斩，导致语义破碎。

✅ **新策略**：基于 Markdown 结构的递归切分，利用标题层级保证每个 Chunk 都是完整的知识点。

### 混合切分策略

**第一层：按标题切分（保证语义完整性）**

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

**第二层：递归细切（防止单章过长）**

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # 每个块约 300-500 中文字
    chunk_overlap=50,     # 重叠 50 字，防止上下文丢失
    separators=["\n\n", "\n", "。", "！", "？"]  # 优先按段落和句子切
)
```

### 配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| CHUNK_SIZE | 500 | 每块约 300-500 中文字 |
| CHUNK_OVERLAP | 50 | 段落间重叠，防止上下文丢失 |
| MAX_HEADER_LEVEL | 3 | 最多识别到三级标题 |

### 元数据增强

切分后的每个 Chunk 自动带上层级路径：

```yaml
metadata:
  source: 文件名.md
  filepath: /path/to/file.md
  Header 1: 第一章 标题
  Header 2: 1.1 小节标题
  Header 3: 1.1.1 子节标题
```

### 效果对比

| 维度 | V3.2 (旧) | V3.3 (新) |
|------|-----------|-----------|
| 切分依据 | 字符数 (800字) | 标题结构 + 递归细切 |
| 片段数 | ~600 | **805** |
| Chunk 完整性 | 可能腰斩段落 | 语义完整 |
| 元数据 | 基础 | + Header 路径 |

### 相关文件

| 文件 | 功能 |
|------|------|
| `scripts/build_index.py` | 向量化脚本（已集成新切分策略） |
| `docs/03_Chunking_Strategy.md` | 切分策略详细文档 |

## V3.3 Rerank 重排序策略

> 2026-01-08 更新：引入 Rerank 提升检索质量

### 问题背景

❌ **现状**：Top-K 向量检索（类似模糊搜索），只看大概长得像不像。

**痛点示例**：
- 问：`GVM 公式是什么？`
- 向量检索可能返回带有 G、V、M 字母的无关段落
- 真正包含公式的文档反而排在后面

### 解决方案

✅ **升级**：Top-K (20) → Rerank (精排) → Top-N (5)

```
用户问题
    │
    ├── 粗排：向量检索 Top-20（覆盖面广）
    │       └── embedding：shibing624/text2vec-base-chinese
    │
    └── 精排：Rerank 模型打分排序（精准度高）
            └── 模型：BAAI/bge-reranker-v2-m3
            └── 输出：Top-5 最相关文档
```

### 配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| RERANK_TOP_K | 20 | 粗排候选数 |
| RERANK_TOP_N | 5 | 精排结果数 |
| RERANK_MODEL | BAAI/bge-reranker-v2-m3 | 模型名称 |

### 依赖安装

```bash
pip3 install FlagEmbedding
```

### 效果对比

| 阶段 | 问"GVM 公式" |
|------|--------------|
| **粗排 Top-5** | 包含 G、V、M 字母的无关段落排第1 |
| **精排 Top-5** | GVM 公式定义排第1 |

### 相关文件

| 文件 | 功能 |
|------|------|
| `scripts/ask_kai.py` | 问答脚本（已集成 Rerank） |
| `docs/04_Rerank_Strategy.md` | Rerank 策略详细文档 |

## 核心方法论

### 人货场匹配与信任构建模型

基于视频号带货和一念草木中案例提炼。

#### 1. 核心框架

| 案例 | 人货场关键洞察 | 信任构建策略 |
|------|---------------|-------------|
| **视频号带货** | 选品→定品→排品策略（GVM公式：人来了×留得住×转得出×卖得多） | 课程内容建立专业信任 + 限时机制制造紧迫感 |
| **一念草木中** | 解决"选茶困扰"→标准化袋装+组合售卖 | "总有一款适合你"的降低决策成本策略 |

#### 2. 人货场匹配模型

```
场（渠道）→ 内容+产品+机制 → 转化
│
├── 直播前：饱和式提需（T-17天）、货盘表跟进
├── 直播中：小循环内容设计、福袋留人、贴片预告
└── 直播后：复盘迭代

货（产品）→ 标准化品控 + 降低选择门槛
├── 一念草木中：袋装组合
└── 视频号：利润品做知识亮点 + 赠品做附加值

人（用户）→ GMV = 人来了 × 留得住 × 转得出 × 卖得多
├── 人来了：活动预热 + 主题贴合需求 + 预约-到课率
├── 留得住：内容设计 + 福袋 + 贴片预告
├── 转得出：产品卖点 + 开价设计 + 紧迫性机制
└── 卖得多：多买多送 + 峰值成交 + 长尾成交设计
```

#### 3. 信任构建四层级

| 信任层级 | 视频号案例 | 一念草木中案例 | 核心逻辑 |
|---------|-----------|---------------|---------|
| 专业信任 | 知识主线完整性、讲师磨课 | 标准品控、品质背书 | "我懂我在说什么" |
| 降低决策风险 | 免单/试用机制 | "总有一款适合你"组合装 | "试试也不亏" |
| 即时反馈 | 福袋/弹幕互动 | 袋装即饮便捷 | "立刻有获得感" |
| 长期预期 | 课程小循环设计 | 低频高频化 | "持续有收益" |

#### 4. 老年人群体调整

| 维度 | 原模型（年轻人） | 老年人调整版 |
|------|-----------------|-------------|
| 人 | 追求效率、性价比 | 追求安全、陪伴、简单 |
| 货 | 功能导向、组合复杂 | 单一功能、包装清晰、操作极简 |
| 场 | 直播节奏快、信息密 | 节奏慢、重复提醒、子女可参与 |
| 信任 | 效率信任（快准省） | 安全信任（不骗人、可退换、有人管） |

**总结**：核心方法论 = **公式拆解 + 流程标准化 + 信任阶梯**

- "效率优先" → "安全优先"
- "快节奏" → "慢节奏重复"
- "自己下单" → "子女代付+关怀联动"

## 更新日志

### v3.3 (2026-01-08) - 切片策略 + Rerank 优化

**核心优化一：切片策略**
- 新增 `docs/03_Chunking_Strategy.md` 切分策略文档
- 更新 `scripts/build_index.py` 实现混合切分策略
- 第一层：MarkdownHeaderTextSplitter 按标题切分
- 第二层：RecursiveCharacterTextSplitter 递归细切
- 修复路径配置 PROJECT_ROOT
- 修复递归扫描子目录 (`**/*.md`)

**核心优化二：Rerank 重排序**
- 新增 `docs/04_Rerank_Strategy.md` Rerank 策略文档
- 更新 `scripts/ask_kai.py` 集成 Rerank 模块
- Top-K (20) → Rerank → Top-N (5)
- 模型：BAAI/bge-reranker-v2-m3
- 安装依赖：`pip3 install FlagEmbedding`

**PDF 质量约束：**
- 新增 `scripts/check_pdf_text.py` PDF 文本图层检测
- 全图片 PDF 禁止入库，自动拦截并提示
- `scripts/scan_library.py` 集成文本检测逻辑

**新增文件：**
- `docs/03_Chunking_Strategy.md` - 切分策略详细文档
- `docs/04_Rerank_Strategy.md` - Rerank 策略详细文档
- `scripts/check_pdf_text.py` - PDF 文本检测工具
- `scripts/scan_library.py` - V3.4 PDF 全文提取
- `skills/sync_feishu/` - 飞书同步 Skill

### v3.0 (2026-01-08) - 内容同步架构 V3.0

**新增功能：**
- 新增 `scripts/scan_library.py` PDF 全文提取脚本（GLM-4.6 排版）
- 新增 `06_Video_Analyze.md` 视频号逐字稿拆解 Skill（DeepSeek-R1）
- 新增抖音平台同步支持（raw_mode，直接保存）
- 新增 `05_Demand_Verify.md` 需求验证系统

**文档更新：**
- 新增内容同步工作流 V3.0 架构图
- 更新飞书多维表同步规范
- 更新 API 配置（DeepSeek + GLM）
- 更新项目结构图

### v2.2 (2026-01-08)

- 新增 `06_Video_Analyze.md` Skill（视频号逐字稿分析）
- 调整序号命名规范（05_Demand_Verify → 05，05_Video_Analyze → 06）
- 清理空文件夹 `05-Drafts/Feishu_Sync/`

### v2.1 (2026-01-07)

- 新增抖音平台同步支持（按 FileName 命名文件）
- 飞书同步路径调整为 `knowledge_base/05-Workbench/Feishu_Sync`

### v2.0 (2026-01-06)

- 新增本地 Embedding 支持（解决 API 404 问题）
- 新增 `ask_kai.py` 智能问答脚本
- 新增 RAG 检索功能
- 更新向量库持久化

### v1.x

- 飞书文档同步
- Markdown 格式清理
- 增量同步支持

## License

MIT
