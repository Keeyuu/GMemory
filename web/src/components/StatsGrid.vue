<script setup lang="ts">
import type { MemoryStats } from '../types/memory'

defineProps<{
  stats: MemoryStats | null
  loading?: boolean
}>()
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <!-- Total Memories -->
    <div class="card p-5">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-neural-500/20 flex items-center justify-center">
          <div class="i-carbon-data-base w-5 h-5 text-neural-400" />
        </div>
        <span class="text-sm text-space-400">Total Memories</span>
      </div>
      <div class="text-3xl font-display font-semibold text-white">
        <template v-if="loading">
          <div class="w-16 h-8 bg-space-800 rounded animate-pulse" />
        </template>
        <template v-else>
          {{ stats?.total_memories ?? 0 }}
        </template>
      </div>
    </div>

    <!-- By Importance -->
    <div class="card p-5">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
          <div class="i-carbon-warning-alt w-5 h-5 text-red-400" />
        </div>
        <span class="text-sm text-space-400">High Priority</span>
      </div>
      <div class="text-3xl font-display font-semibold text-white">
        <template v-if="loading">
          <div class="w-16 h-8 bg-space-800 rounded animate-pulse" />
        </template>
        <template v-else>
          {{ stats?.by_importance?.high ?? 0 }}
        </template>
      </div>
    </div>

    <!-- Processed Sessions -->
    <div class="card p-5">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
          <div class="i-carbon-checkmark-outline w-5 h-5 text-blue-400" />
        </div>
        <span class="text-sm text-space-400">Processed</span>
      </div>
      <div class="text-3xl font-display font-semibold text-white">
        <template v-if="loading">
          <div class="w-16 h-8 bg-space-800 rounded animate-pulse" />
        </template>
        <template v-else>
          {{ stats?.processed_sessions ?? 0 }}
        </template>
      </div>
    </div>

    <!-- Unprocessed Sessions -->
    <div class="card p-5">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
          <div class="i-carbon-pending w-5 h-5 text-amber-400" />
        </div>
        <span class="text-sm text-space-400">Pending</span>
      </div>
      <div class="text-3xl font-display font-semibold text-white">
        <template v-if="loading">
          <div class="w-16 h-8 bg-space-800 rounded animate-pulse" />
        </template>
        <template v-else>
          {{ stats?.unprocessed_sessions ?? 0 }}
        </template>
      </div>
    </div>
  </div>
</template>
