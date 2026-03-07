import axios from 'axios'

// API 基础配置
const API_BASE = import.meta.env.VITE_API_BASE || ''

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 Token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

// API 接口定义
export const api = {
  // 地图相关
  getGraph: () => apiClient.get('/graph'),
  searchSpots: (query, limit = 5) => apiClient.get('/spots/search', { params: { query, limit } }),
  navigate: (data) => apiClient.post('/navigate', data),

  // 认证相关
  register: (username, password) => apiClient.post('/auth/register', { username, password }),
  login: (username, password) => apiClient.post('/auth/login', { username, password }),

  // 日记相关
  getDiaries: (params) => apiClient.get('/diaries/search', { params }),
  getSpotDiaries: (spotId, params) => apiClient.get(`/diaries/spot/${spotId}`, { params }),
  getDiary: (id) => apiClient.get(`/diaries/detail/${id}`),
  createDiary: (data) => apiClient.post('/diaries/', data),
  getComments: (diaryId) => apiClient.get(`/diaries/${diaryId}/comments`),
  addComment: (data) => apiClient.post('/diaries/comment', data),

  // 文件上传
  uploadFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // AI 助手
  chatWithAI: (message) => apiClient.post('/ai/rag_chat', { message }),
}

export default apiClient
