<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 1000px; margin: 0 auto">
      <h1 style="font-size: 24px; margin: 0 0 12px">快速上手：五分钟跑通第一个请求</h1>
      <p>
        本教程带你在五分钟内完成 MediaCut API 的接入：获取 Key、调用同步接口、提交异步 AI 任务、下载结果。
        全部示例基于 curl，可直接复制到终端执行；任何支持 HTTP 的语言同样适用。
      </p>

      <h2 style="font-size: 20px; margin: 40px 0 12px">第 0 步：获取 API Key</h2>
      <p>
        所有接口使用 <code>Authorization: Bearer &lt;API_KEY&gt;</code> 请求头认证。
        <template v-if="STATIC_ONLY">发送邮件说明使用场景即可申请 API Key 与 100 点免费额度。</template>
        <template v-else>在
          <router-link to="/register">注册页</router-link>
          免费注册，即时获取 API Key 与 100 点免费额度。</template>
        下文示例中请把 <code>$API_KEY</code> 替换为你的 Key。
      </p>

      <h2 style="font-size: 20px; margin: 40px 0 12px">第 1 步：调用同步接口（图片剪辑，1 点/次）</h2>
      <p>同步接口直接返回处理结果，适合轻量处理：</p>
      <pre class="code">curl -X POST https://mediacut.chacha.asia/api/v1/image/edit \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@photo.jpg" \
  -F "ops=[{\"op\":\"resize\",\"width\":800},{\"op\":\"watermark\",\"text\":\"@mybrand\"}]"</pre>
      <p>响应包含处理后的图片文件与消耗点数。裁切、缩放、滤镜、水印、格式转换可自由组合。</p>

      <h2 style="font-size: 20px; margin: 40px 0 12px">第 2 步：提交异步 AI 任务（文生图，10 点/次）</h2>
      <p>AI 能力为异步任务：提交后立即返回 task_id，不阻塞你的程序：</p>
      <pre class="code">curl -X POST https://mediacut.chacha.asia/api/v1/ai/image/generate \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"一只在雪山上看日出的橘猫，插画风格"}'

# 响应示例
# {"task_id":"a1b2c3d4e5f60718293a4b5c6d7e8f90","status":"pending","status_url":"/api/v1/tasks/a1b2..."}</pre>

      <h2 style="font-size: 20px; margin: 40px 0 12px">第 3 步：轮询任务状态</h2>
      <p>轮询 status_url，status 依次经过 pending（排队）与 running（处理中），最终变为 succeeded 或 failed：</p>
      <pre class="code">curl -H "Authorization: Bearer $API_KEY" \
  https://mediacut.chacha.asia/api/v1/tasks/a1b2c3d4e5f60718293a4b5c6d7e8f90

# 响应示例
# {"task_id":"a1b2...","status":"succeeded","progress":100,
#  "result":{"files":[{"filename":"image_0.png","type":"image"}]}}</pre>
      <p>建议轮询间隔 3-5 秒；文生图通常数秒内完成。</p>

      <h2 style="font-size: 20px; margin: 40px 0 12px">第 4 步：下载结果文件</h2>
      <p>任务成功后，通过结果接口下载文件，无需自建存储：</p>
      <pre class="code">curl -H "Authorization: Bearer $API_KEY" -o result.png \
  https://mediacut.chacha.asia/api/v1/result/a1b2c3d4e5f60718293a4b5c6d7e8f90/image_0.png</pre>
      <p>下载链接经过鉴权，处理结果在云端临时托管，过期自动清理。</p>

      <h2 style="font-size: 20px; margin: 40px 0 12px">第 5 步：错误处理速查</h2>
      <ul style="line-height: 1.9; padding-left: 20px; margin: 0">
        <li><strong>401</strong>：API Key 无效或缺失，检查 Authorization: Bearer 请求头</li>
        <li><strong>402</strong>：余额不足，请充值</li>
        <li><strong>429</strong>：当日配额已用完，次日自动恢复</li>
        <li><strong>503</strong>：AI 模型暂未配置，稍后重试或联系支持</li>
      </ul>

      <div style="margin-top: 32px">
        <el-button type="primary" size="large" @click="$router.push('/docs')">查看完整接入文档</el-button>
        <el-button size="large" @click="$router.push('/pricing')">查看价格表</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import PortalNav from '../../components/PortalNav.vue'
import { STATIC_ONLY } from '../../staticMode'
</script>

<style scoped>
.code {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.7;
  overflow-x: auto;
  white-space: pre;
}
code {
  background: #f5f7fa;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 13px;
}
</style>
