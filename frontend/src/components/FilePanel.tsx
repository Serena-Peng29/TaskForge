import { useState } from 'react';
import { UploadedFile } from '../types';
import { X, FileText, ChevronRight, ChevronLeft, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface FilePanelProps {
  files: UploadedFile[];
  onRemoveFile: (id: string) => void;
  onClearAll: () => void;
}

export function FilePanel({ files, onRemoveFile, onClearAll }: FilePanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const selectedFile = files.find(f => f.id === selectedFileId) || files[0];

  const handleCopy = async () => {
    if (selectedFile) {
      await navigator.clipboard.writeText(selectedFile.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  if (files.length === 0) {
    return null;
  }

  return (
    <>
      {/* 展开按钮（当折叠时显示） */}
      {isCollapsed && (
        <button
          onClick={() => setIsCollapsed(false)}
          className="absolute right-0 top-1/2 -translate-y-1/2 p-2 bg-gray-900 border border-gray-700 border-r-0 rounded-l-lg hover:bg-gray-800 transition-colors z-10"
        >
          <ChevronLeft className="w-5 h-5 text-gray-400" />
        </button>
      )}

      {/* 文件面板 */}
      <div
        className={`${
          isCollapsed ? 'w-0' : 'w-80'
        } bg-gray-900 border-l border-gray-700 flex flex-col transition-all duration-300 overflow-hidden flex-shrink-0`}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-3 border-b border-gray-700">
          <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-400" />
            上传文件 ({files.length})
          </h3>
          <div className="flex items-center gap-1">
            <button
              onClick={onClearAll}
              className="px-2 py-1 text-xs text-gray-400 hover:text-red-400 transition-colors"
            >
              清空
            </button>
            <button
              onClick={() => setIsCollapsed(true)}
              className="p-1 hover:bg-gray-800 rounded transition-colors"
            >
              <ChevronRight className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>

        {/* 文件列表 */}
        <div className="border-b border-gray-700 max-h-40 overflow-y-auto">
          {files.map((file) => (
            <div
              key={file.id}
              onClick={() => setSelectedFileId(file.id)}
              className={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
                selectedFile?.id === file.id
                  ? 'bg-gray-800 border-l-2 border-blue-500'
                  : 'hover:bg-gray-800/50 border-l-2 border-transparent'
              }`}
            >
              <FileText className="w-4 h-4 text-blue-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 truncate">{file.filename}</p>
                <p className="text-xs text-gray-500">{formatSize(file.size)}</p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveFile(file.id);
                }}
                className="p-1 text-gray-500 hover:text-red-400 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>

        {/* 文件内容预览 */}
        {selectedFile && (
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700">
              <span className="text-xs text-gray-400 truncate">{selectedFile.filename}</span>
              <button
                onClick={handleCopy}
                className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
                title="复制内容"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-green-400" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
            <div className="flex-1 overflow-auto p-3 text-sm text-gray-300 bg-gray-950">
              <div className="markdown-content">
                <ReactMarkdown>{selectedFile.content}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}