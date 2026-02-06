<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMemories } from '../composables/useMemories'
import type { Memory } from '../types/memory'
import MemoryCard from '../components/MemoryCard.vue'

const router = useRouter()
const { getMemories, getRecentMemories } = useMemories()

const memories = ref<Memory[]>([])
const loading = ref(true)
const searchQuery = ref('')
const filterImportance = ref<'all' | 'high' | 'medium' | 'low'>('all')
const scope = ref<'recent7' | 'recent30' | 'all'>('recent30')
const limit = ref<20 | 50 | 100>(50)

const loadData = async () => {
  loading.value = true
  try {
    if (scope.value === 'recent7') {
      memories.value = await getRecentMemories(7, limit.value)
      return
    }

    if (scope.value === 'recent30') {
      memories.value = await getRecentMemories(30, limit.value)
      return
    }

    memories.value = await getMemories({
      limit: limit.value,
      offset: 0,
      importance: filterImportance.value === 'all' ? undefined : filterImportance.value,
    })
  } finally {
    loading.value = false
  }
}

const onScopeChange = async () => {
  await loadData()
}

const onLimitChange = async () => {
  await loadData()
}

const onImportanceChange = async () => {
  if (scope.value === 'all') {
    await loadData()
  }
}

const filteredMemories = computed(() => {
  return memories.value.filter((memory) => {
    const query = searchQuery.value.toLowerCase()
    const searchableText = (memory.content || memory.preview || '').toLowerCase()
    const matchesSearch =
      !query ||
      searchableText.includes(query) ||
      memory.tags.some((tag) => tag.toLowerCase().includes(query))

    const matchesImportance =
      filterImportance.value === 'all' || memory.importance === filterImportance.value

    return matchesSearch && matchesImportance
  })
})

onMounted(loadData)
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-8 h-full flex flex-col">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-display font-semibold text-white mb-1">Memories</h1>
        <p class="text-space-400">Use layered browsing: preview first, full content on demand.</p>
      </div>
      <button
        @click="router.push({ name: 'new-memory' })"
        class="btn-primary flex items-center gap-2"
      >
        <div class="i-carbon-add w-5 h-5" />
        New Memory
      </button>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-12 gap-4">
      <div class="sm:col-span-4 relative">
        <div class="absolute left-3 top-1/2 -translate-y-1/2 text-space-400 pointer-events-none">
          <div class="i-carbon-search w-4 h-4" />
        </div>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search content or tags..."
          class="input pl-10"
        />
      </div>

      <div class="sm:col-span-3">
        <select v-model="scope" class="input appearance-none cursor-pointer" @change="onScopeChange">
          <option value="recent7">Recent 7 days</option>
          <option value="recent30">Recent 30 days</option>
          <option value="all">All memories</option>
        </select>
      </div>

      <div class="sm:col-span-2">
        <select v-model="filterImportance" class="input appearance-none cursor-pointer" @change="onImportanceChange">
          <option value="all">All importance</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <div class="sm:col-span-2">
        <select v-model="limit" class="input appearance-none cursor-pointer" @change="onLimitChange">
          <option :value="20">20 items</option>
          <option :value="50">50 items</option>
          <option :value="100">100 items</option>
        </select>
      </div>

    </div>

    <div class="text-xs text-space-500 -mt-2">
      Showing {{ filteredMemories.length }} / {{ memories.length }} memories
      <span>(preview layer)</span>
    </div>

    <div v-if="loading" class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="card p-5 animate-pulse min-h-[200px]">
        <div class="h-4 w-20 bg-space-800 rounded mb-4" />
        <div class="space-y-2 mb-4">
          <div class="h-4 bg-space-800 rounded" />
          <div class="h-4 bg-space-800 rounded w-3/4" />
          <div class="h-4 bg-space-800 rounded w-1/2" />
        </div>
      </div>
    </div>

    <div v-else-if="filteredMemories.length === 0" class="flex-1 flex flex-col items-center justify-center p-12 text-center border border-dashed border-space-800 rounded-xl bg-space-900/20">
      <div class="w-16 h-16 rounded-full bg-space-800/50 flex items-center justify-center mb-4">
        <div class="i-carbon-search w-8 h-8 text-space-500" />
      </div>
      <h3 class="text-lg font-medium text-white mb-2">No memories found</h3>
      <p class="text-space-400 max-w-sm">
        Try adjusting your search or filters, or create a new memory to get started.
      </p>
      <button
        @click="searchQuery = ''; filterImportance = 'all'"
        class="mt-6 btn-ghost text-sm"
      >
        Clear filters
      </button>
    </div>

    <div v-else class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
      <MemoryCard
        v-for="memory in filteredMemories"
        :key="memory.id"
        :memory="memory"
      />
    </div>
  </div>
</template>
