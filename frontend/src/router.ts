import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import ImageSelection from './components/ImageSelection.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'ImageSelection',
      component: ImageSelection
    },
    {
      path: '/chat',
      name: 'Chat',
      component: Home
    }
  ]
})

export default router

