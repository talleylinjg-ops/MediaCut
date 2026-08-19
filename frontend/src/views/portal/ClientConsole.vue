<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 900px; margin: 0 auto">
      <el-card v-if="me">
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h2 style="margin: 0">{{ me.name }}</h2>
          <el-button type="danger" plain @click="logout">退出登录</el-button>
        </div>
        <p>邮箱：{{ me.email }}</p>
        <el-row :gutter="16" style="margin-top: 16px">
          <el-col :span="6">
            <el-statistic title="计费类型" :value="me.billing_type === 'internal' ? '内部免费' : '对外计费'" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="余额 (点)" :value="me.balance" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="今日配额" :value="me.quota_used" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="配额上限" :value="me.quota_limit" />
          </el-col>
        </el-row>
      </el-card>

      <el-card style="margin-top: 20px">
        <h3>自助充值</h3>
        <p>当前余额：<b>{{ me.balance }}</b> 点。充值后立即到账，可用于抵扣调用费用。</p>
        <el-form inline style="margin-top: 12px" @submit.prevent>
          <el-form-item label="金额 (点)">
            <el-input-number v-model="rechargeAmount" :min="1" :max="1000000" :step="100" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="recharging" @click="recharge">充值</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card style="margin-top: 20px">
        <h3>API Key</h3>
        <p v-if="newKey">
          <el-alert type="success" :closable="false" title="新 Key 已生成，请立即保存（仅此一次展示）：" />
          <code style="display: block; margin-top: 8px; word-break: break-all">{{ newKey }}</code>
        </p>
        <p v-else>Key 以哈希形式存储，仅在申请或重置时展示一次。</p>
        <el-button type="warning" @click="resetKey">重置 API Key</el-button>
      </el-card>

      <el-card style="margin-top: 20px">
        <h3>最近调用记录</h3>
        <el-table :data="logs" v-loading="loading">
          <el-table-column prop="endpoint" label="接口" />
          <el-table-column prop="status_code" label="状态码" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status_code < 400 ? 'success' : 'danger'">{{ row.status_code }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="cost" label="费用 (点)" width="100" />
          <el-table-column prop="created_at" label="时间" width="200">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api'
import PortalNav from '../../components/PortalNav.vue'

const router = useRouter()
const me = ref(null)
const logs = ref([])
const loading = ref(false)
const newKey = ref('')
const rechargeAmount = ref(100)
const recharging = ref(false)

function formatTime(t) {
  return t ? t.replace('T', ' ').slice(0, 19) : ''
}

async function load() {
  loading.value = true
  try {
    const [meResp, logsResp] = await Promise.all([
      http.get('/dev/client/me'),
      http.get('/dev/client/logs')
    ])
    me.value = meResp.data
    logs.value = logsResp.data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function recharge() {
  recharging.value = true
  try {
    const { data } = await http.post('/dev/client/recharge', { amount: rechargeAmount.value })
    me.value.balance = data.balance
    ElMessage.success(`充值成功，当前余额 ${data.balance} 点`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '充值失败')
  } finally {
    recharging.value = false
  }
}

async function resetKey() {
  await ElMessageBox.confirm('重置后旧 Key 立即失效，确定继续？', '重置 API Key', { type: 'warning' })
  const { data } = await http.post('/dev/client/reset-key')
  newKey.value = data.api_key
  ElMessage.success('Key 已重置')
}

function logout() {
  localStorage.removeItem('client_token')
  router.push('/client/login')
}

onMounted(load)
</script>
