import { useState, useEffect, useCallback } from 'react';
import { Memory } from '../types';
import * as api from '../api/client';
import {
  Brain,
  ChevronRight,
  ChevronLeft,
  X,
  Plus,
  Pencil,
  Trash2,
  Search,
  Check,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

interface MemoryPanelProps {
  refreshKey?: number; // 用于触发刷新
}

export function MemoryPanel({ refreshKey = 0 }: MemoryPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 编辑状态
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');

  // 添加状态
  const [isAdding, setIsAdding] = useState(false);
  const [newContent, setNewContent] = useState('');

  // 搜索状态
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const loadMemories = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.getMemories();
      // 确保 memories 是数组
      const memoriesList = Array.isArray(result.memories) ? result.memories : [];
      setMemories(memoriesList);
    } catch (err: any) {
      // 503 表示服务不可用
      if (err.message?.includes('503') || err.message?.includes('not available')) {
        setError('长期记忆服务不可用，请检查 Qdrant 是否启动');
      } else {
        setError(err.message || '加载记忆失败');
      }
      setMemories([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isCollapsed) {
      loadMemories();
    }
  }, [isCollapsed, loadMemories]);

  // 监听 refreshKey 变化，自动刷新
  useEffect(() => {
    if (!isCollapsed && refreshKey > 0) {
      loadMemories();
    }
  }, [refreshKey, isCollapsed, loadMemories]);

  const handleAddMemory = async () => {
    if (!newContent.trim()) return;

    setIsLoading(true);
    try {
      await api.addMemory(newContent);
      setNewContent('');
      setIsAdding(false);
      await loadMemories();
    } catch (err: any) {
      setError(err.message || '添加记忆失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateMemory = async () => {
    if (!selectedMemory || !editContent.trim()) return;

    setIsLoading(true);
    try {
      await api.updateMemory(selectedMemory.id, editContent);
      setIsEditing(false);
      setSelectedMemory({ ...selectedMemory, memory: editContent });
      await loadMemories();
    } catch (err: any) {
      setError(err.message || '更新记忆失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteMemory = async (memoryId: string) => {
    if (!confirm('确定要删除这条记忆吗？')) return;

    setIsLoading(true);
    try {
      await api.deleteMemory(memoryId);
      if (selectedMemory?.id === memoryId) {
        setSelectedMemory(null);
      }
      await loadMemories();
    } catch (err: any) {
      setError(err.message || '删除记忆失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadMemories();
      return;
    }

    setIsSearching(true);
    setIsLoading(true);
    try {
      const result = await api.searchMemories(searchQuery);
      // 确保 results 是数组
      const resultsList = Array.isArray(result.results) ? result.results : [];
      setMemories(resultsList);
    } catch (err: any) {
      setError(err.message || '搜索记忆失败');
      setMemories([]);
    } finally {
      setIsLoading(false);
      setIsSearching(false);
    }
  };

  const startEdit = (memory: Memory) => {
    setSelectedMemory(memory);
    setEditContent(memory.memory);
    setIsEditing(true);
    setIsAdding(false);
  };

  const startAdd = () => {
    setIsAdding(true);
    setIsEditing(false);
    setNewContent('');
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setIsAdding(false);
    setEditContent('');
    setNewContent('');
  };

  return (
    <>
      {/* 展开按钮（当折叠时显示） */}
      {isCollapsed && (
        <button
          onClick={() => setIsCollapsed(false)}
          className="absolute right-0 top-1/2 -translate-y-1/2 p-2 bg-gray-900 border border-gray-700 border-r-0 rounded-l-lg hover:bg-gray-800 transition-colors z-10"
          title="查看记忆"
        >
          <ChevronLeft className="w-5 h-5 text-gray-400" />
        </button>
      )}

      {/* 记忆面板 */}
      <div
        className={`${
          isCollapsed ? 'w-0' : 'w-80'
        } bg-gray-900 border-l border-gray-700 flex flex-col transition-all duration-300 overflow-hidden flex-shrink-0`}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-3 border-b border-gray-700">
          <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            长期记忆 ({memories.length})
          </h3>
          <div className="flex items-center gap-1">
            <button
              onClick={loadMemories}
              disabled={isLoading}
              className="p-1 text-gray-400 hover:text-gray-200 transition-colors disabled:opacity-50"
              title="刷新"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => setIsCollapsed(true)}
              className="p-1 hover:bg-gray-800 rounded transition-colors"
            >
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>

        {/* 搜索栏 */}
        <div className="p-2 border-b border-gray-700">
          <div className="flex gap-1">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="搜索记忆..."
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-200 focus:outline-none focus:border-purple-500"
            />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="p-1 text-gray-400 hover:text-purple-400 transition-colors disabled:opacity-50"
            >
              <Search className="w-4 h-4" />
            </button>
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  loadMemories();
                }}
                className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="p-2 bg-red-900/30 border-b border-red-800 flex items-center gap-2 text-sm text-red-300">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* 添加按钮 */}
        <div className="p-2 border-b border-gray-700">
          <button
            onClick={startAdd}
            className="w-full flex items-center justify-center gap-2 py-1.5 text-sm text-purple-400 hover:bg-purple-900/20 rounded transition-colors"
          >
            <Plus className="w-4 h-4" />
            添加记忆
          </button>
        </div>

        {/* 添加表单 */}
        {isAdding && (
          <div className="p-2 border-b border-gray-700 bg-gray-800/50">
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="输入要记忆的内容..."
              className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-sm text-gray-200 focus:outline-none focus:border-purple-500 resize-none h-20"
            />
            <div className="flex justify-end gap-2 mt-2">
              <button
                onClick={cancelEdit}
                className="px-3 py-1 text-sm text-gray-400 hover:text-gray-200 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleAddMemory}
                disabled={isLoading || !newContent.trim()}
                className="flex items-center gap-1 px-3 py-1 text-sm text-white bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 rounded transition-colors"
              >
                <Check className="w-4 h-4" />
                保存
              </button>
            </div>
          </div>
        )}

        {/* 记忆列表 */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-gray-500">
              加载中...
            </div>
          ) : memories.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-gray-500">
              <Brain className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-sm">暂无记忆</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-800">
              {memories.map((memory) => (
                <div
                  key={memory.id}
                  onClick={() => {
                    setSelectedMemory(memory);
                    setIsEditing(false);
                    setIsAdding(false);
                  }}
                  className={`p-3 cursor-pointer transition-colors ${
                    selectedMemory?.id === memory.id
                      ? 'bg-gray-800 border-l-2 border-purple-500'
                      : 'hover:bg-gray-800/50 border-l-2 border-transparent'
                  }`}
                >
                  <p className="text-sm text-gray-300 line-clamp-3">{memory.memory}</p>
                  {memory.created_at && (
                    <p className="text-xs text-gray-500 mt-1">{memory.created_at}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 选中的记忆详情/编辑 */}
        {selectedMemory && !isEditing && (
          <div className="border-t border-gray-700 p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-500">记忆详情</span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => startEdit(selectedMemory)}
                  className="p-1 text-gray-400 hover:text-blue-400 transition-colors"
                  title="编辑"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDeleteMemory(selectedMemory.id)}
                  className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                  title="删除"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
            <p className="text-sm text-gray-300 whitespace-pre-wrap">{selectedMemory.memory}</p>
          </div>
        )}

        {/* 编辑表单 */}
        {selectedMemory && isEditing && (
          <div className="border-t border-gray-700 p-3 bg-gray-800/50">
            <div className="text-xs text-gray-500 mb-2">编辑记忆</div>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-sm text-gray-200 focus:outline-none focus:border-purple-500 resize-none h-24"
            />
            <div className="flex justify-end gap-2 mt-2">
              <button
                onClick={cancelEdit}
                className="px-3 py-1 text-sm text-gray-400 hover:text-gray-200 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleUpdateMemory}
                disabled={isLoading || !editContent.trim()}
                className="flex items-center gap-1 px-3 py-1 text-sm text-white bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 rounded transition-colors"
              >
                <Check className="w-4 h-4" />
                更新
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}