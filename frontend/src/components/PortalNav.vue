<template>
  <el-menu mode="horizontal" :default-active="active" router :ellipsis="false" style="border-bottom: 1px solid #e4e7ed">
    <el-menu-item index="/" style="font-weight: 700">MediaCut API</el-menu-item>
    <div style="flex: 1"></div>
    <el-menu-item index="/pricing">定价</el-menu-item>
    <el-menu-item index="/docs">接入文档</el-menu-item>
    <el-menu-item index="/register">申请 API Key</el-menu-item>
    <el-menu-item v-if="clientLoggedIn" index="/client/console">客户控制台</el-menu-item>
    <el-menu-item v-else index="/client/login">客户登录</el-menu-item>
    <el-menu-item index="/developers">管理后台</el-menu-item>
  </el-menu>
</template>

<script setup>
import { ref } from 'vue'

const clientLoggedIn = ref(Boolean(localStorage.getItem('client_token')))
</script>
