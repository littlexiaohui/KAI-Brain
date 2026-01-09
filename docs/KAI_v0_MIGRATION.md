# KAI.v0 融合记录

> 融合时间：2026-01-09

## 背景

- **源项目**：`/Users/huangkai/Documents/AI project/chatlog415`
- **目标项目**：`/Users/huangkai/Documents/AI project/KAI`
- **目标**：将 KAI.v0 (业务分身) 的核心资产注入 KAI_Brain

## 核心资产

| 资产 | 源路径 | 目标路径 |
|------|--------|----------|
| 语料库 | `chatlog415/tests/etl_sandbox/corpus/kai_gold_core.jsonl` | `data/persona/kai_work_v0.jsonl` |
| 逻辑引擎 | `chatlog415/scripts/chat_kai_v0.py` | `src/kai_engine/brain.py` |

## 操作日志

### Step 1: Git 备份
```bash
cd /Users/huangkai/Documents/AI\ project/KAI
git add -A
git commit -m "chore: 备份 - KAI.v0 融合前快照"
```

### Step 2: 复制语料文件
```bash
cp chatlog415/tests/etl_sandbox/corpus/kai_gold_core.jsonl \
   KAI/data/persona/kai_work_v0.jsonl
```

### Step 3: 创建 brain.py
从 `chat_kai_v0.py` 提取核心逻辑：
- SYSTEM_PROMPT (人格定义)
- STYLE_CONSTRAINTS (说话风格)
- retrieve() (检索逻辑)
- build_system_message() (Prompt 拼接)

### Step 4: 验证
```bash
wc -l data/persona/kai_work_v0.jsonl
```

## 后续待办

- [ ] 内部验证 brain.py 是否能正常调用
- [ ] 对接 KAI_Brain 现有交互入口
- [ ] Git 提交融合后的代码
