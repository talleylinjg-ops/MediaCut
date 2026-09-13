import axios from 'axios'
import { clearAdminToken, clearClientToken } from '../utils/auth'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 60000
})

http.interceptors.request.use((config) => {
  if (config.headers.Authorization) {
    return config
  }
  if (config.url.startsWith('/dev/client')) {
    const token = localStorage.getItem('client_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  } else {
    const token = localStorage.getItem('admin_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''
    if (status === 401 && url.startsWith('/admin') && url !== '/admin/login') {
      clearAdminToken()
      window.location.href = '/login'
    }
    if (status === 401 && url.startsWith('/dev/client') && url !== '/dev/client/login') {
      clearClientToken()
      window.location.href = '/client/login'
    }
    return Promise.reject(error)
  }
)

export default http
