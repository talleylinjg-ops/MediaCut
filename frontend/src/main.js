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
import SwaggerDoc from './views/SwaggerDoc.vue'

const routes = [
  { path: '/', component: PortalHome },
  { path: '/pricing', component: PortalPricing },
  { path: '/register', component: PortalRegister },
  { path: '/docs', component: PortalDocs },
  { path: '/swagger', component: SwaggerDoc },
  { path: '/client/login', component: ClientLogin },
  { path: '/client/console', component: ClientConsole, meta: { requiresClient: true } },
  { path: '/login', component: Login },
  { path: '/admin', component: AdminHome, meta: { requiresAuth: true } },
  { path: '/account', component: AdminProfile, meta: { requiresAuth: true } },
  { path: '/developers', component: Developers, meta: { requiresAuth: true } },
  { path: '/stats', component: Stats, meta: { requiresAuth: true } },
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

createApp(App).use(router).use(ElementPlus).mount('#app')
