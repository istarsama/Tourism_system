<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="show" class="modal-overlay" @click="handleOverlayClick">
        <div class="modal" @click.stop>
          <h2>{{ isLogin ? '用户登录' : '用户注册' }}</h2>
          
          <div class="form-group">
            <label>用户名</label>
            <input 
              v-model="username" 
              type="text" 
              placeholder="请输入用户名"
              @keyup.enter="handleSubmit"
            />
          </div>
          
          <div class="form-group">
            <label>密码</label>
            <input 
              v-model="password" 
              type="password" 
              placeholder="请输入密码"
              @keyup.enter="handleSubmit"
            />
          </div>
          
          <div class="modal-actions">
            <button class="btn-primary" @click="handleSubmit" :disabled="loading">
              {{ loading ? '处理中...' : (isLogin ? '登录' : '注册') }}
            </button>
            <button class="btn-sm btn-outline" @click="toggleMode">
              {{ isLogin ? '没有账号? 去注册' : '已有账号? 去登录' }}
            </button>
          </div>
          
          <button class="btn-close" @click="handleClose">✕</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { api } from '../api'

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['update:show'])

const authStore = useAuthStore()
const isLogin = ref(true)
const username = ref('')
const password = ref('')
const loading = ref(false)

watch(() => props.show, (newVal) => {
  if (newVal) {
    // 重置表单
    username.value = ''
    password.value = ''
    isLogin.value = true
  }
})

function toggleMode() {
  isLogin.value = !isLogin.value
}

async function handleSubmit() {
  if (!username.value || !password.value) {
    alert('请填写用户名和密码')
    return
  }

  loading.value = true
  
  try {
    if (isLogin.value) {
      const result = await api.login(username.value, password.value)
      authStore.setAuth(result.access_token, username.value)
      alert('登录成功!')
    } else {
      await api.register(username.value, password.value)
      alert('注册成功，请登录')
      isLogin.value = true
      password.value = ''
      return // 不关闭模态框，让用户继续登录
    }
    
    handleClose()
  } catch (error) {
    alert(error.message || '操作失败')
  } finally {
    loading.value = false
  }
}

function handleClose() {
  emit('update:show', false)
}

function handleOverlayClick() {
  handleClose()
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
}

.modal {
  background: white;
  padding: 30px;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  position: relative;
}

.modal h2 {
  margin: 0 0 20px 0;
  color: var(--primary-color);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
  font-size: 14px;
  color: #374151;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  align-items: center;
}

.btn-close {
  position: absolute;
  top: 15px;
  right: 15px;
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
</style>
