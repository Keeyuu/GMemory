<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const searchQuery = ref('')

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({ name: 'search', query: { q: searchQuery.value } })
  }
}

const isSearchPage = computed(() => route.name === 'search')
</script>

<template>
  <header class="h-16 border-b border-space-800 bg-space-950/80 backdrop-blur-md flex items-center px-6 gap-4">
    <!-- Search Bar -->
    <div class="flex-1 max-w-2xl">
      <form @submit.prevent="handleSearch" class="relative">
        <div class="i-carbon-search absolute left-4 top-1/2 -translate-y-1/2 text-space-500 w-5 h-5" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search memories... (semantic + keyword)"
          class="input pl-12 py-2.5 bg-space-900/50"
        />
        <kbd 
          v-if="!isSearchPage"
          class="absolute right-4 top-1/2 -translate-y-1/2 hidden sm:inline-flex items-center gap-1 px-2 py-0.5 text-xs text-space-500 bg-space-800 rounded border border-space-700"
        >
          <span class="text-[10px]">⌘</span>K
        </kbd>
      </form>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-3">
      <button 
        @click="router.push({ name: 'new-memory' })"
        class="btn-primary flex items-center gap-2"
      >
        <div class="i-carbon-add w-4 h-4" />
        <span class="hidden sm:inline">New Memory</span>
      </button>
    </div>
  </header>
</template>
