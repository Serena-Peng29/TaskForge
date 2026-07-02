import { useState } from 'react';
import { Session, Skill, Status, AppConfig, User } from '../types';
import { SessionList } from './SessionList';
import { ConfigModal } from './ConfigModal';
import { PromptModal } from './PromptModal';
import { MCPModal } from './MCPModal';
import {
  Zap,
  ChevronLeft,
  ChevronRight,
  Activity,
  Cpu,
  Wrench,
  BookOpen,
  FileText,
  Server,
  LogOut,
  User as UserIcon,
} from 'lucide-react';

interface SidebarProps {
  skills: Skill[];
  status: Status | null;
  sessions: Session[];
  currentSessionId: string | null;
  config: AppConfig | null;
  tools: { name: string; description: string; enabled: boolean }[];
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, title: string) => void;
  onUpdateConfig: (config: Partial<AppConfig>) => Promise<void>;
  user?: User | null;
  onLogout?: () => void;
}

export function Sidebar({
  skills,
  status,
  sessions,
  currentSessionId,
  config,
  tools,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onRenameSession,
  onUpdateConfig,
  user,
  onLogout,
}: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [modalType, setModalType] = useState<'model' | 'skills' | 'tools' | 'prompt' | 'mcp' | null>(null);

  return (
    <>
      {/* 侧边栏 */}
      <div
        className={`${
          isCollapsed ? 'w-0' : 'w-72'
        } bg-gray-900 border-r border-gray-700 flex flex-col transition-all duration-300 overflow-hidden flex-shrink-0`}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-500" />
            TaskForge
          </h2>
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* 会话列表 */}
        <div className="flex-1 overflow-hidden">
          <SessionList
            sessions={sessions}
            currentSessionId={currentSessionId}
            onSelectSession={onSelectSession}
            onCreateSession={onCreateSession}
            onDeleteSession={onDeleteSession}
            onRenameSession={onRenameSession}
          />
        </div>

        {/* 底部配置区域 */}
        <div className="border-t border-gray-700">
          {/* 模型配置入口 */}
          <button
            onClick={() => setModalType('model')}
            className="w-full flex items-center justify-between p-3 hover:bg-gray-800/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-400" />
              <span className="text-sm font-medium text-gray-300">模型</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 truncate max-w-[100px]">
                {config?.available_models.find((m) => m.id === config?.model)?.name || config?.model || '未设置'}
              </span>
              <ChevronRight className="w-4 h-4 text-gray-500" />
            </div>
          </button>

          {/* 技能配置入口 */}
          <button
            onClick={() => setModalType('skills')}
            className="w-full flex items-center justify-between p-3 hover:bg-gray-800/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-green-400" />
              <span className="text-sm font-medium text-gray-300">技能</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">
                {config?.enabled_skills.length || 0}/{skills.length}
              </span>
              <ChevronRight className="w-4 h-4 text-gray-500" />
            </div>
          </button>

          {/* 工具配置入口 */}
          <button
            onClick={() => setModalType('tools')}
            className="w-full flex items-center justify-between p-3 hover:bg-gray-800/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Wrench className="w-4 h-4 text-orange-400" />
              <span className="text-sm font-medium text-gray-300">工具</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">
                {config?.enabled_tools.length || 0}/{tools.length}
              </span>
              <ChevronRight className="w-4 h-4 text-gray-500" />
            </div>
          </button>

          {/* Prompt 配置入口 */}
          <button
            onClick={() => setModalType('prompt')}
            className="w-full flex items-center justify-between p-3 hover:bg-gray-800/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-medium text-gray-300">Prompt</span>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-500" />
          </button>

          {/* MCP 配置入口 */}
          <button
            onClick={() => setModalType('mcp')}
            className="w-full flex items-center justify-between p-3 hover:bg-gray-800/50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              <span className="text-sm font-medium text-gray-300">MCP</span>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-500" />
          </button>

          {/* Token 使用量 */}
          {status && (
            <div className="p-3 border-t border-gray-800">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Activity className="w-3.5 h-3.5" />
                <span>
                  {status.token_usage.input.toLocaleString()} 入 /
                  {status.token_usage.output.toLocaleString()} 出
                </span>
              </div>
            </div>
          )}

          {/* 用户信息 */}
          {user && onLogout && (
            <div className="p-3 border-t border-gray-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                    <UserIcon className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-sm text-gray-300 truncate max-w-[120px]">
                    {user.username}
                  </span>
                </div>
                <button
                  onClick={onLogout}
                  className="p-1.5 hover:bg-gray-800 rounded-lg transition-colors"
                  title="登出"
                >
                  <LogOut className="w-4 h-4 text-gray-400" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 折叠时的展开按钮 */}
      {isCollapsed && (
        <button
          onClick={() => setIsCollapsed(false)}
          className="absolute left-0 top-1/2 -translate-y-1/2 p-2 bg-gray-900 border border-gray-700 border-l-0 rounded-r-lg hover:bg-gray-800 transition-colors z-10"
        >
          <ChevronRight className="w-5 h-5 text-gray-400" />
        </button>
      )}

      {/* 配置弹窗 */}
      <ConfigModal
        isOpen={modalType !== null && modalType !== 'prompt' && modalType !== 'mcp'}
        onClose={() => setModalType(null)}
        type={(modalType === 'prompt' || modalType === 'mcp' ? 'model' : modalType) || 'model'}
        skills={skills}
        tools={tools}
        config={config}
        onUpdateConfig={onUpdateConfig}
      />

      {/* Prompt 弹窗 */}
      <PromptModal
        isOpen={modalType === 'prompt'}
        onClose={() => setModalType(null)}
      />

      {/* MCP 弹窗 */}
      <MCPModal
        isOpen={modalType === 'mcp'}
        onClose={() => setModalType(null)}
      />
    </>
  );
}