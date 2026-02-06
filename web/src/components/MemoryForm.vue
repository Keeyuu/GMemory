<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Memory } from '../types/memory'

const props = defineProps<{
  initialData?: Partial<Memory>
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', data: Omit<Memory, 'id' | 'created_at' | 'updated_at'>): void
  (e: 'cancel'): void
}>()

const formData = ref({
  content: props.initialData?.content || '',
  tags: props.initialData?.tags ? [...props.initialData.tags] : [],
  importance: props.initialData?.importance || 'medium',
  preview: props.initialData?.preview || ''
})

const tagInput = ref('')

const importanceOptions = [
  { value: 'high', label: 'High', class: 'text-red-400 bg-red-500/10 hover:bg-red-500/20 ring-red-500/50' },
  { value: 'medium', label: 'Medium', class: 'text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 ring-amber-500/50' },
  { value: 'low', label: 'Low', class: 'text-space-400 bg-space-500/10 hover:bg-space-500/20 ring-space-500/50' },
] as const

const addTag = () => {
  const tag = tagInput.value.trim()
  if (tag && !formData.value.tags.includes(tag)) {
    formData.value.tags.push(tag)
  }
  tagInput.value = ''
}

const removeTag = (tagToRemove: string) => {
  formData.value.tags = formData.value.tags.filter(tag => tag !== tagToRemove)
}

const removeLastTag = (e: KeyboardEvent) => {
  if (tagInput.value === '' && formData.value.tags.length > 0 && e.key === 'Backspace') {
    formData.value.tags.pop()
  }
}

const handleSubmit = () => {
  if (!formData.value.content.trim()) return
  
  // Auto-generate preview if empty
  if (!formData.value.preview) {
    formData.value.preview = formData.value.content.slice(0, 150) + (formData.value.content.length > 150 ? '...' : '')
  }
  
  emit('submit', formData.value)
}

const isValid = computed(() => formData.value.content.trim().length > 0)
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-6">
    <!-- Importance Selector -->
    <div class="space-y-2">
      <label class="text-sm font-medium text-space-300">Importance</label>
      <div class="flex gap-3">
        <button
          v-for="option in importanceOptions"
          :key="option.value"
          type="button"
          @click="formData.importance = option.value"
          :class="[
            'px-4 py-2 rounded-lg text-sm font-medium transition-all border border-transparent',
            option.class,
            formData.importance === option.value ? 'ring-1 bg-opacity-30' : 'opacity-60 hover:opacity-100'
          ]"
        >
          {{ option.label }}
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="space-y-2">
      <label class="text-sm font-medium text-space-300">Content</label>
      <textarea
        v-model="formData.content"
        rows="8"
        class="input font-mono text-sm leading-relaxed resize-y min-h-[150px]"
        placeholder="Enter memory content..."
        required
      ></textarea>
    </div>

    <!-- Tags -->
    <div class="space-y-2">
      <label class="text-sm font-medium text-space-300">Tags</label>
      <div class="input flex flex-wrap gap-2 items-center min-h-[46px] py-2">
        <span
          v-for="tag in formData.tags"
          :key="tag"
          class="tag bg-neural-500/20 text-neural-400 px-2 py-1 rounded flex items-center gap-1 group"
        >
          {{ tag }}
          <button
            type="button"
            @click="removeTag(tag)"
            class="text-neural-500/50 hover:text-neural-400 focus:outline-none"
          >
            <div class="i-carbon-close w-3 h-3" />
          </button>
        </span>
        <input
          v-model="tagInput"
          @keydown.enter.prevent="addTag"
          @keydown.backspace="removeLastTag"
          @blur="addTag"
          type="text"
          class="bg-transparent border-none outline-none text-sm flex-1 min-w-[120px] placeholder-space-500/50 p-0 focus:ring-0"
          placeholder="Add tags (press Enter)..."
        />
      </div>
    </div>

    <!-- Preview (Optional) -->
    <div class="space-y-2">
      <div class="flex justify-between">
        <label class="text-sm font-medium text-space-300">Preview (Optional)</label>
        <button 
          type="button" 
          class="text-xs text-neural-400 hover:text-neural-300"
          @click="formData.preview = formData.content.slice(0, 150) + (formData.content.length > 150 ? '...' : '')"
        >
          Auto-generate
        </button>
      </div>
      <textarea
        v-model="formData.preview"
        rows="3"
        class="input text-sm text-space-300"
        placeholder="Short preview for list view..."
      ></textarea>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-end gap-3 pt-4 border-t border-space-800">
      <button
        type="button"
        @click="$emit('cancel')"
        class="btn-ghost"
        :disabled="loading"
      >
        Cancel
      </button>
      <button
        type="submit"
        class="btn-primary flex items-center gap-2"
        :disabled="!isValid || loading"
      >
        <div v-if="loading" class="i-carbon-circle-dash animate-spin w-4 h-4" />
        <div v-else class="i-carbon-save w-4 h-4" />
        Save Memory
      </button>
    </div>
  </form>
</template>
