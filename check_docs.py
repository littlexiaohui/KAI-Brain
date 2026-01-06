#!/usr/bin/env python3
"""逐个处理飞书文档，验证标题提取是否正确"""

import os, requests, json, re
from dotenv import load_dotenv
load_dotenv()

APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

def get_access_token():
    url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={'app_id': APP_ID, 'app_secret': APP_SECRET})
    return resp.json().get('tenant_access_token')

def check_document(token):
    """检查文档的标题结构"""
    headers = {'Authorization': f'Bearer {get_access_token()}'}

    # 获取文档标题
    url = f"{FEISHU_API_BASE}/docx/v1/documents/{token}"
    resp = requests.get(url, headers=headers)
    title = resp.json().get('data', {}).get('document', {}).get('title', 'Unknown')

    # 获取 blocks
    url = f"{FEISHU_API_BASE}/docx/v1/documents/{token}/blocks"
    resp = requests.get(url, headers=headers)
    blocks = resp.json().get('data', {}).get('items', [])

    # 统计标题 block
    heading_blocks = []
    for b in blocks:
        bt = b.get('block_type')
        text = ""
        if bt == 3:
            text = ''.join([e.get('text_run', {}).get('content', '') for e in b.get('heading1', {}).get('elements', [])])
        elif bt == 4:
            text = ''.join([e.get('text_run', {}).get('content', '') for e in b.get('heading2', {}).get('elements', [])])
        elif bt == 5:
            text = ''.join([e.get('text_run', {}).get('content', '') for e in b.get('heading3', {}).get('elements', [])])
        if text.strip():
            heading_blocks.append((bt, text.strip()))

    # 统计加粗段落（可能是模拟的标题）
    bold_paragraphs = []
    for b in blocks:
        if b.get('block_type') == 2:
            for elem in b.get('text', {}).get('elements', []):
                if elem.get('text_element_style', {}).get('bold'):
                    text = elem.get('text_run', {}).get('content', '')
                    if text.strip():
                        bold_paragraphs.append(text.strip())
                    break

    return {
        'title': title,
        'headings': heading_blocks,
        'bold_paragraphs': bold_paragraphs,
        'total_blocks': len(blocks)
    }

def main():
    # 读取 tokens
    with open('docs_list.txt') as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]

    tokens = []
    for line in lines:
        if 'docx/' in line:
            token = line.split('docx/')[1].split('?')[0].split('/')[-1]
            tokens.append(token)

    # 去重
    seen = set()
    unique_tokens = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique_tokens.append(t)

    print(f"=" * 60)
    print(f"共 {len(unique_tokens)} 个唯一文档")
    print(f"=" * 60)

    issues = []

    for i, token in enumerate(unique_tokens, 1):
        result = check_document(token)
        title = result['title']
        headings = result['headings']
        bold = result['bold_paragraphs']

        print(f"\n[{i}/{len(unique_tokens)}] {title}")
        print(f"  Token: {token[:16]}...")

        if headings:
            print(f"  ✅ 发现 {len(headings)} 个真正标题块:")
            for bt, t in headings[:5]:
                prefix = "##" if bt == 3 else ("###" if bt == 4 else "####")
                print(f"     {prefix} {t[:35]}...")
        else:
            print(f"  ⚠️ 没有真正标题块 (block_type 3/4/5)")
            if bold:
                print(f"     发现 {len(bold)} 个加粗段落 (可能是样式模拟的标题)")
                for t in bold[:3]:
                    print(f"       - {t[:35]}...")
                issues.append(f"{title}: 无真正标题，有 {len(bold)} 个加粗段落")

        # 提示是否需要处理
        if not headings and bold:
            print(f"  💡 建议: 在飞书中将加粗段落改为正式标题块")

    print(f"\n{'=' * 60}")
    if issues:
        print(f"⚠️  有 {len(issues)} 个文档缺少真正标题:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ 所有文档都有正确标题结构")

if __name__ == "__main__":
    main()
