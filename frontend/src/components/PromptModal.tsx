import { useState, useEffect } from 'react';
import * as api from '../api/client';
import { X, Check, RotateCcw, FileText, AlertCircle } from 'lucide-react';

interface PromptModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PromptModal({ isOpen, onClose }: PromptModalProps) {
  const [defaultPrompt, setDefaultPrompt] = useState('');
  const [customPrompt, setCustomPrompt] = useState('');
  const [currentPrompt, setCurrentPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadPrompt();
    }
  }, [isOpen]);

  const loadPrompt = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.getPrompt();
      setDefaultPrompt(result.default_prompt);
      setCustomPrompt(result.custom_prompt || '');
      setCurrentPrompt(result.current_prompt);
    } catch (err: any) {
      setError(err.message || '加载 Prompt 失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await api.updatePrompt(customPrompt.trim() || null);
      setCurrentPrompt(result.current_prompt);
      setSuccess('Prompt 已更新');
      setTimeout(() => setSuccess(null), 2000);
    } catch (err: any) {
      setError(err.message || '保存 Prompt 失败');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('确定要重置为默认 Prompt 吗？')) return;

    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await api.resetPrompt();
      setCustomPrompt('');
      setCurrentPrompt(result.current_prompt);
      setSuccess('已重置为默认 Prompt');
      setTimeout(() => setSuccess(null), 2000);
    } catch (err: any) {
      setError(err.message || '重置 Prompt 失败');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative bg-gray-900 rounded-xl shadow-2xl w-full max-w-3xl mx-4 max-h-[85vh] flex flex-col border border-gray-700">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold text-white">System Prompt</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* 错误/成功提示 */}
        {error && (
          <div className="mx-4 mt-3 p-2 bg-red-900/30 border border-red-800 rounded-lg flex items-center gap-2 text-sm text-red-300">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {success && (
          <div className="mx-4 mt-3 p-2 bg-green-900/30 border border-green-800 rounded-lg flex items-center gap-2 text-sm text-green-300">
            <Check className="w-4 h-4 flex-shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-gray-500">
              加载中...
            </div>
          ) : (
            <>
              {/* 当前使用的 Prompt */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  当前生效的 Prompt
                </label>
                <pre className="w-full bg-gray-950 border border-gray-700 rounded-lg p-3 text-xs text-gray-300 font-mono whitespace-pre-wrap max-h-40 overflow-auto">
                  {currentPrompt}
                </pre>
              </div>

              {/* 自定义 Prompt */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  自定义 Prompt 模板
                </label>
                <p className="text-xs text-gray-500 mb-2">
                  留空则使用默认模板。支持变量: {'{workdir}'}, {'{skills}'}, {'{agents}'}
                </p>
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="输入自定义 Prompt 模板..."
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-purple-500 resize-none h-48"
                />
              </div>

              {/* 默认 Prompt */}
              <div>
                <details className="group">
                  <summary className="cursor-pointer text-sm text-gray-400 hover:text-gray-300 flex items-center gap-1">
                    <span className="transform transition-transform group-open:rotate-90">▶</span>
                    查看默认 Prompt 模板
                  </summary>
                  <pre className="mt-2 w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-xs text-gray-400 font-mono whitespace-pre-wrap max-h-60 overflow-auto">
                    {defaultPrompt}
                  </pre>
                </details>
              </div>
            </>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-t border-gray-700">
          <button
            onClick={handleReset}
            disabled={isSaving}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white transition-colors disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
            重置为默认
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 rounded-lg transition-colors"
            >
              {isSaving ? (
                <span>保存中...</span>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  保存
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}