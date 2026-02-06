import { ref } from 'vue'
import type { Memory, MemoryStats, SearchResult } from '../types/memory'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

const memories = ref<Memory[]>([])

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
  const getMemories = async (): Promise<Memory[]> => {
    const data = await request<{ results: Memory[] }>('/memories?limit=200&offset=0')
    memories.value = data.results
    return data.results
  }

  const getRecentMemories = async (days = 7, limit = 10): Promise<Memory[]> => {
    const data = await request<{ memories: Memory[] }>(`/memories/recent?days=${days}&limit=${limit}`)
    return data.memories
  }

  const getStats = async (): Promise<MemoryStats> => {
    return request<MemoryStats>('/stats')
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
        tags: memory.tags,
        importance: memory.importance,
      }),
    })
  }

  const updateMemory = async (id: string, updates: Partial<Memory>): Promise<Memory> => {
    return request<Memory>(`/memories/${id}`, {
      method: 'PUT',
      body: JSON.stringify({
        content: updates.content,
        tags: updates.tags,
        importance: updates.importance,
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
      compact: 'false',
      explain: 'true',
    })
    return request<SearchResult>(`/search?${params.toString()}`)
  }

  return {
    memories,
    getMemories,
    getRecentMemories,
    getStats,
    getMemory,
    addMemory,
    updateMemory,
    deleteMemory,
    searchMemories,
  }
}
