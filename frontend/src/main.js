import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'

const Login = () => import('./views/Login.vue')
const AdminHome = () => import('./views/AdminHome.vue')
const AdminProfile = () => import('./views/AdminProfile.vue')
const Developers = () => import('./views/Developers.vue')
const Stats = () => import('./views/Stats.vue')
const PortalHome = () => import('./views/portal/PortalHome.vue')
const PortalPricing = () => import('./views/portal/PortalPricing.vue')
const PortalRegister = () => import('./views/portal/PortalRegister.vue')
const PortalDocs = () => import('./views/portal/PortalDocs.vue')
const ClientLogin = () => import('./views/portal/ClientLogin.vue')
const ClientConsole = () => import('./views/portal/ClientConsole.vue')
const ApiPlayground = () => import('./views/portal/ApiPlayground.vue')
const SwaggerDoc = () => import('./views/SwaggerDoc.vue')

const routes = [
  {
    path: '/',
    component: PortalHome,
    meta: {
      title: '首页',
      description: '图片剪辑、音频处理与 AI 能力一站式 HTTP API。支持裁切、缩放、滤镜、水印、格式转换、人像抠图、画质增强、语音识别、语音合成、文生图、图生图编辑与文生视频。'
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
      description: '在线试用 MediaCut API：体验图片剪辑、音频处理、AI 处理以及文生图、图生图编辑、文生视频等生成式能力。'
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
  '图片剪辑、音频处理与 AI 能力一站式 HTTP API。支持裁切、缩放、滤镜、水印、格式转换、人像抠图、画质增强、语音识别、语音合成、文生图、图生图编辑与文生视频。'

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

createApp(App).use(router).mount('#app')
