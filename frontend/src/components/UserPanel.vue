<template>
  <div class="user-panel">
    <div v-if="!authStore.isAuthenticated" class="logged-out">
      <button class="btn-primary full-width" @click="showAuthModal = true">
        登录 / 注册
      </button>
    </div>

    <div v-else class="logged-in">
      <div class="user-info">
        <span>欢迎, <b>{{ authStore.username }}</b></span>
        <button class="btn-sm btn-outline" @click="handleLogout">退出</button>
      </div>
    </div>

    <!-- 认证模态框 -->
    <AuthModal v-model:show="showAuthModal" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import AuthModal from './AuthModal.vue'

const authStore = useAuthStore()
const showAuthModal = ref(false)

function handleLogout() {
  authStore.clearAuth()
}
</script>

<style scoped>
.user-panel {
  padding-bottom: 15px;
  border-bottom: 1px solid var(--border-color);
}

.user-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}
</style>
