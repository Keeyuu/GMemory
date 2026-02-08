<script setup lang="ts">
import { ref } from 'vue'
import type {
  ExternalCleanupResult,
  ExternalImportPreview,
  ExternalImportResult,
} from '../types/memory'
import { useMemories } from '../composables/useMemories'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const {
  getStats,
  importExternalProvider,
  previewExternalProviderImport,
  cleanupExternalImportedSessions,
} = useMemories()

const folderPath = ref('')
const scannerType = ref('opencode')
const limit = ref(500)

const importing = ref(false)
const previewing = ref(false)
const cleaning = ref(false)
const error = ref('')
const message = ref('')
const result = ref<ExternalImportResult | null>(null)
const preview = ref<ExternalImportPreview | null>(null)
const cleanupResult = ref<ExternalCleanupResult | null>(null)
const cleanupOlderThanSeconds = ref(0)
const cleanupLimit = ref(1000)
const showCleanupPreviewConfirm = ref(false)
const showCleanupApplyConfirm = ref(false)

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
    preview.value = null
    message.value = `Import completed: ${data.queued} newly queued, ${data.updated} updated; queue pending is now ${data.pending_unprocessed}`
    await getStats()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Import failed'
  } finally {
    importing.value = false
  }
}

const runPreview = async () => {
  error.value = ''
  message.value = ''
  result.value = null

  if (!folderPath.value.trim()) {
    error.value = 'Folder path is required'
    return
  }

  previewing.value = true
  try {
    preview.value = null
    preview.value = await previewExternalProviderImport(
      folderPath.value.trim(),
      scannerType.value,
      Math.max(1, Number(limit.value) || 500),
    )
    message.value = `Preview ready: source pending estimate ${preview.value.source_pending_estimate}, extractable this run ${preview.value.source_extractable_this_run}`
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Preview failed'
  } finally {
    previewing.value = false
  }
}

const formatImportTime = (value?: number) => {
  if (!value) return 'unknown'
  const date = new Date(value * 1000)
  if (Number.isNaN(date.getTime())) return 'unknown'
  return date.toLocaleString()
}

const runCleanup = async (dryRun: boolean) => {
  error.value = ''
  message.value = ''
  cleaning.value = true
  try {
    const safeOlderThan = Math.max(0, Number(cleanupOlderThanSeconds.value) || 0)
    const safeLimit = Math.max(1, Number(cleanupLimit.value) || 1000)
    let data: ExternalCleanupResult
    if (dryRun) {
      data = await cleanupExternalImportedSessions(scannerType.value, {
        dryRun: true,
        olderThanSeconds: safeOlderThan,
        limit: safeLimit,
      })
    } else {
      const previewData = await cleanupExternalImportedSessions(scannerType.value, {
        dryRun: true,
        olderThanSeconds: safeOlderThan,
        limit: safeLimit,
      })
      data = previewData.candidate_count > 0
        ? await cleanupExternalImportedSessions(scannerType.value, {
            dryRun: false,
            olderThanSeconds: safeOlderThan,
            limit: safeLimit,
            confirmToken: previewData.confirm_token,
          })
        : previewData
    }
    cleanupResult.value = data
    message.value = data.summary
    if (!dryRun && result.value) {
      if (
        typeof data.pending_unprocessed_after === 'number' &&
        typeof data.total_imported_after === 'number' &&
        typeof data.processed_sessions_after === 'number'
      ) {
        result.value.pending_unprocessed = data.pending_unprocessed_after
        result.value.total_imported_sessions = data.total_imported_after
        result.value.processed_sessions = data.processed_sessions_after
      } else {
        result.value.pending_unprocessed = Math.max(0, result.value.pending_unprocessed - (data.deleted ?? 0))
        result.value.processed_sessions = Math.max(
          0,
          result.value.total_imported_sessions - result.value.pending_unprocessed,
        )
      }

      if (preview.value) {
        preview.value.queue_pending_before_import = result.value.pending_unprocessed
      }

      await getStats()
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Cleanup failed'
  } finally {
    cleaning.value = false
    showCleanupPreviewConfirm.value = false
    showCleanupApplyConfirm.value = false
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
        <div class="flex items-center gap-2">
          <button class="btn-ghost" :disabled="previewing || importing || cleaning" @click="runPreview">
            <span v-if="previewing">Previewing...</span>
            <span v-else>Preview Scan</span>
          </button>
          <button class="btn-primary" :disabled="importing || previewing || cleaning" @click="runImport">
          <span v-if="importing">Importing...</span>
          <span v-else>Start Import</span>
          </button>
        </div>
      </div>
    </section>

    <section v-if="preview" class="card p-6 space-y-4">
      <h2 class="text-lg font-semibold text-white">Import Preview</h2>
      <div class="grid md:grid-cols-5 gap-4">
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Source Total</div>
          <div class="text-2xl font-mono text-white">{{ preview.source_total_sessions }}</div>
        </div>
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Source Pending Estimate</div>
          <div class="text-2xl font-mono text-amber-300">{{ preview.source_pending_estimate }}</div>
        </div>
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Extractable This Run</div>
          <div class="text-2xl font-mono text-neural-300">{{ preview.source_extractable_this_run }}</div>
        </div>
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Current Queue Pending</div>
          <div class="text-2xl font-mono text-white">{{ preview.queue_pending_before_import }}</div>
        </div>
        <div class="rounded-lg border border-space-800 p-4">
          <div class="text-space-400 text-sm">Scan Limit</div>
          <div class="text-2xl font-mono text-white">{{ preview.scan_limit }}</div>
        </div>
      </div>

      <div class="text-sm text-space-400">
        Source: {{ preview.folder_path }} · Scanner: {{ preview.scanner_type }}
      </div>
      <div v-if="preview.scan_limit_reached" class="text-sm text-amber-300">
        Scan limit reached in preview: increase Session Limit to extract more in one run.
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
          <div class="text-space-400 text-sm">Extracted This Run</div>
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
        Source: {{ result.folder_path }} · Scanner: {{ result.scanner_type }} · Queue Processed: {{ result.processed_sessions }} / {{ result.total_imported_sessions }}
      </div>
      <div class="text-sm text-space-500">
        Imported sessions are queued as unprocessed. Continue with your normal process/save workflow to distill memories.
      </div>

      <div class="rounded-lg border border-space-800 p-4 space-y-3">
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-white font-medium">Queue Cleanup</h3>
          <div class="flex items-center gap-2">
            <button class="btn-ghost" :disabled="cleaning" @click="showCleanupPreviewConfirm = true">
              Preview Cleanup
            </button>
            <button class="btn" :disabled="cleaning" @click="showCleanupApplyConfirm = true">
              <span v-if="cleaning">Running...</span>
              <span v-else>Apply Cleanup</span>
            </button>
          </div>
        </div>

        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-space-400 mb-1">Older Than Seconds (0 = no age filter)</label>
            <input v-model.number="cleanupOlderThanSeconds" type="number" min="0" class="input" />
          </div>
          <div>
            <label class="block text-sm text-space-400 mb-1">Cleanup Scan Limit</label>
            <input v-model.number="cleanupLimit" type="number" min="1" max="5000" class="input" />
          </div>
        </div>

        <div class="text-xs text-space-500">
          Preview first. Apply cleanup will permanently remove imported queue rows matching ghost/stale criteria.
        </div>
      </div>

      <div v-if="cleanupResult" class="rounded-lg border border-space-800 p-4 space-y-3">
        <div class="text-white font-medium">Cleanup Result</div>
        <div class="text-sm text-space-300">{{ cleanupResult.summary }}</div>
        <div class="grid md:grid-cols-3 gap-3 text-sm">
          <div class="rounded-lg border border-space-800 p-3">
            <div class="text-space-500">Scanned</div>
            <div class="text-white font-mono">{{ cleanupResult.scanned }}</div>
          </div>
          <div class="rounded-lg border border-space-800 p-3">
            <div class="text-space-500">Candidates</div>
            <div class="text-amber-300 font-mono">{{ cleanupResult.candidate_count }}</div>
          </div>
          <div class="rounded-lg border border-space-800 p-3">
            <div class="text-space-500">Deleted</div>
            <div class="text-neural-300 font-mono">{{ cleanupResult.deleted ?? 0 }}</div>
          </div>
        </div>

        <div v-if="cleanupResult.would_delete?.length" class="space-y-2">
          <div class="text-sm text-space-300">Preview Items ({{ cleanupResult.would_delete.length }})</div>
          <div class="max-h-56 overflow-y-auto space-y-2 pr-1">
            <div
              v-for="item in cleanupResult.would_delete"
              :key="`${item.agent}:${item.session_id}`"
              class="rounded-lg border border-space-800 p-3 text-xs"
            >
              <div class="font-mono text-space-300">{{ item.agent }}:{{ item.session_id }}</div>
              <div class="text-space-500">{{ formatImportTime(item.imported_at) }}</div>
              <div class="text-amber-300">{{ item.reasons.join(', ') }}</div>
            </div>
          </div>
        </div>
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

    <ConfirmDialog
      v-if="showCleanupPreviewConfirm"
      title="Preview Queue Cleanup"
      message="Run a dry-run cleanup to see which imported queue rows are ghost/stale candidates. No data will be deleted."
      confirm-text="Run Preview"
      type="warning"
      :loading="cleaning"
      @confirm="runCleanup(true)"
      @cancel="showCleanupPreviewConfirm = false"
    />

    <ConfirmDialog
      v-if="showCleanupApplyConfirm"
      title="Apply Queue Cleanup"
      message="This will permanently delete imported queue rows that match cleanup criteria. Run preview first if unsure."
      confirm-text="Delete Queue Rows"
      type="danger"
      :loading="cleaning"
      @confirm="runCleanup(false)"
      @cancel="showCleanupApplyConfirm = false"
    />
  </div>
</template>
