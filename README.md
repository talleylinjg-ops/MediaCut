# 媒体剪辑 API 服务平台

对外提供图片剪辑、音频剪辑与 ModelScope AI 能力的开放 API 服务平台。

## 功能

- **图片剪辑**：裁切、缩放、滤镜（灰度/模糊/锐化/边缘/浮雕）、水印、格式转换（Pillow + OpenCV）
- **音频剪辑**：裁剪、拼接、音量调整、格式转换（FFmpeg）
- **AI 能力**（ModelScope）：AI 抠图、图像增强、语音转文字（ASR）、文字转语音（TTS）
- **API 管理**：开发者注册、API Key 认证、每日配额限流、调用统计
- **异步任务**：AI 耗时任务异步执行，任务状态轮询
- **计费系统**：内部调用按每日配额免费，对外按接口价格扣减预充值余额，余额不足返回 402
- **对外客户门户**：产品介绍、定价、申请注册、接入文档、客户控制台（查看余额/配额/调用记录/重置 Key）
- **可视化管理后台**：Vue3 界面管理开发者、配额、计费类型、充值、统计

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

启动后（单端口 8000，前端由后端托管）：
- 客户门户：http://localhost:8000 （首页 / 定价 / 申请 / 接入文档 / 客户控制台）
- 管理后台：http://localhost:8000/login （默认账号 admin / admin123，登录后进入首页 /admin）
- 账号中心：http://localhost:8000/account （修改管理员密码、配置 ModelScope Token）
- Swagger 文档：http://localhost:8000/docs （前端入口 http://localhost:8000/swagger）
- 健康检查：http://localhost:8000/health

## 生产部署（Ubuntu / Debian + Caddy 自动 HTTPS）

前置条件：一台公网服务器（建议 2 核 4GB 内存以上、20GB 磁盘），域名已解析到该服务器 IP。

```bash
# 克隆代码
git clone <仓库地址> mediacut
cd mediacut

# 一键部署，自动申请并续期 HTTPS 证书
# --preheat-models 首次会下载语音识别与抠图模型，耗时较长
sudo bash deploy/install.sh --domain didimedia.com --preheat-models
```

脚本会依次完成：安装系统依赖（ffmpeg 等）、Node.js、Caddy；创建 Python 虚拟环境并安装依赖；构建前端；写入 `/etc/mediacut/mediacut.env`；注册 systemd 服务 `mediacut`；配置 Caddy 反向代理与 HTTPS。完成后访问 `https://didimedia.com`，管理后台为 `https://didimedia.com/login`。

常用运维命令：

```bash
# 查看服务状态
systemctl status mediacut

# 查看实时日志
journalctl -u mediacut -f

# 修改环境变量后重启
systemctl restart mediacut
```

配置项参见 `.env.example` 与 `deploy/mediacut.env.example`。生产环境务必修改 `ADMIN_PASSWORD` 与 `JWT_SECRET`。

## 开发者对接示例

```bash
# 1. 注册获取 API Key（需设置密码，用于登录客户控制台）
curl -X POST http://localhost:8000/api/v1/dev/register \
  -H "Content-Type: application/json" \
  -d '{"name": "我的应用", "email": "dev@example.com", "password": "secret123"}'

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
| POST | /api/v1/dev/register | 无 | 开发者注册（name/email/password） |
| POST | /api/v1/dev/client/login | 无 | 客户登录（邮箱+密码，返回 JWT） |
| GET | /api/v1/dev/client/me | 客户 JWT | 账户信息（计费类型/余额/配额） |
| GET | /api/v1/dev/client/logs | 客户 JWT | 最近调用记录（含费用） |
| POST | /api/v1/dev/client/reset-key | 客户 JWT | 重置 API Key |
| POST | /api/v1/image/edit | API Key | 图片剪辑（同步，1 点/次） |
| POST | /api/v1/audio/edit | API Key | 音频剪辑（同步，2 点/次） |
| POST | /api/v1/ai/{task_type} | API Key | AI 任务（matting=10/enhance=15/asr=10/tts=5） |
| GET | /api/v1/tasks/{task_id} | API Key | 任务状态 |
| GET | /api/v1/result/{task_id}/{file} | API Key | 结果下载 |
| POST | /api/v1/admin/login | 无 | 管理员登录 |
| GET | /api/v1/admin/developers | 管理员 | 开发者列表 |
| PUT | /api/v1/admin/developers/{id} | 管理员 | 修改状态/配额/计费类型/充值 |
| GET | /api/v1/admin/stats | 管理员 | 调用统计（含收入） |

## 计费说明

- 开发者分为两种计费类型：
  - `internal`（内部免费）：按每日配额限流，不扣费
  - `external`（对外计费）：按接口价格从预充值 `balance`（点数）扣减
- 新注册 `external` 账户自动赠送 100 点，可直接调用；余额不足时接口返回 `402 Payment Required`，当日配额用完返回 `429`
- 充值通过管理后台「开发者管理 → 充值」或 `PUT /admin/developers/{id}` 接口完成

## 测试

```bash
cd backend && python3 -m pytest tests/ -v
```

## 配置说明

通过环境变量或 `.env` 文件配置，参见 `.env.example`。ModelScope AI 能力需要配置 `MODELSCOPE_API_TOKEN`，未配置时 AI 接口返回 503。
