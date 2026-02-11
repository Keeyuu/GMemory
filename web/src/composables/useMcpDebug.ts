import { ref } from 'vue'

const MCP_PROTOCOL_VERSION = '2025-11-25'
const MCP_BASE_RAW = import.meta.env.VITE_MCP_BASE_URL || '/mcp/'
const MCP_BASE = MCP_BASE_RAW.endsWith('/') ? MCP_BASE_RAW : `${MCP_BASE_RAW}/`

const activeSessionId = ref<string | null>(null)

type JsonRecord = Record<string, unknown>

interface JsonRpcSuccess {
  jsonrpc?: string
  id?: number | string | null
  result?: unknown
}

interface JsonRpcError {
  jsonrpc?: string
  id?: number | string | null
  error?: {
    code?: number
    message?: string
    data?: unknown
  }
}

type JsonRpcResponse = JsonRpcSuccess & JsonRpcError

export interface McpDebugResult {
  ok: boolean
  sessionId: string | null
  data?: unknown
  error?: string
}

function readErrorMessage(body: unknown): string | null {
  if (!body || typeof body !== 'object') {
    return null
  }
  const maybeBody = body as { detail?: unknown; error?: unknown }
  if (typeof maybeBody.detail === 'string' && maybeBody.detail.trim()) {
    return maybeBody.detail
  }
  if (typeof maybeBody.error === 'string' && maybeBody.error.trim()) {
    return maybeBody.error
  }
  if (maybeBody.error && typeof maybeBody.error === 'object') {
    const nestedMessage = (maybeBody.error as { message?: unknown }).message
    if (typeof nestedMessage === 'string' && nestedMessage.trim()) {
      return nestedMessage
    }
  }
  return null
}

function extractSessionId(result: unknown): string | null {
  if (!result || typeof result !== 'object') {
    return null
  }

  const payload = result as JsonRecord
  const fromCamel = payload.sessionId
  if (typeof fromCamel === 'string' && fromCamel.trim()) {
    return fromCamel
  }

  const fromSnake = payload.session_id
  if (typeof fromSnake === 'string' && fromSnake.trim()) {
    return fromSnake
  }

  return null
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const rawText = await response.text()
  if (!rawText.trim()) {
    return null
  }

  try {
    return JSON.parse(rawText) as unknown
  } catch {
    const lines = rawText.split(/\r?\n/)
    const eventPayloads: string[] = []
    let currentDataLines: string[] = []

    for (const line of lines) {
      if (!line.trim()) {
        if (currentDataLines.length > 0) {
          eventPayloads.push(currentDataLines.join('\n'))
          currentDataLines = []
        }
        continue
      }

      if (line.startsWith('data:')) {
        currentDataLines.push(line.slice(5).trimStart())
      }
    }

    if (currentDataLines.length > 0) {
      eventPayloads.push(currentDataLines.join('\n'))
    }

    for (let i = eventPayloads.length - 1; i >= 0; i -= 1) {
      const payloadText = eventPayloads[i] ?? ''
      if (!payloadText.trim()) {
        continue
      }

      try {
        const parsed = JSON.parse(payloadText) as unknown
        if (parsed && typeof parsed === 'object') {
          return parsed
        }
      } catch {
        // keep trying older event payloads
      }
    }

    return rawText
  }
}

function buildHeaders(sessionId?: string): HeadersInit {
  let requestHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    Accept: 'application/json, text/event-stream',
    'MCP-Protocol-Version': MCP_PROTOCOL_VERSION,
  }

  if (sessionId) {
    requestHeaders = {
      ...requestHeaders,
      'mcp-session-id': sessionId,
    }
  }

  return requestHeaders
}

async function callMcp(method: string, sessionId?: string): Promise<McpDebugResult> {
  const requestHeaders = buildHeaders(sessionId)

  try {
    const response = await fetch(MCP_BASE, {
      method: 'POST',
      headers: requestHeaders,
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method,
        params: method === 'initialize'
          ? {
              protocolVersion: MCP_PROTOCOL_VERSION,
              capabilities: {},
              clientInfo: {
                name: 'gmemory-web-mcp-debug',
                version: '0.1.0',
              },
            }
          : {},
      }),
    })

    const responseBody = await parseResponseBody(response)
    const responseSessionId =
      response.headers.get('mcp-session-id') ||
      response.headers.get('Mcp-Session-Id')

    if (!response.ok) {
      const message = readErrorMessage(responseBody) || `HTTP ${response.status} ${response.statusText}`.trim()
      return {
        ok: false,
        error: message,
        sessionId: responseSessionId || activeSessionId.value,
      }
    }

    if (!responseBody || typeof responseBody !== 'object') {
      return {
        ok: false,
        error: 'MCP response is not valid JSON-RPC payload',
        sessionId: responseSessionId || activeSessionId.value,
      }
    }

    const payload = responseBody as JsonRpcResponse
    if (payload.error) {
      const message = payload.error.message || 'MCP request failed'
      return {
        ok: false,
        error: message,
        sessionId: responseSessionId || activeSessionId.value,
      }
    }

    const nextSessionId = responseSessionId || extractSessionId(payload.result) || activeSessionId.value
    activeSessionId.value = nextSessionId

    return {
      ok: true,
      sessionId: nextSessionId,
      data: payload.result ?? payload,
    }
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : 'Unknown MCP request error',
      sessionId: activeSessionId.value,
    }
  }
}

async function callMcpNotification(method: string, sessionId?: string): Promise<McpDebugResult> {
  const requestHeaders = buildHeaders(sessionId)

  try {
    const response = await fetch(MCP_BASE, {
      method: 'POST',
      headers: requestHeaders,
      body: JSON.stringify({
        jsonrpc: '2.0',
        method,
        params: {},
      }),
    })

    const responseBody = await parseResponseBody(response)
    const responseSessionId =
      response.headers.get('mcp-session-id') ||
      response.headers.get('Mcp-Session-Id')

    if (!response.ok) {
      const message = readErrorMessage(responseBody) || `HTTP ${response.status} ${response.statusText}`.trim()
      return {
        ok: false,
        error: message,
        sessionId: responseSessionId || activeSessionId.value,
      }
    }

    if (responseBody && typeof responseBody === 'object') {
      const payload = responseBody as JsonRpcResponse
      if (payload.error) {
        return {
          ok: false,
          error: payload.error.message || 'MCP notification failed',
          sessionId: responseSessionId || activeSessionId.value,
        }
      }
    }

    const nextSessionId = responseSessionId || sessionId || activeSessionId.value
    activeSessionId.value = nextSessionId

    return {
      ok: true,
      sessionId: nextSessionId,
      data: {
        method,
        notified: true,
      },
    }
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : 'Unknown MCP request error',
      sessionId: activeSessionId.value,
    }
  }
}

export function useMcpDebug() {
  const initialize = async (): Promise<McpDebugResult> => {
    const initResult = await callMcp('initialize')
    if (!initResult.ok) {
      return initResult
    }

    const initializedResult = await callMcpNotification('notifications/initialized', initResult.sessionId || undefined)
    if (!initializedResult.ok) {
      return {
        ...initializedResult,
        error: `Initialize succeeded but notifications/initialized failed: ${initializedResult.error || 'unknown error'}`,
        sessionId: initResult.sessionId,
      }
    }

    return {
      ...initResult,
      sessionId: initializedResult.sessionId || initResult.sessionId,
      data: {
        initialize: initResult.data,
        initialized: initializedResult.data,
      },
    }
  }

  const listTools = async (sessionId?: string): Promise<McpDebugResult> => {
    const resolvedSessionId = sessionId || activeSessionId.value || undefined
    return callMcp('tools/list', resolvedSessionId)
  }

  return {
    initialize,
    listTools,
    sessionId: activeSessionId,
    mcpBase: MCP_BASE,
  }
}
