import { useEffect, useRef } from 'react';
import { Message, ToolCall } from '../types';
import { MessageItem } from './MessageItem';

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
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <p className="text-xl mb-2">Welcome to TaskForge</p>
            <p className="text-sm">Type a message to start coding with AI assistance</p>
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
