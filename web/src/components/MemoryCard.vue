<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Memory } from '../types/memory'

const props = defineProps<{
  memory: Memory
  showScoring?: boolean  // 是否显示分数分解（搜索结果页使用）
  showFullContent?: boolean
}>()

const router = useRouter()

const navigateToDetail = () => {
  router.push({ name: 'memory-detail', params: { id: props.memory.id } })
}

// 重要度颜色映射
const importanceColor = (importance: string) => {
  switch (importance) {
    case 'high': return 'bg-neural-500'      // 绿色 - 高重要度
    case 'medium': return 'bg-amber-500'     // 黄色 - 中等
    case 'low': return 'bg-space-600'        // 灰色 - 低重要度
    default: return 'bg-space-600'
  }
}

const importanceClass = (importance: string) => {
  switch (importance) {
    case 'high': return 'tag-high'
    case 'medium': return 'tag-medium'
    case 'low': return 'tag-low'
    default: return 'tag-low'
  }
}

// 计算分数条宽度百分比
const scoreBarWidth = (score: number) => `${Math.round(score * 100)}%`

const previewText = computed(() => {
  if (props.memory.preview && props.memory.preview.trim().length > 0) {
    return props.memory.preview
  }
  const raw = props.memory.content || ''
  const normalized = raw.replace(/\s+/g, ' ').trim()
  if (normalized.length <= 180) {
    return normalized
  }
  return `${normalized.slice(0, 180)}...`
})
</script>

<template>
  <article
    role="link"
    tabindex="0"
    @click="navigateToDetail"
    @keydown.enter="navigateToDetail"
    @keydown.space.prevent="navigateToDetail"
    class="card block cursor-pointer hover:border-neural-500/50 hover:shadow-[0_0_20px_rgba(34,197,94,0.1)] transition-all duration-300 group overflow-hidden"
  >
    <div class="flex">
      <!-- 左侧重要度指示条 -->
      <div 
        :class="importanceColor(memory.importance)"
        class="w-1 shrink-0 rounded-l-lg"
      />
      
      <!-- 主内容区域 -->
      <div class="flex-1 p-4 pl-4 min-w-0">
        <!-- Header: 重要度标签 + 分数 + 箭头 -->
        <div class="flex items-center justify-between gap-3 mb-2">
          <div class="flex items-center gap-2 min-w-0">
            <span :class="importanceClass(memory.importance)" class="shrink-0">
              {{ memory.importance }}
            </span>
            <span v-if="memory.score" class="text-xs text-space-500 font-mono shrink-0">
              {{ memory.score.toFixed(2) }}
            </span>
          </div>
          <div class="i-carbon-arrow-right w-4 h-4 text-space-600 group-hover:text-neural-400 group-hover:translate-x-1 transition-all shrink-0" />
        </div>

        <!-- 分数分解条形图（搜索结果页显示） -->
        <div 
          v-if="showScoring && memory.scoring" 
          class="mb-3 space-y-1"
        >
          <div class="flex items-center gap-2 text-xs">
            <span class="text-space-500 w-14 shrink-0">Vector</span>
            <div class="flex-1 h-1.5 bg-space-800 rounded-full overflow-hidden">
              <div 
                class="h-full bg-neural-500 rounded-full transition-all"
                :style="{ width: scoreBarWidth(memory.scoring.vec_score) }"
              />
            </div>
            <span class="text-space-500 font-mono w-8 text-right">{{ (memory.scoring.vec_score * 100).toFixed(0) }}</span>
          </div>
          <div class="flex items-center gap-2 text-xs">
            <span class="text-space-500 w-14 shrink-0">Keyword</span>
            <div class="flex-1 h-1.5 bg-space-800 rounded-full overflow-hidden">
              <div 
                class="h-full bg-blue-500 rounded-full transition-all"
                :style="{ width: scoreBarWidth(memory.scoring.fts_score) }"
              />
            </div>
            <span class="text-space-500 font-mono w-8 text-right">{{ (memory.scoring.fts_score * 100).toFixed(0) }}</span>
          </div>
          <div v-if="memory.scoring.recency_score > 0" class="flex items-center gap-2 text-xs">
            <span class="text-space-500 w-14 shrink-0">Recency</span>
            <div class="flex-1 h-1.5 bg-space-800 rounded-full overflow-hidden">
              <div 
                class="h-full bg-amber-500 rounded-full transition-all"
                :style="{ width: scoreBarWidth(memory.scoring.recency_score) }"
              />
            </div>
            <span class="text-space-500 font-mono w-8 text-right">{{ (memory.scoring.recency_score * 100).toFixed(0) }}</span>
          </div>
        </div>

        <!-- Preview/Full Content -->
        <p
          class="text-space-200 text-sm leading-relaxed mb-3"
          :class="showFullContent ? '' : 'line-clamp-2'"
        >
          {{ showFullContent ? memory.content : previewText }}
        </p>

        <!-- Tags (最多显示3个) -->
        <div class="flex flex-wrap gap-1.5 mb-3">
          <span
            v-for="tag in memory.tags.slice(0, 3)"
            :key="tag"
            class="tag-neural text-xs"
          >
            {{ tag }}
          </span>
          <span v-if="memory.tags.length > 3" class="text-xs text-space-500">
            +{{ memory.tags.length - 3 }}
          </span>
        </div>

        <!-- Footer: tokens + ID -->
        <div class="flex items-center justify-between text-xs text-space-500 pt-2 border-t border-space-800">
          <span class="font-mono">{{ memory.tokens }} tokens</span>
          <span class="font-mono">{{ memory.id.slice(0, 8) }}...</span>
        </div>
      </div>
    </div>
  </article>
</template>
