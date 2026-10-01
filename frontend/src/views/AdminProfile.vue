<template>
  <AdminShell>
    <div class="account-hero">
      <div>
        <h3 class="page-title">账号中心</h3>
        <p class="page-sub">管理管理员账号、云端模型 Token（可选）与支付渠道配置</p>
      </div>
      <div class="hero-right">
        <span class="hero-label">当前级别</span>
        <el-tag type="primary" effect="light" size="large">{{ profile.name || cfg.admin_username || '管理员' }}</el-tag>
      </div>
    </div>
    <div class="account-wrap">

      <el-row :gutter="20">
        <el-col :xs="24" :md="12">
          <el-card class="tcard" shadow="hover">
            <template #header><span class="tcard-header">修改管理员资料</span></template>
            <el-form :model="profile" label-width="110px" class="account-form" @submit.prevent>
              <el-form-item label="登录账号">
                <el-input v-model="profile.username" placeholder="用于登录管理后台" />
              </el-form-item>
              <el-form-item label="管理员级别">
                <el-select v-model="profile.name" style="width: 100%">
                  <el-option v-for="t in adminTiers" :key="t" :label="t" :value="t" />
                  <el-option
                    v-if="profile.name && !adminTiers.includes(profile.name)"
                    :label="profile.name + '（历史值）'"
                    :value="profile.name"
                  />
                </el-select>
                <div class="form-tip">管理员级别只能从预设挡位中选择，不可自由输入</div>
              </el-form-item>
              <el-form-item>
                <el-alert
                  type="info"
                  :closable="false"
                  show-icon
                  style="width: 100%"
                  title="修改登录账号后，下次登录需使用新账号。"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存资料</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card class="tcard" shadow="hover" style="margin-top: 20px">
            <template #header><span class="tcard-header">修改管理员密码</span></template>
            <el-form :model="pwd" label-width="110px" class="account-form" @submit.prevent>
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
        </el-col>

        <el-col :xs="24" :md="12">
          <el-card class="tcard" shadow="hover" style="height: 100%">
            <template #header><span class="tcard-header">ModelScope 云端 API（可选）</span></template>
            <el-alert
              type="success"
              :closable="false"
              show-icon
              style="margin-bottom: 16px"
              title="内置 AI 能力（AI 抠图 / 画质增强 / 语音识别 / 语音合成）已全部本地免费运行，无需任何 Token。填写下方 Token 后，可使用云端生成式能力：图生图编辑（换装/加删物体/换背景，主用 Qwen-Image-Edit，失败自动回退 Qwen-Image）、文生图云端备份、图片理解与对话意图解析。"
            />
            <el-form label-width="110px" class="account-form" @submit.prevent>
              <el-form-item label="API Token">
                <el-input
                  v-model="tokenInput"
                  type="password"
                  show-password
                  placeholder="sk- 开头的 ModelScope 访问令牌"
                />
              </el-form-item>
              <el-form-item label="当前状态">
                <el-tag :type="configured ? 'success' : 'info'">
                  {{ configured ? '已配置云端 Token' : '本地免费模式（无需 Token）' }}
                </el-tag>
              </el-form-item>
              <el-form-item v-if="Object.keys(cfg.models).length" label="使用的模型">
                <div class="model-list">
                  <div v-for="(m, k) in cfg.models" :key="k" class="model-row">
                    <span class="model-name">{{ k }}</span>
                    <code class="model-val">{{ m }}</code>
                  </div>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="savingToken" @click="saveToken">保存 Token</el-button>
                <el-button v-if="configured" @click="clearToken">清除</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
      </el-row>

      <el-card class="tcard" shadow="hover" style="margin-top: 20px">
        <template #header><span class="tcard-header">支付渠道配置</span></template>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
          title="配置后客户控制台即可真实收款（扫码支付）。需在支付宝开放平台 / 微信商户平台申请商户资质并获取密钥。未配置时充值下单会提示渠道未配置。"
        />
        <el-form label-width="110px" @submit.prevent>
          <el-row :gutter="24">
            <el-col :xs="24" :md="12">
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
            </el-col>
            <el-col :xs="24" :md="12">
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
            </el-col>
          </el-row>
          <el-divider content-position="left">回调地址</el-divider>
          <el-form-item label="回调基础地址" style="max-width: 720px">
            <el-input v-model="pay.notify_base" placeholder="如 https://your-domain.com，用于支付平台回调通知" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingPay" @click="savePayConfig">保存支付配置</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </AdminShell>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import http from '../api'
import { clearAdminToken } from '../utils/auth'
import AdminShell from '../components/AdminShell.vue'

const pwd = reactive({ current_password: '', new_password: '', confirm: '' })
const savingPwd = ref(false)

const cfg = reactive({ admin_username: '', modelscope_configured: false, models: {} })
const configured = ref(false)
const tokenInput = ref('')
const savingToken = ref(false)

const profile = reactive({ username: '', name: '' })
const savingProfile = ref(false)
const adminTiers = ['超级管理员', '高级管理员', '普通管理员', '操作员']

async function saveProfile() {
  if (!profile.username.trim()) {
    ElMessage.warning('登录账号不能为空')
    return
  }
  if (!profile.name.trim()) {
    ElMessage.warning('请选择管理员级别')
    return
  }
  savingProfile.value = true
  try {
    await http.put('/admin/profile', {
      username: profile.username.trim(),
      name: profile.name.trim()
    })
    ElMessage.success('管理员资料已更新')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingProfile.value = false
  }
}

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
    clearAdminToken()
    location.href = '/login'
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    savingPwd.value = false
  }
}

async function loadConfig() {
  try {
    const [cfgResp, profileResp] = await Promise.all([
      http.get('/admin/config'),
      http.get('/admin/profile')
    ])
    Object.assign(cfg, cfgResp.data)
    configured.value = cfgResp.data.modelscope_configured
    profile.username = profileResp.data.username || cfgResp.data.admin_username
    profile.name = profileResp.data.name || cfgResp.data.admin_username
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

<style scoped>
.account-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 24px 28px 20px;
  background: linear-gradient(120deg, #409eff22, #ffffff);
  border-radius: 12px;
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
}
.page-title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}
.page-sub {
  margin: 0;
  font-size: 13px;
  color: #909399;
}
.hero-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.hero-label {
  font-size: 13px;
  color: #909399;
}
.account-wrap {
  width: 100%;
}
.account-form {
  max-width: 600px;
}
.tcard {
  border-radius: 10px;
  transition: box-shadow 0.2s;
}
.tcard:hover {
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.1) !important;
}
.tcard :deep(.el-card__header) {
  background: linear-gradient(90deg, #f5f7fa, #ffffff);
  border-radius: 10px 10px 0 0;
}
.tcard-header {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  position: relative;
  padding-left: 12px;
}
.tcard-header::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 16px;
  border-radius: 2px;
  background: #409eff;
}
.tcard :deep(.el-input__wrapper),
.tcard :deep(.el-textarea__inner) {
  border-radius: 6px;
}
.form-tip {
  line-height: 1.6;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.model-list {
  width: 100%;
  line-height: 1.9;
}
.model-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 4px 0;
}
.model-name {
  flex-shrink: 0;
  font-weight: 600;
  color: #606266;
}
.model-val {
  font-size: 12px;
  color: #909399;
  word-break: break-all;
}
</style>
