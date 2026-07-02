import { useEffect, useState } from 'react';
import { useChat } from './hooks/useChat';
import { useAuth } from './hooks/useAuth';
import { ChatWindow } from './components/ChatWindow';
import { Sidebar } from './components/Sidebar';
import { FilePanel } from './components/FilePanel';
import { LoginModal } from './components/LoginModal';
import { UploadedFile } from './types';

function App() {
  const {
    user,
    isLoading: authLoading,
    isAuthenticated,
    authStatus,
    error: authError,
    login,
    register,
    logout,
  } = useAuth();

  const {
    // 状态
    messages,
    isStreaming,
    status,
    skills,
    tools,
    sessions,
    currentSessionId,
    config,
    currentContent,
    // 聊天功能
    sendMessage,
    stopStreaming,
    // 加载函数
    loadSkills,
    loadTools,
    loadStatus,
    loadHistory,
    loadSessions,
    loadConfig,
    // 会话管理
    createNewSession,
    switchToSession,
    deleteSessionById,
    renameSessionById,
    // 配置管理
    updateAppConfig,
  } = useChat();

  // 上传文件状态
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  // Initial load - only when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadSkills();
      loadTools();
      loadStatus();
      loadConfig();
      loadSessions().then(() => {
        loadHistory();
      });
    }
  }, [isAuthenticated, loadSkills, loadTools, loadStatus, loadHistory, loadSessions, loadConfig]);

  const handleCreateSession = async () => {
    try {
      await createNewSession();
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const handleSelectSession = async (sessionId: string) => {
    try {
      await switchToSession(sessionId);
    } catch (error) {
      console.error('Failed to switch session:', error);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSessionById(sessionId);
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const handleRenameSession = async (sessionId: string, title: string) => {
    try {
      await renameSessionById(sessionId, title);
    } catch (error) {
      console.error('Failed to rename session:', error);
    }
  };

  // 处理发送消息，包含文件
  const handleSend = (message: string, files: UploadedFile[]) => {
    // 构建带文件上下文的消息
    let fullMessage = message;
    if (files.length > 0) {
      const fileContext = files.map(f =>
        `\n--- 文件: ${f.filename} ---\n${f.content}\n--- ${f.filename} 结束 ---`
      ).join('\n');
      fullMessage = message ? `${message}\n${fileContext}` : fileContext;
    }

    // 发送完整消息（含文件），但 UI 只显示用户原始问题
    sendMessage(fullMessage, message);
    // 发送后保留文件，用户可通过 FilePanel 的"清空"按钮手动关闭
  };

  // 移除单个文件
  const handleRemoveFile = (id: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== id));
  };

  // 清空所有文件
  const handleClearFiles = () => {
    setUploadedFiles([]);
  };

  // 认证加载中
  if (authLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950 text-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">加载中...</p>
        </div>
      </div>
    );
  }

  // 未认证时显示登录界面
  if (!isAuthenticated) {
    return (
      <LoginModal
        onLogin={login}
        onRegister={register}
        isLoading={authLoading}
        error={authError}
        authAvailable={authStatus?.available ?? true}
      />
    );
  }

  return (
    <div className="h-screen flex bg-gray-950 text-gray-100 relative">
      <Sidebar
        skills={skills}
        status={status}
        sessions={sessions}
        currentSessionId={currentSessionId}
        config={config}
        tools={tools}
        onSelectSession={handleSelectSession}
        onCreateSession={handleCreateSession}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        onUpdateConfig={updateAppConfig}
        user={user}
        onLogout={logout}
      />
      <ChatWindow
        messages={messages}
        isStreaming={isStreaming}
        currentContent={currentContent}
        onSend={handleSend}
        onStop={stopStreaming}
        uploadedFiles={uploadedFiles}
        onFilesChange={setUploadedFiles}
      />
      <FilePanel
        files={uploadedFiles}
        onRemoveFile={handleRemoveFile}
        onClearAll={handleClearFiles}
      />
    </div>
  );
}

export default App;
