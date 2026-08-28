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
      <h3>开发者管理</h3>
      <el-table :data="developers" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column label="API Key" width="220">
          <template #default="{ row }">
            <code style="word-break: break-all">{{ row.api_key || '（无）' }}</code>
          </template>
        </el-table-column>
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
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="copyKey(row)">复制 KEY</el-button>
            <el-button size="small" @click="toggleStatus(row)">
              {{ row.status === 'active' ? '停用' : '启用' }}
            </el-button>
            <el-button size="small" type="warning" plain @click="viewDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-dialog v-model="detailDialog" :title="detail ? `${detail.name}（${detail.email}）的详细记录` : '查看'" width="880px">
        <div v-loading="detailLoading">
          <el-descriptions :column="4" size="small" style="margin-bottom: 12px">
            <el-descriptions-item label="余额">{{ detail?.balance }} 点</el-descriptions-item>
            <el-descriptions-item label="计费类型">{{ detail?.billing_type === 'internal' ? '内部免费' : '对外计费' }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ detail?.status }}</el-descriptions-item>
            <el-descriptions-item label="API Key">
              <code style="word-break: break-all">{{ detail?.api_key || '（无）' }}</code>
            </el-descriptions-item>
          </el-descriptions>

          <h4 style="margin: 8px 0">充值记录</h4>
          <el-table :data="detailOrders" size="small" style="margin-bottom: 16px">
            <el-table-column prop="order_no" label="订单号" width="180" />
            <el-table-column label="金额" width="100">
              <template #default="{ row }">{{ (row.amount_cents / 100).toFixed(2) }} 元</template>
            </el-table-column>
            <el-table-column prop="points" label="到账点数" width="90" />
            <el-table-column label="方式" width="90">
              <template #default="{ row }">{{ row.payment_provider === 'alipay' ? '支付宝' : '微信' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'paid' ? 'success' : 'warning'">{{ row.status === 'paid' ? '已支付' : '待支付' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="detailOrders.length === 0" description="暂无充值记录" :image-size="60" />

          <h4 style="margin: 8px 0">使用记录</h4>
          <el-table :data="detailLogs" size="small">
            <el-table-column prop="endpoint" label="接口" />
            <el-table-column label="状态码" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status_code < 400 ? 'success' : 'danger'">{{ row.status_code }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cost" label="费用(点)" width="90" />
            <el-table-column prop="created_at" label="时间" width="200">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="detailLogs.length === 0" description="暂无使用记录" :image-size="60" />
        </div>
      </el-dialog>
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
const developers = ref([])
const loading = ref(false)
const detailDialog = ref(false)
const detail = ref(null)
const detailLogs = ref([])
const detailOrders = ref([])
const detailLoading = ref(false)

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

async function copyKey(row) {
  const key = row.api_key
  if (!key) return ElMessage.warning('该开发者暂无明文 KEY')
  try {
    await navigator.clipboard.writeText(key)
    ElMessage.success('KEY 已复制到剪贴板')
  } catch (e) {
    const ta = document.createElement('textarea')
    ta.value = key
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('KEY 已复制到剪贴板')
  }
}

async function toggleStatus(row) {
  await http.put(`/admin/developers/${row.id}`, {
    status: row.status === 'active' ? 'disabled' : 'active'
  })
  load()
}

async function viewDetail(row) {
  detail.value = row
  detailLogs.value = []
  detailOrders.value = []
  detailDialog.value = true
  detailLoading.value = true
  try {
    const [logsResp, ordersResp] = await Promise.all([
      http.get(`/admin/developers/${row.id}/logs`),
      http.get(`/admin/developers/${row.id}/orders`)
    ])
    detailLogs.value = logsResp.data
    detailOrders.value = ordersResp.data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载记录失败')
  } finally {
    detailLoading.value = false
  }
}

function formatTime(t) {
  return t ? t.replace('T', ' ').slice(0, 19) : ''
}

onMounted(load)
</script>
