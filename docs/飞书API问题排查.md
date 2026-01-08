# 飞书 API 问题排查

> **Version**: 2.0 | **更新日期**：2026-01-08

## 多维表同步（当前方案）

### 环境配置

| 平台 | App ID | App Secret | Base ID | Table ID |
|------|--------|------------|---------|----------|
| 小红书 | `cli_a9bba125d9395bb6` | `6Evmvygsz5N85IrcEEtVkentcJJKg3H4` | `BWmIb8W7aaSDV5s4FhEc4SdRndf` | `tblbgrbuMF1m6jHg` |
| 公众号 | `cli_a9bba125d9395bb6` | `6Evmvygsz5N85IrcEEtVkentcJJKg3H4` | `IZIAbzf8iazpLPsZgxHcQOKRnig` | `tblClytYsGIfR8v3` |
| 抖音 | `cli_a9bba125d9395bb6` | `6Evmvygsz5N85IrcEEtVkentcJJKg3H4` | `GQw1bDCaVa5x5zsouJtcJEEYn3f` | `tbl7IUFYNP1bmuR3` |

### 字段映射

| 字段名 | 说明 |
|--------|------|
| `Sync_Trigger` | 布尔值，true 触发同步 |
| `Sync_Status` | 同步状态，写入"已同步" |
| `Source_URL` | 原始链接 |
| `FileName` | 抖音文件名来源 |
| `Output` | 抖音内容字段 |
| `MD_Content` | 小红书/公众号内容字段 |

### 已开通权限

- `bitable:app` - 多维表读取
- `bitable:record` - 记录读写

---

## 飞书云文档同步（旧方案，已归档）

### 环境配置

- **App ID**: `cli_a9c1e3d92538dbc7`
- **App Secret**: `jne7sLkgTL8lD8ZX8Hdi0bdoMCFQrtdO`
- **目标文件夹 Token**: `VnVgf3cjpl7IePdhiJFc6oxRnic`
- **文件夹名称**: `KAI-知识原子库`
- **文件夹位置**: 根目录共享文件夹

### 已开通权限

已在飞书开放平台开通以下权限：
- `drive:file` - 云盘文件读写
- `docx:document` - 文档读取
- `docx:block` - 文档块读取
- `search:file` - 搜索文件

## API 测试结果汇总（2026-01-05）

### ✅ 成功的 API

| API | Endpoint | 说明 |
|-----|----------|------|
| 获取 tenant_access_token | `/auth/v3/tenant_access_token/internal` | 认证正常 |
| 获取文件夹元数据 | `/drive/explorer/v2/folder/:folderToken/meta` | 返回文件夹信息 |
| 获取单文档内容 | `/docx/v1/documents/{doc_token}/blocks` | 单文档测试成功 |

### ⚠️ 部分成功的 API（假摔现象）

| API | Endpoint | 现象 |
|-----|----------|------|
| Explorer V2 文件夹内容 | `/drive/explorer/v2/folder/:folderToken/children` | **200 OK，但 items: []** |

### ❌ 完全失败的 API（全部返回 404）

| API | Endpoint |
|-----|----------|
| Drive V1 文件列表 | `/drive/v1/files/{folder_token}/children` |
| Drive V1 文件夹列表 | `/drive/v1/folders/{folder_token}/children` |
| Drive V1 我的文件 | `/drive/v1/my_files` |
| Drive V1 我的文件夹 | `/drive/v1/my_folder` |
| Drive V1 文件列表 | `/drive/v1/files/list` |
| Search V1 文件 | `/search/v1/files` |
| Search V3 文件 | `/search/v3/files` |

## 核心问题

### 现象描述

这是一个典型的"假摔"现象：
- **接口通了**（200 OK）
- **但拿不到数据**（Empty List 或 404）

### 问题分析

1. **鉴权没问题**：`/folder/:folderToken/meta` 返回了正确的文件夹信息，说明 Token 有效。

2. **Drive V1 API 完全不可用**：所有 `/drive/v1/...` 接口返回 404，可能原因：
   - 应用类型限制
   - 数据权限范围未正确配置
   - 需要企业管理员额外授权

3. **Explorer V2 接口表现异常**：
   - `/meta` 正常返回文件夹信息
   - `/children` 返回 200 但 items: []（空列表）

## 代码对比

### 能工作的 API（单文档）

```python
# ✅ 成功 - 获取文档内容
url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks"
response = requests.get(url, headers=headers)
# 返回: {"code": 0, "data": {"items": [...]}, ...}
```

### 失败的 API（Drive V1）

```python
# ❌ 失败 - 返回 404
url = f"https://open.feishu.cn/open-apis/drive/v1/files/{folder_token}/children"
response = requests.get(url, headers=headers)
# 返回: 404 page not found
```

### 异常 API（Explorer V2）

```python
# ⚠️ 假摔 - 返回空列表
url = f"https://open.feishu.cn/open-apis/drive/explorer/v2/folder/{folder_token}/children"
response = requests.get(url, headers=headers)
# 返回: {"code": 0, "data": {"items": []}, "msg": "success"}
```

## 待确认问题

1. **Drive V1 API 为何返回 404？**
   - 自建应用是否可以使用 Drive V1 API？
   - 是否需要特定的「数据权限范围」配置？

2. **Explorer V2 为何返回空列表？**
   - 是否需要 user_access_token 而非 tenant_access_token？
   - 共享文件夹是否需要额外授权？

3. **幽灵文件现象**
   - 旧文档权限是否未正确继承？
   - 新建文档是否能被读取？

## 解决方案

### 方案 1：手动文档列表（临时）

在 `.env` 中配置 `DOC_TOKENS` 手动同步：

```bash
DOC_TOKENS=token1,token2,token3,...
```

### 方案 2：使用 user_access_token

如果问题由权限类型导致，需要改用用户身份认证。

### 方案 3：检查数据权限范围

在飞书开放平台检查应用的「数据权限范围」配置。

## 参考资料

- 飞书开放平台: https://open.feishu.cn/document/
- Drive API 文档: https://open.feishu.cn/document/server-docs/docs/drive/drive-api-overview
