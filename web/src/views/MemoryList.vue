<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMemories } from '../composables/useMemories'
import type { Memory } from '../types/memory'
import MemoryCard from '../components/MemoryCard.vue'

type ImportanceLevel = 'high' | 'medium' | 'low'

interface TypeBucket {
  value: string
  label: string
  count: number
  priority: number
  highestImportance: number
}

const TYPE_PRIORITY: Record<string, number> = {
  pending: 100,
  todo: 95,
  urgent: 90,
  'in-progress': 85,
  in_progress: 85,
  processing: 80,
  high: 75,
  medium: 55,
  low: 40,
  done: 20,
  resolved: 20,
  closed: 10,
}

const IMPORTANCE_SCORE: Record<ImportanceLevel, number> = {
  high: 3,
  medium: 2,
  low: 1,
}

const router = useRouter()
const { getAllMemories } = useMemories()

const allMemories = ref<Memory[]>([])
const loading = ref(true)
const searchQuery = ref('')
const selectedType = ref('')

const resolveTypeValue = (memory: Memory): string => {
  const rawType = (memory.memory_type || '').trim()
  return rawType ? rawType.toLowerCase() : 'untyped'
}

const resolveTypeLabel = (memory: Memory): string => {
  const rawType = (memory.memory_type || '').trim()
  return rawType || 'untyped'
}

const resolveTypePriority = (typeValue: string): number => {
  return TYPE_PRIORITY[typeValue] ?? 50
}

const typeBuckets = computed<TypeBucket[]>(() => {
  const buckets = new Map<string, TypeBucket>()

  for (const memory of allMemories.value) {
    const value = resolveTypeValue(memory)
    const label = resolveTypeLabel(memory)
    const highestImportance = IMPORTANCE_SCORE[memory.importance] ?? 1
    const existing = buckets.get(value)

    if (!existing) {
      buckets.set(value, {
        value,
        label,
        count: 1,
        priority: resolveTypePriority(value),
        highestImportance,
      })
      continue
    }

    existing.count += 1
    existing.highestImportance = Math.max(existing.highestImportance, highestImportance)
  }

  return Array.from(buckets.values()).sort((a, b) => {
    if (b.priority !== a.priority) {
      return b.priority - a.priority
    }

    if (b.highestImportance !== a.highestImportance) {
      return b.highestImportance - a.highestImportance
    }

    if (b.count !== a.count) {
      return b.count - a.count
    }

    return a.label.localeCompare(b.label)
  })
})

const currentType = computed(() => {
  return typeBuckets.value.find((bucket) => bucket.value === selectedType.value) || null
})

const filteredMemories = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  return allMemories.value
    .filter((memory) => resolveTypeValue(memory) === selectedType.value)
    .filter((memory) => {
      if (!query) {
        return true
      }

      const searchable = [
        memory.preview || '',
        memory.content || '',
        memory.memory_type || '',
        ...memory.tags,
      ]
        .join(' ')
        .toLowerCase()

      return searchable.includes(query)
    })
    .sort((a, b) => {
      const importanceDiff =
        (IMPORTANCE_SCORE[b.importance] ?? 1) - (IMPORTANCE_SCORE[a.importance] ?? 1)
      if (importanceDiff !== 0) {
        return importanceDiff
      }

      const updatedA = a.updated_at ? Date.parse(a.updated_at) : 0
      const updatedB = b.updated_at ? Date.parse(b.updated_at) : 0
      return updatedB - updatedA
    })
})

watch(
  typeBuckets,
  (buckets) => {
    if (!buckets.length) {
      selectedType.value = ''
      return
    }

    const exists = buckets.some((bucket) => bucket.value === selectedType.value)
    if (!exists) {
      const firstBucket = buckets[0]
      selectedType.value = firstBucket ? firstBucket.value : ''
    }
  },
  { immediate: true },
)

const loadData = async () => {
  loading.value = true
  try {
    allMemories.value = await getAllMemories()
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-8 h-full flex flex-col">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-display font-semibold text-white mb-1">Memories</h1>
        <p class="text-space-400">Click a type to focus and process all memories in that category.</p>
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
      <div class="sm:col-span-5 relative">
        <div class="absolute left-3 top-1/2 -translate-y-1/2 text-space-400 pointer-events-none">
          <div class="i-carbon-search w-4 h-4" />
        </div>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search in selected type..."
          class="input pl-10"
        />
      </div>
    </div>

    <div class="space-y-3">
      <div class="text-sm text-space-400">Type Queue (default selects highest priority)</div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="bucket in typeBuckets"
          :key="bucket.value"
          type="button"
          @click="selectedType = bucket.value"
          :class="[
            'px-3 py-1.5 rounded-lg text-sm border transition-colors',
            selectedType === bucket.value
              ? 'border-neural-500 bg-neural-500/20 text-neural-300'
              : 'border-space-700 bg-space-900/40 text-space-300 hover:border-space-500 hover:text-white',
          ]"
        >
          {{ bucket.label }}
          <span class="ml-2 text-xs text-space-400">{{ bucket.count }}</span>
        </button>
      </div>
    </div>

    <div class="text-xs text-space-500 -mt-2" v-if="currentType">
      Showing {{ filteredMemories.length }} / {{ currentType.count }} memories in type "{{ currentType.label }}"
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

    <div
      v-else-if="!typeBuckets.length"
      class="flex-1 flex flex-col items-center justify-center p-12 text-center border border-dashed border-space-800 rounded-xl bg-space-900/20"
    >
      <div class="w-16 h-16 rounded-full bg-space-800/50 flex items-center justify-center mb-4">
        <div class="i-carbon-document-view w-8 h-8 text-space-500" />
      </div>
      <h3 class="text-lg font-medium text-white mb-2">No memories yet</h3>
      <p class="text-space-400 max-w-sm">
        Create a memory first. After that, this page will group them by type for easier processing.
      </p>
    </div>

    <div
      v-else-if="filteredMemories.length === 0"
      class="flex-1 flex flex-col items-center justify-center p-12 text-center border border-dashed border-space-800 rounded-xl bg-space-900/20"
    >
      <div class="w-16 h-16 rounded-full bg-space-800/50 flex items-center justify-center mb-4">
        <div class="i-carbon-search w-8 h-8 text-space-500" />
      </div>
      <h3 class="text-lg font-medium text-white mb-2">No memories found</h3>
      <p class="text-space-400 max-w-sm">
        Try another keyword, or click a different type to process a different memory queue.
      </p>
      <button
        @click="searchQuery = ''"
        class="mt-6 btn-ghost text-sm"
      >
        Clear search
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
