<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 800px; margin: 0 auto">
      <h1 style="font-size: 22px; margin: 0 0 12px">MediaCut API 定价</h1>
      <p>所有对外接口按次计费，从预充值余额中扣减。余额不足时接口返回 402。</p>
      <el-table :data="plans" style="margin-top: 24px">
        <el-table-column prop="endpoint" label="接口" width="220" />
        <el-table-column prop="name" label="能力" />
        <el-table-column prop="price" label="价格 (点/次)" width="130">
          <template #default="{ row }">{{ row.price }}</template>
        </el-table-column>
      </el-table>
      <el-card style="margin-top: 24px">
        <h3>充值方式</h3>
        <p>登录客户控制台，点击「自助充值」输入点数即可立即到账，无需人工介入。</p>
        <el-button type="primary" @click="$router.push('/client/console')">去充值</el-button>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import PortalNav from '../../components/PortalNav.vue'
import { getPriceTable } from '../../api/billing'

const plans = getPriceTable()
</script>
