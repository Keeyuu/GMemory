<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useMemories } from '../composables/useMemories'
import type { MemoryStats } from '../types/memory'

const route = useRoute()
const { getStats } = useMemories()
const stats = ref<MemoryStats | null>(null)

onMounted(async () => {
  try {
    stats.value = await getStats()
  } catch {
    stats.value = null
  }
})

const navItems = [
  { name: 'dashboard', label: 'Dashboard', icon: 'i-carbon-dashboard' },
  { name: 'memories', label: 'Memories', icon: 'i-carbon-document-view' },
  { name: 'search', label: 'Search', icon: 'i-carbon-search' },
  { name: 'backup', label: 'Backup', icon: 'i-carbon-data-backup' },
  { name: 'import', label: 'Import', icon: 'i-carbon-upload' },
]

const isActive = (name: string) => {
  if (name === 'dashboard') {
    return route.name === 'dashboard' || route.path === '/'
  }
  return route.name === name
}
</script>

<template>
  <aside class="w-64 border-r border-space-800 bg-space-950/50 backdrop-blur-sm flex flex-col">
    <!-- Logo -->
    <div class="h-16 flex items-center px-6 border-b border-space-800">
      <router-link to="/" class="flex items-center gap-3 group">
        <div class="w-8 h-8 rounded-lg bg-neural-500/20 flex items-center justify-center group-hover:bg-neural-500/30 transition-colors">
          <div class="i-carbon-machine-learning-model w-5 h-5 text-neural-400" />
        </div>
        <span class="font-display font-semibold text-lg text-white">GMemory</span>
      </router-link>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 p-4 space-y-1">
      <router-link
        v-for="item in navItems"
        :key="item.name"
        :to="{ name: item.name }"
        :class="[
          'flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200',
          isActive(item.name)
            ? 'bg-neural-500/20 text-neural-400'
            : 'text-space-400 hover:text-white hover:bg-space-800'
        ]"
      >
        <div :class="[item.icon, 'w-5 h-5']" />
        <span class="font-medium">{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- Stats Footer -->
    <div class="p-4 border-t border-space-800">
      <div class="card p-4 space-y-3">
        <div class="text-xs font-medium text-space-500 uppercase tracking-wider">Quick Stats</div>
        <div class="space-y-2">
          <div class="flex justify-between text-sm">
            <span class="text-space-400">Memories</span>
            <span class="font-mono text-neural-400">{{ stats?.total_memories ?? '--' }}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-space-400">Sessions</span>
            <span class="font-mono text-space-300">{{ stats?.processed_sessions ?? '--' }}</span>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>
