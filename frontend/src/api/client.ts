import { Skill, Tool, Session, Status, AppConfig, Message, UploadedFile, User, TokenResponse, AuthStatus, Workspace, PermissionMode } from '../types';

const API_BASE = '/api';

// ==================== 认证管理 ====================

let authToken: string | null = localStorage.getItem('auth_token');

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
}

export function getAuthToken(): string | null {
  return authToken;
}

function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
}

async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = { ...getAuthHeaders(), ...(options.headers as Record<string, string> || {}) };
  return fetch(url, { ...options, headers });
}

export async function getAuthStatus(): Promise<AuthStatus> {
  const response = await fetch(`${API_BASE}/auth/status`);
  if (!response.ok) throw new Error('Failed to fetch auth status');
  return response.json();
}

export async function register(username: string, password: string): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }
  return response.json();
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }
  const data = await response.json();
  setAuthToken(data.access_token);
  return data;
}

export async function getCurrentUser(): Promise<User> {
  const response = await authFetch(`${API_BASE}/auth/me`);
  if (!response.ok) throw new Error('Failed to get current user');
  return response.json();
}

export function logout(): void {
  setAuthToken(null);
}

// ==================== 基础 API ====================

export async function getSkills(): Promise<Skill[]> {
  const response = await authFetch(`${API_BASE}/skills`);
  if (!response.ok) throw new Error('Failed to fetch skills');
  return response.json();
}

export async function getStatus(): Promise<Status> {
  const response = await authFetch(`${API_BASE}/status`);
  if (!response.ok) throw new Error('Failed to fetch status');
  return response.json();
}

export async function getHistory(): Promise<{ messages: Message[]; count: number }> {
  const response = await authFetch(`${API_BASE}/history`);
  if (!response.ok) throw new Error('Failed to fetch history');
  return response.json();
}

export async function clearHistory(): Promise<void> {
  const response = await authFetch(`${API_BASE}/clear`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to clear history');
}

// ==================== 文件上传 API ====================

export async function uploadFile(file: globalThis.File): Promise<UploadedFile> {
  const formData = new FormData();
  formData.append('file', file);

  const headers: HeadersInit = {};
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to upload file');
  }

  return response.json();
}

// ==================== 会话管理 API ====================

export async function getSessions(): Promise<Session[]> {
  const response = await authFetch(`${API_BASE}/sessions`);
  if (!response.ok) throw new Error('Failed to fetch sessions');
  return response.json();
}

export async function getSession(sessionId: string): Promise<{ messages: Message[] }> {
  const response = await authFetch(`${API_BASE}/sessions/${sessionId}`);
  if (!response.ok) throw new Error('Failed to fetch session');
  return response.json();
}

export async function createSession(title?: string, workspaceId?: string): Promise<Session> {
  const response = await authFetch(`${API_BASE}/sessions/new`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, workspace_id: workspaceId }),
  });
  if (!response.ok) throw new Error('Failed to create session');
  return response.json();
}

export async function switchSession(sessionId: string): Promise<{ status: string; message_count: number }> {
  const response = await authFetch(`${API_BASE}/sessions/${sessionId}/switch`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to switch session');
  return response.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete session');
}

export async function renameSession(sessionId: string, title: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) throw new Error('Failed to rename session');
}

export async function moveSession(sessionId: string, workspaceId: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_id: workspaceId }),
  });
  if (!response.ok) throw new Error('Failed to move session');
}

export async function loadLastSession(): Promise<{ status: string; session_id?: string; message_count?: number }> {
  const response = await authFetch(`${API_BASE}/load`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to load last session');
  return response.json();
}

// ==================== 工具管理 API ====================

export async function getTools(): Promise<Tool[]> {
  const response = await authFetch(`${API_BASE}/tools`);
  if (!response.ok) throw new Error('Failed to fetch tools');
  return response.json();
}

// ==================== 配置管理 API ====================

export async function getConfig(): Promise<AppConfig> {
  const response = await authFetch(`${API_BASE}/config`);
  if (!response.ok) throw new Error('Failed to fetch config');
  return response.json();
}

export async function updateConfig(config: Partial<AppConfig>): Promise<void> {
  const response = await authFetch(`${API_BASE}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!response.ok) throw new Error('Failed to update config');
}

// ==================== 工作区 API ====================

export async function getWorkspaces(): Promise<Workspace[]> {
  const response = await authFetch(`${API_BASE}/workspaces`);
  if (!response.ok) throw new Error('Failed to fetch workspaces');
  return response.json();
}

export async function addWorkspace(path: string, permissionMode: PermissionMode = 'manual'): Promise<Workspace> {
  const response = await authFetch(`${API_BASE}/workspaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, permission_mode: permissionMode }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to add workspace');
  }
  return response.json();
}

export async function pickWorkspaceDirectory(): Promise<{ path: string | null; cancelled: boolean }> {
  const response = await authFetch(`${API_BASE}/workspaces/pick-directory`, { method: 'POST' });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to pick workspace directory');
  }
  return response.json();
}

export async function activateWorkspace(workspaceId: string): Promise<Workspace> {
  const response = await authFetch(`${API_BASE}/workspaces/${workspaceId}/activate`, { method: 'POST' });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to activate workspace');
  }
  return response.json();
}

export async function updateWorkspace(
  workspaceId: string,
  update: { name?: string; permission_mode?: PermissionMode; allowed_tools?: string[] }
): Promise<Workspace> {
  const response = await authFetch(`${API_BASE}/workspaces/${workspaceId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update workspace');
  }
  return response.json();
}

// ==================== Prompt 管理 API ====================

export interface PromptConfig {
  default_prompt: string;
  custom_prompt: string | null;
  current_prompt: string;
}

export async function getPrompt(): Promise<PromptConfig> {
  const response = await authFetch(`${API_BASE}/prompt`);
  if (!response.ok) throw new Error('Failed to fetch prompt');
  return response.json();
}

export async function updatePrompt(customPrompt: string | null): Promise<PromptConfig> {
  const response = await authFetch(`${API_BASE}/prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ custom_prompt: customPrompt }),
  });
  if (!response.ok) throw new Error('Failed to update prompt');
  return response.json();
}

export async function resetPrompt(): Promise<PromptConfig> {
  const response = await authFetch(`${API_BASE}/prompt/reset`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to reset prompt');
  return response.json();
}

// ==================== MCP 管理 API ====================

export interface MCPServer {
  name: string;
  status: string;
  error: string | null;
  tools: string[];
  command: string;
  env: Record<string, string>;
}

export interface MCPStatus {
  available: boolean;
  servers_count: number;
  tools_count: number;
  message?: string;
}

export async function getMCPStatus(): Promise<MCPStatus> {
  const response = await authFetch(`${API_BASE}/mcp/status`);
  if (!response.ok) throw new Error('Failed to fetch MCP status');
  return response.json();
}

export async function getMCPServers(): Promise<MCPServer[]> {
  const response = await authFetch(`${API_BASE}/mcp/servers`);
  if (!response.ok) throw new Error('Failed to fetch MCP servers');
  return response.json();
}

export async function addMCPServer(name: string, command: string, env: Record<string, string> = {}): Promise<{ status: string; name: string }> {
  const response = await authFetch(`${API_BASE}/mcp/servers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, command, env }),
  });
  if (!response.ok) throw new Error('Failed to add MCP server');
  return response.json();
}

export async function deleteMCPServer(name: string): Promise<void> {
  const response = await authFetch(`${API_BASE}/mcp/servers/${encodeURIComponent(name)}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete MCP server');
}

export async function connectMCPServer(name: string): Promise<{ status: string; name: string; error: string | null; tools: string[] }> {
  const response = await authFetch(`${API_BASE}/mcp/servers/${encodeURIComponent(name)}/connect`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to connect MCP server');
  return response.json();
}

export async function disconnectMCPServer(name: string): Promise<{ status: string; name: string }> {
  const response = await authFetch(`${API_BASE}/mcp/servers/${encodeURIComponent(name)}/disconnect`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to disconnect MCP server');
  return response.json();
}

export async function getMCPTools(): Promise<{ tools: any[]; count: number }> {
  const response = await authFetch(`${API_BASE}/mcp/tools`);
  if (!response.ok) throw new Error('Failed to fetch MCP tools');
  return response.json();
}

export async function importMCPConfig(config: Record<string, any>): Promise<{
  status: string;
  servers: Record<string, string>;
  errors: Record<string, string>;
}> {
  const response = await authFetch(`${API_BASE}/mcp/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config }),
  });
  if (!response.ok) throw new Error('Failed to import MCP config');
  return response.json();
}

// ==================== 聊天 API ====================

export interface ChatCallbacks {
  onContent: (content: string) => void;
  onToolStart: (index: number, id: string) => void;
  onToolName: (index: number, name: string) => void;
  onToolArgs: (index: number, args: string) => void;
  onToolExecute: (name: string, args: Record<string, unknown>) => void;
  onToolResult: (name: string, result: string, id?: string) => void;
  onDone: (content: string) => void;
  onError: (error: string) => void;
}

export async function sendChatMessage(
  message: string,
  callbacks: ChatCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, stream: true }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No reader available');

  const decoder = new TextDecoder();
  let buffer = '';
  let fullContent = '';
  let currentEvent = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine) {
          // Empty line signals end of event, reset currentEvent
          currentEvent = '';
          continue;
        }

        if (trimmedLine.startsWith('event: ')) {
          // SSE event type line
          currentEvent = trimmedLine.slice(7);
        } else if (trimmedLine.startsWith('data: ')) {
          // SSE data line
          const data = trimmedLine.slice(6);
          if (data === '[DONE]') continue;

          // Use currentEvent if set, otherwise try to extract from data
          let eventName = currentEvent;
          let eventData: any;

          try {
            eventData = JSON.parse(data);
            // If event name not from event: line, check if it's in the data
            if (!eventName && eventData.event) {
              eventName = eventData.event;
              eventData = JSON.parse(eventData.data || '{}');
            }
          } catch {
            continue;
          }

          if (eventName) {
            handleSSEEvent(eventName, eventData, callbacks, fullContent);

            if (eventName === 'content') {
              fullContent += eventData.content || '';
            } else if (eventName === 'done') {
              fullContent = eventData.content || '';
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function handleSSEEvent(
  eventName: string,
  data: Record<string, unknown>,
  callbacks: ChatCallbacks,
  _currentContent: string
): void {
  switch (eventName) {
    case 'content':
      callbacks.onContent(data.content as string);
      break;
    case 'tool_start':
      callbacks.onToolStart(data.index as number, data.id as string);
      break;
    case 'tool_name':
      callbacks.onToolName(data.index as number, data.name as string);
      break;
    case 'tool_args':
      callbacks.onToolArgs(data.index as number, data.args as string);
      break;
    case 'tool_execute':
      callbacks.onToolExecute(data.name as string, data.args as Record<string, unknown>);
      break;
    case 'tool_result':
      callbacks.onToolResult(data.name as string, data.result as string, data.id as string | undefined);
      break;
    case 'done':
      callbacks.onDone(data.content as string);
      break;
    case 'error':
      callbacks.onError(data.error as string);
      break;
  }
}
