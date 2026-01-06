import os, requests, json
from dotenv import load_dotenv
load_dotenv()

APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')

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

print(f'共 {len(unique_tokens)} 个唯一文档')
