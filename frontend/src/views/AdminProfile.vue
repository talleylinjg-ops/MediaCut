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
      <h3>账号中心</h3>

      <el-card style="max-width: 560px">
        <template #header><b>修改管理员密码</b></template>
        <el-form :model="pwd" label-width="110px" @submit.prevent>
          <el-form-item label="当前密码">
            <el-input v-model="pwd.current_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="pwd.new_password" type="password" show-password placeholder="至少 6 位" />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input v-model="pwd.confirm" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingPwd" @click="changePassword">保存密码</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card style="max-width: 560px; margin-top: 20px">
        <template #header><b>ModelScope AI 配置</b></template>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
          title="在 modelscope.cn 注册后，点击右上角头像 → 访问令牌 获取。填好后 AI 抠图/增强/ASR/TTS 即可使用。"
        />
        <el-form label-width="110px" @submit.prevent>
          <el-form-item label="API Token">
            <el-input
              v-model="tokenInput"
              type="password"
              show-password
              placeholder="sk- 开头的 ModelScope 访问令牌"
            />
          </el-form-item>
          <el-form-item label="当前状态">
            <el-tag :type="configured ? 'success' : 'danger'">
              {{ configured ? '已配置' : '未配置（AI 接口返回 503）' }}
            </el-tag>
          </el-form-item>
          <el-form-item label="使用的模型">
            <div style="line-height: 2">
              <div v-for="(m, k) in cfg.models" :key="k">
                <b>{{ k }}</b>：{{ m }}
              </div>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingToken" @click="saveToken">保存 Token</el-button>
            <el-button v-if="configured" @click="clearToken">清除</el-button>
          </el-form-item>
        </el-form>
      </el-card>
      <el-card style="max-width: 560px; margin-top: 20px">
        <template #header><b>支付渠道配置</b></template>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
          title="配置后客户控制台即可真实收款（扫码支付）。需在支付宝开放平台 / 微信商户平台申请商户资质并获取密钥。未配置时充值下单会提示渠道未配置。"
        />
        <el-form label-width="110px" @submit.prevent>
          <el-divider content-position="left">支付宝（当面付）</el-divider>
          <el-form-item label="当前状态">
            <el-tag :type="cfg.alipay_configured ? 'success' : 'danger'">
              {{ cfg.alipay_configured ? '已配置' : '未配置' }}
            </el-tag>
          </el-form-item>
          <el-form-item label="APPID">
            <el-input v-model="pay.alipay_appid" placeholder="支付宝应用 APPID" />
          </el-form-item>
          <el-form-item label="应用私钥">
            <el-input v-model="pay.alipay_private_key" type="textarea" :rows="3" placeholder="-----BEGIN RSA PRIVATE KEY-----" />
          </el-form-item>
          <el-form-item label="支付宝公钥">
            <el-input v-model="pay.alipay_public_key" type="textarea" :rows="3" placeholder="支付宝公钥内容" />
          </el-form-item>

          <el-divider content-position="left">微信支付（Native 扫码）</el-divider>
          <el-form-item label="当前状态">
            <el-tag :type="cfg.wechat_configured ? 'success' : 'danger'">
              {{ cfg.wechat_configured ? '已配置' : '未配置' }}
            </el-tag>
          </el-form-item>
          <el-form-item label="AppID">
            <el-input v-model="pay.wechat_appid" placeholder="微信公众平台 AppID" />
          </el-form-item>
          <el-form-item label="商户号">
            <el-input v-model="pay.wechat_mchid" placeholder="微信支付商户号" />
          </el-form-item>
          <el-form-item label="APIv3 密钥">
            <el-input v-model="pay.wechat_apiv3_key" placeholder="32 位 APIv3 密钥" />
          </el-form-item>
          <el-form-item label="证书序列号">
            <el-input v-model="pay.wechat_serial_no" placeholder="商户 API 证书序列号" />
          </el-form-item>
          <el-form-item label="商户私钥">
            <el-input v-model="pay.wechat_private_key" type="textarea" :rows="3" placeholder="-----BEGIN PRIVATE KEY-----" />
          </el-form-item>

          <el-divider content-position="left">回调地址</el-divider>
          <el-form-item label="回调基础地址">
            <el-input v-model="pay.notify_base" placeholder="如 https://your-domain.com，用于支付平台回调通知" />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="savingPay" @click="savePayConfig">保存支付配置</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api'

const route = useRoute()
const active = ref(route.path)

const pwd = reactive({ current_password: '', new_password: '', confirm: '' })
const savingPwd = ref(false)

const cfg = reactive({ admin_username: '', modelscope_configured: false, models: {} })
const configured = ref(false)
const tokenInput = ref('')
const savingToken = ref(false)

const pay = reactive({
  alipay_appid: '',
  alipay_private_key: '',
  alipay_public_key: '',
  wechat_appid: '',
  wechat_mchid: '',
  wechat_apiv3_key: '',
  wechat_serial_no: '',
  wechat_private_key: '',
  notify_base: ''
})
const savingPay = ref(false)

async function changePassword() {
  if (pwd.new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (pwd.new_password !== pwd.confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  savingPwd.value = true
  try {
    await http.put('/admin/password', {
      current_password: pwd.current_password,
      new_password: pwd.new_password
    })
    ElMessage.success('密码已修改，请使用新密码重新登录')
    localStorage.removeItem('admin_token')
    location.href = '/login'
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    savingPwd.value = false
  }
}

async function loadConfig() {
  try {
    const { data } = await http.get('/admin/config')
    Object.assign(cfg, data)
    configured.value = data.modelscope_configured
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载配置失败')
  }
}

async function saveToken() {
  savingToken.value = true
  try {
    await http.put('/admin/config', { modelscope_api_token: tokenInput.value })
    ElMessage.success('Token 已保存')
    tokenInput.value = ''
    await loadConfig()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingToken.value = false
  }
}

async function clearToken() {
  savingToken.value = true
  try {
    await http.put('/admin/config', { modelscope_api_token: '' })
    ElMessage.success('已清除 Token')
    await loadConfig()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '清除失败')
  } finally {
    savingToken.value = false
  }
}

async function savePayConfig() {
  const alipayFields = ['alipay_appid', 'alipay_private_key', 'alipay_public_key']
  const wechatFields = ['wechat_appid', 'wechat_mchid', 'wechat_apiv3_key', 'wechat_serial_no', 'wechat_private_key']
  const filled = (fields) => fields.filter((f) => pay[f].trim()).length
  const complete = (fields) => fields.every((f) => pay[f].trim())

  const alipayFill = filled(alipayFields)
  const wechatFill = filled(wechatFields)
  const notifyFilled = Boolean(pay.notify_base.trim())

  if (!alipayFill && !wechatFill && !notifyFilled) {
    ElMessage.warning('请至少填写支付宝或微信一个渠道的完整配置')
    return
  }
  if (alipayFill && !complete(alipayFields)) {
    ElMessage.warning('支付宝配置不完整：APPID、应用私钥、支付宝公钥 缺一不可')
    return
  }
  if (wechatFill && !complete(wechatFields)) {
    ElMessage.warning('微信配置不完整：AppID、商户号、APIv3密钥、证书序列号、商户私钥 缺一不可')
    return
  }
  if (notifyFilled && !/^https?:\/\/.+/.test(pay.notify_base.trim())) {
    ElMessage.warning('回调基础地址需以 http:// 或 https:// 开头')
    return
  }

  savingPay.value = true
  const body = {}
  const map = {
    alipay_appid: 'pay_alipay_appid',
    alipay_private_key: 'pay_alipay_private_key',
    alipay_public_key: 'pay_alipay_public_key',
    wechat_appid: 'pay_wechat_appid',
    wechat_mchid: 'pay_wechat_mchid',
    wechat_apiv3_key: 'pay_wechat_apiv3_key',
    wechat_serial_no: 'pay_wechat_serial_no',
    wechat_private_key: 'pay_wechat_private_key',
    notify_base: 'pay_notify_base'
  }
  for (const [localKey, apiKey] of Object.entries(map)) {
    if (pay[localKey]) body[apiKey] = pay[localKey]
  }
  try {
    await http.put('/admin/config', body)
    ElMessage.success('支付配置已保存')
    Object.keys(pay).forEach((k) => (pay[k] = ''))
    await loadConfig()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingPay.value = false
  }
}

onMounted(loadConfig)
</script>
