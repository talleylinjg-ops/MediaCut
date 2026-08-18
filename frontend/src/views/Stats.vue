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
      <h3>调用统计</h3>
      <el-table :data="stats" v-loading="loading">
        <el-table-column prop="endpoint" label="接口" />
        <el-table-column prop="count" label="调用次数" />
        <el-table-column prop="success" label="成功" />
        <el-table-column prop="failed" label="失败" />
      </el-table>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api'

const route = useRoute()
const active = ref(route.path)
const stats = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/admin/stats')
    stats.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
