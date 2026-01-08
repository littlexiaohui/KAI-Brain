#!/usr/bin/env python3
"""
批量为现有 md 文件添加 Frontmatter 四大金刚
"""
import os
import glob
import frontmatter

# 配置文件映射
SOURCE_MAP = {
    'douyin': {'source': 'douyin', 'content_type': 'script'},
    'xiaohongshu': {'source': 'xiaohongshu', 'content_type': 'post'},
    'wechat': {'source': 'wechat', 'content_type': 'article'},
    'library': {'source': 'library', 'content_type': 'doc'},
}

def add_frontmatter(file_path, source_folder):
    """为单个文件添加 Frontmatter"""
    with open(file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    
    # 如果已有 Frontmatter 且包含 source，跳过
    if post.metadata.get('source'):
        print(f"  ⏭️  已有 Frontmatter: {os.path.basename(file_path)}")
        return False
    
    # 获取配置
    config = SOURCE_MAP.get(source_folder, {'source': source_folder, 'content_type': 'note'})
    
    from datetime import datetime
    # Inbox 里默认 author 为空（待补充），而不是 KAI
    metadata = {
        'source': config['source'],
        'created_at': datetime.now().strftime('%Y-%m-%d'),
        'author': '',  # 待补充
        'content_type': config['content_type'],
    }
    
    # 写入新文件
    from langchain.schema import Document
    new_doc = Document(page_content=post.content, metadata=metadata)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('---\n')
        for k, v in metadata.items():
            f.write(f'{k}: {v}\n')
        f.write('\n---\n\n')
        f.write(post.content)
    
    print(f"  ✅ 添加 Frontmatter: {os.path.basename(file_path)}")
    return True

def main():
    base_dir = "/Users/huangkai/Documents/KAI_Brain/00-Inbox"
    
    folders = ['douyin', 'xiaohongshu', 'wechat', 'library']
    
    total = 0
    updated = 0
    
    for folder in folders:
        folder_path = os.path.join(base_dir, folder)
        if not os.path.exists(folder_path):
            continue
        
        md_files = glob.glob(os.path.join(folder_path, "*.md"))
        print(f"\n📁 {folder}: {len(md_files)} 个文件")
        
        for file_path in md_files:
            if add_frontmatter(file_path, folder):
                updated += 1
            total += 1
    
    print(f"\n✅ 完成: {updated}/{total} 个文件添加了 Frontmatter")

if __name__ == "__main__":
    main()
