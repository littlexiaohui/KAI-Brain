#!/usr/bin/env python3
"""
向量化脚本：将 knowledge_base 下的所有 .md 文件向量化并存储到 Chroma

使用方法：
    python3 build_index.py

依赖：
    - langchain
    - langchain-community
    - chromadb
    - langchain-openai (用于 OpenAI 兼容的 embedding 接口)
"""

import os
import glob
import logging
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# OpenAIEmbeddings 已不再需要，使用本地 HuggingFace 模型
from langchain_community.vectorstores import Chroma

# ========== 配置 ==========
KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
PERSIST_DIR = "./chroma_db_data"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# 加载环境变量
load_dotenv()

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_embedding_model():
    """
    获取 embedding 模型

    优先使用本地 HuggingFace 中文模型(shibing624/text2vec-base-chinese)，
    避免 API 调用失败的问题。
    """
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info("使用本地 HuggingFace 中文 embedding 模型: shibing624/text2vec-base-chinese")
        embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese",
            model_kwargs={'device': 'cpu'}
        )
        return embeddings
    except ImportError:
        # Fallback to sentence-transformers
        from langchain_community.embeddings import SentenceTransformerEmbeddings

        logger.info("使用 SentenceTransformer 中文 embedding 模型: shibing624/text2vec-base-chinese")
        embeddings = SentenceTransformerEmbeddings(
            model_name="shibing624/text2vec-base-chinese"
        )
        return embeddings


def load_markdown_files(base_dir):
    """
    加载目录下所有 .md 文件
    """
    md_files = glob.glob(os.path.join(base_dir, "*.md"))
    logger.info(f"找到 {len(md_files)} 个 .md 文件")

    documents = []

    for file_path in md_files:
        filename = os.path.basename(file_path)
        try:
            # 使用 TextLoader 加载 markdown
            loader = TextLoader(file_path, encoding="utf-8")
            docs = loader.load()

            # 添加文件元数据
            for doc in docs:
                doc.metadata = {
                    "source": filename,
                    "filepath": file_path,
                    "filename": filename
                }

            documents.extend(docs)
            logger.info(f"  ✓ 加载: {filename}")

        except Exception as e:
            logger.warning(f"  ✗ 加载失败 {filename}: {e}")

    logger.info(f"成功加载 {len(documents)} 个文档")
    return documents


def split_documents(documents):
    """
    使用 RecursiveCharacterTextSplitter 切分文档

    优先按 Markdown 标题切分，保持语义完整
    """
    # 分隔符优先级：Markdown 标题 > 段落 > 句子 > 单词
    separators = [
        "\n## ",      # 二级标题
        "\n### ",     # 三级标题
        "\n",         # 段落
        " ",          # 句子边界
        ""            # 单词边界
    ]

    splitter = RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True
    )

    chunks = splitter.split_documents(documents)

    logger.info(f"切分为 {len(chunks)} 个片段")
    return chunks


def create_vector_store(chunks, embeddings):
    """
    创建 Chroma 向量数据库并持久化
    """
    # 如果已存在数据库，先删除
    if os.path.exists(PERSIST_DIR):
        logger.info(f"发现已存在的数据库，将覆盖更新...")

    logger.info("正在创建向量数据库...")

    # 创建 Chroma 向量库
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )

    # 确保数据持久化
    vectorstore.persist()

    logger.info(f"✓ 向量数据库已保存到: {PERSIST_DIR}")
    return vectorstore


def main():
    """
    主流程：加载 -> 切分 -> 向量化 -> 存储
    """
    print("=" * 60)
    print("KAI 知识库向量化脚本")
    print("=" * 60)
    print()

    # 1. 检查目录
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        logger.error(f"知识库目录不存在: {KNOWLEDGE_BASE_DIR}")
        return

    # 2. 加载文档
    print(f"📂 加载文档: {KNOWLEDGE_BASE_DIR}")
    documents = load_markdown_files(KNOWLEDGE_BASE_DIR)
    print()

    if not documents:
        logger.warning("没有加载到任何文档")
        return

    # 3. 切分文档
    print("🔪 切分文档...")
    chunks = split_documents(documents)
    print()

    # 4. 初始化 embedding 模型
    print("🤖 初始化 embedding 模型...")
    try:
        embeddings = get_embedding_model()
        # 测试 embedding
        test_vector = embeddings.embed_query("测试")
        logger.info(f"Embedding 维度: {len(test_vector)}")
        print()
    except Exception as e:
        logger.error(f"初始化 embedding 失败: {e}")
        return

    # 5. 创建向量库
    print("💾 创建向量数据库...")
    vectorstore = create_vector_store(chunks, embeddings)
    print()

    # 6. 统计信息
    print("=" * 60)
    print("✅ 成功索引了 {} 个片段".format(len(chunks)))
    print(f"📁 向量库位置: {os.path.abspath(PERSIST_DIR)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
