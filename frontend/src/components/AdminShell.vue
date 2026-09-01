<template>
  <el-container style="min-height: 100vh">
    <el-aside width="200px" style="background: #fff; border-right: 1px solid #e4e7ed">
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
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const active = ref(route.path)

function logout() {
  localStorage.removeItem('admin_token')
  location.href = '/login'
}
</script>
