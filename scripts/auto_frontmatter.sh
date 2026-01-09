#!/bin/bash
# KAI 自动元数据补全脚本
# 定时任务: 0 */6 * * * /Users/huangkai/Documents/AI\ project/KAI/scripts/auto_frontmatter.sh

BASE_DIR="/Users/huangkai/Documents/KAI_Brain"
LOG_FILE="/tmp/kai_frontmatter.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始扫描..." >> "$LOG_FILE"

cd "$BASE_DIR"

# 查找缺少 source 的文件
missing=$(python3 << 'PYEOF'
import os
import glob
base_dir = "/Users/huangkai/Documents/KAI_Brain"
missing = []
for md_file in glob.glob(f"{base_dir}/**/*.md", recursive=True):
    rel = os.path.relpath(md_file, base_dir)
    if "元数据监控" in rel or rel == "欢迎.md":
        continue
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            if "source:" not in f.read(200):
                missing.append(md_file)
    except:
        pass
print('\n'.join(missing))
PYEOF
)

if [ -z "$missing" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 无需补全" >> "$LOG_FILE"
    exit 0
fi

count=$(echo "$missing" | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 发现 $count 个文件待补全" >> "$LOG_FILE"

echo "$missing" | while read f; do
    # 判断来源
    if echo "$f" | grep -q "xiaohongshu"; then
        source="xiaohongshu"; ct="post"
    elif echo "$f" | grep -q "wechat"; then
        source="wechat"; ct="article"
    elif echo "$f" | grep -q "douyin"; then
        source="douyin"; ct="script"
    elif echo "$f" | grep -q "library"; then
        source="library"; ct="doc"
    elif echo "$f" | grep -q "10-Frameworks"; then
        source="framework"; ct="note"
    else
        source="workbench"; ct="note"
    fi

    frontmatter="---
source: $source
created_at: \"$(date +%Y-%m-%d)\"
author: \"KAI\"
content_type: $ct
---

"

    content=$(cat "$f")
    echo "$frontmatter$content" > "$f"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $(basename "$f")" >> "$LOG_FILE"
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 完成: $count 个文件" >> "$LOG_FILE"
