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
        <el-alert v-if="apiKey" type="success" :closable="false">
          <p>注册成功！请妥善保存您的 API Key：</p>
          <p>
            <code style="word-break: break-all">{{ apiKey }}</code>
            <el-button size="small" type="primary" style="margin-left: 8px" @click="copyKey">复制</el-button>
          </p>
          <el-button type="primary" style="margin-top: 8px" :loading="entering" @click="enterConsole">
            进入客户控制台
          </el-button>
        </el-alert>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../../api'
import PortalNav from '../../components/PortalNav.vue'

const router = useRouter()
const form = reactive({ name: '', email: '', password: '' })
const loading = ref(false)
const entering = ref(false)
const apiKey = ref('')

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

async function copyKey() {
  try {
    await navigator.clipboard.writeText(apiKey.value)
    ElMessage.success('已复制')
  } catch (e) {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function enterConsole() {
  entering.value = true
  try {
    const { data } = await http.post('/dev/client/login', {
      email: form.email,
      password: form.password
    })
    localStorage.setItem('client_token', data.token)
    router.push('/client/console')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '自动登录失败，请手动登录')
    router.push('/client/login')
  } finally {
    entering.value = false
  }
}
</script>
