# KAI 知识库 RAG 系统

> 版本：v2.0 | 构建日期：2026-01-06

KAI 是一个基于飞书云文档的本地知识库 RAG (Retrieval-Augmented Generation) 系统，支持文档同步、本地向量化存储和智能问答。

## 功能特性

| 模块 | 功能 | 状态 |
|------|------|------|
| 文档同步 | 从飞书云文档同步 Markdown | ✅ |
| 格式清理 | 自动修复标题、列表、空行等问题 | ✅ |
| 向量化 | 本地 Embedding 生成向量 | ✅ |
| 持久化 | Chroma 向量数据库存储 | ✅ |
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
# 同步所有文档
python3 sync_all.py

# 或测试单个文档
TEST_DOC_TOKEN=xxx python3 sync_kai_atoms.py
```

### 4. 向量化

```bash
python3 build_index.py
```

### 5. 开始问答

```bash
python3 ask_kai.py "如何提升个人能力？"
```

## 使用流程

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
| `sync_all.py` | 批量同步飞书文档 | `python3 sync_all.py` |
| `sync_kai_atoms.py` | 单文档同步测试 | `TEST_DOC_TOKEN=xxx python3 sync_kai_atoms.py` |
| `clean_markdown.py` | Markdown 格式清理 | `python3 clean_markdown.py` |
| `check_docs.py` | 检查文档标题结构 | `python3 check_docs.py` |
| `gen_index.py` | 生成知识库索引 | `python3 gen_index.py` |
| `build_index.py` | 向量化并存储到 Chroma | `python3 build_index.py` |
| `ask_kai.py` | 知识库问答 | `python3 ask_kai.py "问题"` |

### 数据目录

| 目录/文件 | 说明 |
|-----------|------|
| `knowledge_base/` | 同步后的 Markdown 文档 |
| `chroma_db_data/` | Chroma 向量数据库 |
| `docs_list.txt` | 飞书文档链接列表 |
| `.sync_state.json` | 同步状态记录 |
| `knowledge_base_index.md` | 知识库文档索引 |

### 配置文件

| 文件 | 说明 |
|------|------|
| `.env` | API 配置（需手动创建） |
| `.env.example` | 配置模板 |
| `requirements.txt` | Python 依赖 |

## 飞书文档同步规范

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
- 解决：`clean_markdown.py` 会自动修复

## RAG 系统架构

### Embedding 模型

**写入端 (build_index.py)** 和 **读取端 (ask_kai.py)** 必须使用相同的 Embedding 模型：

```python
# 使用本地 HuggingFace 中文模型
model_name = "shibing624/text2vec-base-chinese"
# 维度: 768
```

### LLM 配置

支持多种 LLM API（通过 `.env` 配置）：

```env
# MiniMax
OPENAI_API_BASE=https://api.minimax.chat/v1
CHAT_MODEL=abab6.5s-chat

# DeepSeek
OPENAI_API_BASE=https://api.deepseek.com/v1
CHAT_MODEL=deepseek-chat
```

## 项目结构

```
KAI/
├── ask_kai.py              # RAG 问答脚本
├── build_index.py          # 向量化脚本
├── sync_all.py             # 批量同步脚本
├── sync_kai_atoms.py       # 单文档同步
├── clean_markdown.py       # Markdown 清理
├── check_docs.py           # 文档检查
├── gen_index.py            # 索引生成
├── requirements.txt        # 依赖列表
├── .env                    # API 配置
├── .env.example            # 配置模板
├── docs_list.txt           # 文档链接列表
├── knowledge_base/         # Markdown 文档
│   ├── *.md               # 20个文档
│   └── ...
├── chroma_db_data/         # 向量数据库
│   ├── chroma.sqlite3
│   └── d6dd0072-.../
└── 知识库索引.md           # 文档索引
```

## 知识库统计

- **文档数量**：20 篇
- **向量片段**：103 个
- **Embedding 维度**：768
- **向量数据库**：Chroma

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
