export function getPriceTable() {
  return [
    { endpoint: '/api/v1/image/edit', name: '图片剪辑（裁切/缩放/滤镜/水印/格式）', price: 1 },
    { endpoint: '/api/v1/audio/edit', name: '音频剪辑（裁剪/拼接/音量/转换）', price: 2 },
    { endpoint: '/api/v1/ai/matting', name: 'AI 人像抠图', price: 10 },
    { endpoint: '/api/v1/ai/enhance', name: 'AI 画质增强', price: 15 },
    { endpoint: '/api/v1/ai/asr', name: 'AI 语音识别', price: 10 },
    { endpoint: '/api/v1/ai/tts', name: 'AI 语音合成', price: 5 },
    { endpoint: '/api/v1/ai/t2i', name: 'AI 文生图', price: 10 },
    { endpoint: '/api/v1/ai/i2i', name: 'AI 图生图编辑', price: 15 },
    { endpoint: '/api/v1/ai/video', name: 'AI 文生视频（画面+运镜）', price: 20 },
    { endpoint: '/api/v1/ai/chat', name: 'AI 对话剪辑', price: 10 }
  ]
}
