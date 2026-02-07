<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { BackupItem, BackupSettings } from '../types/memory'
import { useMemories } from '../composables/useMemories'

const {
  getBackupSettings,
  updateBackupSettings,
  listBackups,
  createBackup,
  restoreBackup,
} = useMemories()

const loading = ref(true)
const saving = ref(false)
const creating = ref(false)
const restoringId = ref<string | null>(null)
const message = ref<string>('')
const error = ref<string>('')

const settings = ref<BackupSettings>({
  enabled: true,
  path: '',
  max_backups: 20,
  auto_backup_time: '02:00',
  last_auto_backup_date: null,
})

const backups = ref<BackupItem[]>([])

const loadAll = async () => {
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const [loadedSettings, loadedBackups] = await Promise.all([
      getBackupSettings(),
      listBackups(),
    ])
    settings.value = loadedSettings
    backups.value = loadedBackups
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load backup settings'
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    const result = await updateBackupSettings(settings.value)
    settings.value = result.settings
    message.value = 'Backup settings saved'
    backups.value = await listBackups()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save backup settings'
  } finally {
    saving.value = false
  }
}

const runBackupNow = async () => {
  creating.value = true
  error.value = ''
  message.value = ''
  try {
    const ok = await createBackup('manual')
    if (ok) {
      message.value = 'Backup created successfully'
      backups.value = await listBackups()
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to create backup'
  } finally {
    creating.value = false
  }
}

const runRestore = async (backupId: string) => {
  restoringId.value = backupId
  error.value = ''
  message.value = ''
  try {
    const ok = await restoreBackup(backupId)
    if (ok) {
      message.value = `Restore completed: ${backupId}`
      backups.value = await listBackups()
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to restore backup'
  } finally {
    restoringId.value = null
  }
}

const formatDateTime = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

onMounted(loadAll)
</script>

<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <div class="flex items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-display font-semibold text-white mb-1">Backup & Restore</h1>
        <p class="text-space-400">Manage periodic backups, retention, and restore points</p>
      </div>
      <button class="btn-primary" :disabled="creating || loading" @click="runBackupNow">
        <span v-if="creating">Creating...</span>
        <span v-else>Create Backup Now</span>
      </button>
    </div>

    <div v-if="error" class="card p-4 border border-red-500/50 text-red-300">{{ error }}</div>
    <div v-if="message" class="card p-4 border border-neural-500/50 text-neural-300">{{ message }}</div>

    <section class="card p-6 space-y-4">
      <h2 class="text-lg font-semibold text-white">Settings</h2>
      <div v-if="loading" class="text-space-400">Loading settings...</div>
      <div v-else class="grid md:grid-cols-2 gap-4">
        <label class="flex items-center gap-3 text-space-200">
          <input v-model="settings.enabled" type="checkbox" class="accent-neural-400" />
          Enable automatic backups
        </label>

        <div>
          <label class="block text-sm text-space-400 mb-1">Auto Backup Time (HH:MM)</label>
          <input
            v-model="settings.auto_backup_time"
            type="text"
            class="input"
            placeholder="02:00"
          />
        </div>

        <div class="md:col-span-2">
          <label class="block text-sm text-space-400 mb-1">Backup Path</label>
          <input v-model="settings.path" type="text" class="input" placeholder="~/.gmemory/backups" />
        </div>

        <div>
          <label class="block text-sm text-space-400 mb-1">Max Backups</label>
          <input v-model.number="settings.max_backups" type="number" min="1" class="input" />
        </div>

        <div>
          <label class="block text-sm text-space-400 mb-1">Last Auto Backup</label>
          <div class="input bg-space-900/40 text-space-300">
            {{ settings.last_auto_backup_date || 'Not yet' }}
          </div>
        </div>
      </div>

      <div class="flex justify-end">
        <button class="btn-primary" :disabled="saving || loading" @click="saveSettings">
          <span v-if="saving">Saving...</span>
          <span v-else>Save Settings</span>
        </button>
      </div>
    </section>

    <section class="card p-6 space-y-4">
      <h2 class="text-lg font-semibold text-white">Backup History</h2>
      <div v-if="loading" class="text-space-400">Loading backups...</div>
      <div v-else-if="backups.length === 0" class="text-space-400">No backups found.</div>
      <div v-else class="space-y-3">
        <div
          v-for="item in backups"
          :key="item.id"
          class="rounded-lg border border-space-800 p-4 flex items-center justify-between gap-4"
        >
          <div class="space-y-1 min-w-0">
            <div class="text-white font-medium">{{ item.id }}</div>
            <div class="text-sm text-space-400">{{ formatDateTime(item.created_at_iso) }} · {{ item.reason }} · {{ formatSize(item.size_bytes) }}</div>
            <div class="text-xs text-space-500 truncate">{{ item.path }}</div>
          </div>
          <button
            class="btn-ghost"
            :disabled="restoringId === item.id"
            @click="runRestore(item.id)"
          >
            <span v-if="restoringId === item.id">Restoring...</span>
            <span v-else>Restore</span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
