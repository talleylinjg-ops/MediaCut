# User Instruction Memory

This file records user instructions, preferences, and teachings for reference in future interactions.

## Format

### User Instruction Entry
User instruction entries should follow this format:

[User Instruction Summary]
- Date: [YYYY-MM-DD]
- Context: [Mentioned scenario or time]
- Instructions:
  - [Content of user teaching or instruction, described line by line]

### Project Knowledge Entry
Entries discovered by the Agent during task execution should follow this format:

[Project Knowledge Summary]
- Date: [YYYY-MM-DD]
- Context: Discovered by Agent while performing [specific task description]
- Category: [Operations & Deployment|Build Methods|Testing Methods|Troubleshooting & Debugging|Workflow & Collaboration|Environment Configuration]
- Instructions:
  - [Specific knowledge points, described line by line]

## Deduplication Strategy
- Before adding a new entry, check for similar or identical instructions.
- If a duplicate is found, skip the new entry or merge it with the existing one.
- When merging, update the context or date information.
- This helps avoid redundant entries and keeps the memory file tidy.

## Entries

[Project Knowledge Summary]
- Date: 2026-08-18
- Context: Discovered by Agent while developing the media edit API platform (Pillow/OpenCV/FFmpeg/ModelScope)
- Category: Operations & Deployment
- Instructions:
  - 项目启动：后端统一托管前端（单端口 8000）。启动命令：`cd /workspace/backend && ./start.sh`（守护循环，uvicorn 崩溃自动重启）；必须用 `background_terminal_create` 且 `timeout: 0`（不限时），否则后台终端到时会自动 kill 导致网站掉线；不再使用 vite dev（5173）
  - 预览地址：`https://8000-5cba46172cd5bd6f.monkeycode-ai.online`（基于端口 8000，重启后域名不变）
  - 后端测试：`cd /workspace/backend && python3 -m pytest tests/ -q`，当前共 51 个用例；`tests/conftest.py` 已隔离测试库（/tmp/test_media.db），严禁在测试中 drop 生产 media.db
  - ModelScope AI 凭证由用户自行到 modelscope.cn 注册，通过环境变量 `MODELSCOPE_API_TOKEN` 配置；未配置时 AI 接口返回 503，代码中只使用占位符
  - 环境已全局安装：Pillow 12、OpenCV 5（headless）、ModelScope 1.39、FFmpeg 5.1，系统 Python 3.11 需用 `pip3 install --break-system-packages` 装包
  - 计费双轨：`Developer.billing_type` 为 `internal`（内部免费，按每日配额）或 `external`（对外按 `billing.PRICE_TABLE` 价格扣 `balance` 点数，余额不足返回 402）；新注册开发者默认 `external` 且余额为 0，接口测试需先充值或设置 `internal`
  - 前端门户与客户控制台：`frontend/src/views/portal/`；API 封装 `api/index.js` 按路径自动选择 `admin_token` 或 `client_token`

[Project Knowledge Summary]
- Date: 2026-08-18
- Context: Discovered by Agent while debugging async task queue tests
- Category: Troubleshooting & Debugging
- Instructions:
  - SQLite 多线程场景必须启用 WAL 模式与 busy_timeout（见 `backend/app/database.py` 的 PRAGMA 事件），否则并发写会报 "database is locked" 导致任务状态卡住
  - 同一 SQLAlchemy session 复用时存在事务快照问题：轮询任务状态时需每次新开 session（或先 commit 结束只读事务），否则读不到其他线程的写入
  - 任务对外 ID 用 UUID（`task.task_id`），与数据库自增主键（`task.id`）区分；线程调度用主键，API 层用 UUID

[Project Knowledge Summary]
- Date: 2026-10-02
- Context: Discovered by Agent while confirming integration status with the user
- Category: Operations & Deployment
- Instructions:
  - didi AI（WordPress 主题）已由用户在其侧接入 MediaCut API 并确认可用；工作区内 `didiAI/` 只是适配层副本，无需再做 functions.php 接入
  - 边缘「完全一致」校验：`bash edge/verify-consistency.sh --origin <源站> [--edge <边缘>]`，对比 dist 全部文件与 SPA 路由的状态码/content-type/字节；deploy-edge.sh 的 MIME 映射已对齐源站 uvicorn（xml 无 charset、ico 为 image/vnd.microsoft.icon），改 MIME 需同步 edge/worker/src/index.js 的 MIME 表
  - 路由归属：`/docs` = 前端接入文档页（PortalDocs），`/api-docs`、`/api-redoc` = 后端 Swagger/Redoc，`/docs` 在边缘 Worker 走 SPA 快照而非回源

[Project Knowledge Summary]
- Date: 2026-10-03
- Context: Discovered by Agent while deploying the edge layer to Cloudflare
- Category: Operations & Deployment
- Instructions:
  - CF 边缘站已上线（纯静态版）：https://mediacut-edge.talley-linjg.workers.dev（Worker name: mediacut-edge，Account: Daqi Account 2e33f078...，R2 桶: didimedia-mediacut-static）
  - CF Token 由用户在会话中提供并通过环境变量传入，严禁写入任何文件或 git
  - 沙箱出口 DNS 对 workers.dev 有污染（解析到错误 IP），验证需用 DoH 拿真实 IP 后 curl --resolve；真实浏览器访问正常
  - 完整版切换：源站就绪后执行 `CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ACCOUNT_ID=... bash edge/deploy-edge.sh --build`（重传完整 dist 并部署）
  - 静态版重传：`bash edge/deploy-edge.sh --build --static`
