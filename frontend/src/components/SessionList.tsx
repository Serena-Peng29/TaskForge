import { Session, Workspace } from '../types';
import { Check, ChevronDown, Edit2, Folder, MessageSquare, Plus, Search, Trash2, X } from 'lucide-react';
import { useMemo, useState } from 'react';

interface SessionListProps {
  sessions: Session[];
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  currentSessionId: string | null;
  onSelectWorkspace: (workspaceId: string) => void;
  onAddWorkspace: () => void;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: (workspaceId?: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, title: string) => void;
}

export function SessionList({
  sessions,
  workspaces,
  activeWorkspace,
  currentSessionId,
  onSelectWorkspace,
  onAddWorkspace,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onRenameSession,
}: SessionListProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(() => new Set());

  const projects = useMemo(() => {
    const knownIds = new Set(workspaces.map(workspace => workspace.id));
    const grouped = workspaces.map(workspace => ({
      workspace,
      sessions: sessions.filter(session => session.workspace_id === workspace.id),
    }));

    const orphanSessions = sessions.filter(session => !session.workspace_id || !knownIds.has(session.workspace_id));
    if (orphanSessions.length > 0) {
      grouped.push({
        workspace: {
          id: 'unassigned',
          name: '未归属会话',
          path: '',
          permission_mode: 'manual',
          allowed_tools: [],
          is_active: false,
        },
        sessions: orphanSessions,
      });
    }
    return grouped;
  }, [sessions, workspaces]);

  const handleStartEdit = (session: Session, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveEdit = (sessionId: string) => {
    if (editTitle.trim()) {
      onRenameSession(sessionId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  const handleDelete = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('确定要删除这个会话吗？')) {
      onDeleteSession(sessionId);
    }
  };

  const toggleProject = (workspaceId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedProjects(prev => {
      const next = new Set(prev);
      if (next.has(workspaceId)) {
        next.delete(workspaceId);
      } else {
        next.add(workspaceId);
      }
      return next;
    });
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return '今天';
    if (days === 1) return '昨天';
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="px-6 pb-6">
        <button
          onClick={() => onCreateSession(activeWorkspace?.id)}
          className="w-full flex items-center justify-center gap-2 px-3 py-3 text-sm font-semibold text-pink-600 bg-pink-50/60 hover:bg-pink-100/70 border border-pink-200 rounded-xl transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          新建会话
        </button>
      </div>

      <div className="px-6 pb-3 flex items-center justify-between text-sm font-semibold text-slate-500">
        <span>项目</span>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onAddWorkspace} className="hover:text-pink-500" title="添加项目">
            <Plus className="w-4 h-4" />
          </button>
          <Search className="w-4 h-4 text-slate-400" />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {projects.length === 0 ? (
          <div className="p-4 text-center text-slate-400 text-sm">暂无项目</div>
        ) : (
          <div className="space-y-2">
            {projects.map(({ workspace, sessions: projectSessions }) => {
              const isExpanded = expandedProjects.has(workspace.id) || workspace.is_active;
              return (
                <div key={workspace.id}>
                  <button
                    type="button"
                    onClick={() => workspace.id !== 'unassigned' && onSelectWorkspace(workspace.id)}
                    className={`group flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left transition-colors ${
                      workspace.is_active ? 'bg-pink-50 border border-pink-100' : 'border border-transparent hover:bg-white/70'
                    }`}
                  >
                    <Folder className={`h-4 w-4 flex-shrink-0 ${workspace.is_active ? 'text-pink-500' : 'text-slate-400'}`} />
                    <span className="min-w-0 flex-1 truncate text-sm font-semibold text-slate-800">{workspace.name}</span>
                    {workspace.id !== 'unassigned' && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onCreateSession(workspace.id);
                        }}
                        className="rounded-md p-1 text-slate-400 opacity-0 transition-opacity hover:bg-pink-100 hover:text-pink-600 group-hover:opacity-100"
                        title="在此项目中新建会话"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={(e) => toggleProject(workspace.id, e)}
                      className="rounded-md p-1 text-slate-400 hover:bg-pink-100"
                      title={isExpanded ? '收起会话' : '展开会话'}
                    >
                      <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </button>
                  </button>

                  {isExpanded && (
                    <div className="ml-7 mt-1 space-y-1">
                      {projectSessions.length === 0 ? (
                        <div className="px-3 py-2 text-sm text-slate-400">暂无对话</div>
                      ) : (
                        projectSessions.map((session) => (
                          <div
                            key={session.id}
                            onClick={() => editingId !== session.id && onSelectSession(session.id)}
                            className={`group/session rounded-lg px-3 py-2 cursor-pointer transition-all ${
                              session.id === currentSessionId
                                ? 'bg-pink-50/90 text-slate-900'
                                : 'hover:bg-white/70 text-slate-700'
                            }`}
                          >
                            <div className="flex items-start gap-2">
                              <MessageSquare className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${
                                session.id === currentSessionId ? 'text-pink-500' : 'text-slate-400'
                              }`} />
                              <div className="min-w-0 flex-1">
                                {editingId === session.id ? (
                                  <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                    <input
                                      type="text"
                                      value={editTitle}
                                      onChange={(e) => setEditTitle(e.target.value)}
                                      onKeyDown={(e) => {
                                        if (e.key === 'Enter') handleSaveEdit(session.id);
                                        if (e.key === 'Escape') setEditingId(null);
                                      }}
                                      className="min-w-0 flex-1 bg-white border border-pink-200 rounded px-2 py-1 text-sm text-slate-900 focus:outline-none focus:border-pink-400"
                                      autoFocus
                                    />
                                    <button onClick={() => handleSaveEdit(session.id)} className="p-1 hover:bg-pink-50 rounded">
                                      <Check className="w-4 h-4 text-green-500" />
                                    </button>
                                    <button onClick={() => setEditingId(null)} className="p-1 hover:bg-pink-50 rounded">
                                      <X className="w-4 h-4 text-red-500" />
                                    </button>
                                  </div>
                                ) : (
                                  <>
                                    <div className="flex items-center gap-2">
                                      <p className="min-w-0 flex-1 truncate text-sm font-medium">{session.title}</p>
                                      <span className="text-xs text-slate-400">{formatDate(session.updated_at)}</span>
                                    </div>
                                    {session.message_count > 0 && (
                                      <p className="mt-0.5 text-xs text-slate-400">{session.message_count} 条消息</p>
                                    )}
                                  </>
                                )}
                              </div>

                              {editingId !== session.id && (
                                <div className="flex items-center gap-1 opacity-0 group-hover/session:opacity-100 transition-opacity">
                                  <button onClick={(e) => handleStartEdit(session, e)} className="p-1 hover:bg-pink-50 rounded" title="重命名">
                                    <Edit2 className="w-3.5 h-3.5 text-slate-400" />
                                  </button>
                                  <button
                                    onClick={(e) => handleDelete(session.id, e)}
                                    className="p-1 hover:bg-pink-50 rounded"
                                    title="删除"
                                    disabled={session.id === currentSessionId}
                                  >
                                    <Trash2 className="w-3.5 h-3.5 text-slate-400 hover:text-red-400" />
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
