import axios from 'axios'

// API 基础配置
const API_BASE = import.meta.env.VITE_API_BASE || ''
const DEFAULT_TIMEOUT_MS = 30000
const parsedOsmTimeoutMs = Number(import.meta.env.VITE_OSM_NAV_TIMEOUT_MS)
const OSM_NAV_TIMEOUT_MS = Number.isFinite(parsedOsmTimeoutMs) && parsedOsmTimeoutMs > 0
  ? parsedOsmTimeoutMs
  : 120000

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: DEFAULT_TIMEOUT_MS,
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
    const isTimeout = error?.code === 'ECONNABORTED'
    const message = isTimeout
      ? '请求超时：OSM 首次加载城市路网可能较慢，请稍后重试'
      : (error.response?.data?.detail || error.message || '请求失败')
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

// API 接口定义
export const api = {
  // 地图相关
  getGraph: () => apiClient.get('/graph'),
  getMapMode: (scope = 'campus') => apiClient.get('/map/mode', { params: { scope } }),
  getNationalSpots: (params = {}) => apiClient.get('/map/national-spots', { params }),
  searchSpots: (query, limit = 5, scope = 'campus') =>
    apiClient.get('/spots/search', { params: { query, limit, scope } }),
  navigate: (data) => apiClient.post('/navigate', data),
  navigateOsm: (data) => apiClient.post('/navigate/osm', data, { timeout: OSM_NAV_TIMEOUT_MS }),

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
