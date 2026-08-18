<template>
  <div style="max-width: 400px; margin: 120px auto">
    <el-card>
      <template #header><b>管理员登录</b></template>
      <el-form @submit.prevent="login">
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-button type="primary" style="width: 100%" @click="login">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api'

const router = useRouter()
const username = ref('')
const password = ref('')

async function login() {
  try {
    const { data } = await http.post('/admin/login', {
      username: username.value,
      password: password.value
    })
    localStorage.setItem('admin_token', data.token)
    router.push('/developers')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  }
}
</script>
