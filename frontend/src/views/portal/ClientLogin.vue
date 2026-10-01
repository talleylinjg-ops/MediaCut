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
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../../api'
import { setClientToken } from '../../utils/auth'
import PortalNav from '../../components/PortalNav.vue'

const router = useRouter()
const form = reactive({ email: '', password: '' })
const loading = ref(false)

async function login() {
  loading.value = true
  try {
    const { data } = await http.post('/dev/client/login', form)
    setClientToken(data.token)
    ElMessage.success('登录成功')
    router.push('/client/console')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
