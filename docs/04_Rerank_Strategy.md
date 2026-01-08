# KAI V3.3 Rerank 重排序策略

> 版本：V3.3
> 更新：引入 Rerank 重排序模块
> 作者：Claude Code

## 问题背景

❌ **现状**：Top-K 向量检索（类似模糊搜索），只看大概长得像不像。

**痛点示例**：
- 问：`GVM 公式是什么？`
- 向量检索可能返回：带有 G、V、M 字母的无关段落
- 真正包含公式的文档反而排在后面

## 解决方案：Rerank 重排序

✅ **升级**：Top-K (20) → Rerank (精排) → Top-N (5)

```
用户问题
    │
    ├── 粗排：向量检索 Top-20（覆盖面广）
    │       └── embedding 模型：shibing624/text2vec-base-chinese
    │
    └── 精排：Rerank 模型打分排序（精准度高）
            └── 模型：BAAI/bge-reranker-v2-m3
            └── 输出：Top-5 最相关文档
```

## 模型选型

| 模型 | 特点 | 推荐场景 |
|------|------|----------|
| **bge-reranker-v2-m3** | 支持中英文，效果 SOTA，模型权重~600MB | ✅ **生产首选** |
| bge-reranker-base | 轻量版，效果略逊 | 资源受限场景 |

**推荐理由**：
- 支持中文效果极佳
- 权重适中（几百 MB）
- FlagEmbedding 官方维护

## 实现代码

```python
from FlagEmbedding import FlagReranker

# 初始化 Rerank 模型（单例模式，避免重复加载）
reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)

def rerank_docs(query, documents):
    """
    Rerank 精排流程

    Args:
        query: 用户问题
        documents: 粗排候选文档列表

    Returns:
        精排后的 Top-N 文档列表
    """
    # 1. 构造配对：[[query, doc1], [query, doc2], ...]
    pairs = [[query, doc.page_content] for doc in documents]

    # 2. 计算分数（normalize=True 归一化到 0-1）
    scores = reranker.compute_score(pairs, normalize=True)

    # 3. 合并文档和分数，按分数降序排序
    combined = list(zip(documents, scores))
    combined.sort(key=lambda x: x[1], reverse=True)

    # 4. 取 Top-N
    top_n = [doc for doc, score in combined[:5]]

    return top_n
```

## 配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| RERANK_ENABLED | True | 是否启用 Rerank |
| RERANK_MODEL | BAAI/bge-reranker-v2-m3 | 模型名称 |
| RERANK_TOP_K | 20 | 粗排候选数（向量检索返回） |
| RERANK_TOP_N | 5 | 精排结果数（Rerank 后） |

## 效果对比

### 问：什么是 GVM 公式？

| 阶段 | 结果 | 说明 |
|------|------|------|
| **粗排 Top-5** | 1. 包含 G、V、M 字母的段落<br>2. 营销数据分析<br>3. 用户行为研究<br>4. **GVM 公式定义** ← 正确答案<br>5. 另一个无关段落 | 向量相似度不高，可能排到第4 |
| **精排 Top-5** | 1. **GVM 公式定义** ← 正确答案<br>2. GVM 应用案例<br>3. GVM 公式推导<br>4. 选品策略（含 GVM）<br>5. 排品逻辑（含 GVM） | Rerank 打分后，正确答案排到第1 |

### 问：如何提升个人能力？

| 阶段 | 结果 | 说明 |
|------|------|------|
| **粗排 Top-5** | 覆盖学习、成长、职场等多方面 | 泛化但不够精准 |
| **精排 Top-5** | 聚焦"能力成长方法论"相关内容 | 更贴合问题意图 |

## 性能考量

| 维度 | 向量检索 | Rerank |
|------|----------|--------|
| 速度 | 快（毫秒级） | 稍慢（需要计算分数） |
| 精度 | 中（依赖 embedding 质量） | 高（交叉编码器） |
| 资源 | 低（单模型） | 中（需加载 Rerank 模型） |

**优化策略**：
- Rerank 模型在首次调用时加载，之后缓存在内存
- 只对 Top-20 候选进行 Rerank，计算量可控
- `use_fp16=True` 启用半精度加速

## 依赖安装

```bash
pip3 install FlagEmbedding
```

## 相关文件

| 文件 | 功能 |
|------|------|
| `scripts/ask_kai.py` | 问答脚本（已集成 Rerank） |
| `scripts/build_index.py` | 向量化脚本 |
| `docs/04_Rerank_Strategy.md` | 本文档 |

## 常见问题

**Q: Rerank 模型加载失败？**
A: 检查网络连接，模型首次使用会自动下载（约 600MB）

**Q: Rerank 反而降低了效果？**
A: 可能是 RERANK_TOP_K 设置太小，建议设为 20-50

**Q: 如何禁用 Rerank？**
A: 设置 `RERANK_ENABLED = False` in `scripts/ask_kai.py`
