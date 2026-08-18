# core 核心层

横切关注点：认证、配额与异步任务调度，被全部 API 路由复用。

## 结构

```
core/
├── security.py    # API Key 生成/哈希/校验、管理员 JWT
├── quota.py       # 每日配额计数与限流
└── task_queue.py  # 进程内线程池异步任务队列
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `security.py` | 32 位 Key 生成、SHA-256 哈希、`authenticate_developer` / `require_admin` FastAPI 依赖 |
| `quota.py` | `check_quota` 预检、`consume_quota` 消耗、跨日重置、`remaining_quota` |
| `task_queue.py` | `create_task` 入库并调度、`run_task` 状态机执行、后台清理线程 |

## 依赖

**本模块依赖**:
- `../models.py` - Developer、Task 数据模型
- `../config.py` - 管理员账号、JWT 密钥、任务 TTL
- `../services/ai_service.py` - 任务线程的推理入口

**依赖本模块的**:
- `../api/` - 全部受保护路由依赖认证与配额
- `../main.py` - 调用日志中间件使用 Key 哈希查询开发者

## 规范

### 安全约定
- API Key 明文仅在生成时返回，库内只存 SHA-256 哈希
- JWT 使用 HS256，`sub` 声明校验管理员身份
- AI 凭证 `MODELSCOPE_API_TOKEN` 只从环境变量读取，不写入代码

### 异步调度约定
- 线程池固定 2 个 worker，单进程模型
- 任务状态单向流转，失败原因写入 `task.error`
- 清理线程每 30 分钟执行一次过期结果清理

### 测试
- `backend/tests/test_security.py`、`test_quota.py`、`test_task_queue.py`
- 任务队列测试用轮询新会话的方式规避 SQLite 事务快照问题

## 注意

任务队列依赖 SQLite WAL 模式（`backend/app/database.py` 中配置）以支持多线程并发读写。若更换数据库，需重新评估 `ThreadPoolExecutor` 方案的线程安全。
