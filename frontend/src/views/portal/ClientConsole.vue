<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 900px; margin: 0 auto">
      <el-card v-if="me">
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h2 style="margin: 0">控制台</h2>
          <el-button type="danger" plain @click="logout">退出登录</el-button>
        </div>
        <p>开发者：{{ me.name }}（{{ me.email }}）</p>
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
        <p>当前余额：<b>{{ me.balance }}</b> 点。生成订单后通过支付方式完成支付，到账后可用于抵扣调用费用。</p>
        <el-form inline style="margin-top: 12px" @submit.prevent>
          <el-form-item label="金额 (点)">
            <el-input-number v-model="rechargeAmount" :min="1" :max="1000000" :step="100" />
          </el-form-item>
          <el-form-item label="支付方式">
            <el-radio-group v-model="payMethod">
              <el-radio value="alipay">支付宝</el-radio>
              <el-radio value="wechat">微信支付</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="recharging" @click="createOrder">去支付</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card style="margin-top: 20px">
        <h3>充值记录</h3>
        <el-table :data="orders" size="small">
          <el-table-column prop="order_no" label="订单号" width="180" />
          <el-table-column prop="amount" label="金额 (点)" width="110" />
          <el-table-column label="支付方式" width="100">
            <template #default="{ row }">{{ row.payment_method === 'alipay' ? '支付宝' : '微信支付' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'paid' ? 'success' : 'warning'">
                {{ row.status === 'paid' ? '已支付' : '待支付' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
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
        <h3>修改密码</h3>
        <el-form label-width="110px" style="max-width: 420px" @submit.prevent>
          <el-form-item label="当前密码">
            <el-input v-model="pwdForm.current" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="pwdForm.next" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="pwdLoading" @click="changePassword">保存</el-button>
          </el-form-item>
        </el-form>
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

      <el-dialog v-model="payDialog" title="收银台（模拟支付）" width="420px">
        <div style="text-align: center">
          <div style="font-size: 13px; color: #909399">支付金额</div>
          <div style="font-size: 28px; font-weight: 700; margin: 8px 0">{{ order ? order.amount : 0 }} 点</div>
          <div
            style="width: 180px; height: 180px; border: 1px solid #e4e7ed; margin: 12px auto; display: flex; align-items: center; justify-content: center; color: #909399; font-size: 13px"
          >
            {{ order?.payment_method === 'alipay' ? '支付宝' : '微信支付' }}<br />付款二维码（模拟）
          </div>
          <div style="font-size: 13px; color: #606266">订单号：{{ order ? order.order_no : '' }}</div>
          <div style="color: #e6a23c; font-size: 13px; margin-top: 8px">演示环境为模拟支付，点击下方按钮模拟扫码支付完成。</div>
        </div>
        <template #footer>
          <el-button @click="payDialog = false">取消</el-button>
          <el-button type="primary" :loading="paying" @click="confirmPay">模拟支付完成</el-button>
        </template>
      </el-dialog>
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
const orders = ref([])
const loading = ref(false)
const newKey = ref('')
const rechargeAmount = ref(100)
const payMethod = ref('alipay')
const recharging = ref(false)
const paying = ref(false)
const payDialog = ref(false)
const order = ref(null)
const pwdForm = ref({ current: '', next: '' })
const pwdLoading = ref(false)

function formatTime(t) {
  return t ? t.replace('T', ' ').slice(0, 19) : ''
}

async function load() {
  loading.value = true
  try {
    const [meResp, logsResp, ordersResp] = await Promise.all([
      http.get('/dev/client/me'),
      http.get('/dev/client/logs'),
      http.get('/dev/client/recharge/orders')
    ])
    me.value = meResp.data
    logs.value = logsResp.data
    orders.value = ordersResp.data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function createOrder() {
  recharging.value = true
  try {
    const { data } = await http.post('/dev/client/recharge/order', {
      amount: rechargeAmount.value,
      payment_method: payMethod.value
    })
    order.value = data
    payDialog.value = true
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建订单失败')
  } finally {
    recharging.value = false
  }
}

async function confirmPay() {
  paying.value = true
  try {
    const { data } = await http.post(`/dev/client/recharge/order/${order.value.order_no}/pay`)
    payDialog.value = false
    me.value.balance = data.balance
    ElMessage.success(`支付成功，当前余额 ${data.balance} 点`)
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '支付失败')
  } finally {
    paying.value = false
  }
}

async function resetKey() {
  await ElMessageBox.confirm('重置后旧 Key 立即失效，确定继续？', '重置 API Key', { type: 'warning' })
  const { data } = await http.post('/dev/client/reset-key')
  newKey.value = data.api_key
  localStorage.setItem('api_key', data.api_key)
  ElMessage.success('Key 已重置')
}

async function changePassword() {
  if (!pwdForm.value.current || !pwdForm.value.next) return ElMessage.warning('请输入当前密码与新密码')
  if (pwdForm.value.next.length < 6) return ElMessage.warning('新密码至少 6 位')
  pwdLoading.value = true
  try {
    await http.post('/dev/client/password', {
      current_password: pwdForm.value.current,
      new_password: pwdForm.value.next
    })
    pwdForm.value.current = ''
    pwdForm.value.next = ''
    ElMessage.success('密码修改成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    pwdLoading.value = false
  }
}

function logout() {
  localStorage.removeItem('client_token')
  router.push('/client/login')
}

onMounted(load)
</script>
