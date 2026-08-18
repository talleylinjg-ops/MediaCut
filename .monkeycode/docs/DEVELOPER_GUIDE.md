# 开发者指南

## 项目目的

媒体剪辑 API 服务平台是一个面向第三方开发者的开放媒体处理 API 平台。它将 Pillow、OpenCV、FFmpeg 与 ModelScope AI 能力封装为可申请、可计量的 REST API，并配套可视化管理后台。

**核心职责**:
- 提供图片剪辑（裁切、缩放、滤镜、水印、格式转换）API
- 提供音频剪辑（裁剪、拼接、音量、格式转换）API
- 提供 ModelScope AI 能力（抠图、增强、ASR、TTS）异步任务 API
- 管理开发者 API Key、配额、计费类型、余额充值与调用统计

**相关系统**:
- ModelScope - AI 模型推理依赖
- FFmpeg - 音频处理引擎

## 环境搭建

### 前置条件

- Python >= 3.11
- Node.js >= 20（前端）
- FFmpeg（系统已安装或通过 `apt-get install -y ffmpeg` 安装）

### 安装

```bash
# 克隆仓库后安装后端依赖
pip3 install --break-system-packages -r backend/requirements.txt

# 安装前端依赖
cd frontend && npm install && cd ..
```

### 环境变量

| 变量 | 必需 | 描述 | 示例 |
|------|------|------|------|
| `MODELSCOPE_API_TOKEN` | 是（AI 功能） | ModelScope 访问凭证 | 到 modelscope.cn 注册获取 |
| `ADMIN_USERNAME` | 否 | 管理后台用户名 | `admin` |
| `ADMIN_PASSWORD` | 否 | 管理后台密码 | `admin123` |
| `JWT_SECRET` | 否 | JWT 签名密钥（生产必改） | 强随机字符串 |
| `DATABASE_URL` | 否 | 数据库连接 | `sqlite:///backend/media.db` |
| `MODELSCOPE_MATTING_MODEL` 等 | 否 | 覆盖默认模型 ID | ModelScope 模型名 |

⚠️ **绝不提交密钥**。使用 `.env` 文件（参考 `.env.example`），其中 `MODELSCOPE_API_TOKEN` 请填入你从 modelscope.cn 获取的凭证。

### 运行

```bash
# 一键启动前后端
bash start.sh

# 或分别启动
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev

# 运行测试
cd backend && python3 -m pytest tests/ -v
```

启动后：
- 前端管理后台：http://localhost:5173
- Swagger 文档：http://localhost:8000/docs

## 开发工作流

### 代码质量工具

| 工具 | 命令 | 目的 |
|------|------|------|
| pytest | `cd backend && python3 -m pytest tests/ -v` | 单元与集成测试 |
| Vite | `cd frontend && npm run build` | 前端构建校验 |

### 提交前检查

1. 运行全部后端测试：`cd backend && python3 -m pytest tests/ -q`
2. 前端如有改动执行 `npm run build` 确认无编译错误

### 分支策略

- `master` - 生产就绪代码

## 常见任务

### 添加新 API 端点

**需修改的文件**:
1. `backend/app/api/[domain].py` - 添加路由（继承 `router = APIRouter(prefix="/api/v1/...")`）
2. `backend/app/main.py` - 挂载新路由 `app.include_router(...)`
3. `backend/app/schemas.py` - 添加请求/响应模型
4. `backend/tests/test_api.py` - 添加集成测试

**步骤**:
1. 若需要开发者认证，路由函数参数加 `developer: Developer = Depends(authenticate_developer)`
2. 需要配额/计费则调用 `quota.check_quota(db, developer, price)` 与 `quota.consume_quota(db, developer, price)`（price 取自 `billing.get_price(endpoint)`）
3. 编写测试并运行

### 添加计费接口

**需修改的文件**:
1. `backend/app/core/billing.py` - `PRICE_TABLE` 加入 `endpoint -> 价格`
2. 路由中调用 `price = billing.get_price(endpoint)` 并传入 `check_quota` / `consume_quota`
3. `frontend/src/api/billing.js` - 同步价格表展示
4. `backend/tests/test_api.py` - 补充余额扣减/不足 402 用例

### 添加新的 AI 任务类型

**需修改的文件**:
1. `backend/app/config.py` - `MODELSCOPE_MODELS` 添加模型映射
2. `backend/app/services/ai_service.py` - `TASK_TYPES` 加入类型，实现对应 run_xxx 函数并在 `run_ai_task` 分发
3. `backend/app/api/ai.py` - 补充参数校验分支

### 添加新的图片滤镜

**需修改的文件**:
1. `backend/app/services/image_service.py` - `FILTERS` 集合加入滤镜名，`apply_filter` 增加 OpenCV 处理分支

### 添加新的音频输出格式

**需修改的文件**:
1. `backend/app/services/audio_service.py` - `OUTPUT_FORMATS` 与 `CODEC_MAP` 加入格式及 FFmpeg 编码器
2. `backend/app/api/audio.py` - `content_type` 映射补充

### 修复 Bug

**流程**:
1. 编写复现 bug 的失败测试
2. 定位根因
3. 最小改动修复
4. 运行 `python3 -m pytest tests/` 确认全部通过

## 编码规范

### 文件组织
- 路由按领域拆分，一个文件一个领域（dev/image/audio/ai/tasks/result/admin）
- 服务层放在 `backend/app/services/`，横切关注点放 `backend/app/core/`
- 测试文件放 `backend/tests/`

### 命名

| 类型 | 约定 | 示例 |
|------|------|------|
| 文件 | snake_case | `image_service.py` |
| 类 | PascalCase | `Developer` |
| 函数 | snake_case | `process_image` |
| 常量 | SCREAMING_SNAKE | `IMAGE_MAX_SIZE` |

### 错误处理

统一使用 FastAPI 异常：
```python
from fastapi import HTTPException
raise HTTPException(status_code=400, detail="invalid parameters")
```

服务层处理引擎错误时抛 HTTPException 交由路由层透传，避免泄漏底层异常。

### 测试
- 测试文件按 `test_[模块].py` 命名
- 服务层测试直接调用服务函数验证正确性与边界
- 集成测试通过 `TestClient` 走完整 HTTP 流程（认证、配额、文件上传）
- AI 相关测试使用 `monkeypatch` 替换 `ai_service.run_ai_task` 避免真实模型调用
