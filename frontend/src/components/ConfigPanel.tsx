import { useState, useEffect } from 'react';
import { Skill, Tool, Model, AppConfig } from '../types';
import { X, Check, ChevronDown } from 'lucide-react';

interface ConfigPanelProps {
  isOpen: boolean;
  onClose: () => void;
  skills: Skill[];
  tools: Tool[];
  models: Model[];
  config: AppConfig | null;
  onUpdateConfig: (config: Partial<AppConfig>) => Promise<void>;
}

export function ConfigPanel({
  isOpen,
  onClose,
  skills,
  tools,
  models,
  config,
  onUpdateConfig,
}: ConfigPanelProps) {
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [enabledSkills, setEnabledSkills] = useState<Set<string>>(new Set());
  const [enabledTools, setEnabledTools] = useState<Set<string>>(new Set());
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'model' | 'skills' | 'tools'>('model');

  // 初始化配置状态
  useEffect(() => {
    if (config) {
      setSelectedModel(config.model);
      setEnabledSkills(new Set(config.enabled_skills));
      setEnabledTools(new Set(config.enabled_tools));
    }
  }, [config]);

  const handleSkillToggle = (skillName: string) => {
    setEnabledSkills((prev) => {
      const next = new Set(prev);
      if (next.has(skillName)) {
        next.delete(skillName);
      } else {
        next.add(skillName);
      }
      return next;
    });
  };

  const handleToolToggle = (toolName: string) => {
    setEnabledTools((prev) => {
      const next = new Set(prev);
      if (next.has(toolName)) {
        next.delete(toolName);
      } else {
        next.add(toolName);
      }
      return next;
    });
  };

  const handleSelectAllSkills = (select: boolean) => {
    if (select) {
      setEnabledSkills(new Set(skills.map((s) => s.name)));
    } else {
      setEnabledSkills(new Set());
    }
  };

  const handleSelectAllTools = (select: boolean) => {
    if (select) {
      setEnabledTools(new Set(tools.map((t) => t.name)));
    } else {
      setEnabledTools(new Set());
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onUpdateConfig({
        model: selectedModel,
        enabled_skills: Array.from(enabledSkills),
        enabled_tools: Array.from(enabledTools),
      });
      onClose();
    } catch (error) {
      console.error('Failed to save config:', error);
      alert('保存配置失败，请重试');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* 配置面板 */}
      <div className="relative bg-gray-900 rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col border border-gray-700">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">配置</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* 标签栏 */}
        <div className="flex border-b border-gray-700">
          <button
            onClick={() => setActiveTab('model')}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'model'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            模型
          </button>
          <button
            onClick={() => setActiveTab('skills')}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'skills'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            技能 ({skills.length})
          </button>
          <button
            onClick={() => setActiveTab('tools')}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'tools'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            工具 ({tools.length})
          </button>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* 模型选择 */}
          {activeTab === 'model' && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                选择模型
              </label>
              <div className="relative">
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white appearance-none cursor-pointer focus:outline-none focus:border-blue-500"
                >
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.provider})
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
              </div>
            </div>
          )}

          {/* 技能选择 */}
          {activeTab === 'skills' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-300">启用技能</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleSelectAllSkills(true)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    全选
                  </button>
                  <span className="text-gray-600">|</span>
                  <button
                    onClick={() => handleSelectAllSkills(false)}
                    className="text-xs text-gray-400 hover:text-gray-300"
                  >
                    清空
                  </button>
                </div>
              </div>
              {skills.length === 0 ? (
                <p className="text-gray-500 text-sm">暂无可用技能</p>
              ) : (
                <div className="space-y-2">
                  {skills.map((skill) => (
                    <label
                      key={skill.name}
                      className="flex items-start gap-3 p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-750 transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={enabledSkills.has(skill.name)}
                        onChange={() => handleSkillToggle(skill.name)}
                        className="mt-0.5 w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-200">
                          {skill.name}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                          {skill.description}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 工具选择 */}
          {activeTab === 'tools' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-300">启用工具</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleSelectAllTools(true)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    全选
                  </button>
                  <span className="text-gray-600">|</span>
                  <button
                    onClick={() => handleSelectAllTools(false)}
                    className="text-xs text-gray-400 hover:text-gray-300"
                  >
                    清空
                  </button>
                </div>
              </div>
              {tools.length === 0 ? (
                <p className="text-gray-500 text-sm">暂无可用工具</p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {tools.map((tool) => (
                    <label
                      key={tool.name}
                      className="flex items-start gap-3 p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-750 transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={enabledTools.has(tool.name)}
                        onChange={() => handleToolToggle(tool.name)}
                        className="mt-0.5 w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-200 font-mono">
                          {tool.name}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                          {tool.description}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end gap-3 px-4 py-3 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg transition-colors"
          >
            {isSaving ? (
              <span>保存中...</span>
            ) : (
              <>
                <Check className="w-4 h-4" />
                保存配置
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}