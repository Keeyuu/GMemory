<script setup lang="ts">
import { ref, watch } from 'vue'
import { useMemories } from '../composables/useMemories'
import MemoryCard from '../components/MemoryCard.vue'

// Simple debounce implementation to avoid dependency
function simpleDebounce<T extends (...args: any[]) => any>(fn: T, delay: number) {
  let timeout: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => fn(...args), delay)
  }
}

const { searchMemories } = useMemories()

const query = ref('')
const mode = ref('hybrid')
const results = ref<any[]>([])
const loading = ref(false)
const hasSearched = ref(false)
const total = ref(0)

const searchModes = [
  { id: 'hybrid', label: 'Hybrid', icon: 'i-carbon-flow-stream' },
  { id: 'vector', label: 'Vector', icon: 'i-carbon-data-class' },
  { id: 'fts', label: 'Keyword', icon: 'i-carbon-search' },
]

const performSearch = async () => {
  if (!query.value.trim()) {
    results.value = []
    hasSearched.value = false
    return
  }

  loading.value = true
  hasSearched.value = true
  
  try {
    const data = await searchMemories(query.value, mode.value)
    results.value = data.results
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const debouncedSearch = simpleDebounce(performSearch, 500)

watch(query, () => {
  debouncedSearch()
})

watch(mode, () => {
  if (query.value) performSearch()
})
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-8 h-full flex flex-col">
    <!-- Header & Search Input -->
    <div class="max-w-3xl mx-auto w-full space-y-6">
      <div class="text-center space-y-2">
        <h1 class="text-3xl font-display font-semibold text-white">Search Memories</h1>
        <p class="text-space-400">Find insights using semantic vector search and keyword matching</p>
      </div>

      <div class="relative">
        <div class="absolute left-4 top-1/2 -translate-y-1/2 text-space-400 pointer-events-none">
          <div v-if="loading" class="i-carbon-circle-dash animate-spin w-5 h-5" />
          <div v-else class="i-carbon-search w-5 h-5" />
        </div>
        <input 
          v-model="query"
          type="text" 
          placeholder="Ask a question or search for keywords..." 
          class="w-full pl-12 pr-4 py-4 bg-space-900 border border-space-700 rounded-xl text-lg text-white placeholder-space-500 focus:outline-none focus:border-neural-500 focus:ring-1 focus:ring-neural-500/50 shadow-lg transition-all"
          autofocus
        />
        <div class="absolute right-4 top-1/2 -translate-y-1/2 flex gap-1">
          <div class="hidden sm:flex items-center gap-1 text-xs text-space-500 bg-space-800 px-2 py-1 rounded border border-space-700">
            <span class="i-carbon-keyboard" />
            <span>/</span>
          </div>
        </div>
      </div>

      <!-- Mode Selector -->
      <div class="flex justify-center">
        <div class="bg-space-900 p-1 rounded-lg border border-space-800 inline-flex">
          <button
            v-for="m in searchModes"
            :key="m.id"
            @click="mode = m.id"
            class="px-4 py-1.5 rounded-md text-sm font-medium flex items-center gap-2 transition-all"
            :class="mode === m.id ? 'bg-space-800 text-white shadow-sm' : 'text-space-400 hover:text-space-200'"
          >
            <div :class="m.icon" class="w-4 h-4" />
            {{ m.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Results -->
    <div class="flex-1 mt-8">
      <div v-if="loading && !results.length" class="grid md:grid-cols-2 gap-4 max-w-5xl mx-auto">
         <div v-for="i in 4" :key="i" class="card p-5 animate-pulse min-h-[160px]">
           <div class="h-4 w-1/3 bg-space-800 rounded mb-4" />
           <div class="space-y-2">
             <div class="h-4 bg-space-800 rounded w-full" />
             <div class="h-4 bg-space-800 rounded w-5/6" />
             <div class="h-4 bg-space-800 rounded w-4/6" />
           </div>
         </div>
      </div>

      <div v-else-if="hasSearched && results.length === 0" class="text-center py-12">
        <div class="w-16 h-16 rounded-full bg-space-900 border border-space-800 flex items-center justify-center mx-auto mb-4">
          <div class="i-carbon-search-locate w-8 h-8 text-space-500" />
        </div>
        <h3 class="text-lg font-medium text-white mb-2">No results found</h3>
        <p class="text-space-400">We couldn't find any memories matching your query.</p>
      </div>

      <div v-else-if="results.length > 0" class="max-w-5xl mx-auto space-y-4">
        <div class="flex items-center justify-between px-2 mb-2">
          <span class="text-sm text-space-400">Found {{ total }} results</span>
        </div>
        <div class="grid md:grid-cols-2 gap-4">
          <MemoryCard
            v-for="memory in results"
            :key="memory.id"
            :memory="memory"
            :show-scoring="true"
          />
        </div>
      </div>
      
      <!-- Initial State -->
      <div v-else class="text-center py-12 opacity-50">
        <div class="i-carbon-idea w-12 h-12 text-space-600 mx-auto mb-4" />
        <p class="text-space-400">Start typing to search your memory bank</p>
      </div>
    </div>
  </div>
</template>
