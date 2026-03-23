import { Message } from '../types';
import ReactMarkdown from 'react-markdown';
import { Wrench, User, Bot, CheckCircle, Loader2, X } from 'lucide-react';
import { useState } from 'react';

// 图片预览模态框
function ImageModal({ src, alt, onClose }: { src: string; alt: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="absolute inset-0 bg-black/80" />
      <div className="relative max-w-[90vw] max-h-[90vh]">
        <button
          onClick={onClose}
          className="absolute -top-10 right-0 p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
        >
          <X className="w-5 h-5 text-white" />
        </button>
        <img
          src={src}
          alt={alt}
          className="max-w-full max-h-[90vh] object-contain rounded-lg"
          onClick={(e) => e.stopPropagation()}
        />
      </div>
    </div>
  );
}

// 自定义图片组件
function MarkdownImage({ src, alt }: { src?: string; alt?: string }) {
  const [selectedImage, setSelectedImage] = useState<{ src: string; alt: string } | null>(null);

  if (!src) return null;

  // 处理本地文件路径，转换为 API URL
  let imageSrc = src;
  if (!src.startsWith('http') && !src.startsWith('data:') && !src.startsWith('/api/')) {
    // 提取文件名（处理 Windows 和 Unix 路径）
    const filename = src.split(/[/\\]/).pop() || src;
    imageSrc = `/api/files/${filename}`;
  }

  return (
    <>
      <img
        src={imageSrc}
        alt={alt || ''}
        className="max-w-full h-auto rounded-lg cursor-pointer hover:opacity-90 transition-opacity my-2"
        onClick={() => setSelectedImage({ src: imageSrc, alt: alt || '' })}
        onError={(e) => {
          // 如果图片加载失败，显示原始路径
          (e.target as HTMLImageElement).style.display = 'none';
        }}
      />
      {selectedImage && (
        <ImageModal
          src={selectedImage.src}
          alt={selectedImage.alt}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </>
  );
}

interface MessageItemProps {
  message: Message;
}

interface ToolCallModalProps {
  tool: {
    name: string;
    args?: string;
    result?: string;
    status?: string;
  };
  onClose: () => void;
}

function ToolCallModal({ tool, onClose }: ToolCallModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60" />
      <div
        className="relative bg-gray-900 rounded-xl shadow-2xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col border border-gray-700"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Wrench className="w-5 h-5 text-orange-400" />
            <span className="font-mono text-orange-400 font-medium">{tool.name}</span>
            {tool.status === 'executing' && (
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
            )}
            {tool.status === 'done' && (
              <CheckCircle className="w-4 h-4 text-green-500" />
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* 参数 */}
          {tool.args && (
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-2">参数</h3>
              <pre className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-gray-300 overflow-x-auto">
                {formatArgs(tool.args)}
              </pre>
            </div>
          )}

          {/* 结果 */}
          {tool.result && (
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-2">返回结果</h3>
              <pre className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-gray-300 overflow-x-auto max-h-96 overflow-y-auto">
                {tool.result}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === 'user';
  const [selectedTool, setSelectedTool] = useState<{
    name: string;
    args?: string;
    result?: string;
    status?: string;
  } | null>(null);

  // 工具调用单独渲染
  if (message.toolCalls && message.toolCalls.length > 0 && !message.content) {
    return (
      <>
        <div className="flex gap-3 p-4 justify-start">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-orange-600">
            <Wrench className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 max-w-[80%] space-y-2">
            {message.toolCalls.map((tool, idx) => (
              <div
                key={idx}
                onClick={() => setSelectedTool(tool)}
                className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-sm cursor-pointer hover:bg-gray-800 hover:border-gray-600 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-orange-400">{tool.name}</span>
                  {tool.status === 'executing' && (
                    <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  )}
                  {tool.status === 'done' && (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  )}
                </div>
                {tool.args && (
                  <pre className="text-gray-500 text-xs overflow-x-auto mt-1 truncate">
                    {formatArgs(tool.args)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
        {selectedTool && <ToolCallModal tool={selectedTool} onClose={() => setSelectedTool(null)} />}
      </>
    );
  }

  return (
    <>
      <div className={`flex gap-3 p-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
        {/* AI消息：头像在左 */}
        {!isUser && (
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-purple-600">
            <Bot className="w-5 h-5 text-white" />
          </div>
        )}

        {/* Content */}
        <div className="max-w-[80%] min-w-0">
          {/* Text content */}
          {message.content && (
            <div className={`rounded-xl px-4 py-3 border ${
              isUser
                ? 'bg-blue-600/20 border-blue-500/50 text-gray-100'
                : 'bg-gray-800 border-gray-700 text-gray-100'
            }`}>
              <div className="markdown-content">
                <ReactMarkdown
                  components={{
                    img: ({ src, alt }) => <MarkdownImage src={src} alt={alt} />
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* 工具调用作为附加内容 */}
          {message.toolCalls && message.toolCalls.length > 0 && message.content && (
            <div className="mt-2 flex flex-wrap gap-1">
              {message.toolCalls.map((tool, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedTool(tool)}
                  className="inline-flex items-center gap-2 bg-gray-800/50 border border-gray-700 rounded px-2 py-1 text-xs cursor-pointer hover:bg-gray-800 hover:border-gray-600 transition-colors"
                >
                  <Wrench className="w-3 h-3 text-orange-400" />
                  <span className="font-mono text-orange-400">{tool.name}</span>
                  {tool.status === 'executing' && (
                    <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                  )}
                  {tool.status === 'done' && (
                    <CheckCircle className="w-3 h-3 text-green-500" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 用户消息：头像在右 */}
        {isUser && (
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-blue-600">
            <User className="w-5 h-5 text-white" />
          </div>
        )}
      </div>
      {selectedTool && <ToolCallModal tool={selectedTool} onClose={() => setSelectedTool(null)} />}
    </>
  );
}

function formatArgs(args: string): string {
  try {
    const parsed = JSON.parse(args);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return args;
  }
}