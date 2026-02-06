export interface ScoringBreakdown {
  vec_score: number      // 向量相似度贡献 (0-1)
  fts_score: number      // 关键词匹配贡献 (0-1)
  tag_score?: number     // 标签匹配贡献 (0-1, 可选)
  recency_score: number  // 时间衰减贡献 (0-1)
  hit_sources: ('vector' | 'fts' | 'tags')[]  // 命中来源
  base_score?: number    // 基础分数
  final_score?: number   // 最终分数
  age_days?: number      // 记忆年龄（天）
}

export interface Memory {
  id: string
  content: string
  memory_type?: string
  tags: string[]
  importance: 'high' | 'medium' | 'low'
  preview?: string
  score?: number
  scoring?: ScoringBreakdown  // 详细分数分解（搜索时使用 --explain）
  tokens?: number
  project_path?: string
  project_name?: string
  agent?: string
  created_at?: string
  updated_at?: string
  access_count?: number
  last_accessed_at?: string
}

export interface MemoryStatItem {
  id: string
  preview: string
  tags: string[]
  importance: 'high' | 'medium' | 'low'
  project_name?: string
  created_at?: string
  updated_at?: string
  access_count: number
  last_accessed_at?: string
}

export interface MemoryStats {
  total_memories: number
  processed_sessions: number
  unprocessed_sessions: number
  scan_runs: number
  scan_errors: number
  top_hot: MemoryStatItem[]
  top_cold: MemoryStatItem[]
  by_project: Record<string, number>
  by_importance: {
    high: number
    medium: number
    low: number
  }
}

export interface SearchResult {
  results: Memory[]
  total: number
  mode: string
}
