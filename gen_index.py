#!/usr/bin/env python3
"""生成知识库索引文档（支持多级目录）"""

import os
import json
from datetime import datetime

STATE_FILE = ".sync_state.json"
OUTPUT_FILE = "knowledge_base_index.md"
KB_DIR = "knowledge_base"

def main():
    # 扫描 knowledge_base 下的所有 .md 文件（递归）
    md_files = []
    for root, dirs, files in os.walk(KB_DIR):
        for f in files:
            if f.endswith('.md'):
                filepath = os.path.join(root, f)
                rel_path = os.path.relpath(filepath, KB_DIR)
                md_files.append(rel_path)

    lines = [
        "# KAI 知识库索引\n",
        f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"> 文档总数: {len(md_files)}\n",
        f"> 扫描目录: {KB_DIR}\n",
    ]

    if md_files:
        lines.append("\n## 文档列表\n")
        lines.append("| # | 文件 | 路径 |\n")
        lines.append("|---|------|------|\n")

        for i, rel_path in enumerate(sorted(md_files), 1):
            lines.append(f"| {i} | {rel_path.split('/')[-1]} | `{rel_path}` |\n")
    else:
        lines.append("\n> 未找到 md 文件\n")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"✅ 已生成 {OUTPUT_FILE}，共 {len(md_files)} 个文档")

if __name__ == "__main__":
    main()
