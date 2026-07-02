import { Message } from '../types';
import ReactMarkdown from 'react-markdown';
import { Wrench, User, Bot, CheckCircle, ChevronRight, Loader2, X, Terminal } from 'lucide-react';
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

function getToolAction(toolName: string, status?: string): string {
  if (status === 'executing' || status === 'pending') {
    return '正在运行';
  }
  if (toolName === 'read_file') return '已读取';
  if (toolName === 'write_file') return '已写入';
  if (toolName === 'edit_file') return '已编辑';
  if (toolName === 'bash') return '已运行';
  if (toolName === 'TodoWrite') return '已更新任务';
  if (toolName === 'Skill') return '已加载技能';
  if (toolName === 'Task') return '已运行子任务';
  return '已调用';
}

function summarizeArgs(args?: string): string {
  if (!args) return '';
  try {
    const parsed = JSON.parse(args);
    if (typeof parsed.path === 'string') return parsed.path;
    if (typeof parsed.command === 'string') return parsed.command;
    if (typeof parsed.skill === 'string') return parsed.skill;
    if (typeof parsed.description === 'string') return parsed.description;
    return '';
  } catch {
    return '';
  }
}

function CompactToolRow({
  tool,
  onSelect,
}: {
  tool: { name: string; args?: string; result?: string; status?: string };
  onSelect: () => void;
}) {
  const isRunning = tool.status === 'executing' || tool.status === 'pending';
  const summary = summarizeArgs(tool.args);

  return (
    <button
      type="button"
      onClick={onSelect}
      className="flex max-w-full min-w-0 items-center gap-2 rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-800/70 hover:text-gray-300 transition-colors"
      title={summary || tool.name}
    >
      {isRunning ? (
        <Loader2 className="w-3.5 h-3.5 text-gray-500 animate-spin flex-shrink-0" />
      ) : (
        <Terminal className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
      )}
      <span className="whitespace-nowrap flex-shrink-0">{getToolAction(tool.name, tool.status)}</span>
      <span className="font-mono text-gray-400 truncate flex-shrink-0 max-w-[11rem]">{tool.name}</span>
      {summary && <span className="truncate text-gray-600 min-w-0">{summary}</span>}
    </button>
  );
}

function ToolRows({
  tools,
  onSelect,
  className = "mt-3",
}: {
  tools: { name: string; args?: string; result?: string; status?: string }[];
  onSelect: (tool: { name: string; args?: string; result?: string; status?: string }) => void;
  className?: string;
}) {
  return (
    <div className={`${className} flex w-full min-w-0 flex-col items-start gap-1 overflow-hidden`}>
      {tools.map((tool, idx) => (
        <CompactToolRow key={`${tool.name}-${tool.args || ''}-${idx}`} tool={tool} onSelect={() => onSelect(tool)} />
      ))}
    </div>
  );
}

function ToolSummary({
  tools,
  defaultCollapsed,
  onSelect,
}: {
  tools: { name: string; args?: string; result?: string; status?: string }[];
  defaultCollapsed?: boolean;
  onSelect: (tool: { name: string; args?: string; result?: string; status?: string }) => void;
}) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed ?? false);
  const hasRunning = tools.some(tool => tool.status === 'pending' || tool.status === 'executing');

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={() => setCollapsed(false)}
        className="mb-2 flex max-w-full items-center gap-2 rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-800/70 hover:text-gray-300 transition-colors"
      >
        {hasRunning ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin flex-shrink-0" />
        ) : (
          <Terminal className="w-3.5 h-3.5 flex-shrink-0" />
        )}
        <span>{hasRunning ? '正在处理' : '已处理'}</span>
        <span>{tools.length} 个工具</span>
        <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" />
      </button>
    );
  }

  return (
    <div className="mb-2">
      <button
        type="button"
        onClick={() => setCollapsed(true)}
        className="mb-1 flex items-center gap-2 rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-800/70 hover:text-gray-300 transition-colors"
      >
        <ChevronRight className="w-3.5 h-3.5 rotate-90" />
        <span>{hasRunning ? '正在处理' : '已处理'}</span>
        <span>{tools.length} 个工具</span>
      </button>
      <ToolRows tools={tools} onSelect={onSelect} className="ml-5" />
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

  if (message.role === 'tool') {
    const tool = {
      name: message.toolResult?.name || 'tool',
      args: message.toolResult?.args,
      result: message.toolResult?.result || message.content,
      status: 'done',
    };
    return (
      <>
        <div className="flex gap-3 px-4 py-1 justify-start">
          <div className="w-8 flex-shrink-0" />
          <div className="w-full max-w-[80%] min-w-0 overflow-hidden">
            <CompactToolRow tool={tool} onSelect={() => setSelectedTool(tool)} />
          </div>
        </div>
        {selectedTool && <ToolCallModal tool={selectedTool} onClose={() => setSelectedTool(null)} />}
      </>
    );
  }

  // 工具调用单独渲染
  if (message.toolCalls && message.toolCalls.length > 0 && !message.content) {
    return (
      <>
        <div className="flex gap-3 px-4 py-1 justify-start">
          <div className="w-8 flex-shrink-0" />
          <div className="w-full max-w-[80%] min-w-0 overflow-hidden">
            {message.activity && (
              <div className="mb-1 flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>{message.activity}</span>
              </div>
            )}
            <ToolSummary tools={message.toolCalls} defaultCollapsed={message.toolCollapsed} onSelect={setSelectedTool} />
          </div>
        </div>
        {selectedTool && <ToolCallModal tool={selectedTool} onClose={() => setSelectedTool(null)} />}
      </>
    );
  }

  return (
    <>
      <div className={`flex min-w-0 gap-3 p-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
        {/* AI消息：头像在左 */}
        {!isUser && (
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-purple-600">
            <Bot className="w-5 h-5 text-white" />
          </div>
        )}

        {/* Content */}
        <div className="max-w-[80%] min-w-0 overflow-hidden">
          {message.activity && !isUser && (
            <div className="mb-2 flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>{message.activity}</span>
            </div>
          )}

          {message.toolCalls && message.toolCalls.length > 0 && (
            <ToolSummary tools={message.toolCalls} defaultCollapsed={message.toolCollapsed} onSelect={setSelectedTool} />
          )}

          {/* Text content */}
          {message.content && (
            <div className={`rounded-xl px-4 py-3 border ${
              isUser
                ? 'bg-blue-600/20 border-blue-500/50 text-gray-100'
                : 'bg-gray-800 border-gray-700 text-gray-100'
            }`}>
              <div className="markdown-content min-w-0 overflow-hidden break-words">
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
