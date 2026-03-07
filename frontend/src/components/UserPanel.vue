<template>
  <div class="user-panel">
    <div v-if="!authStore.isAuthenticated" class="logged-out">
      <button class="btn-primary full-width" @click="handleLogin">
        登录 / 注册
      </button>
    </div>

    <div v-else class="logged-in">
      <div class="user-info">
        <span>欢迎, <b>{{ authStore.username }}</b></span>
        <button class="btn-sm btn-outline" @click="handleLogout">退出</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function handleLogin() {
  // 使用查询参数触发登录模态框
  router.push({ query: { login: 'true' } })
}

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
