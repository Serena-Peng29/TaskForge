import { useEffect, useRef } from 'react';
import { Message } from '../types';
import { MessageItem } from './MessageItem';
import { Loader2 } from 'lucide-react';

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  currentContent: string;
}

export function MessageList({ messages, isStreaming, currentContent }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentContent]);

  return (
    <div className="flex-1 overflow-y-auto">
      {messages.length === 0 && !isStreaming && (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <p className="text-xl mb-2">Welcome to TaskForge</p>
            <p className="text-sm">Type a message to start coding with AI assistance</p>
          </div>
        </div>
      )}

      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}

      {/* Streaming content */}
      {isStreaming && currentContent && (
        <div className="flex gap-3 p-4 bg-gray-900">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-purple-600">
            <Loader2 className="w-5 h-5 text-white animate-spin" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="markdown-content text-gray-100 whitespace-pre-wrap">
              {currentContent}
            </div>
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {isStreaming && !currentContent && (
        <div className="flex gap-3 p-4 bg-gray-900">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-purple-600">
            <Loader2 className="w-5 h-5 text-white animate-spin" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-gray-400">Thinking...</div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}