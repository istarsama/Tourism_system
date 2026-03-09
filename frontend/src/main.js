// Vue 3 应用入口文件
// 负责应用初始化、插件配置、根组件挂载

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { MotionPlugin } from '@vueuse/motion'
import App from './App.vue'
import './style.css'

// 创建 Vue 应用实例
const app = createApp(App)

// 创建 Pinia 状态管理实例
// Pinia 用于全局状态管理，替代 Vuex
const pinia = createPinia()

// 注册 Pinia 插件
// 启用响应式状态管理，所有组件都可以使用 useStore()
app.use(pinia)

// 注册 VueUse Motion 插件
// 提供动画和过渡效果支持，用于界面交互动画
app.use(MotionPlugin)

// 挂载应用到 DOM
// 将根组件 App 挂载到 id 为 'app' 的 DOM 元素上
// 对应 index.html 中的 <div id="app"></div>
app.mount('#app')
