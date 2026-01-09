#!/usr/bin/env python3
"""
KAI Brain V3.5 - RAG + Dynamic Persona + External Prompt Loading
修复核心：
让代码直接读取 'prompts/00_Basic_Chat.md'，确保 PREP 流程和语气约束生效。
"""
import os
import sys
import json
import random
import datetime
import re
from dotenv import load_dotenv
from openai import OpenAI

# 路径适配
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))

# 关键路径配置
PERSONA_PATH = os.path.join(PROJECT_ROOT, "data/persona/kai_work_v0.jsonl")
# ✅ 这里指向你上传的那个 Prompt 文件
SYSTEM_PROMPT_PATH = os.path.join(PROJECT_ROOT, "prompts/00_Basic_Chat.md")

try:
    from retrieval import search_knowledge_base
except ImportError:
    from .retrieval import search_knowledge_base

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class KAIBrain:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key: raise ValueError("❌ 缺少 DEEPSEEK_API_KEY")

        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

        # 1. 加载 Few-Shot 语料
        self.gold_examples = self._load_gold_core()

        # 2. ✅ 加载外部 System Prompt (你的 00_Basic_Chat.md)
        self.system_prompt = self._load_system_prompt()

    def _load_gold_core(self):
        """加载 JSONL 语料"""
        examples = []
        try:
            if os.path.exists(PERSONA_PATH):
                with open(PERSONA_PATH, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            examples.append(data.get('text', ''))
            else:
                print(f"⚠️ [Init] 未找到人格语料: {PERSONA_PATH}")
        except Exception as e:
            print(f"⚠️ [Init] 读取语料失败: {e}")
        return examples

    def _load_system_prompt(self):
        """加载 Markdown 提示词文件"""
        if os.path.exists(SYSTEM_PROMPT_PATH):
            try:
                with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                # print(f"⚙️ [Init] 已加载外部 Prompt: {SYSTEM_PROMPT_PATH}")
                return content
            except Exception as e:
                print(f"⚠️ 加载 Prompt 文件失败: {e}")

        print("⚠️ 未找到外部 Prompt 文件，使用默认兜底 Prompt")
        return """
        You are KAI. 请基于参考资料回答问题。
        风格：专业、冷峻、直接。
        """

    def get_dynamic_examples(self, k=3):
        """随机抽取风格样本"""
        if not self.gold_examples: return ""
        selected = random.sample(self.gold_examples, min(k, len(self.gold_examples)))
        formatted = "\n".join([f"KAI语录{i+1}: {text}" for i, text in enumerate(selected)])
        return f"\n### 风格样本 (模仿这种语气)\n{formatted}\n"

    def _save_to_file(self, query, content):
        """将思考结果固化为本地文件"""
        try:
            # 1. 准备目录
            output_dir = os.path.join(PROJECT_ROOT, "outputs")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 2. 生成文件名 (YYYYMMDD_HHMM_Query前15字.md)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            # 清洗 query 中的非法文件名字符
            safe_query = re.sub(r'[\\/*?:"<>|]', "", query).strip()[:15]
            filename = f"{timestamp}_{safe_query}.md"
            filepath = os.path.join(output_dir, filename)

            # 3. 写入内容 (加上一些元数据头)
            final_content = f"""---
created: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
query: "{query}"
tags: #KAI_Output #Brain_Dump
---

# KAI 思考反馈: {query}

{content}
"""
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(final_content)

            print(f"💾 [IO] 已归档至: outputs/{filename}")
            return filepath
        except Exception as e:
            print(f"⚠️ 文件写入失败: {e}")
            return None

    def think(self, user_query):
        # 1. RAG 检索
        print(f"\n🧠 KAI 正在调取 RAG 记忆库...")
        contexts = search_knowledge_base(user_query, top_k=5, rerank=True)

        if contexts:
            print(f"✅ 命中 {len(contexts)} 条高价值记忆")
            context_str = "\n\n---\n\n".join(contexts)
        else:
            print(f"⚠️ 未命中知识库，启动 PREP 通用逻辑...")
            context_str = "（知识库无直接记录）"

        # 2. 动态注入
        style_injection = self.get_dynamic_examples(k=3)

        # 3. 组装最终 Prompt
        # System: 来自 00_Basic_Chat.md
        # User: 风格样本 + RAG资料 + 用户问题
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
            {style_injection}

            ### 任务输入
            【参考背景 (Memory Injection)】
            {context_str}

            【主理人指令】
            {user_query}

            请严格遵循 System Prompt 中的 <执行流程> 和 <输出风格约束> 进行回应。
            如果参考背景有用，请作为逻辑支撑；如果无用，请基于你的认知执行 PREP 逻辑。
            """}
        ]

        # 4. 生成
        print("🗣️ KAI: ", end="", flush=True)
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True,
            temperature=0.4
        )

        full_ans = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                c = chunk.choices[0].delta.content
                print(c, end="", flush=True)
                full_ans += c
        print("\n")

        # ✅ 保存到文件
        self._save_to_file(user_query, full_ans)

if __name__ == "__main__":
    # 确保 prompts 目录存在且有文件
    prompt_dir = os.path.join(PROJECT_ROOT, "prompts")
    if not os.path.exists(prompt_dir):
        os.makedirs(prompt_dir)
        print(f"⚠️ 请将 00_Basic_Chat.md 放入 {prompt_dir}")

    if len(sys.argv) > 1:
        query = sys.argv[1]
        kai = KAIBrain()
        kai.think(query)
    else:
        print("请提供问题")
