import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import Login from './views/Login.vue'
import Developers from './views/Developers.vue'
import Stats from './views/Stats.vue'
import ApiKeys from './views/ApiKeys.vue'

const routes = [
  { path: '/login', component: Login },
  { path: '/developers', component: Developers, meta: { requiresAuth: true } },
  { path: '/stats', component: Stats, meta: { requiresAuth: true } },
  { path: '/api-keys', component: ApiKeys },
  { path: '/', redirect: '/developers' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const token = localStorage.getItem('admin_token')
  if (to.meta.requiresAuth && !token) {
    return '/login'
  }
  if (to.path === '/login' && token) {
    return '/developers'
  }
  return true
})

createApp(App).use(router).use(ElementPlus).mount('#app')
