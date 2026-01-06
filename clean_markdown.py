#!/usr/bin/env python3
"""
修复 Markdown 文件的"全员标题病"问题

问题：飞书文档转换后，每段文字都被加上了 # (一级标题)
症状：文件中超过 50% 的非空行以 # 开头

解决方案：将 # 一级标题 降级为 普通文本
"""

import os
import re

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
THRESHOLD = 0.5  # 超过 50% 则判定为异常


def is_header_line(line):
    """判断是否是一级标题行"""
    stripped = line.lstrip()
    return stripped.startswith("# ") and not stripped.startswith("##")


def analyze_file(filepath):
    """分析文件，返回统计信息"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()

    non_empty_lines = [l for l in lines if l.strip()]
    header_lines = [l for l in non_empty_lines if is_header_line(l)]

    total_non_empty = len(non_empty_lines)
    header_count = len(header_lines)
    ratio = header_count / total_non_empty if total_non_empty > 0 else 0

    # 检测是否有多余空行（连续超过2个空行）
    extra_empty_lines = 0
    consecutive_empty = 0
    for line in lines:
        if line.strip() == "":
            consecutive_empty += 1
            if consecutive_empty > 2:
                extra_empty_lines += 1
        else:
            consecutive_empty = 0

    # 检测有序列表编号问题（连续的 1. 1. 1.）
    bad_list_count = 0
    prev_was_list = False
    for line in lines:
        stripped = line.strip()
        is_list = re.match(r'^1\.\s', stripped) is not None
        if is_list and prev_was_list:
            bad_list_count += 1
        prev_was_list = is_list

    # 检测空的 ### 标题
    empty_headers = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r'^###\s*$', stripped):
            empty_headers += 1

    # 检测行尾空格
    trailing_spaces = sum(1 for line in lines if line != line.rstrip())

    needs_clean = ratio > THRESHOLD and header_count > 5
    needs_clean = needs_clean or extra_empty_lines > 0
    needs_clean = needs_clean or bad_list_count > 0
    needs_clean = needs_clean or empty_headers > 0
    needs_clean = needs_clean or trailing_spaces > 0

    return {
        "total_lines": len(lines),
        "non_empty_lines": total_non_empty,
        "header_lines": header_count,
        "ratio": ratio,
        "is_abnormal": needs_clean,
        "extra_empty_lines": extra_empty_lines,
        "bad_list_count": bad_list_count,
        "empty_headers": empty_headers,
        "trailing_spaces": trailing_spaces,
    }


def clean_file(filepath):
    """修复文件：将 # 一级标题 降级为普通文本，并清理多余空行，修复有序列表编号，移除空标题和行尾空格"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_lines = len(content.splitlines())
    original_header_count = len(re.findall(r'^#[ \t]', content, re.MULTILINE))

    # 将 # 开头的行（但不是 ## 或更深的）替换为空
    cleaned_lines = []
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            # 去掉行首的 #，保留缩进
            match = re.match(r'^([ \t]*)(.*)', line)
            if match:
                prefix = match.group(1)
                rest = match.group(2).lstrip()
                if rest.startswith("# "):
                    cleaned_lines.append(prefix + rest[2:])  # 去掉 # 和后面的空格
                else:
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    # 修复有序列表编号：将 "1. 1. 1. " 替换为递增的 "1. 2. 3. "
    fixed_lines = []
    list_counter = 0
    prev_was_list = False

    for line in cleaned_lines:
        stripped = line.strip()

        # 检测是否为有序列表项（以 "1. " 开头，且上一行也是列表或当前行之前有列表）
        is_list = re.match(r'^1\.\s', stripped) is not None

        if is_list:
            if not prev_was_list:
                list_counter = 1  # 新列表开始
            else:
                list_counter += 1  # 列表继续，递增
            # 替换 "1. " 为正确的序号
            fixed_line = re.sub(r'^1\.', f'{list_counter}.', line)
            fixed_lines.append(fixed_line)
            prev_was_list = True
        else:
            fixed_lines.append(line)
            prev_was_list = False

    # 清理空的 ### 标题和多余的空行
    final_lines = []
    empty_count = 0
    extra_empty_removed = 0
    empty_headers_removed = 0

    for line in fixed_lines:
        stripped = line.strip()

        # 移除空的 ### 标题
        if re.match(r'^###\s*$', stripped):
            empty_headers_removed += 1
            continue

        if stripped == "":
            empty_count += 1
            if empty_count <= 2:  # 最多保留2个空行
                final_lines.append(line)
            else:
                extra_empty_removed += 1  # 移除多余的空行
        else:
            empty_count = 0
            # 移除行尾空格
            final_lines.append(line.rstrip())

    cleaned = "\n".join(final_lines)
    new_lines = len(cleaned.splitlines())

    # 统计修复的有序列表数量
    original_list_count = len(re.findall(r'\n1\.', '\n' + content))
    current_list_count = len(re.findall(r'\n1\.', '\n' + cleaned))
    lists_fixed = original_list_count - current_list_count

    # 写回文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(cleaned)

    return {
        "original_lines": original_lines,
        "new_lines": new_lines,
        "headers_removed": original_header_count,
        "extra_empty_removed": extra_empty_removed,
        "lists_fixed": lists_fixed,
        "empty_headers_removed": empty_headers_removed,
    }


def main():
    print("=" * 60)
    print("Markdown 文件格式修复工具")
    print("=" * 60)
    print(f"扫描目录: {KNOWLEDGE_BASE_DIR}")
    print(f"判定阈值: 超过 {THRESHOLD * 100:.0f}% 的非空行是 # 标题")
    print("=" * 60)

    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        print(f"❌ 目录不存在: {KNOWLEDGE_BASE_DIR}")
        return

    md_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith(".md")]
    print(f"找到 {len(md_files)} 个 .md 文件\n")

    fixed_files = []
    abnormal_files = []

    # 第一遍：分析
    for filename in md_files:
        filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        stats = analyze_file(filepath)

        if stats["is_abnormal"]:
            abnormal_files.append((filename, stats))
        else:
            issues = []
            if stats.get("extra_empty_lines", 0) > 0:
                issues.append(f"{stats['extra_empty_lines']} 处多余空行")
            if stats.get("empty_headers", 0) > 0:
                issues.append(f"{stats['empty_headers']} 个空标题")
            if stats.get("trailing_spaces", 0) > 0:
                issues.append(f"{stats['trailing_spaces']} 处行尾空格")
            if issues:
                print(f"  ✅ {filename} (正常, {', '.join(issues)} 已清理)")
            else:
                print(f"  ✅ {filename} (正常, 标题占比 {stats['ratio']*100:.1f}%)")

    print("-" * 60)

    # 第二遍：修复异常文件
    for filename, stats in abnormal_files:
        filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        result = clean_file(filepath)

        fixed_files.append({
            "filename": filename,
            "original_lines": result["original_lines"],
            "new_lines": result["new_lines"],
            "headers_removed": result["headers_removed"],
            "extra_empty_removed": result.get("extra_empty_removed", 0),
            "empty_headers_removed": result.get("empty_headers_removed", 0),
            "lists_fixed": result.get("lists_fixed", 0),
        })

        print(f"  🔧 已修复: {filename}")
        print(f"     标题占比: {stats['ratio']*100:.1f}%")
        print(f"     行数: {result['original_lines']} → {result['new_lines']}")
        print()

    # 总结
    print("=" * 60)
    print("修复完成！")
    print("=" * 60)
    print(f"扫描文件数: {len(md_files)}")
    print(f"正常文件数: {len(md_files) - len(abnormal_files)}")
    print(f"修复文件数: {len(fixed_files)}")

    total_headers = sum(f["headers_removed"] for f in fixed_files)
    total_empty_lines = sum(f.get("extra_empty_removed", 0) for f in fixed_files)
    total_lists_fixed = sum(f.get("lists_fixed", 0) for f in fixed_files)
    total_empty_headers = sum(f.get("empty_headers_removed", 0) for f in fixed_files)

    if fixed_files:
        print(f"\n共移除: {total_headers} 个 # 标题, {total_empty_lines} 处多余空行, {total_empty_headers} 个空标题, 修复 {total_lists_fixed} 个列表编号")
        print("\n修复后的文件列表:")
        for f in fixed_files:
            info = []
            if f["headers_removed"] > 0:
                info.append(f"移除 {f['headers_removed']} 个标题")
            if f.get("extra_empty_removed", 0) > 0:
                info.append(f"清理 {f['extra_empty_removed']} 处空行")
            if f.get("empty_headers_removed", 0) > 0:
                info.append(f"移除 {f['empty_headers_removed']} 个空标题")
            if f.get("lists_fixed", 0) > 0:
                info.append(f"修复 {f['lists_fixed']} 个列表")
            info_str = f" ({', '.join(info)})" if info else ""
            print(f"  - {f['filename']}{info_str}")


if __name__ == "__main__":
    main()
