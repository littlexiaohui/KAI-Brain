#!/usr/bin/env python3
"""
PDF 文本图层检测工具
功能：检测 PDF 是否包含可提取的文本图层
用法：
    检查 pdf_temp 中所有文件: python3 scripts/check_pdf_text.py
    检查指定文件: python3 scripts/check_pdf_text.py <pdf路径>
退出码：0=有文本, 1=无文本/错误
"""

import sys
import os
import pdfplumber
import warnings

# 抑制 pdfplumber 字体警告
warnings.filterwarnings('ignore')

PDF_TEMP_DIR = "/Users/huangkai/Documents/KAI_Brain/00-Inbox/pdf_temp"

def has_text_layer(pdf_path):
    """检测 PDF 是否包含文本图层"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    total_text += text

            # 如果提取到的文本超过 100 字符，认为有文本图层
            if len(total_text.strip()) > 100:
                return True, len(total_text.strip())
            else:
                return False, 0
    except Exception as e:
        print(f"   ❌ PDF 读取错误: {e}")
        return False, 0

def main():
    if len(sys.argv) < 2:
        # 检查 pdf_temp 目录中的所有 PDF
        pdf_dir = PDF_TEMP_DIR
        if not os.path.exists(pdf_dir):
            print("📁 pdf_temp 目录不存在，无需检查")
            return 0

        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            print("📭 pdf_temp 目录为空，无需检查")
            return 0

        print("🔍 检查 pdf_temp 中的 PDF 文件...")
        print("-" * 50)

        image_only_count = 0
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_file)
            has_text, char_count = has_text_layer(pdf_path)

            if has_text:
                print(f"   ✅ {pdf_file} ({char_count} 字)")
            else:
                print(f"   ❌ {pdf_file} [全图片PDF，禁止入库！]")
                image_only_count += 1

        print("-" * 50)
        if image_only_count > 0:
            print(f"⚠️  发现 {image_only_count} 个全图片PDF，已禁止入库")
            print("   请使用文字版 PDF 替换后重新扫描")
            return 1
        else:
            print(f"✅ 全部 {len(pdf_files)} 个 PDF 均包含文本图层")
            return 0

    else:
        # 检查指定文件
        pdf_path = sys.argv[1]
        if not os.path.exists(pdf_path):
            print(f"❌ 文件不存在: {pdf_path}")
            return 1

        has_text, char_count = has_text_layer(pdf_path)
        filename = os.path.basename(pdf_path)

        if has_text:
            print(f"✅ {filename} 包含文本图层 ({char_count} 字)")
            return 0
        else:
            print(f"❌ {filename} 是全图片PDF，禁止入库")
            print("")
            print("=" * 50)
            print("⚠️  该 PDF 没有可提取的文本内容")
            print("⚠️  请使用文字版 PDF 或 OCR 处理后的版本")
            print("=" * 50)
            return 1

if __name__ == "__main__":
    sys.exit(main())
