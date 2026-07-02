import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { Message, ToolCall } from '../types';
import { MessageItem } from './MessageItem';
import { Bug, Code2, Sparkles, Wand2 } from 'lucide-react';

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  currentContent: string;
  currentToolCalls: ToolCall[];
}

export function MessageList({ messages, isStreaming, currentContent, currentToolCalls }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const displayMessages = compactToolMessages(messages);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentContent, currentToolCalls]);

  const streamingMessage: Message | null = isStreaming && (currentContent || currentToolCalls.length > 0)
    ? {
      id: 'streaming-assistant',
      role: 'assistant',
      content: currentContent,
      toolCalls: currentToolCalls,
      activity: currentContent
        ? '正在整理回答'
        : currentToolCalls.length > 0
          ? '正在调用工具'
          : '正在思考',
      toolCollapsed: false,
      timestamp: Date.now(),
    }
    : null;

  return (
    <div className="flex-1 overflow-y-auto overflow-x-hidden min-w-0">
      {messages.length === 0 && !isStreaming && (
        <div className="flex h-full items-center justify-center px-8 pb-24 pt-10 text-slate-500">
          <div className="w-full max-w-4xl text-center">
            <div className="mx-auto mb-7 flex h-20 w-20 items-center justify-center rounded-full border border-pink-100 bg-white shadow-[0_12px_36px_rgba(236,72,153,0.16)]">
              <Sparkles className="h-10 w-10 fill-pink-500 text-pink-500" />
            </div>
            <h1 className="text-4xl font-bold tracking-normal text-slate-900">
              欢迎使用 <span className="text-pink-500">TaskForge</span>
            </h1>
            <p className="mt-4 text-lg text-slate-500">让 AI 成为你的编程搭档</p>
            <div className="mx-auto mt-10 grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-3">
              <WelcomeCard icon={<Code2 className="h-6 w-6" />} title="解释代码" subtitle="AI 帮你理解复杂逻辑" />
              <WelcomeCard icon={<Wand2 className="h-6 w-6" />} title="生成代码" subtitle="快速生成高质量代码" />
              <WelcomeCard icon={<Bug className="h-6 w-6" />} title="调试问题" subtitle="定位并解决代码问题" />
            </div>
          </div>
        </div>
      )}

      {displayMessages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}

      {streamingMessage && <MessageItem message={streamingMessage} />}

      {isStreaming && !streamingMessage && (
        <MessageItem
          message={{
            id: 'streaming-thinking',
            role: 'assistant',
            content: '',
            activity: '正在思考',
            timestamp: Date.now(),
          }}
        />
      )}

      <div ref={bottomRef} />
    </div>
  );
}

function WelcomeCard({ icon, title, subtitle }: { icon: ReactNode; title: string; subtitle: string }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white/70 p-6 text-left shadow-sm transition-colors hover:border-pink-200 hover:bg-pink-50/40">
      <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-xl bg-pink-100 text-pink-500">
        {icon}
      </div>
      <div className="font-semibold text-slate-900">{title}</div>
      <div className="mt-1 text-sm text-slate-500">{subtitle}</div>
    </div>
  );
}

function compactToolMessages(messages: Message[]): Message[] {
  const result: Message[] = [];
  let pendingTools: ToolCall[] = [];

  const flushPendingTools = (timestamp = Date.now()) => {
    if (pendingTools.length === 0) return;
    result.push({
      id: `tool-group-${result.length}-${timestamp}`,
      role: 'assistant',
      content: '',
      toolCalls: pendingTools,
      toolCollapsed: true,
      timestamp,
    });
    pendingTools = [];
  };

  const toolFromMessage = (message: Message): ToolCall => ({
    id: message.id,
    name: message.toolResult?.name || 'tool',
    args: message.toolResult?.args || '',
    result: message.toolResult?.result || message.content,
    status: 'done',
  });

  for (const message of messages) {
    if (message.role === 'user') {
      flushPendingTools(message.timestamp - 1);
      result.push(message);
      continue;
    }

    if (message.role === 'tool') {
      pendingTools.push(toolFromMessage(message));
      continue;
    }

    if (message.role === 'assistant') {
      const hasContent = message.content.trim().length > 0;
      const tools = [...pendingTools, ...(message.toolCalls || [])];

      if (!hasContent) {
        pendingTools = tools;
        continue;
      }

      result.push({
        ...message,
        toolCalls: tools.length > 0 ? tools : undefined,
        toolCollapsed: tools.length > 0 ? true : message.toolCollapsed,
      });
      pendingTools = [];
      continue;
    }

    flushPendingTools(message.timestamp - 1);
    result.push(message);
  }

  flushPendingTools();

  return result;
}
