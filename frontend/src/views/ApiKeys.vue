<template>
  <el-container>
    <el-aside width="200px">
      <el-menu :default-active="active" router>
        <el-menu-item index="/developers">开发者管理</el-menu-item>
        <el-menu-item index="/stats">调用统计</el-menu-item>
        <el-menu-item index="/api-keys">API 申请演示</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <h3>API Key 申请演示</h3>
      <el-form style="max-width: 480px">
        <el-form-item label="开发者名称">
          <el-input v-model="name" placeholder="例如：张三科技" />
        </el-form-item>
        <el-form-item label="联系邮箱">
          <el-input v-model="email" placeholder="例如：dev@example.com" />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="register">申请 API Key</el-button>
      </el-form>
      <el-alert v-if="result" type="success" :closable="false" style="margin-top: 16px">
        <p>API Key：{{ result.api_key }}</p>
        <p>请妥善保存，调用接口时放入 <code>Authorization: Bearer &lt;key&gt;</code> 请求头。</p>
      </el-alert>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api'

const route = useRoute()
const active = ref(route.path)
const name = ref('')
const email = ref('')
const result = ref(null)
const loading = ref(false)

async function register() {
  loading.value = true
  try {
    const { data } = await http.post('/dev/register', {
      name: name.value,
      email: email.value
    })
    result.value = data
    ElMessage.success('申请成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '申请失败')
  } finally {
    loading.value = false
  }
}
</script>
