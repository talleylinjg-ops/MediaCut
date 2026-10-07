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

      <h2 style="font-size: 20px; margin: 40px 0 12px">计费规则说明</h2>
      <ul style="line-height: 1.9; padding-left: 20px; margin: 0">
        <li><strong>免费额度</strong>：注册即赠 100 点，无需绑定支付方式；免费额度与充值余额共用扣减。</li>
        <li><strong>按量计费</strong>：每次成功调用扣减对应点数，失败任务（status=failed）不扣点。</li>
        <li><strong>同步与异步同价</strong>：价格以能力为单位，同步接口直接返回结果，异步 AI 任务在提交时计费。</li>
        <li><strong>文生图免费渠道</strong>：部分文生图请求由免费生成渠道（Pollinations）支持时不扣点，仍计入调用配额。</li>
        <li><strong>余额不足</strong>：接口返回 402，充值后立即恢复调用。</li>
        <li><strong>每日配额</strong>：另有平台级每日调用配额保护，超出返回 429，次日自动恢复。</li>
      </ul>

      <el-card style="margin-top: 24px">
        <h3>充值方式</h3>
        <p v-if="!STATIC_ONLY">登录客户控制台，点击「自助充值」输入点数即可立即到账，无需人工介入。</p>
        <p v-else>当前为展示版站点；正式开通后支持控制台自助充值，也可通过邮件申请 API Key（含 100 点免费额度）。</p>
        <el-button v-if="!STATIC_ONLY" type="primary" @click="$router.push('/client/console')">去充值</el-button>
        <el-button v-else type="primary" tag="a" href="mailto:saas@didimedia.com?subject=MediaCut%20API%20Key%20%E7%94%B3%E8%AF%B7">邮件申请 API Key</el-button>
      </el-card>

      <div style="margin-top: 24px">
        <el-button @click="$router.push('/docs')">查看接入文档</el-button>
        <el-button @click="$router.push('/guide/quickstart')">快速上手教程</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import PortalNav from '../../components/PortalNav.vue'
import { getPriceTable } from '../../api/billing'
import { STATIC_ONLY } from '../../staticMode'

const plans = getPriceTable()
</script>
