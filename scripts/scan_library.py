# -*- coding: utf-8 -*-
"""
KAI 全文搬运工 v3.4 (PDF扫描工具)
功能：扫描 pdf_temp 中的 PDF，提取文字并保存为 Markdown
约束：全图片PDF禁止入库，会自动拦截

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
MODEL_OCR = "glm-4.6v"  # OCR 模型
MODEL_FORMAT = "glm-4.6"  # 排版模型
# ========================================

API_KEY = os.environ.get("ZHIPUAI_API_KEY", "")
if not API_KEY:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "ZHIPUAI_API_KEY" in line and "=" in line:
                    API_KEY = line.split("=", 1)[1].strip()
                    break

if not API_KEY:
    print("❌ 未找到 ZHIPUAI_API_KEY")
    exit(1)

client = ZhipuAI(api_key=API_KEY)

for folder in [INPUT_FOLDER, OUTPUT_FOLDER, ARCHIVE_FOLDER]:
    os.makedirs(folder, exist_ok=True)


def has_text_layer(pdf_path):
    """检测 PDF 是否包含可提取的文本图层"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    total_text += text
            return len(total_text.strip()) > 100, len(total_text.strip())
    except Exception as e:
        print(f"   ❌ PDF 读取错误: {e}")
        return False, 0


def pdf_to_text(pdf_path):
    """从有文本图层的 PDF 提取文字"""
    text_content = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_content += t + "\n\n"
    return text_content


def pdf_to_images(pdf_path, max_pages=None):
    """将 PDF 转为图片 (base64) - 仅用于无文本图层的 PDF"""
    images = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = list(pdf.pages)[:max_pages] if max_pages else pdf.pages
            for i, page in enumerate(pages):
                img = page.to_image(resolution=150).original
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                images.append(img_b64)
                if (i + 1) % 50 == 0:
                    print(f"   📷 已转换 {i + 1} 页...")
        return images
    except Exception as e:
        print(f"   ❌ PDF 转图片失败: {e}")
        return None


def ocr_images(images, batch_size=15):
    """分批 OCR 图片"""
    import time
    all_results = []
    total = len(images)

    for i in range(0, total, batch_size):
        batch = images[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"   🧠 OCR 第 {i + 1}-{min(i + batch_size, total)} 页 (共 {total} 页)...")

        content_parts = [{"type": "text", "text": "请逐页识别图片中的文字，直接输出，不要总结。"}]
        for img_b64 in batch:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            })

        max_retries = 3
        for retry in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=MODEL_OCR,
                    messages=[{"role": "user", "content": content_parts}],
                    temperature=0.1,
                )
                result = response.choices[0].message.content
                all_results.append(result)
                print(f"   ✅ 完成 {i + 1}-{min(i + batch_size, total)} 页")
                break
            except Exception as e:
                error_msg = str(e)
                if ("Connection error" in error_msg or "timeout" in error_msg.lower()) and retry < max_retries - 1:
                    print(f"   ⚠️ 连接失败，{retry + 1}/{max_retries} 次重试...")
                    time.sleep(3)
                else:
                    print(f"   ❌ 第 {i + 1}-{min(i + batch_size, total)} 页失败: {e}")
                    all_results.append(f"\n[OCR 失败: 第 {i + 1}-{min(i + batch_size, total)} 页]\n")
                    break

    return "\n\n--- 分隔符 ---\n\n".join(all_results)


def format_content(content, filename, char_count=0):
    """用 GLM-4.6 排版"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    if char_count > 8000:
        # 大文本分批排版
        print(f"   ⚠️ 内容较长 ({char_count} 字)，简化排版...")
        prompt = f"""请将以下文字整理成 Markdown 格式，添加适当标题，保留所有内容：

{content[:6000]}"""
    else:
        prompt = f"""
# Role
你是专业的书籍排版员。

# Task
将下面的 OCR 结果整理成干净的 Markdown 格式。

# Rules
1. 合并所有内容，按阅读顺序排列
2. 识别章节结构，加 Markdown 标题符号
3. 修复格式、表格、列表
4. 保留所有内容，不要总结

# Meta Data
> 📂 来源：{filename}
> 🏷️ 标签：#PDF #文字版
> 📅 日期：{today}
> 📊 字数：{char_count}

---

# 内容
{content}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_FORMAT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"   ⚠️ 排版失败: {e}")
        return f"# {filename}\n\n{content}"


def sanitize_filename(name):
    illegal = r'[\\/:*?"<>|]'
    name = re.sub(illegal, "", name)
    return name.strip()


def main():
    print("📚 KAI 全文搬运工 v3.4 启动...")
    print(f"   输入: {INPUT_FOLDER}")
    print(f"   输出: {OUTPUT_FOLDER}")
    print("")

    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.pdf')]

    if not files:
        print("📭 pdf_temp 文件夹为空")
        return

    for file in files:
        print(f"\n📖 处理中: {file} ...")
        pdf_path = os.path.join(INPUT_FOLDER, file)

        # 1. 检测是否有文本图层
        print("   🔍 检测 PDF 类型...")
        has_text, char_count = has_text_layer(pdf_path)

        if has_text:
            print(f"   ✅ 文字版 PDF，提取 {char_count} 字")
            text_content = pdf_to_text(pdf_path)
            formatted_md = format_content(text_content, file, char_count)
        else:
            # 全图片PDF，弹出警告并拒绝入库
            print("   ❌ 全图片PDF，禁止入库！")
            print("")
            print("=" * 50)
            print(f"   ⚠️  文件: {file}")
            print("   ⚠️  该 PDF 没有文本图层，无法直接提取")
            print("   ⚠️  请使用文字版 PDF 或 OCR 处理后重新存入")
            print("=" * 50)
            print("")
            print(f"   📦 移动到归档 (待OCR处理)...")
            shutil.move(pdf_path, os.path.join(ARCHIVE_FOLDER, file))
            print(f"   ✅ 已移至 pdf_archive，请处理后再试")
            continue

        # 2. 保存结果
        if formatted_md:
            safe_name = sanitize_filename(file.replace(".pdf", "").replace(".PDF", ""))
            md_filename = f"{safe_name}.md"
            save_path = os.path.join(OUTPUT_FOLDER, md_filename)

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(formatted_md)
            print(f"   ✅ 已保存: {md_filename}")

            # 归档原文件
            shutil.move(pdf_path, os.path.join(ARCHIVE_FOLDER, file))
            print("   📦 原文件已归档")
        else:
            print(f"   ⚠️ 处理失败")

    print("\n" + "=" * 50)
    print("✨ 全部处理完成！")
    print("=" * 50)


if __name__ == "__main__":
    import sys
    from io import BytesIO
    import base64
    main()
