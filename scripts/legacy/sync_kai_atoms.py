#!/usr/bin/env python3
"""
飞书云文档同步脚本 - 将飞书云文档同步到本地作为 KAI 知识库
"""

import os
import json
import requests
import markdown
from dotenv import load_dotenv

# 加载环境变量（从 config/.env）
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'))

# 配置
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
TARGET_FOLDER_TOKEN = os.getenv("TARGET_FOLDER_TOKEN")
# 可选：直接指定单个文档的 token 测试
TEST_DOC_TOKEN = os.getenv("TEST_DOC_TOKEN", "")

# 目录配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# 飞书 API 地址
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


class FeishuSync:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self.tenant_access_token = None

    def get_tenant_access_token(self):
        """获取 tenant_access_token（每次都刷新）"""
        url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()

        if data.get("code") == 0:
            self.tenant_access_token = data.get("tenant_access_token")
            return True
        else:
            print(f"✗ 获取 Token 失败: {data.get('msg')}")
            return False

    def ensure_token_valid(self):
        """确保 Token 有效，如果无效则重新获取"""
        if not self.tenant_access_token:
            return self.get_tenant_access_token()
        return True

    def get_folder_children(self, folder_token):
        """获取文件夹下的所有文件 - 使用 Drive V1 API"""
        url = f"{FEISHU_API_BASE}/drive/v1/files/{folder_token}/children"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }

        all_items = []
        page_token = None

        while True:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token

            response = requests.get(url, headers=headers, params=params)

            # 调试：打印响应状态
            print(f"  [调试] HTTP {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")

            # 处理非 JSON 响应（如 404 页面）
            try:
                data = response.json()
            except Exception:
                print(f"  [调试] 响应内容: {response.text[:200]}")
                print(f"\n✗ 无法访问文件夹内容 (HTTP {response.status_code})")
                return []

            if data.get("code") == 0:
                items = data.get("data", {}).get("items", [])
                all_items.extend(items)
                print(f"  -> 获取到 {len(items)} 个文件")

                page_token = data.get("data", {}).get("page_token")
                if not page_token:
                    break
            else:
                print(f"获取文件夹内容失败: {data.get('msg')}")
                break

        return all_items

    def get_document_content(self, doc_token):
        """获取文档内容（Blocks）- 递归获取所有 blocks"""
        self.ensure_token_valid()
        url = f"{FEISHU_API_BASE}/docx/v1/documents/{doc_token}/blocks"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}"
        }

        all_blocks = []
        page_token = None

        while True:
            params = {"page_size": 500, "user_id_type": "open_id"}
            if page_token:
                params["page_token"] = page_token

            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if data.get("code") == 0:
                blocks = data.get("data", {}).get("items", [])
                all_blocks.extend(blocks)

                # 递归获取所有子 blocks
                for block in blocks:
                    if block.get("children"):
                        child_blocks = self.get_child_blocks(doc_token, block["children"], headers)
                        all_blocks.extend(child_blocks)

                page_token = data.get("data", {}).get("page_token")
                if not page_token:
                    break
            else:
                print(f"获取文档内容失败: {data.get('msg')}")
                break

        return all_blocks

    def get_child_blocks(self, doc_token, child_ids, headers):
        """获取子 blocks - 逐个获取"""
        all_child_blocks = []

        for child_id in child_ids:
            url = f"{FEISHU_API_BASE}/docx/v1/documents/{doc_token}/blocks/{child_id}"
            params = {"user_id_type": "open_id"}

            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            if data.get("code") == 0:
                block = data.get("data", {})
                all_child_blocks.append(block)

                # 递归获取子 blocks 的子 blocks
                if block.get("children"):
                    child_blocks = self.get_child_blocks(doc_token, block["children"], headers)
                    all_child_blocks.extend(child_blocks)

        return all_child_blocks

    def get_document_title(self, doc_token):
        """获取文档标题"""
        self.ensure_token_valid()
        url = f"{FEISHU_API_BASE}/docx/v1/documents/{doc_token}"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}"
        }

        response = requests.get(url, headers=headers)
        data = response.json()

        if data.get("code") == 0:
            return data.get("data", {}).get("document", {}).get("title", "untitled")
        return "untitled"

    def download_image(self, image_key, doc_token):
        """下载图片到本地 assets 目录"""
        # 先获取图片下载链接
        url = f"{FEISHU_API_BASE}/drive/v1/files/{image_key}"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}"
        }

        response = requests.get(url, headers=headers)
        data = response.json()

        if data.get("code") == 0:
            download_url = data.get("data", {}).get("download_url")
            if download_url:
                # 下载图片
                img_response = requests.get(download_url)
                if img_response.status_code == 200:
                    # 生成文件名
                    ext = ".png"
                    content_type = img_response.headers.get("Content-Type", "")
                    if "jpeg" in content_type:
                        ext = ".jpg"
                    elif "gif" in content_type:
                        ext = ".gif"
                    elif "webp" in content_type:
                        ext = ".webp"

                    filename = f"{doc_token}_{image_key[-8:]}{ext}"
                    filepath = os.path.join(ASSETS_DIR, filename)

                    # 保存图片
                    with open(filepath, "wb") as f:
                        f.write(img_response.content)

                    return f"./assets/{filename}"

        return None

    def block_to_markdown(self, block, doc_token):
        """将单个 Block 转换为 Markdown"""
        # 规范化 block 结构：有些 API 返回 {block: {...}}，有些直接返回 block 内容
        if "block" in block:
            actual_block = block["block"]
            block_type = actual_block.get("block_type")
            block_content = actual_block
            has_children = bool(block.get("children"))
        else:
            block_type = block.get("block_type")
            block_content = block
            has_children = bool(block.get("children"))

        # 如果是容器 block（有 children），跳过转换，内容在子 blocks 中
        if has_children and block_type == 1:
            return ""

        md_text = ""

        if block_type == 1:  # 文本
            text_elements = block_content.get("text", {}).get("elements", [])
            for elem in text_elements:
                if elem.get("type") == "text":
                    text_run = elem.get("text_run", {})
                    content = text_run.get("content", "")

                    # 处理行内样式
                    if elem.get("text_element_style", {}).get("bold"):
                        content = f"**{content}**"
                    if elem.get("text_element_style", {}).get("italic"):
                        content = f"*{content}*"
                    if elem.get("text_element_style", {}).get("strikethrough"):
                        content = f"~~{content}~~"
                    if elem.get("text_element_style", {}).get("code"):
                        content = f"`{content}`"

                    md_text += content
                elif elem.get("type") == "equation":
                    md_text += elem.get("equation", {}).get("content", "")

        elif block_type == 2:  # 普通段落文本
            text_field = block_content.get("text", {})
            elements = text_field.get("elements", [])
            if not elements:
                elements = block_content.get("elements", [])
            text = self._extract_text_from_elements(elements)
            md_text = f"{text}\n\n"

        elif block_type == 3:  # 标题2 (飞书 API 中 block_type=3 是 heading1 一级标题)
            # 内容在 heading1 字段里，不是 text 字段
            elements = block_content.get("heading1", {}).get("elements", [])
            if not elements:
                elements = block_content.get("text", {}).get("elements", [])
            text = self._extract_text_from_elements(elements)
            md_text = f"## {text}\n\n"

        elif block_type == 4:  # 标题3 (heading2)
            elements = block_content.get("heading2", {}).get("elements", [])
            if not elements:
                elements = block_content.get("text", {}).get("elements", [])
            text = self._extract_text_from_elements(elements)
            md_text = f"### {text}\n\n"

        elif block_type == 5:  # 标题4 (heading3)
            elements = block_content.get("heading3", {}).get("elements", [])
            if not elements:
                elements = block_content.get("text", {}).get("elements", [])
            text = self._extract_text_from_elements(elements)
            md_text = f"#### {text}\n\n"

        elif block_type == 7:  # 引用
            text = self._extract_text_from_elements(block_content.get("quote", {}).get("elements", []))
            md_text = f"> {text}\n\n"

        elif block_type == 10:  # 无序列表
            text = self._extract_text_from_elements(block_content.get("bullet", {}).get("elements", []))
            md_text = f"- {text}\n"

        elif block_type == 11:  # 有序列表
            order = block_content.get('ordered', {}).get('order', 1)
            text = self._extract_text_from_elements(block_content.get("ordered", {}).get("elements", []))
            md_text = f"{order}. {text}\n"

        elif block_type == 13:  # 有序列表
            order = block_content.get('ordered', {}).get('order', 1)
            if not order:
                order = block_content.get('ordered', {}).get('style', {}).get('sequence', '1')
            text = self._extract_text_from_elements(block_content.get("ordered", {}).get("elements", []))
            md_text = f"{order}. {text}\n"

        elif block_type == 17:  # 代码块
            language = block_content.get('code', {}).get('language', '')
            code_text = self._extract_text_from_elements(block_content.get("code", {}).get("elements", []))
            md_text = f"```{language}\n{code_text}\n```\n\n"

        elif block_type == 19:  # 分割线
            md_text = "---\n\n"

        elif block_type == 21:  # 图片
            image_key = block_content.get('image', {}).get('image_key')
            if image_key:
                local_path = self.download_image(image_key, doc_token)
                if local_path:
                    md_text = f"![image]({local_path})\n\n"
                else:
                    md_text = "![image](下载失败)\n\n"

        return md_text

    def _extract_text_from_elements(self, elements):
        """从 elements 数组中提取纯文本（增强版：支持更多元素类型）"""
        text = ""
        for elem in elements:
            elem_type = elem.get("type")

            # 1. 普通文本 (text)
            if elem_type == "text":
                text += elem.get("text_run", {}).get("content", "")

            # 2. 公式 (equation)
            elif elem_type == "equation":
                text += elem.get("equation", {}).get("content", "")

            # 3. 直接是 text_run 结构
            elif "text_run" in elem:
                text += elem.get("text_run", {}).get("content", "")

            # 4. 万能兜底：遍历 elem 的所有 key，查找任何含有 content 的字段
            else:
                for key, value in elem.items():
                    if isinstance(value, dict):
                        if "content" in value:
                            text += value["content"]
                            break
                        # 有些特殊元素的内容字段叫 text_run
                        if "text_run" in value:
                            text += value["text_run"].get("content", "")
                            break

        return text

    def convert_blocks_to_markdown(self, blocks, doc_token):
        """将所有 Blocks 转换为 Markdown"""
        md_content = ""
        seen_ids = set()

        # 只处理没有子 blocks 的叶子节点，避免重复
        for block in blocks:
            # 获取 block_id（兼容两种结构）
            block_id = block.get("block_id") or (block.get("block", {}).get("block_id"))
            if block_id and block_id in seen_ids:
                continue
            if block_id:
                seen_ids.add(block_id)

            # 跳过有 children 的 block（它们是容器，内容在子 blocks 中）
            if block.get("children"):
                continue
            # 对于嵌套结构的 block
            if "block" in block and block["block"].get("children"):
                continue

            md_content += self.block_to_markdown(block, doc_token)

        return md_content

    def process_folder(self, folder_token, output_dir):
        """递归处理文件夹"""
        items = self.get_folder_children(folder_token)

        for item in items:
            item_type = item.get("type")
            token = item.get("token")
            name = item.get("name", "untitled")

            if item_type == "folder":
                # 递归处理子文件夹
                print(f"📁 进入文件夹: {name}")
                self.process_folder(token, output_dir)

            elif item_type == "file" and item.get("file_extension") == "md":
                # 处理云文档
                print(f"📄 处理文档: {name}")
                self.sync_document(token, name, output_dir)

    def sync_document(self, doc_token, title, output_dir):
        """同步单个文档"""
        # 获取文档标题（优先使用实际标题，否则用文件名）
        actual_title = self.get_document_title(doc_token)
        if actual_title and actual_title != "untitled":
            title = actual_title
        else:
            # 如果飞书返回 untitled，尝试从 STATE_FILE 恢复原有标题
            if os.path.exists(STATE_FILE):
                try:
                    with open(STATE_FILE, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    if doc_token in state and state[doc_token].get('filename'):
                        # 从已有文件名提取标题（去掉 .md 后缀）
                        old_filename = state[doc_token]['filename']
                        old_title = old_filename.replace('.md', '')
                        if old_title and old_title != 'untitled':
                            print(f"  ↳ 从记录恢复标题: {old_title}")
                            title = old_title
                except:
                    pass

        # 清理文件名
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        safe_title = safe_title.strip() or "untitled"

        # 获取文档内容
        blocks = self.get_document_content(doc_token)

        if blocks:
            # 转换为 Markdown
            md_content = self.convert_blocks_to_markdown(blocks, doc_token)

            # 处理文件名冲突
            filepath = os.path.join(output_dir, f"{safe_title}.md")
            counter = 1
            while os.path.exists(filepath):
                # 如果文件已存在且内容相同，跳过
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        existing_content = f.read()
                    if existing_content == md_content:
                        print(f"○ 无变化: {title}")
                        return
                except:
                    pass
                # 文件名冲突，加上序号区分
                safe_title = f"{safe_title}_{counter}"
                filepath = os.path.join(output_dir, f"{safe_title}.md")
                counter += 1

            # 保存文件
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)

            print(f"✓ 已保存: {filepath}")
        else:
            print(f"✗ 文档为空或获取失败: {title}")

    def run(self, test_mode=False):
        """运行同步"""
        print("=" * 50)
        print("飞书云文档同步工具")
        print("=" * 50)

        # 验证配置
        if not all([APP_ID, APP_SECRET]):
            print("✗ 请在 .env 文件中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
            return

        if test_mode and not TEST_DOC_TOKEN:
            print("✗ 测试模式需要在 .env 中配置 TEST_DOC_TOKEN")
            return

        if not test_mode and not TARGET_FOLDER_TOKEN:
            print("✗ 请在 .env 文件中配置 TARGET_FOLDER_TOKEN")
            return

        # 创建输出目录
        os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
        os.makedirs(ASSETS_DIR, exist_ok=True)

        # 认证
        if not self.get_tenant_access_token():
            return

        if test_mode:
            # 测试模式：获取单个文档
            print(f"\n测试模式：获取文档 Token: {TEST_DOC_TOKEN}")
            self.sync_document(TEST_DOC_TOKEN, "test_doc", KNOWLEDGE_BASE_DIR)
        else:
            # 开始同步
            print(f"\n开始同步文件夹 Token: {TARGET_FOLDER_TOKEN}")
            print(f"输出目录: {KNOWLEDGE_BASE_DIR}")
            print("-" * 50)

            self.process_folder(TARGET_FOLDER_TOKEN, KNOWLEDGE_BASE_DIR)

            print("-" * 50)
            print("✓ 同步完成!")

    def test_single_document(self, doc_token):
        """测试获取单个文档"""
        print("\n" + "=" * 50)
        print("测试模式：获取单个文档")
        print("=" * 50)

        # 认证
        if not self.get_tenant_access_token():
            return

        # 获取文档标题
        title = self.get_document_title(doc_token)
        print(f"文档标题: {title}")

        # 获取文档内容
        blocks = self.get_document_content(doc_token)
        print(f"获取到 {len(blocks)} 个 blocks")

        if blocks:
            md_content = self.convert_blocks_to_markdown(blocks, doc_token)
            print(f"\nMarkdown 内容预览（前500字符）:\n{md_content[:500]}")

            # 保存文件
            os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
            os.makedirs(ASSETS_DIR, exist_ok=True)
            filepath = os.path.join(KNOWLEDGE_BASE_DIR, f"{title}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"\n✓ 已保存: {filepath}")
        else:
            print("✗ 文档为空或获取失败")


def parse_doc_tokens_from_links(links_content):
    """从链接列表中提取文档 token"""
    import re
    tokens = []
    for line in links_content.strip().split('\n'):
        line = line.strip()
        # 跳过注释和空行
        if not line or line.startswith('#'):
            continue
        # 提取 token: https://ai.feishu.cn/docx/XXXXXXXXXX?...
        match = re.search(r'/docx/([a-zA-Z0-9]+)', line)
        if match:
            tokens.append(match.group(1))
    return tokens


def main():
    sync = FeishuSync(APP_ID, APP_SECRET)

    # 如果设置了 TEST_DOC_TOKEN，使用测试模式
    if TEST_DOC_TOKEN:
        sync.test_single_document(TEST_DOC_TOKEN)
    # 如果设置了多个文档列表，使用批量模式
    elif os.getenv("DOC_TOKENS"):
        doc_tokens = os.getenv("DOC_TOKENS").split(",")
        print(f"\n批量模式：同步 {len(doc_tokens)} 个文档")
        for doc_token in doc_tokens:
            doc_token = doc_token.strip()
            if doc_token:
                title = sync.get_document_title(doc_token)
                print(f"\n处理文档: {title}")
                sync.sync_document(doc_token, title, KNOWLEDGE_BASE_DIR)
    # 如果存在 docs_list.txt 文件，从文件读取链接
    elif os.path.exists("docs_list.txt"):
        print("\n从 docs_list.txt 读取文档链接...")
        with open("docs_list.txt", "r", encoding="utf-8") as f:
            content = f.read()

        doc_tokens = parse_doc_tokens_from_links(content)
        print(f"找到 {len(doc_tokens)} 个文档链接")

        if not doc_tokens:
            print("请在 docs_list.txt 中添加文档链接，每行一个")
            return

        for i, doc_token in enumerate(doc_tokens, 1):
            title = sync.get_document_title(doc_token)
            print(f"\n[{i}/{len(doc_tokens)}] 处理文档: {title}")
            sync.sync_document(doc_token, title, KNOWLEDGE_BASE_DIR)

        print(f"\n✓ 完成！共同步 {len(doc_tokens)} 个文档")
    else:
        sync.run()


if __name__ == "__main__":
    main()
