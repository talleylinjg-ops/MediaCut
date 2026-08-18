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
  - 项目启动：执行 `bash start.sh` 同时启动后端（uvicorn，端口 8000）与前端（vite dev，端口 5173）；前端通过 `/api` 反向代理访问后端，避免跨域
  - 后端测试：`cd /workspace/backend && python3 -m pytest tests/ -v`，当前共 47 个用例（服务层 + 接口集成）
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
