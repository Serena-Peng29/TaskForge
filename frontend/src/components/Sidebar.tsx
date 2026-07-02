import { useState } from 'react';
import { Session, Skill, Status, AppConfig, User, Workspace } from '../types';
import { SessionList } from './SessionList';
import { ConfigModal } from './ConfigModal';
import { PromptModal } from './PromptModal';
import { MCPModal } from './MCPModal';
import {
  Zap,
  PanelLeftClose,
  ChevronDown,
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
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: (workspaceId?: string) => void;
  onSelectWorkspace: (workspaceId: string) => void;
  onAddWorkspace: () => void;
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
  workspaces,
  activeWorkspace,
  onSelectSession,
  onCreateSession,
  onSelectWorkspace,
  onAddWorkspace,
  onDeleteSession,
  onRenameSession,
  onUpdateConfig,
  user,
  onLogout,
}: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [modalType, setModalType] = useState<'model' | 'skills' | 'tools' | 'prompt' | 'mcp' | null>(null);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  return (
    <>
      {/* 侧边栏 */}
      <div
        className={`${
          isCollapsed ? 'w-0' : 'w-72'
        } bg-white/70 border-r border-pink-100/80 shadow-[18px_0_50px_rgba(236,72,153,0.08)] backdrop-blur-xl flex flex-col transition-all duration-300 overflow-hidden flex-shrink-0`}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-8">
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Zap className="w-6 h-6 fill-pink-500 text-pink-500" />
            TaskForge
          </h2>
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-2 hover:bg-pink-50 rounded-lg transition-colors"
            title="收起侧边栏"
          >
            <PanelLeftClose className="w-4 h-4 text-slate-500" />
          </button>
        </div>

        {/* 会话列表 */}
        <div className="flex-1 overflow-hidden">
          <SessionList
            sessions={sessions}
            workspaces={workspaces}
            activeWorkspace={activeWorkspace}
            currentSessionId={currentSessionId}
            onSelectWorkspace={onSelectWorkspace}
            onAddWorkspace={onAddWorkspace}
            onSelectSession={onSelectSession}
            onCreateSession={onCreateSession}
            onDeleteSession={onDeleteSession}
            onRenameSession={onRenameSession}
          />
        </div>

        <div className="border-t border-pink-100/80 bg-white/50">
          {user && onLogout ? (
            <>
              <button
                type="button"
                onClick={() => setIsUserMenuOpen(prev => !prev)}
                className="w-full px-6 py-5 hover:bg-pink-50/70 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-11 h-11 bg-pink-100 text-pink-600 rounded-full flex items-center justify-center font-bold text-lg">
                      {user.username.slice(0, 1).toUpperCase() || <UserIcon className="w-4 h-4" />}
                    </div>
                    <span className="text-base font-semibold text-slate-700 truncate">
                      {user.username}
                    </span>
                  </div>
                  <ChevronDown
                    className={`w-4 h-4 text-slate-400 transition-transform ${
                      isUserMenuOpen ? 'rotate-180' : ''
                    }`}
                  />
                </div>
              </button>

              {isUserMenuOpen && (
                <div className="border-t border-pink-100/80">
                  <SidebarSettings
                    skills={skills}
                    status={status}
                    config={config}
                    tools={tools}
                    onOpenModal={setModalType}
                    onLogout={onLogout}
                  />
                </div>
              )}
            </>
          ) : (
            <SidebarSettings
              skills={skills}
              status={status}
              config={config}
              tools={tools}
              onOpenModal={setModalType}
            />
          )}
        </div>
      </div>

      {/* 折叠时的展开按钮 */}
      {isCollapsed && (
        <button
          onClick={() => setIsCollapsed(false)}
          className="absolute left-0 top-1/2 -translate-y-1/2 p-2 bg-white border border-pink-100 border-l-0 rounded-r-lg hover:bg-pink-50 transition-colors z-10"
        >
          <ChevronRight className="w-5 h-5 text-slate-500" />
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

interface SidebarSettingsProps {
  skills: Skill[];
  status: Status | null;
  config: AppConfig | null;
  tools: { name: string; description: string; enabled: boolean }[];
  onOpenModal: (type: 'model' | 'skills' | 'tools' | 'prompt' | 'mcp') => void;
  onLogout?: () => void;
}

function SidebarSettings({
  skills,
  status,
  config,
  tools,
  onOpenModal,
  onLogout,
}: SidebarSettingsProps) {
  return (
    <>
      <button
        onClick={() => onOpenModal('model')}
        className="w-full flex items-center justify-between px-6 py-3 hover:bg-pink-50/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-pink-500" />
          <span className="text-sm font-medium text-slate-800">模型</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 truncate max-w-[100px]">
            {config?.available_models.find((m) => m.id === config?.model)?.name || config?.model || '未设置'}
          </span>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </div>
      </button>

      <button
        onClick={() => onOpenModal('skills')}
        className="w-full flex items-center justify-between px-6 py-3 hover:bg-pink-50/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-pink-500" />
          <span className="text-sm font-medium text-slate-800">技能</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">
            {config?.enabled_skills.length || 0}/{skills.length}
          </span>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </div>
      </button>

      <button
        onClick={() => onOpenModal('tools')}
        className="w-full flex items-center justify-between px-6 py-3 hover:bg-pink-50/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Wrench className="w-4 h-4 text-pink-500" />
          <span className="text-sm font-medium text-slate-800">工具</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">
            {config?.enabled_tools.length || 0}/{tools.length}
          </span>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </div>
      </button>

      <button
        onClick={() => onOpenModal('prompt')}
        className="w-full flex items-center justify-between px-6 py-3 hover:bg-pink-50/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-pink-500" />
          <span className="text-sm font-medium text-slate-800">Prompt</span>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-400" />
      </button>

      <button
        onClick={() => onOpenModal('mcp')}
        className="w-full flex items-center justify-between px-6 py-3 hover:bg-pink-50/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-pink-500" />
          <span className="text-sm font-medium text-slate-800">MCP</span>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-400" />
      </button>

      {status && (
        <div className="px-6 py-4 border-t border-pink-100/80">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Activity className="w-3.5 h-3.5" />
            <span>
              {status.token_usage.input.toLocaleString()} 入 /
              {status.token_usage.output.toLocaleString()} 出
            </span>
          </div>
        </div>
      )}

      {onLogout && (
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-6 py-3 border-t border-pink-100/80 text-sm text-slate-500 hover:bg-pink-50/80 hover:text-slate-800 transition-colors"
        >
          <LogOut className="w-4 h-4 text-slate-400" />
          退出登录
        </button>
      )}
    </>
  );
}
