import { useState, KeyboardEvent, useRef, DragEvent, ChangeEvent } from 'react';
import { ChevronDown, Folder, Paperclip, Send, ShieldCheck, Square } from 'lucide-react';
import { PermissionMode, UploadedFile, Workspace } from '../types';
import * as api from '../api/client';

interface InputBarProps {
  onSend: (message: string, files: UploadedFile[]) => void;
  onStop: () => void;
  isStreaming: boolean;
  disabled?: boolean;
  uploadedFiles: UploadedFile[];
  onFilesChange: (files: UploadedFile[]) => void;
  activeWorkspace: Workspace | null;
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
  activeWorkspace,
  onPermissionChange,
}: InputBarProps) {
  const [input, setInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
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

  const activeMode = activeWorkspace?.permission_mode || 'manual';

  return (
    <div
      className={`px-8 pb-8 pt-3 transition-colors ${isDragging ? 'bg-pink-50/60' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drop zone indicator */}
      {isDragging && (
        <div className="max-w-3xl mx-auto mb-3 p-4 border-2 border-dashed border-pink-300 rounded-xl bg-pink-50/80 text-center">
          <span className="text-pink-500">拖放文件到这里上传</span>
        </div>
      )}

      <div className="mx-auto max-w-3xl rounded-2xl bg-slate-900/5 p-2 shadow-[0_16px_45px_rgba(15,23,42,0.08)] backdrop-blur">
        <div className="rounded-[1.25rem] border border-slate-200 bg-white/92 px-4 py-3 shadow-sm">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
          accept=".txt,.py,.js,.ts,.tsx,.jsx,.json,.yaml,.yml,.md,.html,.css,.xml,.csv,.sh,.bash,.sql,.c,.cpp,.h,.hpp,.java,.go,.rs,.rb,.php,.swift,.kt,.scala,.lua,.r,.m,.toml,.ini,.env,.docx"
        />

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={uploadedFiles.length > 0 ? `${uploadedFiles.length} 个文件已上传` : "随心输入"}
          className="block w-full resize-none border-0 bg-transparent px-1 py-0 text-base text-slate-900 placeholder:text-slate-400 focus:outline-none"
          rows={2}
          style={{ minHeight: '42px', maxHeight: '120px' }}
          disabled={disabled}
        />

        <div className="mt-1.5 flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled || isUploading}
              className="flex h-8 w-8 items-center justify-center rounded-full text-slate-500 hover:bg-pink-50 hover:text-pink-600 disabled:text-slate-300 transition-colors"
              title="附加文件"
            >
              <Paperclip className={`w-5 h-5 ${isUploading ? 'animate-pulse' : ''}`} />
            </button>

            <div className="relative">
              <ShieldCheck className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-pink-500 pointer-events-none" />
              <select
                value={activeMode}
                onChange={(e) => onPermissionChange(e.target.value as PermissionMode)}
                disabled={!activeWorkspace}
                className="appearance-none border-0 bg-transparent py-1.5 pl-8 pr-7 text-sm font-semibold text-pink-600 disabled:text-slate-400 focus:outline-none"
                title="权限模式"
              >
                {Object.entries(PERMISSION_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-1 top-1/2 -translate-y-1/2 w-4 h-4 text-pink-500 pointer-events-none" />
            </div>
          </div>

          <div className="flex flex-shrink-0 items-center gap-3">
            <button
              type="button"
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-50"
              title="当前模型"
            >
              <span>5.5</span>
              <span className="text-slate-400">高</span>
              <ChevronDown className="w-4 h-4" />
            </button>
            {isStreaming ? (
              <button
                onClick={onStop}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-red-500 text-white hover:bg-red-600 transition-colors"
                title="停止"
              >
                <Square className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={(!input.trim() && uploadedFiles.length === 0) || disabled}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-pink-500 text-white hover:bg-pink-600 disabled:bg-slate-200 disabled:text-slate-400 transition-colors"
                title="发送"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-6 px-4 text-sm text-slate-500">
        <div className="flex min-w-0 items-center gap-2">
          <Folder className="h-4 w-4 flex-shrink-0" />
          <span className="truncate font-medium text-slate-700">{activeWorkspace?.name || '未选择项目'}</span>
        </div>
      </div>
      </div>
    </div>
  );
}
