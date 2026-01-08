# -*- coding: utf-8 -*-
"""
KAI 全文搬运工 v3.0
功能：提取 PDF 全文，保留原汁原味，只做排版修复

使用：
    python3 scripts/scan_library.py
"""

import os
import shutil
import pdfplumber
from zhipuai import ZhipuAI
from datetime import datetime
import re

# ================= 配置区 =================
INPUT_FOLDER = "/Users/huangkai/Documents/KAI_Brain/00-Inbox/pdf_temp"
OUTPUT_FOLDER = "/Users/huangkai/Documents/KAI_Brain/00-Inbox/library"
ARCHIVE_FOLDER = "/Users/huangkai/Documents/KAI_Brain/00-Inbox/pdf_archive"

MODEL_NAME = "glm-4-flash"
# ========================================

# 加载 API Key
API_KEY = os.environ.get("ZHIPUAI_API_KEY", "")
if not API_KEY:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "ZHIPUAI_API_KEY" in line and "=" in line:
                    API_KEY = line.split("=", 1)[1].strip()
                    break

client = ZhipuAI(api_key=API_KEY)

for folder in [INPUT_FOLDER, OUTPUT_FOLDER, ARCHIVE_FOLDER]:
    os.makedirs(folder, exist_ok=True)


def extract_text(pdf_path):
    """直接提取全文，不切片，有多少拿多少"""
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"   📄 共 {total_pages} 页，正在全量提取...")
            for page in pdf.pages:
                extract = page.extract_text()
                if extract:
                    full_text += extract + "\n\n"
        return full_text
    except Exception as e:
        print(f"   ❌ 读取失败: {e}")
        return None


def format_full_text(content, filename):
    today = datetime.now().strftime("%Y-%m-%d")

    # 截断保护
    if len(content) > 80000:
        print(f"   ⚠️ 文本过长({len(content)}字)，将只处理前 8万字...")
        content = content[:80000]

    prompt = f"""
    # Role
    你是一位专业的书籍排版员。

    # Task
    我给你的是一段从 PDF 识别出来的原始文本，格式很乱（断行、缺乏标题符号）。
    请帮我把它整理成干净的 Markdown 格式。

    # Rules (严格执行)
    1. **保留全文**：❌ 绝对不要总结！❌ 绝对不要删减！✅ 必须保留原文的所有细节和案例。
    2. **恢复结构**：根据上下文，识别出章节标题，并加上 Markdown 的标题符号（# 一级标题, ## 二级标题）。
    3. **修复排版**：
       - 把被 PDF 强制截断的段落合并。
       - 把列表项修复为标准的 bullet points (- )。
       - 识别出文中的表格，尽可能还原为 Markdown 表格。
    4. **元数据**：在文首保留 KAI 的标准元数据头。

    # Meta Data Structure
    # {{文档标题}}
    > 📂 来源：{filename}
    > 🏷️ 标签：#全文档 #PDF原件
    > 📅 日期：{today}

    ---

    # Input Text
    {content}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # 温度设极低，确保只做搬运
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"   ❌ GLM 排版请求失败: {e}")
        return None


def sanitize_filename(name):
    illegal = r'[\\/:*?"<>|]'
    name = re.sub(illegal, "", name)
    return name.strip()


def main():
    print("📚 KAI 全文搬运工 v3.0 启动...")
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.pdf')]

    if not files:
        print("📭 收件箱为空")
        return

    for file in files:
        print(f"\n📖 处理中: {file} ...")
        pdf_path = os.path.join(INPUT_FOLDER, file)

        # 1. 提取全文
        text_content = extract_text(pdf_path)
        if not text_content:
            continue

        print(f"   🧠 原文共 {len(text_content)} 字符，正在 AI 排版重构...")

        # 2. AI 排版 (不做总结)
        formatted_md = format_full_text(text_content, file)

        if formatted_md:
            # 3. 保存（加 Full_ 前缀）
            safe_name = sanitize_filename(file.replace(".pdf", "").replace(".PDF", ""))
            md_filename = f"Full_{safe_name}.md"
            save_path = os.path.join(OUTPUT_FOLDER, md_filename)

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(formatted_md)
            print(f"   ✅ 全文已提取: {md_filename}")

            # 4. 归档
            shutil.move(pdf_path, os.path.join(ARCHIVE_FOLDER, file))
            print("   📦 原文件已归档")

    print("\n" + "=" * 50)
    print("✨ 全部处理完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
