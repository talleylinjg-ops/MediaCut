import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import Login from './views/Login.vue'
import AdminHome from './views/AdminHome.vue'
import AdminProfile from './views/AdminProfile.vue'
import Developers from './views/Developers.vue'
import Stats from './views/Stats.vue'
import PortalHome from './views/portal/PortalHome.vue'
import PortalPricing from './views/portal/PortalPricing.vue'
import PortalRegister from './views/portal/PortalRegister.vue'
import PortalDocs from './views/portal/PortalDocs.vue'
import ClientLogin from './views/portal/ClientLogin.vue'
import ClientConsole from './views/portal/ClientConsole.vue'
import ApiPlayground from './views/portal/ApiPlayground.vue'
import SwaggerDoc from './views/SwaggerDoc.vue'

const routes = [
  {
    path: '/',
    component: PortalHome,
    meta: {
      title: '首页',
      description: '图片剪辑、音频处理与 AI 能力一站式 HTTP API。支持裁切、缩放、滤镜、水印、格式转换、人像抠图、画质增强、语音识别、语音合成、文生图与图生图编辑。'
    }
  },
  {
    path: '/pricing',
    component: PortalPricing,
    meta: {
      title: '定价',
      description: 'MediaCut API 计费方式与价格说明：注册即享免费额度，图片、音频与 AI 处理按量计费，配额透明。'
    }
  },
  {
    path: '/register',
    component: PortalRegister,
    meta: {
      title: '申请 API Key',
      description: '免费注册 MediaCut API 账号，在线申请 API Key，立即接入图片、音频与 AI 媒体处理能力。'
    }
  },
  {
    path: '/docs',
    component: PortalDocs,
    meta: {
      title: '接入文档',
      description: 'MediaCut API 接入文档：认证方式、请求示例、异步任务流程与接口说明。'
    }
  },
  {
    path: '/swagger',
    component: SwaggerDoc,
    meta: { title: 'API 参考', description: 'MediaCut API 完整接口参考文档（Swagger / OpenAPI）。' }
  },
  {
    path: '/playground',
    component: ApiPlayground,
    meta: {
      title: '在线试用',
      description: '在线试用 MediaCut API：直接上传或输入内容体验图片剪辑、音频处理与 AI 能力，无需本地部署。'
    }
  },
  {
    path: '/client/try',
    component: ApiPlayground,
    meta: { title: '在线试用', description: '在线试用 MediaCut API：体验图片剪辑、音频处理与 AI 能力。' }
  },
  { path: '/client/login', component: ClientLogin, meta: { title: '客户登录', noindex: true } },
  {
    path: '/client/console',
    component: ClientConsole,
    meta: { requiresClient: true, title: '控制台', noindex: true }
  },
  { path: '/login', component: Login, meta: { title: '管理员登录', noindex: true } },
  { path: '/admin', component: AdminHome, meta: { requiresAuth: true, title: '管理后台', noindex: true } },
  { path: '/account', component: AdminProfile, meta: { requiresAuth: true, title: '账号中心', noindex: true } },
  { path: '/developers', component: Developers, meta: { requiresAuth: true, title: '开发者管理', noindex: true } },
  { path: '/stats', component: Stats, meta: { requiresAuth: true, title: '调用统计', noindex: true } },
  { path: '/api-keys', redirect: '/register' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const adminToken = localStorage.getItem('admin_token')
  const clientToken = localStorage.getItem('client_token')
  if (to.meta.requiresAuth && !adminToken) {
    return '/login'
  }
  if (to.meta.requiresClient && !clientToken) {
    return '/client/login'
  }
  if (to.path === '/login' && adminToken) {
    return '/admin'
  }
  if (to.path === '/client/login' && clientToken) {
    return '/client/console'
  }
  return true
})

const SITE_NAME = 'MediaCut API'
const DEFAULT_DESC =
  '图片剪辑、音频处理与 AI 能力一站式 HTTP API。支持裁切、缩放、滤镜、水印、格式转换、人像抠图、画质增强、语音识别、语音合成、文生图与图生图编辑。'

function setMetaTag(name, content, attr = 'name') {
  let tag = document.head.querySelector(`meta[${attr}="${name}"]`)
  if (!tag) {
    tag = document.createElement('meta')
    tag.setAttribute(attr, name)
    document.head.appendChild(tag)
  }
  tag.setAttribute('content', content)
}

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} | ${SITE_NAME}`
    : `${SITE_NAME} - 图片/音频/AI 媒体剪辑 API 服务平台`
  setMetaTag('description', to.meta.description || DEFAULT_DESC)
  setMetaTag('robots', to.meta.noindex ? 'noindex,nofollow' : 'index,follow,max-image-preview:large')
  setCanonical(to.path)
})

const SITE_ORIGIN = 'https://didimedia.com'

function setCanonical(path) {
  let link = document.head.querySelector('link[rel="canonical"]')
  if (!link) {
    link = document.createElement('link')
    link.setAttribute('rel', 'canonical')
    document.head.appendChild(link)
  }
  link.setAttribute('href', SITE_ORIGIN + path)
}

createApp(App).use(router).use(ElementPlus).mount('#app')
