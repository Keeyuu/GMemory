import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'

import 'virtual:uno.css'
import '@unocss/reset/tailwind.css'
import './style.css'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/memories', redirect: '/search' },
  { path: '/memories/new', name: 'new-memory', component: () => import('./views/NewMemory.vue') },
  { path: '/memory/:id', name: 'memory-detail', component: () => import('./views/MemoryDetail.vue') },
  { path: '/search', name: 'search', component: () => import('./views/Search.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const app = createApp(App)
app.use(router)
app.mount('#app')
