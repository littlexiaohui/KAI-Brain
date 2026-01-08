# -*- coding: utf-8 -*-
"""
KAI 系统 ETL 实战脚本 (V5.0) - 多平台通用版
从飞书多维表读取 AI 生成的内容，清洗格式后同步到本地

使用说明：
1. 运行: python3 sync_feishu_final.py
2. 后续添加新平台：在 SOURCES 列表中添加配置即可
"""

import requests
import os
from datetime import datetime

# ============== 加载环境变量 ==============
_env_loaded = False
for _env_file in [".env", "../.env"]:
    _env_path = os.path.join(os.path.dirname(__file__), _env_file)
    if os.path.exists(_env_path):
        with open(_env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
        _env_loaded = True
        break

# ============== 多平台数据源配置 ==============
# 后续添加新平台：复制一份配置，修改对应字段即可
SOURCES = [
    {
        "name": "小红书",
        "app_id": "cli_a9bba125d9395bb6",
        "app_secret": "6Evmvygsz5N85IrcEEtVkentcJJKg3H4",
        "base_id": "BWmIb8W7aaSDV5s4FhEc4SdRndf",
        "table_id": "tblbgrbuMF1m6jHg",
        "view_id": "vewuU0SBe4",
        "content_field": "MD_Content",
        "local_folder": "00-Inbox/xiaohongshu"
    },
    {
        "name": "公众号",
        "app_id": "cli_a9bba125d9395bb6",
        "app_secret": "6Evmvygsz5N85IrcEEtVkentcJJKg3H4",
        "base_id": "IZIAbzf8iazpLPsZgxHcQOKRnig",
        "table_id": "tblClytYsGIfR8v3",
        "view_id": "vewH5nv4np",
        "content_field": "MD_Content",
        "local_folder": "00-Inbox/wechat"
    },
    {
        "name": "抖音",
        "app_id": "cli_a9bba125d9395bb6",
        "app_secret": "6Evmvygsz5N85IrcEEtVkentcJJKg3H4",
        "base_id": "GQw1bDCaVa5x5zsouJtcJEEYn3f",
        "table_id": "tbl7IUFYNP1bmuR3",
        "view_id": "vewoYfNBdV",
        "content_field": "Output",
        "local_folder": "00-Inbox/douyin",
        "raw_mode": True  # 抖音内容已处理，直接保存
    }
]

# 基础保存路径
BASE_SAVE_DIR = "/Users/huangkai/Documents/KAI_Brain"


def get_tenant_access_token(app_id, app_secret):
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {"app_id": app_id, "app_secret": app_secret}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["tenant_access_token"]


def get_table_records(access_token, base_id, table_id, view_id):
    """获取多维表记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}/records"

    params = {
        "view_id": view_id,
        "page_size": 100,
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    all_records = []
    page_token = None

    while True:
        if page_token:
            params["page_token"] = page_token

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        records = data.get("data", {}).get("items", [])
        all_records.extend(records)

        if data.get("data", {}).get("has_more"):
            page_token = data.get("data", {}).get("page_token")
        else:
            break

    return all_records


def filter_records(records):
    """筛选待同步记录：Sync_Trigger=True 且 Sync_Status≠已同步"""
    filtered = []

    for record in records:
        fields = record.get("fields", {})
        sync_trigger = fields.get("Sync_Trigger", False)
        sync_status = fields.get("Sync_Status", "")
        is_trigger_true = str(sync_trigger).lower() == "true" or sync_trigger is True

        if is_trigger_true and sync_status != "已同步":
            filtered.append(record)

    return filtered


def extract_title(raw_text, fallback_first_sentence=False):
    """从内容中提取 title 作为文件名"""
    if not raw_text:
        return "untitled"

    import re
    patterns = [
        r'^title:\s*["\'](.+?)["\']',
        r'^title:\s*(.+?)\s*$',
    ]

    for pattern in patterns:
        match = re.search(pattern, raw_text, re.MULTILINE)
        if match:
            return match.group(1).strip()

    # 抖音模式：取第一句作为标题
    if fallback_first_sentence:
        # 去除 markdown 格式符号后提取第一句
        clean_text = re.sub(r'[#*`\[\]()]', '', raw_text)
        clean_text = clean_text.strip()
        # 取第一句（中文句号、英文句号、感叹号、问号分隔）
        first_sentence = re.split(r'[。！？.!?]', clean_text, 1)[0]
        first_sentence = first_sentence.strip()
        if first_sentence:
            # 限制长度
            return first_sentence[:50] if len(first_sentence) > 50 else first_sentence

    return "untitled"


def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    if not filename:
        return "untitled"

    import re
    illegal_chars = r'[\\/:\*?"<>|]'
    filename = re.sub(illegal_chars, "", filename)
    filename = re.sub(r'\s+', "_", filename)
    filename = filename.strip("_ ")

    return filename if filename else "untitled"


def clean_code_block(text):
    """去除代码块标记"""
    if text is None:
        return ""

    text = text.strip()
    import re
    text = re.sub(r'^```markdown\s*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n```\s*$', '', text)

    return text


def inject_metadata(text, url):
    """注入 date 和 source 元数据"""
    if text is None:
        return text

    today = datetime.now().strftime("%Y-%m-%d")

    # 处理 url：如果是 dict（飞书返回的富文本格式），尝试提取 link
    if isinstance(url, dict):
        url = url.get("link") or url.get("text") or ""
    elif isinstance(url, str):
        # 处理 JSON 字符串格式
        import json
        if url.strip().startswith("{") or url.strip().startswith("["):
            try:
                url_obj = json.loads(url.replace("'", '"'))
                if isinstance(url_obj, dict):
                    url = url_obj.get("link") or url_obj.get("text") or ""
            except:
                pass

    # 如果 url 还是复杂格式，跳过 source 注入
    if url and (url.startswith("{") or url.startswith("[")):
        url = ""

    first_dash_idx = text.find("---")

    if first_dash_idx == -1:
        return text

    import re
    tags_pattern = r'^tags:\s*\[.*\]'
    tags_match = re.search(tags_pattern, text, re.MULTILINE)

    if tags_match:
        tags_end_idx = tags_match.end()
        insertion_text = f"  date: {today}\n  source: {url}\n"
        text = text[:tags_end_idx] + "\n" + insertion_text + text[tags_end_idx:]
    else:
        insert_idx = first_dash_idx + 3
        insertion_text = f"\n  date: {today}\n  source: {url}\n"
        text = text[:insert_idx] + insertion_text + text[insert_idx:]

    return text


def save_to_file(content, filename, save_dir):
    """保存文件到本地"""
    safe_filename = sanitize_filename(filename)
    if not safe_filename.endswith(".md"):
        safe_filename += ".md"

    filepath = os.path.join(save_dir, safe_filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def update_record_status(access_token, base_id, table_id, record_id):
    """更新记录的同步状态"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}/records/batch_update"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    payload = {
        "records": [
            {
                "record_id": record_id,
                "fields": {
                    "Sync_Status": "已同步"
                }
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def sync_source(source_config):
    """同步单个数据源"""
    app_id = source_config["app_id"]
    app_secret = source_config["app_secret"]

    # 获取该平台的访问令牌
    print(f"\n🚀 开始同步: {source_config['name']}")
    print(f"   🔑 获取访问令牌...")
    access_token = get_tenant_access_token(app_id, app_secret)
    print(f"   ✓ 获取成功")

    base_id = source_config["base_id"]
    table_id = source_config["table_id"]
    view_id = source_config["view_id"]
    content_field = source_config["content_field"]
    local_folder = source_config["local_folder"]

    # 确保保存目录存在
    save_dir = os.path.join(BASE_SAVE_DIR, local_folder)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 获取记录
    all_records = get_table_records(access_token, base_id, table_id, view_id)
    print(f"   📄 获取到 {len(all_records)} 条记录")

    # 筛选待同步记录
    filtered_records = filter_records(all_records)
    print(f"   📋 待同步: {len(filtered_records)} 条")

    if not filtered_records:
        print(f"   ℹ️  没有需要同步的记录")
        return

    success_count = 0

    for record in filtered_records:
        record_id = record.get("record_id")
        fields = record.get("fields", {})

        raw_content = fields.get(content_field, "")
        url = fields.get("Source_URL", "")
        filename = fields.get("FileName", "")
        if filename:
            title = filename
        else:
            title = extract_title(raw_content, fallback_first_sentence=source_config.get("raw_mode", False))

        print(f"\n   处理: {title}")

        if source_config.get("raw_mode"):
            # 抖音模式：内容已处理，直接保存
            final_content = raw_content
        else:
            # 清洗和注入元数据
            cleaned = clean_code_block(raw_content)
            final_content = inject_metadata(cleaned, url)

        # 保存
        filepath = save_to_file(final_content, title, save_dir)
        print(f"   ✅ 已保存: {filepath}")

        # 更新状态
        try:
            update_record_status(access_token, base_id, table_id, record_id)
            print(f"   🔄 状态已更新")
        except Exception as e:
            print(f"   ⚠️ 状态更新失败: {e}")

        success_count += 1

    print(f"\n✨ {source_config['name']} 同步完成: {success_count} 条")


def main():
    """主函数"""
    print("=" * 50)
    print("KAI 多平台数据同步 (V5.0)")
    print("=" * 50)

    try:
        # 遍历所有数据源
        for source in SOURCES:
            sync_source(source)

        print("\n" + "=" * 50)
        print("🎉 全部同步完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        raise


if __name__ == "__main__":
    main()
