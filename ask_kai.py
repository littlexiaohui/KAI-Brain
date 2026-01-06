#!/usr/bin/env python3
"""
KAI 知识库问答脚本 - 从向量数据库检索相关内容并生成回答

使用方法：
    python3 ask_kai.py "你的问题"

依赖：
    - langchain
    - langchain-community
    - chromadb
    - langchain-huggingface
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# ========== 配置 ==========
PERSIST_DIR = "./chroma_db_data"
OUTPUT_DIR = "./outputs"

# 加载环境变量（用于 LLM API）
load_dotenv()

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def save_output(question, answer, sources):
    """
    保存问答结果到 Markdown 文件

    文件名格式：时间戳_问题前10字.md
    例如：20260106_1200_如何构建信任.md
    """
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    # 清理问题中的特殊字符，取前10个字
    safe_title = "".join(c for c in question if c.isalnum() or c in "_-—— ")[:10].strip()
    safe_title = safe_title.replace(" ", "")
    filename = f"{timestamp}_{safe_title}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # 构建 Markdown 内容
    md_content = f"""# {question}

> 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## 问题

{question}

## 回答

{answer}

## 引用来源

"""

    for i, source in enumerate(sources, 1):
        md_content += f"- {source}\n"

    # 写入文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    return filepath


def get_embedding_model():
    """
    获取 embedding 模型

    ⚠️ 重要：必须与 build_index.py 使用相同的模型！
    这里使用本地 HuggingFace 中文模型，与写入端保持一致。
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


def get_llm():
    """
    获取 LLM 模型用于生成回答

    支持：
    - MiniMax (abab6.5s-chat)
    - DeepSeek
    - OpenAI 兼容 API
    """
    api_base = os.getenv("OPENAI_API_BASE", "").rstrip("/")
    api_key = os.getenv("OPENAI_API_KEY", "")
    chat_model = os.getenv("CHAT_MODEL", "abab6.5s-chat")

    # 如果有配置 API，使用在线 LLM
    if api_base and api_key:
        logger.info(f"使用在线 LLM: {chat_model}")
        llm = ChatOpenAI(
            model=chat_model,
            openai_api_base=api_base,
            openai_api_key=api_key,
            temperature=0.7
        )
    else:
        # Fallback: 简单规则匹配（无 API 时使用）
        logger.warning("未配置 LLM API，将使用基于规则的回答")
        from langchain.llms import FakeListLLM
        llm = FakeListLLM(responses=["请配置 LLM API 以获得智能回答"])

    return llm


def create_qa_chain(vectorstore):
    """
    创建问答链
    """
    llm = get_llm()

    # 定制 prompt
    prompt_template = """基于以下内容回答问题。如果内容中没有相关信息，请直接说"知识库中没有相关内容"。

=== 背景知识 ===
{context}

=== 问题 ===
{question}

请用中文回答："""
    PROMPT = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )

    # 创建检索问答链
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        chain_type_kwargs={"prompt": PROMPT}
    )

    return qa_chain


def main():
    """
    主流程：加载向量库 -> 检索相关内容 -> 生成回答
    """
    if len(sys.argv) < 2:
        print("❌ 请提供问题，例如：")
        print("   python3 ask_kai.py \"如何提升个人能力？\"")
        return

    question = sys.argv[1]

    print("=" * 60)
    print("KAI 知识库问答")
    print("=" * 60)
    print(f"\n问题：{question}\n")

    # 1. 检查向量库
    if not os.path.exists(PERSIST_DIR):
        print("❌ 向量库不存在，请先运行 build_index.py")
        return

    logger.info(f"加载向量库: {PERSIST_DIR}")

    # 2. 加载 embedding 模型
    logger.info("初始化 embedding 模型...")
    embeddings = get_embedding_model()

    # 3. 加载向量库
    logger.info("加载向量数据库...")
    vectorstore = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings
    )

    # 4. 检查数据
    count = vectorstore._collection.count()
    logger.info(f"向量库中共有 {count} 个片段")
    print(f"📚 已索引 {count} 个知识片段\n")

    # 5. 检索相关内容
    print("🔍 检索相关知识...\n")
    docs = vectorstore.similarity_search(question, k=3)

    # 收集来源列表（去重）
    sources = []
    seen = set()
    for doc in docs:
        source = doc.metadata.get('source', '未知来源')
        if source not in seen:
            seen.add(source)
            sources.append(source)

    print("【检索结果】")
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get('source', '未知来源')
        print(f"\n--- 结果 {i} (来源: {source}) ---")
        # 显示前200字
        content = doc.page_content[:200].replace('\n', ' ')
        print(f"{content}...")

    # 6. 生成回答
    print("\n" + "=" * 60)
    print("🤖 KAI 回答：")
    print("=" * 60)

    qa_chain = create_qa_chain(vectorstore)
    result = qa_chain.invoke({"query": question})

    answer = result["result"]
    print(answer)

    # 7. 保存到文件
    filepath = save_output(question, answer, sources)
    print(f"\n✅ 已保存到: {filepath}")


if __name__ == "__main__":
    main()
