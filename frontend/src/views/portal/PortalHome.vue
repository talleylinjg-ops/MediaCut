<template>
  <div>
    <PortalNav />
    <div style="padding: 40px; max-width: 1000px; margin: 0 auto">
      <h1 style="font-size: 24px; margin: 0 0 12px">大气媒体剪辑 API 服务平台</h1>
      <p>
        一站式图片、音频与 AI 处理能力，通过简单 HTTP 接口接入，配额透明、按量计费。
      </p>
      <el-row :gutter="20" style="margin-top: 24px">
        <el-col :span="8">
          <el-card>
            <h3>图片剪辑</h3>
            <p>裁切、缩放、滤镜、水印、格式转换</p>
            <p><el-tag type="success">1 点 / 次</el-tag></p>
            <el-button v-if="!STATIC_ONLY" size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=image')">去试用</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>音频剪辑</h3>
            <p>裁剪、拼接、音量调整、格式转换</p>
            <p><el-tag type="warning">2 点 / 次</el-tag></p>
            <el-button v-if="!STATIC_ONLY" size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=audio')">去试用</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>AI 处理</h3>
            <p>人像抠图、画质增强、语音识别、语音合成</p>
            <p><el-tag type="danger">5-15 点 / 次</el-tag></p>
            <el-button v-if="!STATIC_ONLY" size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=ai')">去试用</el-button>
          </el-card>
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="8">
          <el-card>
            <h3>AI 创作与工具</h3>
            <p>文生图、图生图编辑、文生视频、语音合成、人像抠图、画质增强、语音识别</p>
            <p><el-tag type="danger">10-20 点 / 次</el-tag></p>
            <el-button v-if="!STATIC_ONLY" size="small" type="primary" plain style="margin-top: 8px" @click="$router.push('/playground?tab=create')">去创作</el-button>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>异步 AI 任务</h3>
            <p>大模型任务异步排队处理，提交后轮询状态获取结果</p>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card>
            <h3>计费双轨</h3>
            <p>内部调用按每日配额免费使用，对外按接口价格扣减预充值余额</p>
          </el-card>
        </el-col>
      </el-row>
      <h2 style="font-size: 20px; margin: 40px 0 12px">为什么选择 MediaCut API</h2>
      <ul style="line-height: 1.9; padding-left: 20px; margin: 0">
        <li><strong>开箱即用</strong>：无需部署 GPU 服务器或安装模型依赖，一个 HTTP 请求即可完成图片裁切、人像抠图、语音识别等处理。</li>
        <li><strong>价格透明</strong>：按量计费 1-20 点/次，注册即赠 100 点，无最低消费、无预付套餐、无需绑定支付方式。</li>
        <li><strong>语言无关</strong>：标准 HTTP 接口 + Bearer Token 认证，curl、Python、Node.js、PHP、Java、Go 等任何语言可直接调用，无需专用 SDK。</li>
        <li><strong>全能力栈</strong>：从基础剪辑（裁切/缩放/水印/格式转换）到 AI 能力（人像抠图/画质增强/语音识别/语音合成/文生图/文生视频）一个平台全部覆盖。</li>
        <li><strong>异步任务模型</strong>：AI 任务提交后返回 task_id，轮询状态即可获取结果，无需自建 webhook 基础设施。</li>
        <li><strong>结果托管</strong>：处理结果存放在云端，下载时提供带签名的临时链接，无需自建对象存储与鉴权逻辑。</li>
      </ul>

      <h2 style="font-size: 20px; margin: 40px 0 12px">适用场景</h2>
      <ul style="line-height: 1.9; padding-left: 20px; margin: 0">
        <li><strong>App 与小程序</strong>：用户上传图片后一键裁切、缩放、压缩、加水印，1 点/次即可完成。</li>
        <li><strong>电商与零售</strong>：商品图批量格式转换、人像抠图换背景、画质增强提升商品展示效果。</li>
        <li><strong>内容创作</strong>：文生图生成配图、文生视频生成开场镜头（画面 + 运镜）、图生图编辑修改素材。</li>
        <li><strong>音频与播客</strong>：音频裁剪拼接、语音识别转写文字、语音合成生成配音。</li>
        <li><strong>自动化工作流</strong>：对话式剪辑用自然语言指令驱动媒体处理，适合集成到客服与运营系统。</li>
        <li><strong>企业内部系统</strong>：截图处理、水印标注、素材格式归一化，统一接入一个 API。</li>
      </ul>

      <h2 style="font-size: 20px; margin: 40px 0 12px">能力详解</h2>
      <h3 style="font-size: 16px; margin: 20px 0 6px">图片剪辑 API（1 点/次）</h3>
      <p style="margin: 0">
        通过 POST /api/v1/image/edit 一个请求完成图片裁切、按宽高缩放、旋转，16 种滤镜（黑白、复古、暖调、冷调、锐化等），文字或图片水印叠加，以及 PNG/JPEG/WebP/BMP 格式转换；参数以 JSON 数组传入，可任意组合串行处理。
      </p>
      <h3 style="font-size: 16px; margin: 20px 0 6px">音频剪辑 API（2 点/次）</h3>
      <p style="margin: 0">
        通过 POST /api/v1/audio/edit 完成音频按时间段裁剪、多段拼接、音量增益或衰减与 MP3/WAV 等格式转换，适合播客后期、通知音生成与语音素材整理。
      </p>
      <h3 style="font-size: 16px; margin: 20px 0 6px">人像抠图 API（10 点/次）</h3>
      <p style="margin: 0">
        AI 自动分离人像与背景，输出透明背景 PNG 或自定义背景图，适合证件照处理、电商模特图换背景与社交应用头像装饰；提交图片 URL 后异步处理，任务完成即下载结果。
      </p>
      <h3 style="font-size: 16px; margin: 20px 0 6px">画质增强 API（15 点/次）</h3>
      <p style="margin: 0">
        AI 超分辨率与降噪：把低分辨率、有噪点的图片放大并重建细节，适合老照片修复、商品图提升清晰度与素材二次利用。
      </p>
      <h3 style="font-size: 16px; margin: 20px 0 6px">语音识别 API（10 点/次）</h3>
      <p style="margin: 0">
        上传 MP3/WAV 音频，返回转写文本；适合会议录音整理、播客字幕生成与客服通话质检场景。
      </p>
      <h3 style="font-size: 16px; margin: 20px 0 6px">语音合成 API（5 点/次）</h3>
      <p style="margin: 0">
        输入文本生成自然语音（MP3/WAV），适合短视频配音、播报音生成与无障碍朗读功能。
      </p>
      <h3 style="font-size: 16px; margin: 20px 0 6px">文生图 API（10 点/次）</h3>
      <p style="margin: 0">
        输入中文或英文提示词生成图片；请求默认走免费生成渠道（Pollinations）不扣点，由 ModelScope Qwen-Image 渠道处理时扣 10 点，适合文章配图、素材灵感与创意设计。
      </p>
      <h3 style="font-size: 16px; margin: 20px 0 6px">图生图编辑 API（15 点/次）</h3>
      <p style="margin: 0">
        上传参考图并附带编辑指令（如「把背景换成海滩」「改成水彩风格」），AI 基于原图生成编辑结果，适合商品图变体与素材二次创作。
      </p>
      <h3 style="font-size: 16px; margin: 20px 0 6px">文生视频 API（20 点/次）</h3>
      <p style="margin: 0">
        输入提示词生成 MP4 短视频：AI 先生成画面，再叠加程序化运镜（推拉 zoom、平移 pan），适合氛围镜头、开场素材与内容营销；如实说明——画面为静态图驱动，支持与限制详见常见问题。
      </p>
      <h3 style="font-size: 16px; margin: 20px 0 6px">对话式剪辑 API（10 点/次）</h3>
      <p style="margin: 0">
        用自然语言描述处理需求（如「把这张图裁成 1:1 并加水印」「这段音频剪掉前 10 秒」），AI 解析指令并自动编排图片/音频处理流程，适合无开发背景的运营人员与自动化工作流。
      </p>

      <h2 style="font-size: 20px; margin: 40px 0 12px">常见问题</h2>
      <el-collapse>
        <el-collapse-item title="MediaCut API 是什么？" name="faq-what">
          MediaCut API 是一站式图片、音频与 AI 媒体处理 HTTP API 服务平台：提供图片剪辑（裁切/缩放/滤镜/水印/格式转换）、音频剪辑（裁剪/拼接/音量/转换）、人像抠图、画质增强、语音识别、语音合成、文生图、图生图编辑与文生视频（画面+运镜）能力，按量计费并提供免费额度。
        </el-collapse-item>
        <el-collapse-item title="收费吗？如何计费？" name="faq-price">
          注册即赠 100 点免费额度。同步接口按次计费：图片剪辑 1 点/次、音频剪辑 2 点/次；AI 能力 5-20 点/次（语音合成 5 点、人像抠图/语音识别/文生图/对话剪辑 10 点、画质增强/图生图编辑 15 点、文生视频 20 点）。部分文生图请求由免费生成渠道支持时不扣点。
        </el-collapse-item>
        <el-collapse-item title="如何接入？需要什么认证方式？" name="faq-integrate">
          注册后即时获取 API Key，所有业务接口使用 Authorization: Bearer 请求头认证。同步接口直接返回处理结果；异步 AI 接口提交任务后返回 task_id，轮询 GET /api/v1/tasks/{task_id} 获取状态，完成后通过 GET /api/v1/result/{task_id}/{filename} 下载结果。
        </el-collapse-item>
        <el-collapse-item title="支持哪些编程语言？" name="faq-language">
          全部能力以标准 HTTP 接口提供，curl、Python、Node.js、PHP、Java、Go 等任何语言均可直接调用，无需专用 SDK；接入文档页提供可直接复制的 curl 示例。
        </el-collapse-item>
        <el-collapse-item title="文生视频是真视频生成吗？" name="faq-video">
          文生视频的实现方式：先用 AI 生成画面，再通过程序化运镜（推拉 zoom / 平移 pan）合成 MP4 短视频（H.264）。画面内容由 AI 生成，镜头运动为程序化驱动，适合做氛围镜头与素材开场；不支持真人级动态内容生成。
        </el-collapse-item>
        <el-collapse-item title="结果是什么格式？" name="faq-format">
          图片输出 PNG/JPEG/WebP 等常见格式，音频输出 MP3/WAV，视频输出 MP4（H.264）。处理结果通过带鉴权的下载链接获取，任务结果包含图片、音频、视频或文本（如语音识别转写文字）。
        </el-collapse-item>
        <el-collapse-item title="异步任务如何轮询状态？" name="faq-poll">
          提交异步 AI 任务后接口返回 task_id 与 status_url。轮询 GET /api/v1/tasks/{task_id}，status 依次为 pending（排队）、running（处理中）、succeeded（成功）或 failed（失败）；成功后调用 GET /api/v1/result/{task_id}/{filename} 下载结果，无需配置 webhook 回调。
        </el-collapse-item>
        <el-collapse-item title="常见错误码是什么含义？" name="faq-errors">
          401：API Key 无效或缺失；402：余额不足，请充值；429：当日配额已用完；503：AI 模型未配置。认证类错误请检查 Authorization: Bearer 请求头是否携带有效 Key。
        </el-collapse-item>
        <el-collapse-item title="有免费额度或免费能力吗？" name="faq-free">
          注册即赠 100 点免费额度，无需绑定支付方式。部分文生图请求由免费生成渠道（Pollinations）支持时不扣点，仍计入调用配额；内部渠道调用另有每日免费配额。
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import PortalNav from '../../components/PortalNav.vue'
import { STATIC_ONLY } from '../../staticMode'
</script>
