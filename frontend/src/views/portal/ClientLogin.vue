<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 480px; margin: 0 auto">
      <el-card>
        <h2>客户登录</h2>
        <el-form :model="form" label-width="70px" @submit.prevent>
          <el-form-item label="邮箱">
            <el-input v-model="form.email" placeholder="注册时填写的邮箱" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password @keyup.enter="login" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="login">登录</el-button>
          </el-form-item>
        </el-form>
        <el-button link type="primary" @click="$router.push('/register')">还没有账号？去申请</el-button>
      </el-card>

      <el-card v-if="savedKey" style="margin-top: 16px; background: #fdf6ec; border-color: #e6a23c">
        <h3 style="margin: 0 0 8px; font-size: 14px; color: #e6a23c">本机暂存的 API Key</h3>
        <code style="display: block; word-break: break-all; background: #fff; padding: 8px 10px; border-radius: 6px; border: 1px solid #f3d19e">{{ savedKey }}</code>
        <div style="margin-top: 10px; display: flex; gap: 8px">
          <el-button size="small" type="warning" plain @click="copyKey">复制，分享给他人调用</el-button>
          <el-button size="small" type="danger" plain @click="clearSavedKey">清除本机 Key</el-button>
        </div>
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
const form = reactive({ email: '', password: '' })
const loading = ref(false)
const savedKey = ref(localStorage.getItem('saved_api_key') || '')

function copyKey() {
  if (!savedKey.value) return
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(savedKey.value)
      .then(() => ElMessage.success('Key 已复制，可粘贴分享给他人'))
      .catch(() => ElMessage.error('复制失败，请手动选择复制'))
  } else {
    ElMessage.error('当前浏览器不支持自动复制，请手动选择复制')
  }
}

function clearSavedKey() {
  localStorage.removeItem('saved_api_key')
  savedKey.value = ''
  ElMessage.success('已清除本机保存的 Key')
}

async function login() {
  loading.value = true
  try {
    const { data } = await http.post('/dev/client/login', form)
    localStorage.setItem('client_token', data.token)
    if (data.api_key) {
      localStorage.setItem('saved_api_key', data.api_key)
      savedKey.value = data.api_key
    }
    ElMessage.success('登录成功，API Key 已自动保存到本机')
    router.push('/client/console')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
