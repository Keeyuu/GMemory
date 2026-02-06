<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMemories } from '../composables/useMemories'
import type { Memory } from '../types/memory'
import MemoryForm from '../components/MemoryForm.vue'

const router = useRouter()
const { addMemory } = useMemories()
const loading = ref(false)

const handleCreate = async (data: Omit<Memory, 'id' | 'created_at' | 'updated_at'>) => {
  loading.value = true
  try {
    const newMemory = await addMemory(data)
    router.push({ name: 'memory-detail', params: { id: newMemory.id } })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <button 
        @click="router.back()" 
        class="flex items-center gap-2 text-space-400 hover:text-white transition-colors group mb-4"
      >
        <div class="i-carbon-arrow-left w-4 h-4 group-hover:-translate-x-1 transition-transform" />
        <span>Back</span>
      </button>
      <h1 class="text-2xl font-display font-semibold text-white mb-2">Create New Memory</h1>
      <p class="text-space-400">Add a new distilled insight to your knowledge base.</p>
    </div>

    <!-- Form -->
    <div class="card p-6">
      <MemoryForm
        :loading="loading"
        @submit="handleCreate"
        @cancel="router.back()"
      />
    </div>
  </div>
</template>
