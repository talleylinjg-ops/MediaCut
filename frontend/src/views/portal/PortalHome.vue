<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 1000px; margin: 0 auto">
      <h2>大气媒体剪辑 API 服务平台</h2>
      <p>
        一站式图片、音频与 AI 处理能力，通过简单 HTTP 接口接入，配额透明、按量计费。
      </p>
      <el-row :gutter="20" style="margin-top: 24px">
        <el-col :span="8">
          <el-card>
            <h3>图片剪辑</h3>
            <p>裁切、缩放、滤镜、水印、格式转换</p>
            <p><el-tag type="success">1 点 / 次</el-tag></p>
            <el-button size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=image')">去试用</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>音频剪辑</h3>
            <p>裁剪、拼接、音量调整、格式转换</p>
            <p><el-tag type="warning">2 点 / 次</el-tag></p>
            <el-button size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=audio')">去试用</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>AI 处理</h3>
            <p>人像抠图、画质增强、语音识别、语音合成</p>
            <p><el-tag type="danger">5-15 点 / 次</el-tag></p>
            <el-button size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=ai')">去试用</el-button>
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <el-card>
            <h3>异步 AI 任务</h3>
            <p>大模型任务异步排队处理，提交后轮询状态获取结果</p>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <h3>计费双轨</h3>
            <p>内部调用按每日配额免费使用，对外按接口价格扣减预充值余额</p>
          </el-card>
        </el-col>
      </el-row>
      <div style="margin-top: 32px">
        <el-button type="primary" size="large" @click="$router.push('/register')">立即申请 API Key</el-button>
        <el-button size="large" @click="$router.push('/docs')">查看接入文档</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import PortalNav from '../../components/PortalNav.vue'
</script>
