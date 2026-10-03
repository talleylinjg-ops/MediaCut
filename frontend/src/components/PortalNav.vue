<template>
  <el-menu mode="horizontal" :default-active="active" router :ellipsis="false" style="border-bottom: 1px solid #e4e7ed">
    <el-menu-item index="/" style="font-weight: 700">MediaCut API</el-menu-item>
    <div style="flex: 1"></div>
    <el-menu-item v-if="!STATIC_ONLY" index="/playground" style="font-weight: 600">在线试用</el-menu-item>
    <el-menu-item index="/pricing">定价</el-menu-item>
    <el-menu-item index="/docs">接入文档</el-menu-item>
    <el-menu-item v-if="!STATIC_ONLY" index="/swagger">API 文档</el-menu-item>
    <el-menu-item index="/register">申请 API Key</el-menu-item>
    <template v-if="!STATIC_ONLY">
      <el-menu-item v-if="clientLoggedIn" index="/client/console">控制台</el-menu-item>
      <el-menu-item v-else index="/client/login">客户登录</el-menu-item>
    </template>
  </el-menu>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { isClientLoggedIn, onAuthChange } from '../utils/auth'
import { STATIC_ONLY } from '../staticMode'

const clientLoggedIn = ref(isClientLoggedIn())
let offAuth = null

onMounted(() => {
  offAuth = onAuthChange(() => {
    clientLoggedIn.value = isClientLoggedIn()
  })
})

onUnmounted(() => {
  if (offAuth) offAuth()
})
</script>
