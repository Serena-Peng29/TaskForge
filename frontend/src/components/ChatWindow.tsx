import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { Message, UploadedFile } from '../types';

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
  currentContent: string;
  onSend: (message: string, files: UploadedFile[]) => void;
  onStop: () => void;
  uploadedFiles: UploadedFile[];
  onFilesChange: (files: UploadedFile[]) => void;
}

export function ChatWindow({
  messages,
  isStreaming,
  currentContent,
  onSend,
  onStop,
  uploadedFiles,
  onFilesChange,
}: ChatWindowProps) {
  return (
    <div className="flex-1 flex flex-col bg-gray-950">
      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        currentContent={currentContent}
      />
      <InputBar
        onSend={onSend}
        onStop={onStop}
        isStreaming={isStreaming}
        uploadedFiles={uploadedFiles}
        onFilesChange={onFilesChange}
      />
    </div>
  );
}