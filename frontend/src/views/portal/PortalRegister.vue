<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 560px; margin: 0 auto">
      <el-card>
        <h2>申请 API Key</h2>
        <el-form :model="form" label-width="90px" @submit.prevent>
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
          <p><code>{{ apiKey }}</code></p>
          <el-button type="primary" style="margin-top: 8px" @click="$router.push('/client/login')">
            前往客户控制台
          </el-button>
        </el-alert>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api'
import PortalNav from '../../components/PortalNav.vue'

const form = reactive({ name: '', email: '', password: '' })
const loading = ref(false)
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
</script>
