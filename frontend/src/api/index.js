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

export default http
