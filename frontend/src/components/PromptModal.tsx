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
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm" onClick={onClose} />

      <div className="relative bg-white/95 rounded-2xl shadow-2xl w-full max-w-3xl mx-4 max-h-[85vh] flex flex-col border border-pink-100">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-pink-100">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-pink-500" />
            <h2 className="text-lg font-semibold text-slate-900">System Prompt</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-pink-50 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* 错误/成功提示 */}
        {error && (
          <div className="mx-5 mt-3 p-2 bg-red-50 border border-red-100 rounded-lg flex items-center gap-2 text-sm text-red-600">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {success && (
          <div className="mx-5 mt-3 p-2 bg-green-50 border border-green-100 rounded-lg flex items-center gap-2 text-sm text-green-700">
            <Check className="w-4 h-4 flex-shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-slate-500">
              加载中...
            </div>
          ) : (
            <>
              {/* 当前使用的 Prompt */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  当前生效的 Prompt
                </label>
                <pre className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-700 font-mono whitespace-pre-wrap max-h-40 overflow-auto">
                  {currentPrompt}
                </pre>
              </div>

              {/* 自定义 Prompt */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  自定义 Prompt 模板
                </label>
                <p className="text-xs text-slate-500 mb-2">
                  留空则使用默认模板。支持变量: {'{workdir}'}, {'{skills}'}, {'{agents}'}
                </p>
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="输入自定义 Prompt 模板..."
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-mono text-sm focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70 resize-none h-48"
                />
              </div>

              {/* 默认 Prompt */}
              <div>
                <details className="group">
                  <summary className="cursor-pointer text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1">
                    <span className="transform transition-transform group-open:rotate-90">▶</span>
                    查看默认 Prompt 模板
                  </summary>
                  <pre className="mt-2 w-full bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-600 font-mono whitespace-pre-wrap max-h-60 overflow-auto">
                    {defaultPrompt}
                  </pre>
                </details>
              </div>
            </>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-t border-pink-100 bg-pink-50/30">
          <button
            onClick={handleReset}
            disabled={isSaving}
            className="flex items-center gap-2 px-3 py-2 text-sm text-slate-500 hover:text-slate-800 transition-colors disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
            重置为默认
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-500 hover:text-slate-800 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-pink-500 hover:bg-pink-600 disabled:bg-pink-200 rounded-lg transition-colors"
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
