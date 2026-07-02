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
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  onAddWorkspace: (path: string) => Promise<void>;
  onSelectWorkspace: (workspaceId: string) => Promise<void>;
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
  workspaces,
  activeWorkspace,
  onAddWorkspace,
  onSelectWorkspace,
  onPermissionChange,
}: ChatWindowProps) {
  return (
    <div className="flex-1 min-w-0 flex flex-col bg-gray-950 overflow-hidden">
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
        workspaces={workspaces}
        activeWorkspace={activeWorkspace}
        onAddWorkspace={onAddWorkspace}
        onSelectWorkspace={onSelectWorkspace}
        onPermissionChange={onPermissionChange}
      />
    </div>
  );
}
