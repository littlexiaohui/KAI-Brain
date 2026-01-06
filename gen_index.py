#!/usr/bin/env python3
"""生成知识库索引文档"""

import os
import json
from datetime import datetime

STATE_FILE = ".sync_state.json"
OUTPUT_FILE = "knowledge_base_index.md"

def main():
    if not os.path.exists(STATE_FILE):
        print("❌ 没有同步状态文件，请先运行 sync_all.py")
        return

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    lines = [
        "# KAI 知识库索引\n",
        f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"> 文档总数: {len(state)}\n",
        "\n## 文档列表\n",
        "| # | 标题 | 文件名 | 更新时间 |\n",
        "|---|------|--------|----------|\n",
    ]

    for i, (token, info) in enumerate(state.items(), 1):
        title = info.get('title', 'Unknown')
        filename = info.get('filename', '')
        updated_at = info.get('updated_at', 0)
        if updated_at:
            date = datetime.fromtimestamp(updated_at).strftime('%Y-%m-%d')
        else:
            date = '-'
        lines.append(f"| {i} | {title} | `{filename}` | {date} |\n")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"✅ 已生成 {OUTPUT_FILE}，共 {len(state)} 个文档")

if __name__ == "__main__":
    main()
