import axios from 'axios'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 60000
})

http.interceptors.request.use((config) => {
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
      localStorage.removeItem('admin_token')
      window.location.href = '/login'
    }
    if (status === 401 && url.startsWith('/dev/client') && url !== '/dev/client/login') {
      localStorage.removeItem('client_token')
      window.location.href = '/client/login'
    }
    return Promise.reject(error)
  }
)

export default http
