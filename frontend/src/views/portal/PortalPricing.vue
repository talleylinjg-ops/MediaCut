<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 800px; margin: 0 auto">
      <h2>定价</h2>
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
        <p>联系管理员在管理后台为客户账户充值点数，或由内部合作方免费提供配额。</p>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import PortalNav from '../../components/PortalNav.vue'
import { getPriceTable } from '../../api/billing'

const plans = getPriceTable()
</script>
