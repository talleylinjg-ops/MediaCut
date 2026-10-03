<template>
  <div>
    <PortalNav />
    <div style="padding: 48px 40px; max-width: 640px; margin: 0 auto">
      <h1 style="font-size: 22px; margin: 0 0 12px">申请 MediaCut API Key</h1>
      <p>
        当前为静态展示站点，API Key 由人工开通。请发送邮件说明您的使用场景、
        预期调用量与联系方式，我们将在 1-2 个工作日内回复并为您开通账号与 Key。
      </p>
      <el-alert type="info" :closable="false" style="margin: 16px 0">
        开通后即可使用全部能力：图片剪辑、音频剪辑、人像抠图、画质增强、语音识别、语音合成、文生图、图生图编辑与文生视频，注册账号含 100 点免费额度。
      </el-alert>
      <el-button type="primary" size="large" tag="a" href="mailto:saas@didimedia.com?subject=MediaCut%20API%20Key%20%E7%94%B3%E8%AF%B7">
        发送申请邮件
      </el-button>
    </div>
  </div>
</template>

<script setup>
import PortalNav from '../../components/PortalNav.vue'
</script>
