/**
 * Vue Router 配置文件
 * 
 * 路由策略：
 * - 使用 Hash 模式，避免服务器配置问题
 * - 懒加载组件，优化首屏加载速度
 * - 地图组件在 App.vue 中持久化，不通过路由加载
 * 
 * 路由结构：
 * - /nav - 导航面板
 * - /diary - 日记列表
 * - /diary/:id - 单篇日记详情（独立URL）
 * - /login - 登录/注册页面
 */

import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  // 使用 Hash 模式（#/nav, #/diary）
  history: createWebHashHistory(),
  
  routes: [
    {
      path: '/',
      redirect: '/nav'
    },
    {
      path: '/nav',
      name: 'Navigation',
      // 懒加载：只有访问该路由时才加载组件
      component: () => import('../components/NavigationPanel.vue'),
      meta: {
        title: '导航',
        icon: 'Navigation'
      }
    },
    {
      path: '/diary',
      name: 'DiaryList',
      component: () => import('../components/DiaryPanel.vue'),
      meta: {
        title: '社区日记',
        icon: 'BookOpen'
      },
      // 支持景点筛选：/diary?spotId=123
      props: route => ({
        spotId: route.query.spotId ? Number(route.query.spotId) : null
      }),
      children: [
        {
          // 日记详情作为子路由，但不渲染到 router-view
          // 只是用来触发 URL 变化，实际显示通过 App.vue 中的全局模态框控制
          path: ':id',
          name: 'DiaryDetail',
          meta: {
            title: '日记详情',
            isModal: true  // 标记为模态框路由
          }
        }
      ]
    },
    {
      path: '/user',
      name: 'User',
      component: () => import('../components/UserPanel.vue'),
      meta: {
        title: '个人中心',
        icon: 'User'
      }
    },
    // 404 页面
    {
      path: '/:pathMatch(.*)*',
      redirect: '/nav'
    }
  ],

  // 路由跳转时滚动行为（保持在顶部）
  scrollBehavior() {
    return { top: 0 }
  }
})

// 全局路由守卫：设置页面标题和权限检查
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - 校园导游`
  }
  
  // 权限检查（可选）
  if (to.meta.requiresAuth) {
    const authStore = useAuthStore()
    if (!authStore.isAuthenticated) {
      next('/login')
      return
    }
  }
  
  next()
})

export default router
