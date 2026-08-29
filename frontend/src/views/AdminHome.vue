<template>
  <AdminShell>
    <h3>平台总览</h3>
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card>
            <el-statistic title="开发者总数" :value="d.total_developers" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <el-statistic title="启用中" :value="d.active_developers" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <el-statistic title="对外计费账户" :value="d.external_developers" />
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top: 20px">
        <el-col :span="8">
          <el-card>
            <el-statistic title="今日调用次数" :value="d.today_calls" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <el-statistic title="累计收入 (点)" :value="d.total_revenue" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <el-statistic title="账户余额总量 (点)" :value="d.total_balance" />
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top: 20px">
        <el-col :span="8">
          <el-card>
            <el-statistic title="排队/处理中任务" :value="d.pending_tasks" />
          </el-card>
        </el-col>
      </el-row>
  </AdminShell>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api'
import AdminShell from '../components/AdminShell.vue'

const d = reactive({
  total_developers: 0,
  active_developers: 0,
  external_developers: 0,
  today_calls: 0,
  total_revenue: 0,
  pending_tasks: 0,
  total_balance: 0
})

async function load() {
  try {
    const { data } = await http.get('/admin/dashboard')
    Object.assign(d, data)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
}

onMounted(load)
</script>
