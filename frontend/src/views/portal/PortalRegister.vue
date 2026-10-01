<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 560px; margin: 0 auto">
      <el-card>
        <h2>申请 API Key</h2>
        <el-alert v-if="meKey" type="info" :closable="false" show-icon style="margin-bottom: 16px">
          <p>您已登录并申请过 API Key：<code>{{ meKey }}</code></p>
          <div style="margin-top: 8px">
            <el-button size="small" type="primary" @click="copyKey(meKey)">复制 Key</el-button>
            <el-button size="small" @click="goPlayground">在线试用</el-button>
            <el-button size="small" @click="goConsole">进入控制台</el-button>
          </div>
        </el-alert>
        <el-alert v-if="apiKey" type="success" :closable="false">
          <p>申请成功！请妥善保存您的 API Key（仅此一次展示，请立即复制）：</p>
          <p>
            <code style="word-break: break-all">{{ apiKey }}</code>
            <el-button size="small" type="primary" style="margin-left: 8px" @click="copyKey(apiKey)">复制</el-button>
          </p>
          <el-button type="primary" style="margin-top: 8px" @click="goPlayground">在线试用</el-button>
        </el-alert>
        <el-form v-if="!apiKey && !meKey" :model="form" label-width="90px" @submit.prevent>
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
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../../api'
import { clearClientToken } from '../../utils/auth'
import PortalNav from '../../components/PortalNav.vue'

const router = useRouter()
const form = reactive({ name: '', email: '', password: '' })
const loading = ref(false)
const apiKey = ref('')
const meKey = ref('')

onMounted(async () => {
  if (!localStorage.getItem('client_token')) return
  try {
    const { data } = await http.get('/dev/client/me')
    if (data.api_key) meKey.value = data.api_key
  } catch (e) {
    clearClientToken()
  }
})

async function submit() {
  loading.value = true
  try {
    const { data } = await http.post('/dev/register', form)
    apiKey.value = data.api_key
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}

function goPlayground() {
  router.push('/client/try')
}

function goConsole() {
  router.push('/client/console')
}

async function copyKey(k) {
  try {
    await navigator.clipboard.writeText(k)
    ElMessage.success('已复制')
  } catch (e) {
    const ta = document.createElement('textarea')
    ta.value = k
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制')
  }
}
</script>
