<template>
  <el-container>
    <el-aside width="200px">
      <el-menu :default-active="active" router>
        <el-menu-item index="/admin">首页</el-menu-item>
        <el-menu-item index="/developers">开发者管理</el-menu-item>
        <el-menu-item index="/stats">调用统计</el-menu-item>
        <el-menu-item index="/account">账号中心</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <h3>调用统计</h3>
      <el-table :data="stats" v-loading="loading">
        <el-table-column prop="endpoint" label="接口" />
        <el-table-column prop="count" label="调用次数" />
        <el-table-column prop="success" label="成功" />
        <el-table-column prop="failed" label="失败" />
        <el-table-column prop="revenue" label="收入(点)" />
      </el-table>

      <h3 style="margin-top: 28px">调用明细</h3>
      <el-table :data="logs" v-loading="logsLoading" size="small">
        <el-table-column prop="developer_name" label="会员" width="160" />
        <el-table-column prop="developer_id" label="ID" width="60" />
        <el-table-column prop="endpoint" label="接口" />
        <el-table-column label="状态码" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status_code < 400 ? 'success' : 'danger'">{{ row.status_code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="费用(点)" width="90" />
        <el-table-column prop="created_at" label="使用时间" width="200">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
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
const logs = ref([])
const logsLoading = ref(false)

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

async function loadLogs() {
  logsLoading.value = true
  try {
    const { data } = await http.get('/admin/logs')
    logs.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载明细失败')
  } finally {
    logsLoading.value = false
  }
}

function formatTime(t) {
  return t ? t.replace('T', ' ').slice(0, 19) : ''
}

onMounted(() => {
  load()
  loadLogs()
})
</script>
