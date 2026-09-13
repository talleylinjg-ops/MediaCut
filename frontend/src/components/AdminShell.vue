<template>
  <el-container style="min-height: 100vh">
    <el-aside width="200px" style="background: #fff; border-right: 1px solid #e4e7ed">
      <div class="admin-identity">
        <el-avatar :size="32" style="background: #409eff">{{ avatarText }}</el-avatar>
        <div class="admin-meta">
          <div class="admin-name">{{ admin.name || '管理员' }}</div>
          <div class="admin-account">{{ admin.username }}</div>
        </div>
      </div>
      <el-menu :default-active="active" router>
        <el-menu-item index="/admin">首页</el-menu-item>
        <el-menu-item index="/developers">开发者管理</el-menu-item>
        <el-menu-item index="/stats">调用统计</el-menu-item>
        <el-menu-item index="/account">账号中心</el-menu-item>
        <el-menu-item :index="active" style="color: #f56c6c" @click="logout">退出登录</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <slot />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api'
import { clearAdminToken } from '../utils/auth'

const route = useRoute()
const active = ref(route.path)
const admin = ref({ username: '', name: '' })
const avatarText = computed(() => (admin.value.name || admin.value.username || '管').slice(0, 1))

onMounted(async () => {
  try {
    const { data } = await http.get('/admin/profile')
    admin.value = { username: data.username || '', name: data.name || '' }
  } catch (e) {
    // 无效会话由请求拦截器统一跳转登录
  }
})

function logout() {
  clearAdminToken()
  location.href = '/login'
}
</script>

<style scoped>
.admin-identity {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 16px 12px;
  border-bottom: 1px solid #e4e7ed;
}
.admin-identity .admin-meta {
  min-width: 0;
}
.admin-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.admin-account {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
