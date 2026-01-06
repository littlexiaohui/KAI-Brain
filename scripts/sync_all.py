#!/usr/bin/env python3
"""同步飞书文档到 Markdown（支持增量同步）"""

import os, requests, re, json, time
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'))

APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"
KB_DIR = "knowledge_base"
STATE_FILE = ".sync_state.json"

def get_token():
    url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={'app_id': APP_ID, 'app_secret': APP_SECRET})
    return resp.json().get('tenant_access_token')

def load_state():
    """加载同步状态"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    """保存同步状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def sync_one(token, force=False):
    """同步单个文档，返回 (标题, 是否更新)"""
    headers = {'Authorization': f'Bearer {get_token()}'}

    # 获取文档信息
    resp = requests.get(f"{FEISHU_API_BASE}/docx/v1/documents/{token}", headers=headers)
    doc_info = resp.json().get('data', {}).get('document', {})
    title = doc_info.get('title', 'untitled')
    # 获取文档更新时间（飞书返回的是毫秒时间戳）
    updated_time = doc_info.get('updated_at', 0)

    # 检查是否需要更新
    state = load_state()
    if not force and token in state:
        old_time = state.get(token, {}).get('updated_at', 0)
        if updated_time <= old_time:
            return title, False  # 无需更新

    # 获取 blocks
    blocks = requests.get(f"{FEISHU_API_BASE}/docx/v1/documents/{token}/blocks", headers=headers).json()
    blocks = blocks.get('data', {}).get('items', [])

    # 转换
    md = ""
    seen = set()
    for b in blocks:
        if b.get('block_id') in seen:
            continue
        seen.add(b.get('block_id'))

        bt = b.get('block_type')
        if bt == 2:
            t = ''.join([e.get('text_run', {}).get('content', '') for e in b.get('text', {}).get('elements', [])])
            md += f"{t}\n\n"
        elif bt == 3:
            t = ''.join([e.get('text_run', {}).get('content', '') for e in b.get('heading1', {}).get('elements', [])]).strip()
            md += f"# {t}\n\n"
        elif bt == 4:
            t = ''.join([e.get('text_run', {}).get('content', '') for e in b.get('heading2', {}).get('elements', [])]).strip()
            md += f"## {t}\n\n"
        elif bt == 5:
            t = ''.join([e.get('text_run', {}).get('content', '') for e in b.get('heading3', {}).get('elements', [])]).strip()
            md += f"### {t}\n\n"
        elif bt == 10:
            t = ''.join([e.get('text_run', {}).get('content', '') for e in b.get('bullet', {}).get('elements', [])])
            md += f"- {t}\n"
        elif bt == 13:
            t = ''.join([e.get('text_run', {}).get('content', '') for e in b.get('ordered', {}).get('elements', [])])
            md += f"- {t}\n"
        elif bt == 19:
            md += "---\n\n"

    # 清理空行
    lines = md.split('\n')
    cleaned = []
    empty = 0
    for l in lines:
        if l.strip() == '':
            empty += 1
            if empty <= 2:
                cleaned.append('')
        else:
            empty = 0
            cleaned.append(l.rstrip())

    # 保存
    safe = re.sub(r'[\\/*?:"<>|]', '', title)[:50].strip()
    path = f"{KB_DIR}/{safe}.md"

    # 检查文件是否存在且内容相同
    need_write = True
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            old_content = f.read()
        if old_content == '\n'.join(cleaned):
            need_write = False

    if need_write:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(cleaned))

    # 更新状态
    state = load_state()
    state[token] = {
        'title': title,
        'updated_at': updated_time,
        'filename': f"{safe}.md"
    }
    save_state(state)

    return title, True

# 主程序
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--force', action='store_true', help='强制同步所有文档')
parser.add_argument('--full', action='store_true', help='全量同步（重新同步所有文档）')
args = parser.parse_args()

# 读取 tokens
with open('docs_list.txt') as f:
    tokens = [l.strip() for l in f if l.strip() and not l.startswith('#')]

# 提取唯一 token
unique = []
seen = set()
for l in tokens:
    if 'docx/' in l:
        t = l.split('docx/')[-1].split('?')[0].split('/')[-1]
        if t not in seen:
            seen.add(t)
            unique.append(t)

# 同步
synced = 0
updated = 0
skipped = 0

if args.full:
    # 全量同步：不清空状态，但强制重新检查每个文档
    print("[全量同步模式] - 强制检查所有文档")

for t in unique:
    title, is_updated = sync_one(t, force=args.force)
    if is_updated:
        print(f"✓ {title}")
        updated += 1
    else:
        print(f"○ {title} (无变化)")
        skipped += 1
    synced += 1

print(f"\n完成: {synced} 个文档")
print(f"  更新: {updated} 个")
print(f"  无变化: {skipped} 个")

# 固定工作流：自动更新索引
print("\n[自动更新知识库索引...]")
import subprocess
result = subprocess.run(['python3', 'gen_index.py'], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(f"⚠️ 索引更新失败: {result.stderr}")

if args.force:
    print("\n[强制模式] 已忽略时间戳，全部重新同步")
