# 接口文档

本系统为 REST API 服务。所有剪辑接口与任务接口需要 API Key 认证，管理接口需要管理员 JWT 认证。

## 认证方式

### 开发者 API Key

注册时获取，调用接口时放入请求头：

```
Authorization: Bearer <API_KEY>
```

无效或停用状态返回 `401 invalid api key`。

### 管理员 JWT

登录后获取 token，调用管理接口：

```
Authorization: Bearer <JWT_TOKEN>
```

无效 token 返回 `401 admin authentication required`。

## 错误响应格式

所有错误统一返回 JSON：

```json
{"detail": "错误描述"}
```

| 状态码 | 含义 |
|--------|------|
| 400 | 参数非法 / 文件格式不支持 |
| 401 | API Key 或管理员凭证无效 |
| 404 | 资源不存在 |
| 413 | 文件过大（图片 20MB / 音频 100MB） |
| 429 | 超出每日配额 |
| 500 | 处理引擎内部错误 |
| 503 | AI 服务不可用（未配置 ModelScope 凭证） |

## 开发者接口

### POST /api/v1/dev/register

注册开发者，返回 API Key（仅此一次返回明文）。

**请求体**:
```json
{"name": "我的应用", "email": "dev@example.com"}
```

**响应**:
```json
{"developer_id": 1, "api_key": "<32位随机Key>"}
```

### POST /api/v1/dev/reset-key

按名称与邮箱重置 API Key。

**请求体**: 同 register

**响应**: 同 register

## 图片剪辑接口

### POST /api/v1/image/edit

**认证**: API Key

**请求**: multipart/form-data

| 字段 | 类型 | 说明 |
|------|------|------|
| file | File | 图片文件（png/jpeg/webp/bmp，≤20MB） |
| params | String | JSON 字符串，剪辑参数 |

**params 结构**:
```json
{
  "crop": [0, 0, 100, 100],
  "resize": {"width": 800, "height": 600},
  "filter": "gray",
  "watermark": {"text": "水印", "position": [10, 10], "size": 24, "color": [255, 0, 0]},
  "output_format": "jpeg"
}
```

| 参数 | 取值 | 说明 |
|------|------|------|
| crop | `[left, top, right, bottom]` | 裁切区域 |
| resize | `{width, height}` | 缩放尺寸 |
| filter | `gray` / `blur` / `sharpen` / `edge` / `emboss` | 滤镜 |
| watermark | `{text, position, size, color}` | 水印 |
| output_format | `png` / `jpeg` / `webp` / `bmp` | 输出格式 |

**响应**: 处理后的图片二进制，响应头 `X-Remaining-Quota` 为剩余配额。

## 音频剪辑接口

### POST /api/v1/audio/edit

**认证**: API Key

**请求**: multipart/form-data

| 字段 | 类型 | 说明 |
|------|------|------|
| file | File | 音频文件（mp3/wav/ogg/flac，≤100MB） |
| params | String | JSON 字符串，剪辑参数 |

**params 结构**:
```json
{
  "crop": {"start": 0.5, "end": 3.0},
  "volume": {"gain": 1.5},
  "concat": {"files": ["/path/seg1.wav", "/path/seg2.wav"]},
  "output_format": "mp3"
}
```

| 参数 | 取值 | 说明 |
|------|------|------|
| crop | `{start, end}` | 裁剪时间区间（秒） |
| volume | `{gain}` | 音量增益倍数 |
| concat | `{files}` | 服务端文件路径列表拼接 |
| output_format | `mp3` / `wav` / `ogg` / `aac` / `flac` / `m4a` | 输出格式 |

**响应**: 处理后的音频二进制。

## AI 能力接口

### POST /api/v1/ai/{task_type}

**认证**: API Key

**task_type**: `matting`（抠图）/ `enhance`（增强）/ `asr`（语音转文字）/ `tts`（文字转语音）

**请求**: multipart/form-data

| task_type | 字段 | 说明 |
|-----------|------|------|
| matting / enhance | file | 图片文件 |
| asr | file | 音频文件 |
| tts | text | 合成文本 |

**响应**（立即返回，异步处理）:
```json
{
  "task_id": "b352cb4752144a8ab2ab8235b66de715",
  "status": "pending",
  "status_url": "/api/v1/tasks/b352cb4752144a8ab2ab8235b66de715"
}
```

## 任务接口

### GET /api/v1/tasks/{task_id}

**认证**: API Key（仅限任务归属的开发者）

**响应**:
```json
{
  "task_id": "b352cb...",
  "task_type": "matting",
  "status": "succeeded",
  "result_url": "b352cb.../result_xxx.png",
  "error": null,
  "created_at": "2026-08-18T01:26:04.146102",
  "updated_at": "2026-08-18T01:26:04.157446"
}
```

`status` 取值：`pending`（排队）/ `running`（处理中）/ `succeeded`（成功）/ `failed`（失败）。

## 结果下载接口

### GET /api/v1/result/{task_id}/{filename}

**认证**: API Key（仅限任务归属的开发者）

**响应**: 结果文件二进制。文件名受路径穿越防护，仅允许 `storage/results/{task_id}/` 下的直接文件名。

## 管理后台接口

### POST /api/v1/admin/login

**请求体**:
```json
{"username": "admin", "password": "admin123"}
```

**响应**: `{"token": "<JWT>"}`

### GET /api/v1/admin/developers

**认证**: 管理员

**响应**: 开发者列表，字段包括 `id`、`name`、`email`、`api_key_hash`、`status`、`quota_limit`、`quota_used`、`quota_date`、`created_at`。

### PUT /api/v1/admin/developers/{id}

**认证**: 管理员

**请求体**（至少一项）:
```json
{"status": "active", "quota_limit": 5000}
```

`status` 取值：`active` / `disabled`。

### GET /api/v1/admin/stats

**认证**: 管理员

**响应**: 按接口聚合的调用统计：
```json
[
  {"endpoint": "/api/v1/image/edit", "count": 2, "success": 1, "failed": 1}
]
```

## 通用接口

### GET /health

无认证。健康检查，返回 `{"status": "ok"}`。

### GET /docs

Swagger UI 在线接口文档（支持在线调试）。
