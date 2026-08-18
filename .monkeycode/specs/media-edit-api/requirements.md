# 媒体剪辑 API 服务平台 需求文档

Feature: media-edit-api
Updated: 2026-08-18

## Introduction

本系统是一个对外提供媒体剪辑能力的 API 服务平台。平台将已部署的 Pillow、OpenCV、FFmpeg 处理引擎与 ModelScope AI 能力封装为标准化 REST API，面向第三方开发者提供「申请对接 → 获取 API Key → 调用剪辑接口」的完整服务流程。

## Glossary

- **系统**: 媒体剪辑 API 服务平台
- **开发者**: 申请并使用平台 API 的第三方用户
- **平台管理员**: 管理开发者、API Key 与配额的后台操作者
- **API Key**: 开发者调用平台接口时使用的身份凭证
- **图片剪辑**: 对图片执行裁切、缩放、滤镜、水印、格式转换等操作
- **音频剪辑**: 对音频执行裁剪、拼接、音量调整、格式转换等操作
- **AI 能力**: 通过 ModelScope 提供的抠图、图像增强、语音识别、语音合成能力
- **配额**: 开发者单位时间内可调用的接口次数上限

## Requirements

### 需求 1: 开发者申请对接

**User Story:** AS 开发者, I want 注册并申请 API Key, so that 我能获得调用平台剪辑接口的合法凭证

#### Acceptance Criteria

1. WHEN 开发者提交注册申请，系统 SHALL 创建开发者账号并生成专属 API Key
2. WHEN 开发者携带 API Key 调用任意接口，系统 SHALL 验证 Key 的有效性并放行合法请求
3. WHEN 开发者携带无效或过期 API Key 调用接口，系统 SHALL 拒绝请求并返回 401 错误
4. WHILE 开发者处于有效状态，系统 SHALL 记录该开发者的调用日志与配额消耗
5. IF 开发者申请重置 API Key，系统 SHALL 作废旧 Key 并签发新 Key

### 需求 2: 图片剪辑接口

**User Story:** AS 开发者, I want 通过 API 上传图片并执行剪辑操作, so that 我能获得处理后的图片结果

#### Acceptance Criteria

1. WHEN 开发者提交图片剪辑请求，系统 SHALL 基于 Pillow 或 OpenCV 执行指定剪辑操作
2. WHEN 开发者指定裁切参数，系统 SHALL 返回按指定区域裁切后的图片
3. WHEN 开发者指定缩放参数，系统 SHALL 返回按指定尺寸缩放后的图片
4. WHEN 开发者指定滤镜类型，系统 SHALL 返回应用滤镜后的图片
5. WHEN 开发者指定水印文本与位置，系统 SHALL 返回叠加水印后的图片
6. WHEN 开发者指定输出格式，系统 SHALL 返回转换格式后的图片
7. IF 图片文件损坏或参数非法，系统 SHALL 返回 400 错误并说明原因

### 需求 3: 音频剪辑接口

**User Story:** AS 开发者, I want 通过 API 上传音频并执行剪辑操作, so that 我能获得处理后的音频结果

#### Acceptance Criteria

1. WHEN 开发者提交音频剪辑请求，系统 SHALL 基于 FFmpeg 执行指定剪辑操作
2. WHEN 开发者指定时间区间，系统 SHALL 返回该时间段的音频片段
3. WHEN 开发者指定拼接序列，系统 SHALL 返回拼接后的音频
4. WHEN 开发者指定音量增益，系统 SHALL 返回调整音量后的音频
5. WHEN 开发者指定输出格式，系统 SHALL 返回转换格式后的音频
6. IF 音频文件损坏或参数非法，系统 SHALL 返回 400 错误并说明原因

### 需求 4: AI 能力接口

**User Story:** AS 开发者, I want 调用基于 ModelScope 的 AI 能力, so that 我能获得智能化剪辑结果

#### Acceptance Criteria

1. WHEN 开发者提交 AI 抠图请求，系统 SHALL 调用 ModelScope 抠图模型并返回前景分离后的图片
2. WHEN 开发者提交图像增强请求，系统 SHALL 调用 ModelScope 增强模型并返回修复后的图片
3. WHEN 开发者提交语音转文字请求，系统 SHALL 调用 ModelScope ASR 模型并返回识别文本
4. WHEN 开发者提交文字转语音请求，系统 SHALL 调用 ModelScope TTS 模型并返回合成音频
5. IF ModelScope 服务不可用，系统 SHALL 返回 503 错误并记录失败原因
6. WHEN 开发者提交 AI 任务，系统 SHALL 返回任务 ID，开发者通过轮询获取处理结果

### 需求 5: 异步任务队列

**User Story:** AS 开发者, I want 提交耗时 AI 任务后不必同步等待, so that 我能异步获取处理结果

#### Acceptance Criteria

1. WHEN 开发者提交 AI 剪辑任务，系统 SHALL 创建任务并立即返回任务 ID 与状态 URL
2. WHEN 开发者携带任务 ID 查询状态，系统 SHALL 返回当前任务状态（排队/处理中/成功/失败）
3. WHEN 任务处理成功，系统 SHALL 在状态查询中返回结果文件地址
4. WHEN 任务处理失败，系统 SHALL 在状态查询中返回错误信息
5. WHEN 任务创建超过 24 小时未查询，系统 SHALL 清理该任务的结果文件
6. WHILE 任务排队中，系统 SHALL 按先进先出顺序调度任务执行

### 需求 6: 配额与限流

**User Story:** AS 平台管理员, I want 控制开发者的调用配额, so that 平台资源能被公平使用

#### Acceptance Criteria

1. WHEN 开发者调用接口，系统 SHALL 在配额范围内放行请求
2. WHEN 开发者超出配额限制，系统 SHALL 拒绝请求并返回 429 错误
3. WHEN 平台管理员调整开发者配额，系统 SHALL 在后续请求中应用新配额
4. IF 开发者配额即将用尽，系统 SHALL 在响应头中提示剩余配额

### 需求 7: 管理后台

**User Story:** AS 平台管理员, I want 通过管理后台管理开发者与配额, so that 我能维护平台运营

#### Acceptance Criteria

1. WHEN 平台管理员查看开发者列表，系统 SHALL 展示全部开发者及其 API Key 状态
2. WHEN 平台管理员查看调用统计，系统 SHALL 展示各接口的调用次数与分布
3. WHEN 平台管理员启用或停用开发者，系统 SHALL 立即生效该开发者的接口访问权限
4. WHEN 平台管理员修改开发者配额，系统 SHALL 保存修改并生效
5. WHEN 平台管理员使用可视化后台，系统 SHALL 提供开发者、Key、配额、统计的图形化操作界面

### 需求 8: 接口文档

**User Story:** AS 开发者, I want 查阅平台接口文档, so that 我能正确调用各剪辑接口

#### Acceptance Criteria

1. WHEN 开发者访问文档页面，系统 SHALL 提供各接口的参数说明与示例
2. WHEN 开发者访问文档页面，系统 SHALL 提供在线调试能力
