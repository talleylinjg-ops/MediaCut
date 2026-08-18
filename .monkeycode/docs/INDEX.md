# 媒体剪辑 API 服务平台 文档

本文档描述媒体剪辑 API 服务平台的系统架构、接口契约与开发指南，适用于平台开发维护者、API 对接开发者及管理员。

**快速链接**: [架构](./ARCHITECTURE.md) | [接口](./INTERFACES.md) | [开发者指南](./DEVELOPER_GUIDE.md)

---

## 核心文档

### [架构](./ARCHITECTURE.md)
系统设计、技术栈、子系统划分与请求/任务数据流。从这里开始了解系统如何运作。

### [接口](./INTERFACES.md)
全部 REST API 契约：认证方式、参数说明、错误码与对接示例。集成或使用本系统的参考。

### [开发者指南](./DEVELOPER_GUIDE.md)
环境搭建、运行测试、编码规范与常见任务（添加接口、AI 任务类型、滤镜、格式）。贡献者必读。

---

## 模块

| 模块 | 描述 | README |
|------|------|--------|
| `backend/app/services/` | 图片/音频/AI 处理引擎封装 | [README](./模块/services.md) |
| `backend/app/core/` | 认证、配额、异步任务调度 | [README](./模块/core.md) |
| `backend/app/api/` | HTTP 接口层 | [README](./模块/api.md) |

---

## 核心概念

理解这些领域概念有助于导航代码库：

| 概念 | 描述 |
|------|------|
| [API Key 与配额](./专有概念/API-Key与配额.md) | 开发者身份凭证与每日调用计量 |
| [异步任务](./专有概念/异步任务.md) | AI 处理的后台执行单元与状态机 |

---

## 入门指南

### 项目新人？

按此路径学习：
1. **[架构](./ARCHITECTURE.md)** - 了解全局
2. **[核心概念](#核心概念)** - 学习领域术语
3. **[开发者指南](./DEVELOPER_GUIDE.md)** - 搭建环境
4. **[接口](./INTERFACES.md)** - 探索公开 API

### 需要对接 API？

1. **[接口](./INTERFACES.md)** - API 契约与认证
2. 注册获取 API Key：`POST /api/v1/dev/register`
3. 调用剪辑接口（见 [快速启动](../..//README.md) 中的 curl 示例）

---

## 快速参考

### 命令

```bash
bash start.sh                               # 启动前后端
cd backend && python3 -m pytest tests/ -v   # 运行测试
cd frontend && npm run build                # 前端构建
```

### 重要文件

| 文件 | 目的 |
|------|------|
| `backend/app/main.py` | 后端应用入口 |
| `backend/app/core/task_queue.py` | 异步任务调度 |
| `.env.example` | 环境变量模板 |
| `.monkeycode/specs/media-edit-api/` | 需求、设计、任务列表文档 |
