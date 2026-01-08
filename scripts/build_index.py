#!/usr/bin/env python3
"""
向量化脚本：将 knowledge_base 下的所有 .md 文件向量化并存储到 Chroma

使用方法：
    python3 scripts/build_index.py

依赖：
    - langchain
    - langchain-community
    - chromadb
    - langchain-openai (用于 OpenAI 兼容的 embedding 接口)
    - python-frontmatter (V5.1 用于解析 Frontmatter)

切分策略 (V3.3):
    - 第一层：按 Markdown 标题切分（保证语义完整性）
    - 第二层：递归细切（防止单章过长）

元数据 (V5.1 四大金刚):
    - source: 来源平台 (xiaohongshu/wechat/douyin)
    - created_at: 创建日期
    - author: 作者
    - content_type: 内容类型 (post/article/script/doc)
"""

import os
import glob
import logging
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

# ========== 配置 ==========
# 知识库目录（相对于项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_BASE_DIR = os.path.join(PROJECT_ROOT, "knowledge_base")
PERSIST_DIR = os.path.join(PROJECT_ROOT, "chroma_db_data")

# 切分参数 (V3.3 混合切分策略)
CHUNK_SIZE = 500       # 每个块约 300-500 中文字
CHUNK_OVERLAP = 50     # 重叠 50 字，防止上下文丢失

# V5.1 Frontmatter 四大金刚字段
FRONTMATTER_FIELDS = ['source', 'created_at', 'author', 'content_type']

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
    递归加载目录下所有 .md 文件
    V5.1 新增：解析 YAML Frontmatter 四大金刚字段
    """
    import frontmatter

    # 递归扫描所有子目录
    md_files = glob.glob(os.path.join(base_dir, "**/*.md"), recursive=True)
    logger.info(f"找到 {len(md_files)} 个 .md 文件")

    documents = []

    for file_path in md_files:
        filename = os.path.basename(file_path)
        try:
            # V5.1 使用 python-frontmatter 解析 Frontmatter
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)

            # 获取 Frontmatter 元数据（四大金刚）
            fm_metadata = post.metadata

            # 基础元数据
            metadata = {
                "source": fm_metadata.get('source', 'unknown'),
                "filepath": file_path,
                "filename": filename,
                "created_at": fm_metadata.get('created_at', ''),
                "author": fm_metadata.get('author', 'KAI'),
                "content_type": fm_metadata.get('content_type', 'note')
            }

            # 创建 Document
            from langchain.schema import Document
            doc = Document(page_content=post.content, metadata=metadata)

            documents.append(doc)
            logger.info(f"  ✓ 加载: {filename} [{metadata['source']}]")

        except Exception as e:
            logger.warning(f"  ✗ 加载失败 {filename}: {e}")

    logger.info(f"成功加载 {len(documents)} 个文档")
    return documents


def split_documents(documents):
    """
    V3.3 混合切分策略：MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter

    第一层：按 Markdown 标题切分（保证语义完整性）
    第二层：递归细切（防止单章过长）
    """
    # 1. 第一层：按标题切分（保留层级元数据）
    headers_to_split_on = [
        ("#", "Header 1"),      # 一级标题
        ("##", "Header 2"),     # 二级标题
        ("###", "Header 3"),    # 三级标题
    ]

    # 先按标题切分
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )
    header_splits = []
    for doc in documents:
        splits = markdown_splitter.split_text(doc.page_content)
        for split in splits:
            # 保留原有元数据 + 添加标题元数据
            split.metadata = {**doc.metadata, **split.metadata}
            split.metadata['filepath'] = doc.metadata.get('filepath', '')
            header_splits.append(split)

    logger.info(f"第一层按标题切分: {len(header_splits)} 个片段")

    # 2. 第二层：递归细切（防止单章过长）
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", " "],  # 优先按段落和句子切
        length_function=len,
        add_start_index=True
    )

    chunks = text_splitter.split_documents(header_splits)

    logger.info(f"第二层递归细切后: {len(chunks)} 个片段")
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
