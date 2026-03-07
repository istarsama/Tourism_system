import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'

// 日记数据管理Store
// 负责管理日记列表、详情、评论等数据
// 与后端日记接口对接：/diaries/*
export const useDiaryStore = defineStore('diary', () => {
  // ==================== 状态数据 ====================
  // 日记列表
  // 对应后端返回的日记数组
  // 结构: [{id, title, content, user_name, view_count, score, created_at}, ...]
  const diaries = ref([])

  // 当前查看的日记详情
  // 对应后端/diary/detail/{id}返回的单个日记对象
  const currentDiary = ref(null)

  // 当前日记的评论列表
  // 对应后端/diary/{id}/comments返回的评论数组
  // 结构: [{id, content, score, user_name, created_at}, ...]
  const comments = ref([])

  // 加载状态
  const loading = ref(false)

  // 错误信息
  const error = ref(null)

  // ==================== 异步方法 ====================
  // 加载日记列表（通用搜索）
  // 调用后端: GET /diaries/search?keyword=xxx&sort_by=latest
  // 参数: params-{keyword?, sort_by?, limit?}
  // 副作用: 更新diaries数组
  async function loadDiaries(params = {}) {
    loading.value = true
    error.value = null
    try {
      const data = await api.getDiaries(params)
      diaries.value = data
      return data
    } catch (err) {
      error.value = err.message
      console.error('Failed to load diaries:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  // 加载指定景点的日记列表
  // 调用后端: GET /diaries/spot/{spot_id}?keyword=xxx&sort_by=latest
  // 参数: spotId-景点ID, params-{keyword?, sort_by?}
  // 副作用: 更新diaries数组
  async function loadSpotDiaries(spotId, params = {}) {
    loading.value = true
    error.value = null
    try {
      const data = await api.getSpotDiaries(spotId, params)
      diaries.value = data
      return data
    } catch (err) {
      error.value = err.message
      console.error('Failed to load spot diaries:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  // 加载单个日记详情
  // 调用后端: GET /diaries/detail/{id}
  // 参数: id-日记ID
  // 副作用: 更新currentDiary
  async function loadDiary(id) {
    loading.value = true
    error.value = null
    try {
      const data = await api.getDiary(id)
      currentDiary.value = data
      return data
    } catch (err) {
      error.value = err.message
      console.error('Failed to load diary:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 创建新日记
  // 调用后端: POST /diaries/
  // 参数: diaryData-{title, content, spot_id?, media_json?}
  // 副作用: 刷新diaries列表
  async function createDiary(diaryData) {
    loading.value = true
    error.value = null
    try {
      const result = await api.createDiary(diaryData)
      await loadDiaries() // 刷新列表
      return result
    } catch (err) {
      error.value = err.message
      console.error('Failed to create diary:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 加载日记评论
  // 调用后端: GET /diaries/{diary_id}/comments
  // 参数: diaryId-日记ID
  // 副作用: 更新comments数组
  async function loadComments(diaryId) {
    try {
      const data = await api.getComments(diaryId)
      comments.value = data
      return data
    } catch (err) {
      console.error('Failed to load comments:', err)
      return []
    }
  }

  // 添加评论
  // 调用后端: POST /diaries/comment
  // 参数: commentData-{diary_id, content, score}
  // 副作用: 刷新comments列表
  async function addComment(commentData) {
    try {
      const result = await api.addComment(commentData)
      if (commentData.diary_id) {
        await loadComments(commentData.diary_id) // 刷新评论列表
      }
      return result
    } catch (err) {
      console.error('Failed to add comment:', err)
      throw err
    }
  }

  // ==================== Store导出 ====================
  return {
    diaries,        // 日记列表
    currentDiary,   // 当前日记详情
    comments,       // 评论列表
    loading,        // 加载状态
    error,          // 错误信息
    loadDiaries,    // 加载日记列表
    loadSpotDiaries,// 加载景点日记
    loadDiary,      // 加载日记详情
    createDiary,    // 创建日记
    loadComments,   // 加载评论
    addComment,     // 添加评论
  }
})
