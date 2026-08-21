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

onMounted(loadConfig)
</script>
