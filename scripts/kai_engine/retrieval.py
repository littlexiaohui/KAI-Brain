#!/usr/bin/env python3
"""
Retrieval Module - 连接 Chroma 向量库与 Rerank 精排模型
KAI Brain V3.3 记忆桥梁
"""

import os
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from FlagEmbedding import FlagReranker

# 路径配置
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
CHROMA_PATH = os.path.join(PROJECT_ROOT, "chroma_db_data")  # V3.3 标准路径

_embedding_model = None
_reranker_model = None
_vector_db = None

def get_db():
    global _embedding_model, _vector_db
    if _vector_db is None:
        print("⚙️ [Retrieval] 加载 Embedding 模型...")
        _embedding_model = HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese")
        _vector_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=_embedding_model)
    return _vector_db

def get_reranker():
    global _reranker_model
    if _reranker_model is None:
        print("⚙️ [Retrieval] 加载 Rerank 模型...")
        try:
            _reranker_model = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)
        except Exception as e:
            print(f"⚠️ Rerank 模型加载失败: {e}")
            _reranker_model = None
    return _reranker_model

def search_knowledge_base(query, top_k=5, rerank=True):
    """搜索知识库"""
    try:
        db = get_db()
        # 1. 粗排
        results = db.similarity_search_with_score(query, k=20)
        if not results:
            return []

        if not rerank:
            return [doc.page_content for doc, _ in results[:top_k]]

        # 2. 精排
        reranker = get_reranker()
        if not reranker:
            return [doc.page_content for doc, _ in results[:top_k]]

        pass_1_docs = [doc for doc, _ in results]
        pairs = [[query, doc.page_content] for doc in pass_1_docs]
        scores = reranker.compute_score(pairs)

        combined = list(zip(pass_1_docs, scores))
        combined.sort(key=lambda x: x[1], reverse=True)

        # 3. 格式化输出 (带 Metadata)
        final_docs = []
        for doc, score in combined[:top_k]:
            meta = doc.metadata
            source = meta.get('source', 'unknown')
            path = meta.get('header_path', '') or meta.get('Header 1', '')
            content = f"【来源: {source} | 路径: {path}】\n{doc.page_content}"
            final_docs.append(content)

        return final_docs
    except Exception as e:
        print(f"⚠️ 检索出错: {e}")
        return []
