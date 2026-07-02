import { useState, KeyboardEvent, useRef, DragEvent, ChangeEvent } from 'react';
import { ChevronDown, Folder, Paperclip, Plus, Send, ShieldCheck, Square } from 'lucide-react';
import { PermissionMode, UploadedFile, Workspace } from '../types';
import * as api from '../api/client';

interface InputBarProps {
  onSend: (message: string, files: UploadedFile[]) => void;
  onStop: () => void;
  isStreaming: boolean;
  disabled?: boolean;
  uploadedFiles: UploadedFile[];
  onFilesChange: (files: UploadedFile[]) => void;
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  onAddWorkspace: (path: string) => Promise<void>;
  onSelectWorkspace: (workspaceId: string) => Promise<void>;
  onPermissionChange: (mode: PermissionMode) => Promise<void>;
}

const PERMISSION_LABELS: Record<PermissionMode, string> = {
  manual: '手动批准',
  allowlist: '白名单',
  auto: '自动批准',
};

export function InputBar({
  onSend,
  onStop,
  isStreaming,
  disabled,
  uploadedFiles,
  onFilesChange,
  workspaces,
  activeWorkspace,
  onAddWorkspace,
  onSelectWorkspace,
  onPermissionChange,
}: InputBarProps) {
  const [input, setInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isAddingWorkspace, setIsAddingWorkspace] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const generateFileId = () => `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const handleSubmit = () => {
    const trimmed = input.trim();
    if ((!trimmed && uploadedFiles.length === 0) || disabled) return;

    // 不再在消息中嵌入文件内容，而是传递文件对象
    onSend(trimmed, uploadedFiles);
    setInput('');
    // 不清空文件，让用户可以选择保留或手动清空
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    await uploadFiles(Array.from(files));
    e.target.value = '';
  };

  const uploadFiles = async (files: globalThis.File[]) => {
    setIsUploading(true);
    try {
      const newFiles: UploadedFile[] = [];
      for (const file of files) {
        try {
          const uploaded = await api.uploadFile(file);
          newFiles.push({
            ...uploaded,
            id: generateFileId(),
            uploadedAt: Date.now(),
          });
        } catch (error) {
          console.error(`Failed to upload ${file.name}:`, error);
          alert(`Failed to upload ${file.name}: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      }
      onFilesChange([...uploadedFiles, ...newFiles]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await uploadFiles(files);
    }
  };

  const handleAddWorkspace = async () => {
    setIsAddingWorkspace(true);
    try {
      const picked = await api.pickWorkspaceDirectory();
      if (!picked.path || picked.cancelled) return;
      const path = picked.path;
      await onAddWorkspace(path);
    } catch (error) {
      alert(error instanceof Error ? error.message : '添加工作区失败');
    } finally {
      setIsAddingWorkspace(false);
    }
  };

  const activeMode = activeWorkspace?.permission_mode || 'manual';
  const activePath = activeWorkspace?.path || '点击设置工作目录';

  return (
    <div
      className={`border-t border-gray-700 bg-gray-900 p-4 transition-colors ${isDragging ? 'bg-blue-900/20' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drop zone indicator */}
      {isDragging && (
        <div className="max-w-4xl mx-auto mb-3 p-4 border-2 border-dashed border-blue-500 rounded-lg bg-blue-900/30 text-center">
          <span className="text-blue-400">拖放文件到这里上传</span>
        </div>
      )}

      <div className="max-w-4xl mx-auto flex gap-3">
        {/* File upload button */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
          accept=".txt,.py,.js,.ts,.tsx,.jsx,.json,.yaml,.yml,.md,.html,.css,.xml,.csv,.sh,.bash,.sql,.c,.cpp,.h,.hpp,.java,.go,.rs,.rb,.php,.swift,.kt,.scala,.lua,.r,.m,.toml,.ini,.env,.docx"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isUploading}
          className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-gray-300 rounded-lg flex items-center justify-center transition-colors"
          title="附加文件"
        >
          <Paperclip className={`w-5 h-5 ${isUploading ? 'animate-pulse' : ''}`} />
        </button>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={uploadedFiles.length > 0 ? `${uploadedFiles.length} 个文件已上传，输入消息...` : "输入消息... (Shift+Enter 换行)"}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
          rows={1}
          style={{ minHeight: '48px', maxHeight: '200px' }}
          disabled={disabled}
        />

        {isStreaming ? (
          <button
            onClick={onStop}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <Square className="w-4 h-4" />
            停止
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={(!input.trim() && uploadedFiles.length === 0) || disabled}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <Send className="w-4 h-4" />
            发送
          </button>
        )}
      </div>

      <div className="max-w-4xl mx-auto mt-3 flex flex-wrap items-center gap-2 text-sm text-gray-300">
        <div className="relative">
          <Folder className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          <select
            value={activeWorkspace?.id || ''}
            onChange={(e) => e.target.value ? onSelectWorkspace(e.target.value) : undefined}
            className="appearance-none bg-gray-800 border border-gray-700 rounded-md pl-9 pr-8 py-2 max-w-[360px] text-gray-100 focus:outline-none focus:border-blue-500"
            title={activePath}
          >
            {!activeWorkspace && <option value="">点击设置工作目录</option>}
            {workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>
                {workspace.name} · {workspace.path}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>

        <button
          type="button"
          onClick={handleAddWorkspace}
          disabled={disabled || isAddingWorkspace}
          className="h-9 px-3 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-800 disabled:text-gray-600 border border-gray-700 rounded-md flex items-center gap-2 transition-colors"
          title="添加工作区"
        >
          <Plus className="w-4 h-4" />
          添加工作区
        </button>

        <div className="relative">
          <ShieldCheck className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          <select
            value={activeMode}
            onChange={(e) => onPermissionChange(e.target.value as PermissionMode)}
            disabled={!activeWorkspace}
            className="appearance-none bg-gray-800 border border-gray-700 rounded-md pl-9 pr-8 py-2 text-gray-100 disabled:text-gray-500 disabled:bg-gray-900 focus:outline-none focus:border-blue-500"
            title="权限模式"
          >
            {Object.entries(PERMISSION_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
      </div>
    </div>
  );
}
