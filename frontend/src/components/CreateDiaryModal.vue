<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="show" class="modal-overlay" @click="handleClose">
        <div class="modal create-diary-modal" @click.stop>
          <div class="modal-header">
            <h2>✍️ 发布日记</h2>
            <button class="btn-close" @click="handleClose">✕</button>
          </div>

          <form @submit.prevent="handleSubmit" class="diary-form">
            <!-- 标题 -->
            <div class="form-group">
              <label>标题 <span class="required">*</span></label>
              <input
                v-model="formData.title"
                type="text"
                placeholder="给你的日记起个标题..."
                maxlength="100"
                required
              />
              <span class="char-count">{{ formData.title.length }}/100</span>
            </div>

            <!-- 景点选择 -->
            <div class="form-group">
              <label>关联{{ scopeLabel }} <span class="required">*</span></label>
              <select v-model="formData.spot_id">
                <option :value="null" disabled>请选择景点</option>
                <option v-for="spot in spots" :key="spot.id" :value="spot.id">
                  {{ spot.name }}{{ spot.city ? `（${spot.city}）` : '' }}
                </option>
              </select>
            </div>

            <!-- 内容 -->
            <div class="form-group">
              <label>正文 <span class="required">*</span></label>
              <textarea
                v-model="formData.content"
                rows="8"
                placeholder="分享你的旅行体验..."
                maxlength="5000"
                required
              ></textarea>
              <span class="char-count">{{ formData.content.length }}/5000</span>
            </div>

            <!-- 图片上传 -->
            <div class="form-group">
              <label>图片（最多9张）</label>
              <div class="image-upload-area">
                <!-- 已上传的图片预览 -->
                <div v-for="(url, index) in formData.media_files" :key="index" class="image-preview">
                  <img :src="url" alt="预览图" />
                  <button type="button" class="remove-image" @click="removeImage(index)">
                    ✕
                  </button>
                </div>

                <!-- 上传按钮 -->
                <label v-if="formData.media_files.length < 9" class="upload-btn">
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    @change="handleFileSelect"
                    style="display: none"
                  />
                  <div class="upload-placeholder">
                    <span class="upload-icon">📷</span>
                    <span class="upload-text">点击上传</span>
                  </div>
                </label>
              </div>
              <p class="hint">支持 JPG、PNG、GIF 格式，单张最大 5MB</p>
            </div>

            <!-- 提交按钮 -->
            <div class="form-actions">
              <button type="button" class="btn-outline" @click="handleClose">
                取消
              </button>
              <button type="submit" class="btn-primary" :disabled="submitting || !isFormValid">
                {{ submitting ? '发布中...' : '发布日记' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useDiaryStore } from '../stores/diary'
import { api } from '../api'

const props = defineProps({
  show: Boolean,
  scope: {
    type: String,
    default: 'campus'
  },
  presetSpotId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:show', 'success'])

const diaryStore = useDiaryStore()

const spots = ref([])
const submitting = ref(false)
const uploadingImages = ref(false)

const formData = ref({
  title: '',
  spot_id: null,
  content: '',
  media_files: []
})

const isNationalScope = computed(() => props.scope === 'national')
const scopeLabel = computed(() => (isNationalScope.value ? '全国景点' : '校园景点'))

// 表单验证
const isFormValid = computed(() => {
  return formData.value.title.trim() && 
         formData.value.content.trim() &&
         !uploadingImages.value
})

// 加载景点列表
onMounted(async () => {
  await loadSpots()
  applyPresetSpot()
})

watch(() => props.scope, async () => {
  await loadSpots()
  applyPresetSpot()
})

watch(() => props.show, (show) => {
  if (show) {
    applyPresetSpot()
  }
})

async function loadSpots() {
  try {
    if (isNationalScope.value) {
      spots.value = await api.getNationalSpots({ only_active: true })
      return
    }
    const response = await api.getGraph()
    spots.value = response.nodes.filter(node => node.type === 'spot')
  } catch (error) {
    console.error('加载景点失败:', error)
    spots.value = []
  }
}

function applyPresetSpot() {
  if (typeof props.presetSpotId === 'number' && props.presetSpotId > 0) {
    formData.value.spot_id = props.presetSpotId
    return
  }
  formData.value.spot_id = null
}

// 文件选择处理
async function handleFileSelect(event) {
  const files = Array.from(event.target.files)
  
  if (files.length === 0) return
  
  // 检查数量限制
  const remaining = 9 - formData.value.media_files.length
  if (files.length > remaining) {
    alert(`最多还能上传 ${remaining} 张图片`)
    return
  }
  
  // 检查文件大小（5MB）
  const maxSize = 5 * 1024 * 1024
  const oversized = files.find(file => file.size > maxSize)
  if (oversized) {
    alert(`图片 "${oversized.name}" 超过 5MB，请压缩后上传`)
    return
  }
  
  uploadingImages.value = true
  
  try {
    // 逐个上传图片
    for (const file of files) {
      const result = await api.uploadFile(file)
      // 后端返回的 URL 格式：{url: "/uploads/xxx.jpg"}
      const fullUrl = result.url.startsWith('http') 
        ? result.url 
        : `${window.location.origin}${result.url}`
      
      formData.value.media_files.push(fullUrl)
    }
  } catch (error) {
    alert('图片上传失败: ' + error.message)
  } finally {
    uploadingImages.value = false
  }
  
  // 清空 input，允许重复选择同一文件
  event.target.value = ''
}

// 删除图片
function removeImage(index) {
  formData.value.media_files.splice(index, 1)
}

// 提交表单
async function handleSubmit() {
  if (!isFormValid.value) return
  const selectedSpotId = Number(formData.value.spot_id)
  if (!Number.isInteger(selectedSpotId) || selectedSpotId <= 0) {
    alert('请选择一个景点后再发布')
    return
  }
  
  submitting.value = true
  
  try {
    const payload = {
      scope: props.scope,
      title: formData.value.title.trim(),
      content: formData.value.content.trim(),
      media_files: formData.value.media_files
    }
    if (isNationalScope.value) {
      payload.national_spot_id = selectedSpotId
    } else {
      payload.spot_id = selectedSpotId
    }
    await diaryStore.createDiary(payload)
    
    alert('✅ 日记发布成功！')
    
    // 重置表单
    formData.value = {
      title: '',
      spot_id: null,
      content: '',
      media_files: []
    }
    
    emit('success')
    emit('update:show', false)
  } catch (error) {
    alert('发布失败: ' + error.message)
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  if (submitting.value) return
  
  // 如果有未保存的内容，提示用户
  if (formData.value.title || formData.value.content || formData.value.media_files.length > 0) {
    if (!confirm('有未保存的内容，确定要关闭吗？')) {
      return
    }
  }
  
  emit('update:show', false)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.create-diary-modal {
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  width: 100%;
}

.modal {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  position: relative;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.modal-header h2 {
  margin: 0;
  color: #1f2937;
  font-size: 1.5rem;
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 24px;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #f3f4f6;
  color: #374151;
}

.diary-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.form-group label {
  font-weight: 600;
  color: #374151;
  font-size: 14px;
}

.required {
  color: #ef4444;
}

.form-group input,
.form-group select,
.form-group textarea {
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: all 0.2s;
  font-family: inherit;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #003d74;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.char-count {
  position: absolute;
  right: 12px;
  bottom: 12px;
  font-size: 12px;
  color: #9ca3af;
  background: white;
  padding: 2px 4px;
}

.form-group textarea {
  resize: vertical;
  min-height: 120px;
}

/* 图片上传区域 */
.image-upload-area {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.image-preview {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-image {
  position: absolute;
  top: 4px;
  right: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.2s;
}

.remove-image:hover {
  background: rgba(239, 68, 68, 0.9);
  transform: scale(1.1);
}

.upload-btn {
  aspect-ratio: 1;
  cursor: pointer;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  background: #f9fafb;
}

.upload-btn:hover {
  border-color: #003d74;
  background: #eff6ff;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.upload-icon {
  font-size: 32px;
}

.upload-text {
  font-size: 12px;
  color: #6b7280;
}

.hint {
  font-size: 12px;
  color: #9ca3af;
  margin: 0;
}

/* 表单操作按钮 */
.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 8px;
}

.btn-outline,
.btn-primary {
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-outline {
  background: white;
  border: 1px solid #d1d5db;
  color: #374151;
}

.btn-outline:hover {
  background: #f9fafb;
}

.btn-primary {
  background: #003d74;
  color: white;
  min-width: 104px;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #7aa2c7;
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
