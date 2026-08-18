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
      <h3>开发者管理</h3>
      <el-table :data="developers" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="api_key_hash" label="API Key (哈希)" width="200" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="计费" width="100">
          <template #default="{ row }">
            <el-tag :type="row.billing_type === 'internal' ? 'info' : 'primary'">
              {{ row.billing_type === 'internal' ? '内部免费' : '对外' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="balance" label="余额(点)" width="90" />
        <el-table-column prop="quota_limit" label="每日配额" width="100" />
        <el-table-column prop="quota_used" label="已用配额" width="100" />
        <el-table-column label="操作" width="300">
          <template #default="{ row }">
            <el-button size="small" @click="toggleStatus(row)">
              {{ row.status === 'active' ? '停用' : '启用' }}
            </el-button>
            <el-button size="small" type="primary" @click="editQuota(row)">改配额</el-button>
            <el-button size="small" type="warning" @click="recharge(row)">充值</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api'

const route = useRoute()
const active = ref(route.path)
const developers = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/admin/developers')
    developers.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function toggleStatus(row) {
  await http.put(`/admin/developers/${row.id}`, {
    status: row.status === 'active' ? 'disabled' : 'active'
  })
  load()
}

async function editQuota(row) {
  const { value } = await ElMessageBox.prompt('输入每日配额上限', '修改配额', {
    inputValue: String(row.quota_limit)
  })
  await http.put(`/admin/developers/${row.id}`, { quota_limit: Number(value) })
  load()
}

async function recharge(row) {
  const { value } = await ElMessageBox.prompt('输入充值点数（单位：点）', `为 ${row.name} 充值`, {
    inputValue: '100'
  })
  await http.put(`/admin/developers/${row.id}`, { recharge: Number(value) })
  load()
}

onMounted(load)
</script>
