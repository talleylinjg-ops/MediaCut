<template>
  <div style="min-height: 100vh; display: flex; flex-direction: column">
    <PortalNav />
    <div style="padding: 40px; max-width: 900px; margin: 0 auto; flex: 1">
      <el-card v-if="me">
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h2 style="margin: 0">控制台</h2>
          <div>
            <el-button @click="openProfile" style="margin-right: 8px">修改资料</el-button>
            <el-button @click="pwdDialog = true" style="margin-right: 8px">修改密码</el-button>
            <el-button type="danger" plain @click="logout">退出登录</el-button>
          </div>
        </div>
        <p>开发者：{{ me.name }}（{{ me.email }}）</p>
        <el-row :gutter="16" style="margin-top: 16px">
          <el-col :span="8">
            <el-statistic title="计费类型" :value="me.billing_type === 'internal' ? '内部免费' : '对外计费'" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="余额 (点)" :value="me.balance" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="点数兑换" value="1 元 = 100 点" />
          </el-col>
        </el-row>
      </el-card>

      <el-card style="margin-top: 20px">
        <h3>自助充值</h3>
        <p>当前余额：<b>{{ me.balance }}</b> 点。输入人民币金额，扫码完成支付后点数自动到账（1 元 = 100 点）。</p>
        <el-alert
          v-if="!payReady"
          type="error"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
          title="支付渠道未配置，暂无法充值。请联系平台管理员在账号中心配置支付渠道。"
        />
        <el-form inline style="margin-top: 12px" @submit.prevent>
          <el-form-item label="金额 (元)">
            <el-input-number v-model="rechargeYuan" :min="0.01" :max="10000" :step="10" :precision="2" />
          </el-form-item>
          <el-form-item label="支付方式">
            <el-radio-group v-model="payMethod">
              <el-radio value="alipay">支付宝</el-radio>
              <el-radio value="wechat">微信支付</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="recharging" :disabled="!payReady" @click="createOrder">去支付</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card style="margin-top: 20px">
        <h3>充值记录</h3>
        <el-table :data="orders" size="small">
          <el-table-column prop="order_no" label="订单号" width="180" />
          <el-table-column label="金额" width="110">
            <template #default="{ row }">{{ yuan(row.amount_cents) }} 元</template>
          </el-table-column>
          <el-table-column prop="points" label="到账点数" width="110" />
          <el-table-column label="支付方式" width="100">
            <template #default="{ row }">{{ row.payment_provider === 'alipay' ? '支付宝' : '微信支付' }}</template>
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
        <el-alert v-if="newKey" type="success" :closable="false" title="新 Key 已生成，登录期间可随时查看/复制。退出登录将清除本机残留：" />
        <div v-if="newKey || savedKey" style="margin-top: 10px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap">
          <code style="word-break: break-all; background: #f5f7fa; padding: 8px 12px; border-radius: 6px; border: 1px solid #e4e7ed">{{ newKey || savedKey }}</code>
          <el-button size="small" type="primary" plain @click="copyKey(newKey || savedKey)">复制</el-button>
        </div>
        <p v-if="!newKey && savedKey" style="margin: 8px 0 0; font-size: 12px; color: #909399">
          本机暂存的 API Key（仅本会员登录期内保留）。退出登录时将一并清除，需要长期使用请点击【复制】发给对方。
        </p>
        <p v-if="!newKey && !savedKey" style="margin: 8px 0 0; font-size: 12px; color: #909399">
          Key 以哈希形式存储，仅申请或重置时展示一次。重置后将自动保存到本机。
        </p>
        <div style="margin-top: 10px">
          <el-button type="warning" @click="resetKey">重置 API Key</el-button>
          <el-button v-if="savedKey" type="danger" plain size="small" style="margin-left: 8px" @click="clearSavedKey">清除本机 Key</el-button>
        </div>
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

      <div style="text-align: center; margin-top: 32px; color: #909399; font-size: 14px">
        联系我们：<a href="mailto:172645428@qq.com" style="color: #409eff">172645428@qq.com</a>
      </div>
    </div>

    <el-dialog v-model="payDialog" title="扫码支付" width="420px" :close-on-click-modal="false" @closed="stopPolling">
      <div style="text-align: center">
        <div style="font-size: 13px; color: #909399">支付金额</div>
        <div style="font-size: 28px; font-weight: 700; margin: 8px 0">
          {{ yuan(order ? order.amount_cents : 0) }} 元（{{ order ? order.points : 0 }} 点）
        </div>
        <div style="margin: 12px auto">
          <canvas ref="qrCanvas" style="width: 200px; height: 200px" />
        </div>
        <div style="font-size: 13px; color: #606266">
          请使用{{ order?.payment_provider === 'alipay' ? '支付宝' : '微信' }}扫码支付
        </div>
        <div style="font-size: 12px; color: #909399; margin-top: 4px">订单号：{{ order ? order.order_no : '' }}</div>
      </div>
      <template #footer>
        <el-button :loading="paying" @click="cancelPay">取消支付</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="pwdDialog" title="修改密码" width="420px">
      <el-form label-width="90px" @submit.prevent>
        <el-form-item label="当前密码">
          <el-input v-model="pwdForm.current" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.next" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialog = false">取消</el-button>
        <el-button type="primary" :loading="pwdLoading" @click="changePassword">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="profileDialog" title="修改资料" width="420px">
      <el-form label-width="70px" @submit.prevent>
        <el-form-item label="名称">
          <el-input v-model="profileForm.name" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="profileForm.email" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="profileDialog = false">取消</el-button>
        <el-button type="primary" :loading="profileLoading" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import QRCode from 'qrcode'
import http from '../../api'
import PortalNav from '../../components/PortalNav.vue'

const router = useRouter()
const me = ref(null)
const logs = ref([])
const orders = ref([])
const loading = ref(false)
const newKey = ref('')
const savedKey = ref(localStorage.getItem('saved_api_key') || '')
const rechargeYuan = ref(10)
const payMethod = ref('alipay')
const recharging = ref(false)
const paying = ref(false)
const payDialog = ref(false)
const order = ref(null)
const qrCanvas = ref(null)
const pwdDialog = ref(false)
const pwdForm = ref({ current: '', next: '' })
const pwdLoading = ref(false)
const profileDialog = ref(false)
const profileForm = ref({ name: '', email: '' })
const profileLoading = ref(false)
const payStatus = ref({ alipay: false, wechat: false })
const payReady = computed(() => Boolean(payStatus.value[payMethod.value]))
let pollTimer = null

function yuan(cents) {
  return (cents / 100).toFixed(2)
}

function formatTime(t) {
  return t ? t.replace('T', ' ').slice(0, 19) : ''
}

async function load() {
  loading.value = true
  try {
    const [meResp, logsResp, ordersResp, payResp] = await Promise.all([
      http.get('/dev/client/me'),
      http.get('/dev/client/logs'),
      http.get('/dev/client/recharge/orders'),
      http.get('/dev/pay/status')
    ])
    me.value = meResp.data
    logs.value = logsResp.data
    orders.value = ordersResp.data
    payStatus.value = payResp.data
    if (meResp.data.api_key && !localStorage.getItem('saved_api_key')) {
      localStorage.setItem('saved_api_key', meResp.data.api_key)
      savedKey.value = meResp.data.api_key
    }
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
      amount_yuan: rechargeYuan.value,
      payment_method: payMethod.value
    })
    order.value = data
    payDialog.value = true
    await nextTick()
    if (qrCanvas.value && data.qr_content) {
      await QRCode.toCanvas(qrCanvas.value, data.qr_content, { width: 200, margin: 1 })
    }
    startPolling()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建订单失败')
  } finally {
    recharging.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const { data } = await http.get(`/dev/client/recharge/order/${order.value.order_no}`)
      if (data.status === 'paid') {
        stopPolling()
        payDialog.value = false
        const meResp = await http.get('/dev/client/me')
        me.value = meResp.data
        ElMessage.success(`支付成功，到账 ${order.value.points} 点，当前余额 ${me.value.balance} 点`)
        load()
      }
    } catch (e) {
      stopPolling()
      ElMessage.error('查询订单状态失败')
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function cancelPay() {
  stopPolling()
  payDialog.value = false
}

async function resetKey() {
  await ElMessageBox.confirm('重置后旧 Key 立即失效，确定继续？', '重置 API Key', { type: 'warning' })
  const { data } = await http.post('/dev/client/reset-key')
  newKey.value = data.api_key
  savedKey.value = data.api_key
  localStorage.setItem('saved_api_key', data.api_key)
  ElMessage.success('Key 已重置，已保存到本机，可复制分享')
}

function copyKey(k) {
  if (!k) return
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(k)
      .then(() => ElMessage.success('Key 已复制，可粘贴分享给他人'))
      .catch(() => ElMessage.error('复制失败，请手动选择复制'))
  } else {
    ElMessage.error('当前浏览器不支持自动复制，请手动选择复制')
  }
}

function clearSavedKey() {
  localStorage.removeItem('saved_api_key')
  savedKey.value = ''
  newKey.value = ''
  ElMessage.success('已清除本机保存的 Key')
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
    pwdDialog.value = false
    ElMessage.success('密码修改成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    pwdLoading.value = false
  }
}

function openProfile() {
  profileForm.value = { name: me.value.name || '', email: me.value.email || '' }
  profileDialog.value = true
}

async function saveProfile() {
  if (!profileForm.value.name.trim() || !profileForm.value.email.trim()) {
    return ElMessage.warning('名称与邮箱不能为空')
  }
  profileLoading.value = true
  try {
    const { data } = await http.put('/dev/client/profile', {
      name: profileForm.value.name.trim(),
      email: profileForm.value.email.trim()
    })
    me.value = data
    profileDialog.value = false
    ElMessage.success('资料已更新')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    profileLoading.value = false
  }
}

function logout() {
  localStorage.removeItem('client_token')
  localStorage.removeItem('api_key')
  localStorage.removeItem('saved_api_key')
  sessionStorage.removeItem('api_key')
  savedKey.value = ''
  ElMessage.success('已退出登录，本机保存的 API Key 已一并清除')
  router.push('/client/login')
}

onMounted(load)
</script>
