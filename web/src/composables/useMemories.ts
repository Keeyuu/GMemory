import { ref } from 'vue'
import type {
  BackupItem,
  BackupSettings,
  Memory,
  MemoryStats,
  NativeGhostCleanupResult,
  SearchResult,
} from '../types/memory'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

const memories = ref<Memory[]>([])
const stats = ref<MemoryStats | null>(null)

interface ListMemoriesOptions {
  limit?: number
  offset?: number
  importance?: 'high' | 'medium' | 'low'
  memoryType?: string
}

interface ListMemoriesResponse {
  results: Memory[]
  total: number
  has_more: boolean
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const body = await response.json()
      if (body?.detail) {
        message = String(body.detail)
      }
    } catch {
      // ignore JSON parse error
    }
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export function useMemories() {
  const getMemories = async (options: ListMemoriesOptions = {}): Promise<Memory[]> => {
    const params = new URLSearchParams({
      limit: String(options.limit ?? 200),
      offset: String(options.offset ?? 0),
    })

    if (options.importance) {
      params.set('importance', options.importance)
    }

    if (options.memoryType) {
      params.set('memory_type', options.memoryType)
    }

    const data = await request<ListMemoriesResponse>(`/memories?${params.toString()}`)
    memories.value = data.results
    return data.results
  }

  const getAllMemories = async (options: Omit<ListMemoriesOptions, 'offset' | 'limit'> = {}): Promise<Memory[]> => {
    const pageSize = 200
    let offset = 0
    let hasMore = true
    const all: Memory[] = []

    while (hasMore) {
      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String(offset),
      })

      if (options.importance) {
        params.set('importance', options.importance)
      }

      if (options.memoryType) {
        params.set('memory_type', options.memoryType)
      }

      const page = await request<ListMemoriesResponse>(`/memories?${params.toString()}`)
      all.push(...page.results)
      hasMore = page.has_more
      offset += pageSize
    }

    memories.value = all
    return all
  }

  const getRecentMemories = async (days = 7, limit = 10): Promise<Memory[]> => {
    const data = await request<{ memories: Memory[] }>(`/memories/recent?days=${days}&limit=${limit}`)
    return data.memories
  }

  const getStats = async (): Promise<MemoryStats> => {
    const data = await request<MemoryStats>('/stats')
    stats.value = data
    return data
  }

  const getMemory = async (id: string): Promise<Memory | undefined> => {
    try {
      return await request<Memory>(`/memories/${id}`)
    } catch {
      return undefined
    }
  }

  const addMemory = async (
    memory: Omit<Memory, 'id' | 'created_at' | 'updated_at'>,
  ): Promise<Memory> => {
    return request<Memory>('/memories', {
      method: 'POST',
      body: JSON.stringify({
        content: memory.content,
        preview: memory.preview,
        tags: memory.tags,
        importance: memory.importance,
        memory_type: memory.memory_type,
      }),
    })
  }

  const updateMemory = async (
    id: string,
    updates: Omit<Memory, 'id' | 'created_at' | 'updated_at'>,
  ): Promise<Memory> => {
    return request<Memory>(`/memories/${id}`, {
      method: 'PUT',
      body: JSON.stringify({
        content: updates.content,
        preview: updates.preview,
        tags: updates.tags,
        importance: updates.importance,
        memory_type: updates.memory_type,
      }),
    })
  }

  const deleteMemory = async (id: string): Promise<boolean> => {
    const result = await request<{ deleted: boolean }>(`/memories/${id}`, {
      method: 'DELETE',
    })
    return result.deleted
  }

  const searchMemories = async (query: string, mode = 'hybrid'): Promise<SearchResult> => {
    const params = new URLSearchParams({
      q: query,
      mode,
      limit: '20',
      compact: 'true',
      explain: 'true',
    })
    return request<SearchResult>(`/search?${params.toString()}`)
  }

  const getBackupSettings = async (): Promise<BackupSettings> => {
    return request<BackupSettings>('/backup/settings')
  }

  const updateBackupSettings = async (payload: Partial<BackupSettings>): Promise<{ updated: boolean; settings: BackupSettings }> => {
    return request<{ updated: boolean; settings: BackupSettings }>('/backup/settings', {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  const listBackups = async (): Promise<BackupItem[]> => {
    const data = await request<{ backups: BackupItem[] }>('/backup/list')
    return data.backups
  }

  const createBackup = async (reason = 'manual'): Promise<boolean> => {
    const data = await request<{ created: boolean }>('/backup/create', {
      method: 'POST',
      body: JSON.stringify({ reason }),
    })
    return data.created
  }

  const restoreBackup = async (backupId: string): Promise<boolean> => {
    const data = await request<{ restored: boolean }>('/backup/restore', {
      method: 'POST',
      body: JSON.stringify({ backup_id: backupId }),
    })
    return data.restored
  }

  const cleanupNativeGhostSessions = async (
    options: { scannerType?: string; dryRun?: boolean; limit?: number; confirmToken?: string } = {},
  ): Promise<NativeGhostCleanupResult> => {
    return request<NativeGhostCleanupResult>('/sessions/native/ghost-cleanup', {
      method: 'POST',
      body: JSON.stringify({
        scanner_type: options.scannerType ?? 'all',
        dry_run: options.dryRun ?? true,
        limit: Math.max(1, Number(options.limit ?? 5000) || 5000),
        confirm_token: options.confirmToken ?? null,
      }),
    })
  }

  return {
    memories,
    stats,
    getMemories,
    getAllMemories,
    getRecentMemories,
    getStats,
    getMemory,
    addMemory,
    updateMemory,
    deleteMemory,
    searchMemories,
    getBackupSettings,
    updateBackupSettings,
    listBackups,
    createBackup,
    restoreBackup,
    cleanupNativeGhostSessions,
  }
}
