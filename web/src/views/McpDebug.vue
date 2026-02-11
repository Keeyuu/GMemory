<script setup lang="ts">
import { ref } from 'vue'
import { useMcpDebug } from '../composables/useMcpDebug'

const { initialize, listTools, sessionId, mcpBase } = useMcpDebug()

const loading = ref(false)
const output = ref('Ready')

const renderResult = (payload: unknown) => {
  output.value = JSON.stringify(payload, null, 2)
}

const handleInitialize = async () => {
  loading.value = true
  const result = await initialize()
  renderResult(result)
  loading.value = false
}

const handleListTools = async () => {
  loading.value = true
  const result = await listTools(sessionId.value ?? undefined)
  renderResult(result)
  loading.value = false
}
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-display font-semibold text-white mb-1">MCP Debug</h1>
      <p class="text-space-400">Minimal MCP initialize and tools/list debugger. Please Initialize before List Tools.</p>
    </div>

    <section class="card p-5 space-y-4">
      <div class="grid md:grid-cols-2 gap-4 text-sm">
        <div>
          <div class="text-space-500 mb-1">MCP Base</div>
          <div class="font-mono text-neural-300 break-all">{{ mcpBase }}</div>
        </div>
        <div>
          <div class="text-space-500 mb-1">Current Session</div>
          <div class="font-mono text-space-200 break-all">{{ sessionId ?? 'none' }}</div>
        </div>
      </div>

      <div class="flex gap-3">
        <button class="btn" :disabled="loading" @click="handleInitialize">
          <span v-if="loading" class="i-carbon-circle-dash animate-spin w-4 h-4 mr-2 inline-block" />
          Initialize
        </button>
        <button class="btn" :disabled="loading" @click="handleListTools">
          <span v-if="loading" class="i-carbon-circle-dash animate-spin w-4 h-4 mr-2 inline-block" />
          List Tools
        </button>
      </div>
    </section>

    <section class="card p-5">
      <h2 class="text-sm font-semibold text-space-300 mb-3">Result</h2>
      <pre class="m-0 p-4 rounded-lg bg-space-950 border border-space-800 text-xs text-space-200 overflow-auto min-h-[220px] whitespace-pre-wrap">{{ output }}</pre>
    </section>
  </div>
</template>
