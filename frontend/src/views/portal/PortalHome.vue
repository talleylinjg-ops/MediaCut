<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 1000px; margin: 0 auto">
      <h1 style="font-size: 24px; margin: 0 0 12px">大气媒体剪辑 API 服务平台</h1>
      <p>
        一站式图片、音频与 AI 处理能力，通过简单 HTTP 接口接入，配额透明、按量计费。
      </p>
      <el-row :gutter="20" style="margin-top: 24px">
        <el-col :span="8">
          <el-card>
            <h3>图片剪辑</h3>
            <p>裁切、缩放、滤镜、水印、格式转换</p>
            <p><el-tag type="success">1 点 / 次</el-tag></p>
            <el-button v-if="!STATIC_ONLY" size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=image')">去试用</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>音频剪辑</h3>
            <p>裁剪、拼接、音量调整、格式转换</p>
            <p><el-tag type="warning">2 点 / 次</el-tag></p>
            <el-button v-if="!STATIC_ONLY" size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=audio')">去试用</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>AI 处理</h3>
            <p>人像抠图、画质增强、语音识别、语音合成</p>
            <p><el-tag type="danger">5-15 点 / 次</el-tag></p>
            <el-button v-if="!STATIC_ONLY" size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=ai')">去试用</el-button>
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="8">
          <el-card>
            <h3>AI 创作与工具</h3>
            <p>文生图、图生图编辑、文生视频、语音合成、人像抠图、画质增强、语音识别</p>
            <p><el-tag type="danger">10-20 点 / 次</el-tag></p>
            <el-button v-if="!STATIC_ONLY" size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=create')">去创作</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>异步 AI 任务</h3>
            <p>大模型任务异步排队处理，提交后轮询状态获取结果</p>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>计费双轨</h3>
            <p>内部调用按每日配额免费使用，对外按接口价格扣减预充值余额</p>
          </el-card>
        </el-col>
      </el-row>
      <div style="margin-top: 32px">
        <el-button v-if="!STATIC_ONLY" type="primary" size="large" @click="$router.push('/register')">立即申请 API Key</el-button>
        <el-button v-else type="primary" size="large" tag="a" href="mailto:saas@didimedia.com?subject=MediaCut%20API%20Key%20%E7%94%B3%E8%AF%B7">邮件申请 API Key</el-button>
        <el-button size="large" @click="$router.push('/docs')">查看接入文档</el-button>
      </div>

      <h2 style="font-size: 20px; margin: 40px 0 12px">常见问题</h2>
      <el-collapse>
        <el-collapse-item title="MediaCut API 是什么？" name="faq-what">
          MediaCut API 是一站式图片、音频与 AI 媒体处理 HTTP API 服务平台：提供图片剪辑（裁切/缩放/滤镜/水印/格式转换）、音频剪辑（裁剪/拼接/音量/转换）、人像抠图、画质增强、语音识别、语音合成、文生图、图生图编辑与文生视频（画面+运镜）能力，按量计费并提供免费额度。
        </el-collapse-item>
        <el-collapse-item title="收费吗？如何计费？" name="faq-price">
          注册即赠 100 点免费额度。同步接口按次计费：图片剪辑 1 点/次、音频剪辑 2 点/次；AI 能力 5-20 点/次（语音合成 5 点、人像抠图/语音识别/文生图/对话剪辑 10 点、画质增强/图生图编辑 15 点、文生视频 20 点）。部分文生图请求由免费生成渠道支持时不扣点。
        </el-collapse-item>
        <el-collapse-item title="如何接入？需要什么认证方式？" name="faq-integrate">
          注册后即时获取 API Key，所有业务接口使用 Authorization: Bearer 请求头认证。同步接口直接返回处理结果；异步 AI 接口提交任务后返回 task_id，轮询 GET /api/v1/tasks/{task_id} 获取状态，完成后通过 GET /api/v1/result/{task_id}/{filename} 下载结果。
        </el-collapse-item>
        <el-collapse-item title="支持哪些编程语言？" name="faq-language">
          全部能力以标准 HTTP 接口提供，curl、Python、Node.js、PHP、Java、Go 等任何语言均可直接调用，无需专用 SDK；接入文档页提供可直接复制的 curl 示例。
        </el-collapse-item>
        <el-collapse-item title="文生视频是真视频生成吗？" name="faq-video">
          文生视频的实现方式：先用 AI 生成画面，再通过程序化运镜（推拉 zoom / 平移 pan）合成 MP4 短视频（H.264）。画面内容由 AI 生成，镜头运动为程序化驱动，适合做氛围镜头与素材开场；不支持真人级动态内容生成。
        </el-collapse-item>
        <el-collapse-item title="结果是什么格式？" name="faq-format">
          图片输出 PNG/JPEG/WebP 等常见格式，音频输出 MP3/WAV，视频输出 MP4（H.264）。处理结果通过带鉴权的下载链接获取，任务结果包含图片、音频、视频或文本（如语音识别转写文字）。
        </el-collapse-item>
        <el-collapse-item title="异步任务如何轮询状态？" name="faq-poll">
          提交异步 AI 任务后接口返回 task_id 与 status_url。轮询 GET /api/v1/tasks/{task_id}，status 依次为 pending（排队）、running（处理中）、succeeded（成功）或 failed（失败）；成功后调用 GET /api/v1/result/{task_id}/{filename} 下载结果，无需配置 webhook 回调。
        </el-collapse-item>
        <el-collapse-item title="常见错误码是什么含义？" name="faq-errors">
          401：API Key 无效或缺失；402：余额不足，请充值；429：当日配额已用完；503：AI 模型未配置。认证类错误请检查 Authorization: Bearer 请求头是否携带有效 Key。
        </el-collapse-item>
        <el-collapse-item title="有免费额度或免费能力吗？" name="faq-free">
          注册即赠 100 点免费额度，无需绑定支付方式。部分文生图请求由免费生成渠道（Pollinations）支持时不扣点，仍计入调用配额；内部渠道调用另有每日免费配额。
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import PortalNav from '../../components/PortalNav.vue'
import { STATIC_ONLY } from '../../staticMode'
</script>
