#!/usr/bin/env python3
"""
KAI v0 - Web 版 (V3.6 RAG 增强版)
基于 Streamlit 的业务分身对话界面
集成 Chroma 向量库 + Rerank + 外部 Prompt
"""

import streamlit as st
import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts", "kai_engine"))

from brain import KAIBrain

# 页面配置
st.set_page_config(
    page_title="KAI v3.6 - 工作分身",
    page_icon="💼",
    layout="wide"
)

st.title("💼 KAI v3.6: 工作分身")
st.caption("基于 Chroma RAG + 外部 Prompt | 风格：冷酷/逻辑/数据驱动 | PREP 流程")

# 初始化缓存（防止每次提问都重读文件）
@st.cache_resource
def init_brain():
    """初始化 KAI 大脑 V3.6"""
    return KAIBrain()

try:
    brain = init_brain()
    st.success("🧠 KAI v3.6 已上线 | RAG + External Prompt + I/O")
except Exception as e:
    st.error(f"❌ 大脑加载失败: {e}")
    st.stop()

# 聊天记录管理
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 处理输入
if prompt := st.chat_input("输入业务问题..."):
    # 用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # KAI 回复
    with st.chat_message("assistant"):
        with st.spinner("🧠 KAI 正在调取 RAG 记忆库..."):
            result = brain.think(prompt)

        # result 格式: {"response": str, "retrieved": list}
        response = result["response"]
        retrieved = result.get("retrieved", [])

        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

        # 可选：显示检索到的记忆片段
        if retrieved:
            with st.expander("📎 检索到的记忆片段"):
                for i, r in enumerate(retrieved):
                    score = r.get('score', 0)
                    text = r.get('text', '')[:150]
                    st.text(f"[{score:.3f}] {text}...")
