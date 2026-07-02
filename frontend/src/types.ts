export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  toolCalls?: ToolCall[];
  toolResult?: {
    name: string;
    args?: string;
    result: string;
  };
  activity?: string;
  toolCollapsed?: boolean;
  timestamp: number;
}

export interface ToolCall {
  id: string;
  name: string;
  args: string;
  status: 'pending' | 'executing' | 'done';
  result?: string;
}

export interface Skill {
  name: string;
  description: string;
  enabled: boolean;
}

export interface Tool {
  name: string;
  description: string;
  enabled: boolean;
}

export interface Model {
  id: string;
  name: string;
  provider: string;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  workspace_id?: string | null;
}

export interface Status {
  token_usage: {
    input: number;
    output: number;
    calls: number;
  };
  message_count: number;
  skills: string[];
  current_session: string | null;
  current_model: string;
}

export interface AppConfig {
  model: string;
  enabled_tools: string[];
  enabled_skills: string[];
  available_models: Model[];
  // 高级配置
  temperature?: number;
  api_key?: string;
  base_url?: string;
  workspace_dir: string;
  permission_mode: PermissionMode;
  allowed_tools: string[];
}

export type PermissionMode = 'auto' | 'allowlist' | 'manual';

export interface Workspace {
  id: string;
  name: string;
  path: string;
  permission_mode: PermissionMode;
  allowed_tools: string[];
  is_active: boolean;
}

// 预设模型提供商
export interface ModelProvider {
  id: string;
  name: string;
  base_url: string;
  models: { id: string; name: string }[];
}

export const MODEL_PROVIDERS: ModelProvider[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    models: [
      { id: 'gpt-4o', name: 'GPT-4o' },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' },
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
    ],
  },
  {
    id: 'anthropic',
    name: 'Anthropic (Claude)',
    base_url: 'https://api.anthropic.com/v1',
    models: [
      { id: 'claude-opus-4-20250514', name: 'Claude Opus 4' },
      { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4' },
      { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet' },
      { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku' },
    ],
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    base_url: 'https://api.deepseek.com/v1',
    models: [
      { id: 'deepseek-chat', name: 'DeepSeek Chat' },
      { id: 'deepseek-reasoner', name: 'DeepSeek Reasoner' },
    ],
  },
  {
    id: 'moonshot',
    name: 'Moonshot (Kimi)',
    base_url: 'https://api.moonshot.cn/v1',
    models: [
      { id: 'moonshot-v1-8k', name: 'Moonshot V1 8K' },
      { id: 'moonshot-v1-32k', name: 'Moonshot V1 32K' },
      { id: 'moonshot-v1-128k', name: 'Moonshot V1 128K' },
    ],
  },
  {
    id: 'zhipu',
    name: '智谱 AI',
    base_url: 'https://open.bigmodel.cn/api/paas/v4',
    models: [
      { id: 'glm-4-plus', name: 'GLM-4 Plus' },
      { id: 'glm-4-air', name: 'GLM-4 Air' },
      { id: 'glm-4-flash', name: 'GLM-4 Flash' },
    ],
  },
  {
    id: 'qwen',
    name: '阿里云通义千问',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: [
      { id: 'qwen-max', name: 'Qwen Max' },
      { id: 'qwen-plus', name: 'Qwen Plus' },
      { id: 'qwen-turbo', name: 'Qwen Turbo' },
    ],
  },
  {
    id: 'custom',
    name: '自定义',
    base_url: '',
    models: [],
  },
];

export interface SSEEvent {
  event: string;
  data: string;
}

export interface UploadedFile {
  filename: string;
  content: string;
  size: number;
  type: string;
  id: string;  // 唯一标识
  uploadedAt: number;  // 上传时间戳
}

// ==================== 认证相关类型 ====================

export interface User {
  id: string;
  username: string;
  created_at: string;
  is_active: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  username: string;
}

export interface AuthStatus {
  available: boolean;
  user_manager: boolean;
  jwt_manager: boolean;
}
