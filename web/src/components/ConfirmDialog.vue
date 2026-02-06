<script setup lang="ts">
defineProps<{
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  loading?: boolean
  type?: 'danger' | 'warning' | 'info'
}>()

defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div 
      class="absolute inset-0 bg-space-950/80 backdrop-blur-sm transition-opacity"
      @click="$emit('cancel')"
    />

    <!-- Dialog -->
    <div class="relative w-full max-w-md bg-space-900 border border-space-800 rounded-xl shadow-2xl p-6 transform transition-all">
      <div class="flex items-start gap-4 mb-4">
        <div 
          class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center"
          :class="{
            'bg-red-500/10 text-red-500': type === 'danger',
            'bg-amber-500/10 text-amber-500': type === 'warning',
            'bg-neural-500/10 text-neural-500': type !== 'danger' && type !== 'warning'
          }"
        >
          <div v-if="type === 'danger'" class="i-carbon-warning-filled w-6 h-6" />
          <div v-else-if="type === 'warning'" class="i-carbon-warning-alt w-6 h-6" />
          <div v-else class="i-carbon-information w-6 h-6" />
        </div>
        
        <div class="flex-1">
          <h3 class="text-lg font-semibold text-white mb-2">{{ title }}</h3>
          <p class="text-space-300 text-sm leading-relaxed">{{ message }}</p>
        </div>
      </div>

      <div class="flex justify-end gap-3 mt-6">
        <button 
          @click="$emit('cancel')" 
          class="btn-ghost text-sm"
          :disabled="loading"
        >
          {{ cancelText || 'Cancel' }}
        </button>
        <button 
          @click="$emit('confirm')" 
          class="btn text-sm flex items-center gap-2"
          :class="type === 'danger' ? 'bg-red-500 text-white hover:bg-red-600' : 'btn-primary'"
          :disabled="loading"
        >
          <div v-if="loading" class="i-carbon-circle-dash animate-spin w-4 h-4" />
          {{ confirmText || 'Confirm' }}
        </button>
      </div>
    </div>
  </div>
</template>
