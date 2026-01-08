# -*- coding: utf-8 -*-
"""
KAI 图书管理员 (V2.0)
功能：扫描 pdf_temp，处理 PDF 并生成结构化 Markdown 笔记

使用：
    python3 scripts/scan_library.py
"""

import os
import shutil
import pdfplumber
from zhipuai import ZhipuAI
from datetime import datetime
from PIL import Image
import pytesseract

# ================= 配置区 =================
INPUT_FOLDER = "/Users/huangkai/Documents/KAI_Brain/00-Inbox/pdf_temp"
OUTPUT_FOLDER = "/Users/huangkai/Documents/KAI_Brain/00-Inbox/library"
ARCHIVE_FOLDER = "/Users/huangkai/Documents/KAI_Brain/00-Inbox/pdf_archive"

MODEL_NAME = "glm-4-flash"  # GLM-4-Flash 最便宜，适合大批量
# ========================================

# 加载 API Key
API_KEY = os.environ.get("ZHIPUAI_API_KEY", "")
if not API_KEY:
    # 尝试从 config/.env 读取
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "ZHIPUAI_API_KEY" in line and "=" in line:
                    API_KEY = line.split("=", 1)[1].strip()
                    break

client = ZhipuAI(api_key=API_KEY)

# 确保文件夹存在
for folder in [INPUT_FOLDER, OUTPUT_FOLDER, ARCHIVE_FOLDER]:
    os.makedirs(folder, exist_ok=True)


def extract_text_from_pdf(pdf_path):
    """本地提取PDF文本，支持长文档和扫描版"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # 1. 优先提取文本
                extracted = page.extract_text()
                if extracted and len(extracted) > 50:  # 文本够多就用这个
                    text += extracted + "\n"
                else:
                    # 2. 扫描版 PDF，尝试 OCR
                    print(f"  📷 第 {i+1} 页尝试 OCR...")
                    try:
                        img = page.to_image(resolution=150).original
                        ocr_text = pytesseract.image_to_string(img, lang='chi_sim+eng')
                        if ocr_text:
                            text += ocr_text + "\n"
                            print(f"     OCR 提取到 {len(ocr_text)} 字")
                    except Exception as ocr_err:
                        print(f"     OCR 失败: {ocr_err}")

        return text if text.strip() else None
    except Exception as e:
        print(f"  ❌ 读取PDF失败: {e}")
        return None


def summarize_with_glm(content, filename):
    """调用GLM生成结构化笔记"""
    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
    # Role
    你是KAI系统的首席图书管理员。

    # Task
    请阅读以下文档内容，为我生成一份高质量的 Markdown 读书笔记。

    # Requirements
    1. **标题**：请自动提取或总结文档标题。
    2. **标签**：根据内容自动生成3个标签（如 #商业模式 #AI #报告）。
    3. **深度**：不要流水账，要提取洞察。
    4. **格式**：严格按照下方模板输出。

    # Output Template
    # {{标题}}

    > 📂 来源：{filename}
    > 🏷️ 标签：#PDF #Library {{自动补充标签}}
    > 📅 日期：{today}

    ## 1. 核心摘要 (Executive Summary)
    (300字以内，讲清楚这个文档解决了什么问题)

    ## 2. 关键洞察 (Key Insights)
    - 💡 **观点1**：...
    - 💡 **观点2**：...
    - 📊 **关键数据**：...

    ## 3. 章节脉络
    (核心章节的大纲)

    ## 4. KAI 行动建议
    (基于文档，给内容创作者的3个落地建议)

    ---
    # Content
    {content[:100000]}  # 截取前10万字符防止报错
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"  ❌ GLM 请求失败: {e}")
        return None


def sanitize_filename(name):
    """清理文件名中的非法字符"""
    illegal = r'[\\/:*?"<>|]'
    name = re.sub(illegal, "", name)
    return name.strip()


def main():
    print("📚 KAI 图书管理员 V2.0 启动中...")
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.pdf')]

    if not files:
        print("📭 收件箱为空 (00-Inbox/pdf_temp)")
        return

    print(f"🔍 发现 {len(files)} 个 PDF 文件，准备处理...")

    for file in files:
        print(f"\n📖 处理中: {file} ...")
        pdf_path = os.path.join(INPUT_FOLDER, file)

        # 1. 提取文字
        print("  🔍 提取文字...")
        text_content = extract_text_from_pdf(pdf_path)
        if not text_content:
            continue

        print(f"  📝 提取到 {len(text_content)} 字")

        # 2. 内容太短跳过
        if len(text_content) < 100:
            print("  ⚠️ 内容太短，跳过。")
            continue

        # 3. AI 处理
        print("  🧠 GLM 正在阅读并总结...")
        summary = summarize_with_glm(text_content, file)

        if summary:
            # 4. 保存 Markdown
            safe_name = sanitize_filename(file.replace(".pdf", "").replace(".PDF", ""))
            md_filename = f"Library_{safe_name}.md"
            save_path = os.path.join(OUTPUT_FOLDER, md_filename)

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"  ✅ 笔记已生成: {md_filename}")

            # 5. 归档原文件
            shutil.move(pdf_path, os.path.join(ARCHIVE_FOLDER, file))
            print("  📦 原文件已归档")

    print("\n" + "=" * 50)
    print("✨ 全部处理完成！")
    print("=" * 50)


if __name__ == "__main__":
    import re
    main()
