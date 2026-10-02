<template>
  <div style="height: 100vh; display: flex; flex-direction: column">
    <PortalNav />
    <div style="padding: 8px 20px; border-bottom: 1px solid #e4e7ed; display: flex; align-items: center; gap: 16px">
      <strong>API 文档（Swagger）</strong>
      <el-button size="small" @click="$router.push('/')">返回首页</el-button>
    </div>
    <iframe :src="docsUrl" style="flex: 1; width: 100%; border: none" title="Swagger 文档" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import PortalNav from '../components/PortalNav.vue'

const docsUrl = ref('/api-docs')
</script>
