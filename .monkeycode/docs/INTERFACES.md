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

### 客户 JWT

开发者使用注册邮箱与密码登录后获取 token，用于客户控制台接口：

```
Authorization: Bearer <JWT_TOKEN>
```

## 错误响应格式

所有错误统一返回 JSON：

```json
{"detail": "错误描述"}
```

| 状态码 | 含义 |
|--------|------|
| 400 | 参数非法 / 文件格式不支持 |
| 401 | API Key 或管理员/客户凭证无效 |
| 402 | 对外计费账户余额不足 |
| 404 | 资源不存在 |
| 409 | 邮箱已注册 |
| 413 | 文件过大（图片 20MB / 音频 100MB） |
| 429 | 超出每日配额 |
| 500 | 处理引擎内部错误 |
| 503 | AI 服务不可用（未配置 ModelScope 凭证） |

## 计费说明

- 开发者区分两种计费类型：
  - `internal`（内部免费）：仅受每日配额限制，不扣费
  - `external`（对外计费）：每次成功调用按接口价格扣减 `balance`（点数），余额不足返回 `402`
- 价格表：
  - 图片剪辑 `/api/v1/image/edit`：1 点/次
  - 音频剪辑 `/api/v1/audio/edit`：2 点/次
  - AI 抠图 `/api/v1/ai/matting`：10 点/次
  - AI 增强 `/api/v1/ai/enhance`：15 点/次
  - AI 语音识别 `/api/v1/ai/asr`：10 点/次
  - AI 语音合成 `/api/v1/ai/tts`：5 点/次
- 充值由管理员在管理后台完成（`PUT /api/v1/admin/developers/{id}` 传 `recharge`）

## 开发者接口

### POST /api/v1/dev/register

注册开发者（默认 `external` 计费），返回 API Key（仅此一次返回明文）。

**请求体**:
```json
{"name": "我的应用", "email": "dev@example.com", "password": "secret123"}
```

`password` 至少 6 位，用于登录客户控制台。邮箱重复返回 409。

**响应**:
```json
{"developer_id": 1, "api_key": "<32位随机Key>"}
```

### POST /api/v1/dev/client/login

**请求体**:
```json
{"email": "dev@example.com", "password": "secret123"}
```

**响应**: `{"token": "<JWT>"}`

### GET /api/v1/dev/client/me

**认证**: 客户 JWT

**响应**:
```json
{
  "id": 1, "name": "我的应用", "email": "dev@example.com",
  "billing_type": "external", "balance": 499,
  "quota_limit": 1000, "quota_used": 1, "quota_date": "2026-08-18"
}
```

### GET /api/v1/dev/client/logs

**认证**: 客户 JWT

**响应**: 最近 50 条调用记录：
```json
[
  {"endpoint": "/api/v1/image/edit", "status_code": 200, "cost": 1, "created_at": "..."}
]
```

### POST /api/v1/dev/client/reset-key

**认证**: 客户 JWT

重置 API Key，旧 Key 立即失效。**响应**: 同 register（返回新明文 Key）。

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

**响应**: 开发者列表，字段包括 `id`、`name`、`email`、`api_key_hash`、`billing_type`、`balance`、`status`、`quota_limit`、`quota_used`、`quota_date`、`created_at`。

### PUT /api/v1/admin/developers/{id}

**认证**: 管理员

**请求体**（至少一项）:
```json
{"status": "active", "quota_limit": 5000, "billing_type": "external", "recharge": 500}
```

`status` 取值：`active` / `disabled`；`billing_type` 取值：`internal` / `external`；`recharge` 为充值点数（非负整数，累加到 `balance`）。

### GET /api/v1/admin/stats

**认证**: 管理员

**响应**: 按接口聚合的调用统计：
```json
[
  {"endpoint": "/api/v1/image/edit", "count": 2, "success": 1, "failed": 1, "revenue": 1}
]
```

`revenue` 为成功调用累计收费点数。

## 通用接口

### GET /health

无认证。健康检查，返回 `{"status": "ok"}`。

### GET /docs

Swagger UI 在线接口文档（支持在线调试）。
