<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 560px; margin: 0 auto">
      <el-card>
        <h2>申请 API Key</h2>
        <el-form v-if="!apiKey" :model="form" label-width="90px" @submit.prevent>
          <el-form-item label="名称">
            <el-input v-model="form.name" placeholder="您的应用或团队名称" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" placeholder="用于登录客户控制台" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="submit">注册</el-button>
          </el-form-item>
        </el-form>
        <el-alert v-if="apiKey && isExisting" type="info" :closable="false" show-icon style="margin-bottom: 16px">
          <p>您已申请过 API Key（保存在浏览器中）：<code>{{ apiKey }}</code></p>
          <div style="margin-top: 8px">
            <el-button size="small" type="primary" @click="copyKey">复制 Key</el-button>
            <el-button size="small" @click="goPlayground">在线试用</el-button>
            <el-button size="small" @click="reapply">清除并重新申请</el-button>
          </div>
        </el-alert>
        <el-alert v-if="apiKey && !isExisting" type="success" :closable="false">
          <p>申请成功！请妥善保存您的 API Key：</p>
          <p>
            <code style="word-break: break-all">{{ apiKey }}</code>
            <el-button size="small" type="primary" style="margin-left: 8px" @click="copyKey">复制</el-button>
          </p>
          <el-button type="primary" style="margin-top: 8px" @click="goPlayground">在线试用</el-button>
          <el-button style="margin-top: 8px" @click="reapply">重新申请</el-button>
        </el-alert>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../../api'
import PortalNav from '../../components/PortalNav.vue'

const router = useRouter()
const form = reactive({ name: '', email: '', password: '' })
const loading = ref(false)
const apiKey = ref('')
const isExisting = ref(false)

onMounted(() => {
  const saved = localStorage.getItem('api_key')
  if (saved) {
    apiKey.value = saved
    isExisting.value = true
  }
})

async function submit() {
  loading.value = true
  try {
    const { data } = await http.post('/dev/register', form)
    apiKey.value = data.api_key
    isExisting.value = false
    localStorage.setItem('api_key', data.api_key)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}

function reapply() {
  localStorage.removeItem('api_key')
  apiKey.value = ''
  isExisting.value = false
}

function goPlayground() {
  router.push('/client/try')
}

async function copyKey() {
  try {
    await navigator.clipboard.writeText(apiKey.value)
    ElMessage.success('已复制')
  } catch (e) {
    const ta = document.createElement('textarea')
    ta.value = apiKey.value
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制')
  }
}
</script>
