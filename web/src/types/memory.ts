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

export interface BackupItem {
  id: string
  reason: string
  created_at: number
  created_at_iso: string
  path: string
  db_file: string
  config_file: string
  source_db: string
  size_bytes: number
}

export interface BackupSettings {
  enabled: boolean
  path: string
  max_backups: number
  auto_backup_time: string
  last_auto_backup_date?: string | null
}

export interface ExternalImportResult {
  queued: number
  updated: number
  failed: number
  imported?: number
  total_sessions: number
  source_total_sessions: number
  source_pending_estimate?: number
  source_extractable_this_run?: number
  scan_limit?: number
  scan_limit_reached?: boolean
  queue_pending_before_import?: number
  scanner_type: string
  folder_path: string
  pending_unprocessed: number
  processed_sessions: number
  total_imported_sessions: number
  errors: Array<{ session_id: string; error: string }>
}

export interface ExternalImportPreview {
  scanner_type: string
  folder_path: string
  source_total_sessions: number
  source_pending_estimate: number
  source_extractable_this_run: number
  scan_limit: number
  scan_limit_reached: boolean
  queue_pending_before_import: number
}

export interface ExternalCleanupCandidate {
  session_id: string
  agent: string
  source_scanner: string
  imported_at?: number
  reasons: string[]
}

export interface ExternalCleanupResult {
  dry_run: boolean
  scanner_type: string
  scanned: number
  candidate_count: number
  confirm_token?: string
  deleted?: number
  would_delete?: ExternalCleanupCandidate[]
  failed?: Array<{ session_id: string; error: string }>
  by_reason: Record<string, number>
  queue_pending_before_cleanup?: number
  total_imported_before_cleanup?: number
  pending_unprocessed_after?: number
  total_imported_after?: number
  processed_sessions_after?: number
  summary: string
}

export interface NativeGhostCleanupCandidate {
  session_id: string
  agent: string
  reason: string
}

export interface NativeGhostCleanupResult {
  dry_run: boolean
  scanner_type: string
  scanned_processed_records: number
  scanned_native_files: number
  candidate_count: number
  confirm_token?: string
  deleted?: number
  failed?: Array<{ scanner: string; count: number; error: string }>
  would_delete?: NativeGhostCleanupCandidate[]
  by_scanner: Record<string, number>
  parse_errors: number
  limit_reached: boolean
  details: Array<{
    scanner: string
    supported: boolean
    reason?: string
    native_files?: number
    processed_records?: number
    candidate_count?: number
    parse_errors?: number
  }>
  summary: string
}
