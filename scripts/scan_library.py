# -*- coding: utf-8 -*-
"""
KAI 图书管理员 v2.0 (防偷懒版)
功能：智能处理 PDF，生成结构化 Markdown 笔记
支持：文字版 PDF（直接提取）+ 扫描版 PDF（OCR 识别）

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


def extract_page_text(page):
    """单页提取：优先文字，失败则 OCR"""
    # 1. 尝试直接提取文字
    text = page.extract_text()
    if text and len(text) > 50:
        return text, "text"

    # 2. 扫描版，尝试 OCR
    try:
        img = page.to_image(resolution=150).original
        ocr_text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        if ocr_text and len(ocr_text) > 30:
            return ocr_text, "ocr"
    except Exception as e:
        pass

    return None, "none"


def extract_text_smartly(pdf_path):
    """
    智能提取：
    - <50页：全提取
    - >50页：前30页 + 后5页（三明治切片）
    - 扫描版自动 OCR
    """
    full_text = ""
    ocr_pages = 0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"   📄 共 {total_pages} 页...")

            if total_pages < 50:
                # 全读
                for i, page in enumerate(pdf.pages):
                    text, method = extract_page_text(page)
                    if text:
                        full_text += text + "\n"
                        if method == "ocr":
                            ocr_pages += 1
                            print(f"   📷 第 {i+1} 页 OCR")
            else:
                # 三明治切片
                print("   ✂️ 书籍较长，启动'三明治切片'模式...")

                # 前 30 页
                for i in range(min(30, total_pages)):
                    text, method = extract_page_text(pdf.pages[i])
                    if text:
                        full_text += text + "\n"
                        if method == "ocr":
                            ocr_pages += 1
                            print(f"   📷 第 {i+1} 页 OCR")

                full_text += "\n\n......(中间案例省略)......\n\n"

                # 后 5 页
                for i in range(max(30, total_pages - 5), total_pages):
                    text, method = extract_page_text(pdf.pages[i])
                    if text:
                        full_text += text + "\n"
                        if method == "ocr":
                            ocr_pages += 1
                            print(f"   📷 第 {i+1} 页 OCR")

        if ocr_pages > 0:
            print(f"   📷 共 OCR 识别 {ocr_pages} 页")

        return full_text if full_text.strip() else None

    except Exception as e:
        print(f"   ❌ 读取失败: {e}")
        return None


def summarize_with_glm(content, filename):
    today = datetime.now().strftime("%Y-%m-%d")

    # 强制截断保护
    if len(content) > 60000:
        content = content[:50000] + "\n...(中间过长截断)...\n" + content[-5000:]
        print(f"   ⚠️ 文本过长，已压缩至 {len(content)} 字符")

    prompt = f"""
    # Role
    你是KAI系统的首席图书管理员。你的任务是强制从文本中提炼干货，**严禁偷懒**。

    # Task
    阅读以下文档（可能是书籍的精选片段），生成一份深度 Markdown 笔记。
    **即使文本显示不完整，也要基于现有内容进行最大程度的总结，绝对不要输出“由于文档过长无法生成”之类的废话。**

    # Output Template
    # {{标题}}

    > 📂 来源：{filename}
    > 🏷️ 标签：#PDF #阅读笔记 {{自动补充2个标签}}
    > 📅 日期：{today}

    ## 1. 核心摘要 (一句话讲透)
    (用最直白的语言概括这本书解决了什么痛点)

    ## 2. 关键洞察 (Key Insights)
    - 💡 **洞察1**：...
    - 💡 **洞察2**：...
    - 💡 **洞察3**：...

    ## 3. 核心章节脉络
    (基于读取到的内容，整理逻辑大纲)

    ## 4. KAI 行动建议
    (给读者的3个具体执行动作)

    ---
    # 输入文本
    {content}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"   ❌ GLM 请求失败: {e}")
        return None


def sanitize_filename(name):
    illegal = r'[\\/:*?"<>|]'
    name = re.sub(illegal, "", name)
    return name.strip()


def main():
    print("📚 KAI 图书管理员 v2.0 (防偷懒版) 启动...")
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.pdf')]

    if not files:
        print("📭 收件箱为空")
        return

    for file in files:
        print(f"\n📖 处理中: {file} ...")
        pdf_path = os.path.join(INPUT_FOLDER, file)

        # 1. 提取
        text_content = extract_text_smartly(pdf_path)
        if not text_content or len(text_content) < 100:
            print("   ⚠️ 内容太少或无法提取，跳过。")
            continue

        print(f"   🧠 提取字符数: {len(text_content)}，正在发送给 GLM...")

        # 2. AI 总结
        summary = summarize_with_glm(text_content, file)

        if summary:
            # 3. 保存
            safe_name = sanitize_filename(file.replace(".pdf", "").replace(".PDF", ""))
            md_filename = f"Library_{safe_name}.md"
            save_path = os.path.join(OUTPUT_FOLDER, md_filename)

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"   ✅ 笔记已生成: {md_filename}")

            # 4. 归档
            shutil.move(pdf_path, os.path.join(ARCHIVE_FOLDER, file))
            print("   📦 原文件已归档")

    print("\n" + "=" * 50)
    print("✨ 全部处理完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
