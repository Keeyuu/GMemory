<script setup lang="ts">
import { ref } from 'vue'
import type { ExternalImportResult } from '../types/memory'
import { useMemories } from '../composables/useMemories'

const { importExternalProvider } = useMemories()

const folderPath = ref('')
const scannerType = ref('opencode')
const limit = ref(500)

const importing = ref(false)
const error = ref('')
const message = ref('')
const result = ref<ExternalImportResult | null>(null)

const scannerOptions = [
  { value: 'opencode', label: 'OpenCode' },
  { value: 'github-copilot', label: 'GitHub Copilot' },
]

const runImport = async () => {
  error.value = ''
  message.value = ''
  result.value = null

  if (!folderPath.value.trim()) {
    error.value = 'Folder path is required'
    return
  }

  importing.value = true
  try {
    const data = await importExternalProvider(
      folderPath.value.trim(),
      scannerType.value,
      Math.max(1, Number(limit.value) || 500),
    )
    result.value = data
    message.value = `Import completed: ${data.queued} queued, ${data.updated} updated, ${data.pending_unprocessed} pending`
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Import failed'
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-display font-semibold text-white mb-1">External Provider Import</h1>
      <p class="text-space-400">Import session data from an external folder into GMemory</p>
    </div>

    <div v-if="error" class="card p-4 border border-red-500/50 text-red-300">{{ error }}</div>
    <div v-if="message" class="card p-4 border border-neural-500/50 text-neural-300">{{ message }}</div>

    <section class="card p-6 space-y-4">
      <h2 class="text-lg font-semibold text-white">Import Settings</h2>

      <div class="grid md:grid-cols-2 gap-4">
        <div class="md:col-span-2">
          <label class="block text-sm text-space-400 mb-1">Folder Path</label>
          <input
            v-model="folderPath"
            type="text"
            class="input"
            placeholder="/path/to/external/provider/sessions"
          />
        </div>

        <div>
          <label class="block text-sm text-space-400 mb-1">Provider Type</label>
          <select v-model="scannerType" class="input">
            <option v-for="item in scannerOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm text-space-400 mb-1">Session Limit</label>
          <input v-model.number="limit" type="number" min="1" max="5000" class="input" />
        </div>
      </div>

      <div class="flex justify-end">
        <button class="btn-primary" :disabled="importing" @click="runImport">
          <span v-if="importing">Importing...</span>
          <span v-else>Start Import</span>
        </button>
      </div>
    </section>

    <section v-if="result" class="card p-6 space-y-4">
      <h2 class="text-lg font-semibold text-white">Import Result</h2>

      <div class="grid md:grid-cols-5 gap-4">
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Source Sessions</div>
          <div class="text-2xl font-mono text-white">{{ result.source_total_sessions }}</div>
        </div>
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Scanned This Run</div>
          <div class="text-2xl font-mono text-white">{{ result.total_sessions }}</div>
        </div>
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Queued New</div>
          <div class="text-2xl font-mono text-neural-300">{{ result.queued }}</div>
        </div>
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Pending Unprocessed</div>
          <div class="text-2xl font-mono text-amber-300">{{ result.pending_unprocessed }}</div>
        </div>
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Failed</div>
          <div class="text-2xl font-mono text-red-300">{{ result.failed }}</div>
        </div>
      </div>

      <div class="text-sm text-space-400">
        Source: {{ result.folder_path }} · Scanner: {{ result.scanner_type }} · Processed: {{ result.processed_sessions }} / {{ result.total_imported_sessions }}
      </div>
      <div class="text-sm text-space-500">
        Imported sessions are queued as unprocessed. Continue with your normal process/save workflow to distill memories.
      </div>

      <div v-if="result.errors.length > 0" class="space-y-2">
        <h3 class="text-white font-medium">Errors (first {{ result.errors.length }})</h3>
        <div class="space-y-2 max-h-80 overflow-y-auto pr-1">
          <div
            v-for="item in result.errors"
            :key="`${item.session_id}-${item.error}`"
            class="rounded-lg border border-space-800 p-3"
          >
            <div class="text-sm font-mono text-space-300">{{ item.session_id }}</div>
            <div class="text-sm text-red-300">{{ item.error }}</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
