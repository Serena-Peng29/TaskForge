import { useState, useCallback, useRef } from 'react';
import { Message, ToolCall, Status, Skill, Tool, Session, AppConfig } from '../types';
import * as api from '../api/client';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState<Status | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [currentContent, setCurrentContent] = useState('');
  const [currentToolCalls, setCurrentToolCalls] = useState<Map<number, ToolCall>>(new Map());
  const abortControllerRef = useRef<AbortController | null>(null);

  // ==================== 加载函数 ====================

  const loadSkills = useCallback(async () => {
    try {
      const data = await api.getSkills();
      setSkills(data);
    } catch (error) {
      console.error('Failed to load skills:', error);
    }
  }, []);

  const loadTools = useCallback(async () => {
    try {
      const data = await api.getTools();
      setTools(data);
    } catch (error) {
      console.error('Failed to load tools:', error);
    }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const data = await api.getStatus();
      setStatus(data);
      setCurrentSessionId(data.current_session);
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  }, []);

  const loadConfig = useCallback(async () => {
    try {
      const data = await api.getConfig();
      setConfig(data);
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      const data = await api.getSessions();
      setSessions(data);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const data = await api.getHistory();
      const formattedMessages: Message[] = data.messages.map((msg: any, idx: number) => ({
        id: `msg-${idx}-${Date.now()}`,
        role: msg.role,
        content: msg.content || '',
        timestamp: Date.now() + idx,
      }));
      setMessages(formattedMessages);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  }, []);

  // ==================== 会话管理 ====================

  const createNewSession = useCallback(async (title?: string) => {
    try {
      const session = await api.createSession(title);
      setSessions(prev => [session, ...prev]);
      setCurrentSessionId(session.id);
      setMessages([]);
      return session;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  }, []);

  const switchToSession = useCallback(async (sessionId: string) => {
    try {
      const result = await api.switchSession(sessionId);
      setCurrentSessionId(sessionId);
      await loadHistory();
      await loadStatus();
      return result;
    } catch (error) {
      console.error('Failed to switch session:', error);
      throw error;
    }
  }, [loadHistory, loadStatus]);

  const deleteSessionById = useCallback(async (sessionId: string) => {
    try {
      await api.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
    } catch (error) {
      console.error('Failed to delete session:', error);
      throw error;
    }
  }, []);

  const renameSessionById = useCallback(async (sessionId: string, title: string) => {
    try {
      await api.renameSession(sessionId, title);
      setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title } : s));
    } catch (error) {
      console.error('Failed to rename session:', error);
      throw error;
    }
  }, []);

  // ==================== 配置管理 ====================

  const updateAppConfig = useCallback(async (newConfig: Partial<AppConfig>) => {
    try {
      await api.updateConfig(newConfig);
      if (config) {
        setConfig({ ...config, ...newConfig });
      }
      // 重新加载 skills 和 tools 以更新 enabled 状态
      await loadSkills();
      await loadTools();
    } catch (error) {
      console.error('Failed to update config:', error);
      throw error;
    }
  }, [config, loadSkills, loadTools]);

  // ==================== 聊天功能 ====================

  const clearHistory = useCallback(async () => {
    try {
      await api.clearHistory();
      setMessages([]);
      setCurrentContent('');
      setCurrentToolCalls(new Map());
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  }, []);

  const generateId = () => `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const sendMessage = useCallback(async (content: string, displayContent?: string) => {
    if (isStreaming) return;

    // Add user message (displayContent 用于 UI 显示，content 是实际发送的内容)
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: displayContent ?? content,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Prepare assistant message
    const assistantId = generateId();
    setIsStreaming(true);
    setCurrentContent('');
    setCurrentToolCalls(new Map());

    abortControllerRef.current = new AbortController();

    let fullContent = '';
    const toolCalls = new Map<number, ToolCall>();

    try {
      await api.sendChatMessage(
        content,
        {
          onContent: (chunk) => {
            fullContent += chunk;
            setCurrentContent(fullContent);
          },
          onToolStart: (index, id) => {
            toolCalls.set(index, {
              id,
              name: '',
              args: '',
              status: 'pending',
            });
            setCurrentToolCalls(new Map(toolCalls));
          },
          onToolName: (index, name) => {
            const tc = toolCalls.get(index);
            if (tc) {
              tc.name = name;
              tc.status = 'executing';
              setCurrentToolCalls(new Map(toolCalls));
            }
          },
          onToolArgs: (index, args) => {
            const tc = toolCalls.get(index);
            if (tc) {
              tc.args += args;
              setCurrentToolCalls(new Map(toolCalls));
            }
          },
          onToolExecute: (name) => {
            // Mark tool as executing
            for (const [, tc] of toolCalls) {
              if (tc.name === name) {
                tc.status = 'executing';
                break;
              }
            }
            setCurrentToolCalls(new Map(toolCalls));
          },
          onToolResult: (name, result) => {
            for (const [, tc] of toolCalls) {
              if (tc.name === name) {
                tc.result = result;
                tc.status = 'done';
                break;
              }
            }
            setCurrentToolCalls(new Map(toolCalls));
          },
          onDone: (content) => {
            const assistantMessage: Message = {
              id: assistantId,
              role: 'assistant',
              content: content || fullContent,
              toolCalls: Array.from(toolCalls.values()),
              timestamp: Date.now(),
            };
            setMessages(prev => [...prev, assistantMessage]);
            setCurrentContent('');
            setCurrentToolCalls(new Map());
            // 刷新会话列表
            loadSessions();
          },
          onError: (error) => {
            console.error('Chat error:', error);
            const errorMessage: Message = {
              id: assistantId,
              role: 'assistant',
              content: `Error: ${error}`,
              timestamp: Date.now(),
            };
            setMessages(prev => [...prev, errorMessage]);
          },
        },
        abortControllerRef.current.signal
      );
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Chat error:', error);
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
      loadStatus();
    }
  }, [isStreaming, loadStatus, loadSessions]);

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  return {
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
    currentToolCalls,
    // 聊天功能
    sendMessage,
    stopStreaming,
    clearHistory,
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
  };
}