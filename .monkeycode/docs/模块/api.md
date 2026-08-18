# api 路由层

对外暴露的 HTTP 接口，负责参数解析、认证校验与响应组装。

## 结构

```
api/
├── dev.py      # 开发者注册、Key 重置
├── image.py    # 图片剪辑（同步）
├── audio.py    # 音频剪辑（同步）
├── ai.py       # AI 任务提交（异步）
├── tasks.py    # 任务状态查询
├── result.py   # 结果文件下载
└── admin.py    # 管理后台（登录、开发者、配额、统计）
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `image.py` | multipart 上传 + JSON 参数，返回处理图片二进制 |
| `audio.py` | multipart 上传 + JSON 参数，返回处理音频二进制 |
| `ai.py` | 按 task_type 校验上传/文本，创建异步任务 |
| `tasks.py` | 任务状态查询（归属隔离） |
| `result.py` | 结果下载（路径穿越防护） |
| `admin.py` | 管理员 JWT、开发者 CRUD、调用统计聚合 |

## 依赖

**本模块依赖**:
- `../core/security.py` - 认证依赖
- `../core/quota.py` - 配额预检与消耗
- `../core/task_queue.py` - AI 任务创建
- `../services/` - 图片/音频/AI 处理
- `../schemas.py` - 请求/响应模型

**依赖本模块的**:
- `../main.py` - 应用入口统一挂载各 router

## 规范

### 认证模式
```python
developer: Developer = Depends(authenticate_developer)
```
- 公开接口（注册、登录）：无认证
- 剪辑/任务接口：API Key 认证 + 配额
- 管理接口：`dependencies=[Depends(require_admin)]`

### 错误处理
参数校验失败抛 `HTTPException(400)`；配额超额 `429`；无效凭证 `401`；AI 未配置 `503`。

### 配额约定
先 `check_quota` 预检再执行处理，处理成功后 `consume_quota`，响应头携带 `X-Remaining-Quota`。

### 测试
- `backend/tests/test_api.py` 覆盖注册、认证、图片/音频剪辑、AI 任务、配额、管理接口全流程

## 添加新接口

1. 在 `api/` 新建领域文件，定义 `router = APIRouter(prefix="/api/v1/...")`
2. 在 `main.py` 中 `app.include_router(...)`
3. 在 `tests/test_api.py` 添加集成测试
