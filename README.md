# 媒体剪辑 API 服务平台

对外提供图片剪辑、音频剪辑与 ModelScope AI 能力的开放 API 服务平台。

## 功能

- **图片剪辑**：裁切、缩放、滤镜（灰度/模糊/锐化/边缘/浮雕）、水印、格式转换（Pillow + OpenCV）
- **音频剪辑**：裁剪、拼接、音量调整、格式转换（FFmpeg）
- **AI 能力**（ModelScope）：AI 抠图、图像增强、语音转文字（ASR）、文字转语音（TTS）
- **API 管理**：开发者注册、API Key 认证、每日配额限流、调用统计
- **异步任务**：AI 耗时任务异步执行，任务状态轮询
- **可视化管理后台**：Vue3 界面管理开发者、配额、统计

## 技术栈

- 后端：Python 3.11 / FastAPI / SQLAlchemy / SQLite
- 前端：Vite / Vue3 / Element Plus
- 处理引擎：Pillow、OpenCV、FFmpeg、ModelScope

## 快速启动

```bash
# 1. 安装依赖
pip3 install --break-system-packages -r backend/requirements.txt
cd frontend && npm install && cd ..

# 2. 配置 ModelScope 凭证（AI 能力可选）
cp .env.example .env   # 填入 MODELSCOPE_API_TOKEN

# 3. 启动服务
bash start.sh
```

启动后：
- 管理后台：http://localhost:5173 （默认账号 admin / admin123，生产请修改）
- Swagger 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 开发者对接示例

```bash
# 1. 注册获取 API Key
curl -X POST http://localhost:8000/api/v1/dev/register \
  -H "Content-Type: application/json" \
  -d '{"name": "我的应用", "email": "dev@example.com"}'

# 2. 图片剪辑（灰度 + 转 JPEG）
curl -X POST http://localhost:8000/api/v1/image/edit \
  -H "Authorization: Bearer <你的API_KEY>" \
  -F "file=@input.png" \
  -F 'params={"filter": "gray", "output_format": "jpeg"}' \
  -o output.jpg

# 3. 音频裁剪（0.5s ~ 3s）
curl -X POST http://localhost:8000/api/v1/audio/edit \
  -H "Authorization: Bearer <你的API_KEY>" \
  -F "file=@input.mp3" \
  -F 'params={"crop": {"start": 0.5, "end": 3}, "output_format": "mp3"}' \
  -o output.mp3

# 4. 提交 AI 抠图任务（异步）
curl -X POST http://localhost:8000/api/v1/ai/matting \
  -H "Authorization: Bearer <你的API_KEY>" \
  -F "file=@input.png"
# -> {"task_id": "...", "status": "pending", "status_url": "/api/v1/tasks/{task_id}"}

# 5. 查询任务状态
curl -H "Authorization: Bearer <你的API_KEY>" \
  http://localhost:8000/api/v1/tasks/{task_id}
```

## API 一览

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | /api/v1/dev/register | 无 | 开发者注册 |
| POST | /api/v1/dev/reset-key | 无 | 重置 API Key |
| POST | /api/v1/image/edit | API Key | 图片剪辑（同步） |
| POST | /api/v1/audio/edit | API Key | 音频剪辑（同步） |
| POST | /api/v1/ai/{task_type} | API Key | AI 任务（matting/enhance/asr/tts） |
| GET | /api/v1/tasks/{task_id} | API Key | 任务状态 |
| GET | /api/v1/result/{task_id}/{file} | API Key | 结果下载 |
| POST | /api/v1/admin/login | 无 | 管理员登录 |
| GET | /api/v1/admin/developers | 管理员 | 开发者列表 |
| PUT | /api/v1/admin/developers/{id} | 管理员 | 修改状态/配额 |
| GET | /api/v1/admin/stats | 管理员 | 调用统计 |

## 测试

```bash
cd backend && python3 -m pytest tests/ -v
```

## 配置说明

通过环境变量或 `.env` 文件配置，参见 `.env.example`。ModelScope AI 能力需要配置 `MODELSCOPE_API_TOKEN`，未配置时 AI 接口返回 503。
