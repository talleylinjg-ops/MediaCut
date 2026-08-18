# services 服务层

封装媒体处理与 AI 推理业务逻辑，供 API 路由层与任务队列调用。

## 结构

```
services/
├── image_service.py   # Pillow + OpenCV 图片剪辑
├── audio_service.py   # FFmpeg 音频剪辑
└── ai_service.py      # ModelScope AI 能力封装
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `image_service.py` | 图片裁切、缩放、滤镜、水印、格式转换；上传校验 |
| `audio_service.py` | 音频裁剪、拼接、音量、格式转换；FFmpeg 子进程管理 |
| `ai_service.py` | ModelScope pipeline 懒加载与缓存；四类 AI 任务分发 |

## 依赖

**本模块依赖**:
- `../config.py` - 大小限制、模型映射、AI 凭证
- Pillow / OpenCV / numpy - 图片处理
- FFmpeg 命令行 - 音频处理
- modelscope 库 - AI 推理

**依赖本模块的**:
- `../api/` - 图片/音频剪辑接口调用服务函数
- `../core/task_queue.py` - AI 任务线程调用 `run_ai_task`

## 规范

### 错误处理
所有引擎异常统一转换为 `HTTPException` 抛出：
- 参数非法 / 格式不支持 → `400`
- 文件超限 → `413`
- 处理引擎失败 → `500`
- ModelScope 未配置 → `503`

### 测试
- 服务函数直接测试：`backend/tests/test_image_service.py`、`test_audio_service.py`
- AI 服务通过 `monkeypatch` 替换 `run_ai_task` 验证任务流程

## 添加新 AI 任务类型

1. `ai_service.py` 的 `TASK_TYPES` 加入类型
2. 实现 `run_xxx` 函数并在 `run_ai_task` 分发
3. `config.py` 的 `MODELSCOPE_MODELS` 添加模型映射
4. `api/ai.py` 补充参数校验
