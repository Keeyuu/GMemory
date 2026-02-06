<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMemories } from '../composables/useMemories'
import type { Memory } from '../types/memory'
import MemoryForm from '../components/MemoryForm.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const { getMemory, updateMemory, deleteMemory } = useMemories()

const memory = ref<Memory | null>(null)
const loading = ref(true)
const saving = ref(false)
const isEditing = ref(false)
const showDeleteConfirm = ref(false)

const previewText = computed(() => {
  if (!memory.value) return ''
  const preview = memory.value.preview?.trim()
  if (preview) {
    return preview
  }
  const normalized = (memory.value.content || '').replace(/\s+/g, ' ').trim()
  if (normalized.length <= 180) {
    return normalized
  }
  return `${normalized.slice(0, 180)}...`
})

const loadData = async () => {
  loading.value = true
  try {
    const id = route.params.id as string
    const data = await getMemory(id)
    if (data) {
      memory.value = data
    } else {
      router.push({ name: 'search' })
    }
  } finally {
    loading.value = false
  }
}

const handleUpdate = async (data: Omit<Memory, 'id' | 'created_at' | 'updated_at'>) => {
  if (!memory.value) return
  
  saving.value = true
  try {
    const updated = await updateMemory(memory.value.id, data)
    memory.value = updated
    isEditing.value = false
  } finally {
    saving.value = false
  }
}

const handleDelete = async () => {
  if (!memory.value) return
  
  saving.value = true
  try {
    await deleteMemory(memory.value.id)
    router.push({ name: 'search' })
  } finally {
    saving.value = false
    showDeleteConfirm.value = false
  }
}

const importanceColor = (importance: string) => {
  switch (importance) {
    case 'high': return 'text-red-400 bg-red-500/10 ring-red-500/50'
    case 'medium': return 'text-amber-400 bg-amber-500/10 ring-amber-500/50'
    case 'low': return 'text-space-400 bg-space-500/10 ring-space-500/50'
    default: return 'text-space-400 bg-space-500/10 ring-space-500/50'
  }
}

onMounted(loadData)
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- Back Navigation -->
    <button 
      @click="router.back()" 
      class="flex items-center gap-2 text-space-400 hover:text-white transition-colors group"
    >
      <div class="i-carbon-arrow-left w-4 h-4 group-hover:-translate-x-1 transition-transform" />
        <span>Back to Search</span>
      </button>

    <div v-if="loading" class="card p-8 animate-pulse space-y-4">
      <div class="h-6 w-32 bg-space-800 rounded" />
      <div class="space-y-2">
        <div class="h-4 bg-space-800 rounded" />
        <div class="h-4 bg-space-800 rounded" />
        <div class="h-4 bg-space-800 rounded w-2/3" />
      </div>
    </div>

    <template v-else-if="memory">
      <!-- Edit Mode -->
      <div v-if="isEditing" class="card p-6 border-neural-500/30">
        <div class="flex items-center justify-between mb-6">
          <h1 class="text-xl font-display font-semibold text-white">Edit Memory</h1>
        </div>
        <MemoryForm 
          :initial-data="memory"
          :loading="saving"
          @submit="handleUpdate"
          @cancel="isEditing = false"
        />
      </div>

      <!-- View Mode -->
      <div v-else class="space-y-6">
        <!-- Header Card -->
        <div class="card p-6 space-y-4">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-3">
              <span 
                class="px-2.5 py-1 rounded-md text-xs font-medium uppercase tracking-wider ring-1 ring-inset"
                :class="importanceColor(memory.importance)"
              >
                {{ memory.importance }}
              </span>
              <span v-if="memory.score" class="text-xs font-mono text-space-500">
                Score: {{ memory.score.toFixed(3) }}
              </span>
            </div>
            
            <div class="flex items-center gap-2">
              <button 
                @click="isEditing = true"
                class="btn-ghost p-2 text-space-400 hover:text-neural-400"
                title="Edit"
              >
                <div class="i-carbon-edit w-5 h-5" />
              </button>
              <button 
                @click="showDeleteConfirm = true"
                class="btn-ghost p-2 text-space-400 hover:text-red-400"
                title="Delete"
              >
                <div class="i-carbon-trash-can w-5 h-5" />
              </button>
            </div>
          </div>

          <!-- Metadata -->
          <div class="flex flex-wrap gap-4 text-xs text-space-500 border-t border-space-800 pt-4">
            <div class="flex items-center gap-1.5">
              <div class="i-carbon-fingerprint-recognition w-4 h-4" />
              <span class="font-mono">{{ memory.id }}</span>
            </div>
            <div class="flex items-center gap-1.5" v-if="memory.created_at">
              <div class="i-carbon-calendar w-4 h-4" />
              <span>Created: {{ new Date(memory.created_at).toLocaleDateString() }}</span>
            </div>
            <div class="flex items-center gap-1.5" v-if="memory.tokens">
              <div class="i-carbon-data-base w-4 h-4" />
              <span>{{ memory.tokens }} tokens</span>
            </div>
          </div>
        </div>

        <!-- Preview Card -->
        <div class="card p-6">
          <h2 class="text-sm uppercase tracking-wider text-space-400 mb-3">Preview</h2>
          <p class="text-space-200 text-sm leading-relaxed whitespace-pre-wrap">{{ previewText }}</p>
        </div>

        <!-- Full Content Card -->
        <div class="card p-8">
          <h2 class="text-sm uppercase tracking-wider text-space-400 mb-4">Full Content</h2>
          <div class="prose prose-invert max-w-none font-mono text-sm leading-relaxed whitespace-pre-wrap">
            {{ memory.content }}
          </div>
        </div>

        <!-- Tags -->
        <div v-if="memory.tags.length > 0" class="flex flex-wrap gap-2">
          <span 
            v-for="tag in memory.tags" 
            :key="tag"
            class="tag-neural px-3 py-1.5 text-sm border border-neural-500/10"
          >
            #{{ tag }}
          </span>
        </div>
      </div>
    </template>
    
    <!-- Delete Dialog -->
    <ConfirmDialog
      v-if="showDeleteConfirm"
      title="Delete Memory"
      message="Are you sure you want to delete this memory? This action cannot be undone."
      confirm-text="Delete"
      type="danger"
      :loading="saving"
      @confirm="handleDelete"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>
