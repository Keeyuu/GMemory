<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Memory, MemoryStats } from '../types/memory'
import StatsGrid from '../components/StatsGrid.vue'
import MemoryCard from '../components/MemoryCard.vue'
import { useMemories } from '../composables/useMemories'

const { getStats, getRecentMemories } = useMemories()

const stats = ref<MemoryStats | null>(null)
const recentMemories = ref<Memory[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const formatAccessTime = (value?: string | number | null) => {
  if (!value) return 'Never accessed'
  const parsed =
    typeof value === 'number'
      ? (value < 1_000_000_000_000 ? value * 1000 : value)
      : value
  const date = new Date(parsed)
  if (Number.isNaN(date.getTime())) return 'Never accessed'
  return date.toLocaleDateString()
}

onMounted(async () => {
  try {
    const [statsResult, recentResult] = await Promise.allSettled([
      getStats(),
      getRecentMemories(7, 6),
    ])

    if (statsResult.status === 'fulfilled') {
      stats.value = statsResult.value
    }

    if (recentResult.status === 'fulfilled') {
      recentMemories.value = recentResult.value
    }

    if (statsResult.status === 'rejected' && recentResult.status === 'rejected') {
      error.value = 'Failed to load dashboard data'
    }
  } catch (e) {
    error.value = 'Failed to load data'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-8">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-display font-semibold text-white mb-1">Dashboard</h1>
        <p class="text-space-400">Your knowledge base at a glance</p>
      </div>
      <div class="flex items-center gap-2 text-sm text-space-500">
        <div class="i-carbon-time w-4 h-4" />
        <span>Last synced: just now</span>
      </div>
    </div>

    <!-- Stats -->
    <StatsGrid :stats="stats" :loading="loading" />

    <!-- Recent Memories -->
    <section>
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-white flex items-center gap-2">
          <div class="i-carbon-recently-viewed w-5 h-5 text-neural-400" />
          Recent Memories
        </h2>
        <router-link 
          to="/search" 
          class="text-sm text-neural-400 hover:text-neural-300 flex items-center gap-1"
        >
          View all
          <div class="i-carbon-arrow-right w-4 h-4" />
        </router-link>
      </div>

      <div v-if="loading" class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="card p-5 animate-pulse">
          <div class="h-4 w-20 bg-space-800 rounded mb-4" />
          <div class="space-y-2 mb-4">
            <div class="h-4 bg-space-800 rounded" />
            <div class="h-4 bg-space-800 rounded w-3/4" />
          </div>
          <div class="flex gap-2">
            <div class="h-5 w-16 bg-space-800 rounded" />
            <div class="h-5 w-12 bg-space-800 rounded" />
          </div>
        </div>
      </div>

      <div v-else-if="error" class="card p-8 text-center">
        <div class="i-carbon-warning-alt w-12 h-12 text-red-400 mx-auto mb-4" />
        <p class="text-space-400">{{ error }}</p>
      </div>

      <div v-else class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MemoryCard
          v-for="memory in recentMemories"
          :key="memory.id"
          :memory="memory"
        />
      </div>
    </section>

    <!-- Hot/Cold Curation -->
    <section class="grid lg:grid-cols-2 gap-6">
      <div class="card p-6">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <div class="i-carbon-fire w-5 h-5 text-red-400" />
          Top Hot
        </h2>
        <div v-if="(stats?.top_hot?.length ?? 0) === 0" class="text-sm text-space-500">
          No hot memories yet.
        </div>
        <div v-else class="space-y-3">
          <router-link
            v-for="item in stats?.top_hot"
            :key="item.id"
            :to="{ name: 'memory-detail', params: { id: item.id } }"
            class="block rounded-lg border border-space-800 hover:border-red-500/50 transition-colors p-3"
          >
            <p class="text-sm text-space-200 line-clamp-2 mb-2">{{ item.preview }}</p>
            <div class="flex items-center justify-between text-xs text-space-500">
              <span>{{ item.access_count }} accesses</span>
              <span>{{ formatAccessTime(item.last_accessed_at) }}</span>
            </div>
          </router-link>
        </div>
      </div>

      <div class="card p-6">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <div class="i-carbon-snow w-5 h-5 text-blue-400" />
          Top Cold
        </h2>
        <div v-if="(stats?.top_cold?.length ?? 0) === 0" class="text-sm text-space-500">
          No cold memories yet.
        </div>
        <div v-else class="space-y-3">
          <router-link
            v-for="item in stats?.top_cold"
            :key="item.id"
            :to="{ name: 'memory-detail', params: { id: item.id } }"
            class="block rounded-lg border border-space-800 hover:border-blue-500/50 transition-colors p-3"
          >
            <p class="text-sm text-space-200 line-clamp-2 mb-2">{{ item.preview }}</p>
            <div class="flex items-center justify-between text-xs text-space-500">
              <span>{{ item.access_count }} accesses</span>
              <span>{{ formatAccessTime(item.last_accessed_at) }}</span>
            </div>
          </router-link>
        </div>
      </div>
    </section>

    <!-- Importance Distribution -->
    <section class="card p-6">
      <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <div class="i-carbon-chart-pie w-5 h-5 text-neural-400" />
        Importance Distribution
      </h2>
      <div class="flex items-center gap-8">
        <div class="flex-1 h-4 rounded-full bg-space-800 overflow-hidden flex">
          <div 
            class="bg-red-500 transition-all duration-500"
            :style="{ width: `${(stats?.by_importance?.high ?? 0) / (stats?.total_memories || 1) * 100}%` }"
          />
          <div 
            class="bg-amber-500 transition-all duration-500"
            :style="{ width: `${(stats?.by_importance?.medium ?? 0) / (stats?.total_memories || 1) * 100}%` }"
          />
          <div 
            class="bg-space-500 transition-all duration-500"
            :style="{ width: `${(stats?.by_importance?.low ?? 0) / (stats?.total_memories || 1) * 100}%` }"
          />
        </div>
        <div class="flex gap-6 text-sm">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded bg-red-500" />
            <span class="text-space-400">High</span>
            <span class="font-mono text-white">{{ stats?.by_importance?.high ?? 0 }}</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded bg-amber-500" />
            <span class="text-space-400">Medium</span>
            <span class="font-mono text-white">{{ stats?.by_importance?.medium ?? 0 }}</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded bg-space-500" />
            <span class="text-space-400">Low</span>
            <span class="font-mono text-white">{{ stats?.by_importance?.low ?? 0 }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
