import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { Message, PermissionMode, ToolCall, UploadedFile, Workspace } from '../types';

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
  currentContent: string;
  currentToolCalls: ToolCall[];
  onSend: (message: string, files: UploadedFile[]) => void;
  onStop: () => void;
  uploadedFiles: UploadedFile[];
  onFilesChange: (files: UploadedFile[]) => void;
  activeWorkspace: Workspace | null;
  onPermissionChange: (mode: PermissionMode) => Promise<void>;
}

export function ChatWindow({
  messages,
  isStreaming,
  currentContent,
  currentToolCalls,
  onSend,
  onStop,
  uploadedFiles,
  onFilesChange,
  activeWorkspace,
  onPermissionChange,
}: ChatWindowProps) {
  return (
    <main className="flex-1 min-w-0 p-4 overflow-hidden">
      <div className="relative h-full min-w-0 flex flex-col overflow-hidden rounded-2xl border border-pink-100 bg-white/82 shadow-[0_18px_70px_rgba(15,23,42,0.08)] backdrop-blur-xl">
        <div className="pointer-events-none absolute inset-0 taskforge-canvas-bg" />
        <div className="relative flex min-h-0 flex-1 flex-col">
      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        currentContent={currentContent}
        currentToolCalls={currentToolCalls}
      />
      <InputBar
        onSend={onSend}
        onStop={onStop}
        isStreaming={isStreaming}
        uploadedFiles={uploadedFiles}
        onFilesChange={onFilesChange}
        activeWorkspace={activeWorkspace}
        onPermissionChange={onPermissionChange}
      />
        </div>
      </div>
    </main>
  );
}
