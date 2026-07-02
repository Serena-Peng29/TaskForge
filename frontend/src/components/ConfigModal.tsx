import { useState, useEffect } from 'react';
import { Skill, Tool, AppConfig, MODEL_PROVIDERS } from '../types';
import { X, Check, Cpu, BookOpen, Wrench, Key, Globe, Thermometer, Folder } from 'lucide-react';

interface ConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  type: 'model' | 'skills' | 'tools';
  skills: Skill[];
  tools: Tool[];
  config: AppConfig | null;
  onUpdateConfig: (config: Partial<AppConfig>) => Promise<void>;
}

export function ConfigModal({
  isOpen,
  onClose,
  type,
  skills,
  tools,
  config,
  onUpdateConfig,
}: ConfigModalProps) {
  // 模型配置状态
  const [selectedProvider, setSelectedProvider] = useState<string>('custom');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [apiKey, setApiKey] = useState<string>('');
  const [baseUrl, setBaseUrl] = useState<string>('');
  const [temperature, setTemperature] = useState<number>(0.7);
  const [workspaceDir, setWorkspaceDir] = useState<string>('');

  // 技能/工具选择状态
  const [enabledItems, setEnabledItems] = useState<Set<string>>(new Set());

  const [isSaving, setIsSaving] = useState(false);

  // 初始化状态
  useEffect(() => {
    if (config) {
      setSelectedModel(config.model);
      setApiKey('');
      setBaseUrl(config.base_url || '');
      setTemperature(config.temperature ?? 0.7);
      setWorkspaceDir(config.workspace_dir || '');
      setEnabledItems(new Set(
        type === 'skills' ? config.enabled_skills : config.enabled_tools
      ));

      // 尝试匹配提供商
      const provider = MODEL_PROVIDERS.find(p =>
        p.base_url === config.base_url ||
        (p.id === 'custom' && !MODEL_PROVIDERS.slice(0, -1).some(pro => pro.base_url === config.base_url))
      );
      if (provider) {
        setSelectedProvider(provider.id);
      }
    }
  }, [config, type]);

  const handleToggle = (name: string) => {
    setEnabledItems((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const handleSelectAll = (select: boolean) => {
    if (type === 'skills') {
      setEnabledItems(select ? new Set(skills.map((s) => s.name)) : new Set());
    } else {
      setEnabledItems(select ? new Set(tools.map((t) => t.name)) : new Set());
    }
  };

  const handleProviderChange = (providerId: string) => {
    setSelectedProvider(providerId);
    const provider = MODEL_PROVIDERS.find((p) => p.id === providerId);
    if (provider && provider.id !== 'custom') {
      setBaseUrl(provider.base_url);
      if (provider.models.length > 0) {
        setSelectedModel(provider.models[0].id);
      }
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (type === 'model') {
        const nextConfig: Partial<AppConfig> = {
          model: selectedModel,
          base_url: baseUrl,
          temperature,
          workspace_dir: workspaceDir.trim(),
        };
        if (apiKey.trim()) {
          nextConfig.api_key = apiKey.trim();
        }
        await onUpdateConfig(nextConfig);
      } else if (type === 'skills') {
        await onUpdateConfig({
          enabled_skills: Array.from(enabledItems),
        });
      } else {
        await onUpdateConfig({
          enabled_tools: Array.from(enabledItems),
        });
      }
      onClose();
    } catch (error) {
      console.error('Failed to save config:', error);
      alert('保存配置失败，请重试');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  const getTitle = () => {
    switch (type) {
      case 'model': return '模型配置';
      case 'skills': return '技能管理';
      case 'tools': return '工具管理';
    }
  };

  const getIcon = () => {
    switch (type) {
      case 'model': return <Cpu className="w-5 h-5 text-pink-500" />;
      case 'skills': return <BookOpen className="w-5 h-5 text-pink-500" />;
      case 'tools': return <Wrench className="w-5 h-5 text-pink-500" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm" onClick={onClose} />

      <div className="relative bg-white/95 rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col border border-pink-100">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-pink-100">
          <div className="flex items-center gap-2">
            {getIcon()}
            <h2 className="text-lg font-semibold text-slate-900">{getTitle()}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-pink-50 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-5">
          {type === 'model' && (
            <div className="space-y-4">
              {/* 提供商选择 */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  模型提供商
                </label>
                <select
                  value={selectedProvider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-slate-900 appearance-none cursor-pointer focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70"
                >
                  {MODEL_PROVIDERS.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* 模型选择 */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  模型
                </label>
                {selectedProvider !== 'custom' ? (
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-slate-900 appearance-none cursor-pointer focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70"
                  >
                    {MODEL_PROVIDERS.find(p => p.id === selectedProvider)?.models.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    placeholder="输入模型 ID，如 gpt-4o"
                    className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-slate-900 focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70"
                  />
                )}
              </div>

              {/* API Key */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2 flex items-center gap-1">
                  <Key className="w-4 h-4" />
                  API Key
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-slate-900 focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70 font-mono text-sm"
                />
              </div>

              {/* Base URL */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2 flex items-center gap-1">
                  <Globe className="w-4 h-4" />
                  API 地址
                </label>
                <input
                  type="text"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://api.openai.com/v1"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-slate-900 focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70 font-mono text-sm"
                />
              </div>

              {/* Temperature */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2 flex items-center gap-1">
                  <Thermometer className="w-4 h-4" />
                  温度: {temperature.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full h-2 bg-pink-100 rounded-lg appearance-none cursor-pointer accent-pink-500"
                />
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>精确 (0)</span>
                  <span>创意 (2)</span>
                </div>
              </div>

              {/* Workspace */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2 flex items-center gap-1">
                  <Folder className="w-4 h-4" />
                  项目目录
                </label>
                <input
                  type="text"
                  value={workspaceDir}
                  onChange={(e) => setWorkspaceDir(e.target.value)}
                  placeholder="/Users/you/path/to/project"
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2.5 text-slate-900 focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70 font-mono text-sm"
                />
              </div>
            </div>
          )}

          {type === 'skills' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-500">
                  已选择 {enabledItems.size}/{skills.length} 个技能
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleSelectAll(true)}
                    className="text-xs text-pink-500 hover:text-pink-600"
                  >
                    全选
                  </button>
                  <span className="text-slate-300">|</span>
                  <button
                    onClick={() => handleSelectAll(false)}
                    className="text-xs text-slate-500 hover:text-slate-700"
                  >
                    清空
                  </button>
                </div>
              </div>
              {skills.length === 0 ? (
                <p className="text-slate-400 text-sm py-4 text-center">暂无可用技能</p>
              ) : (
                <div className="space-y-2">
                  {skills.map((skill) => (
                    <label
                      key={skill.name}
                      className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                        enabledItems.has(skill.name)
                          ? 'bg-pink-50 border border-pink-200 shadow-sm'
                          : 'bg-white border border-slate-200 hover:border-pink-200 hover:bg-pink-50/40'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={enabledItems.has(skill.name)}
                        onChange={() => handleToggle(skill.name)}
                        className="mt-0.5 w-4 h-4 rounded border-slate-300 text-pink-500 focus:ring-pink-200"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-900">
                          {skill.name}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {skill.description || '暂无描述'}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          {type === 'tools' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-500">
                  已选择 {enabledItems.size}/{tools.length} 个工具
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleSelectAll(true)}
                    className="text-xs text-pink-500 hover:text-pink-600"
                  >
                    全选
                  </button>
                  <span className="text-slate-300">|</span>
                  <button
                    onClick={() => handleSelectAll(false)}
                    className="text-xs text-slate-500 hover:text-slate-700"
                  >
                    清空
                  </button>
                </div>
              </div>
              {tools.length === 0 ? (
                <p className="text-slate-400 text-sm py-4 text-center">暂无可用工具</p>
              ) : (
                <div className="space-y-2">
                  {tools.map((tool) => (
                    <label
                      key={tool.name}
                      className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                        enabledItems.has(tool.name)
                          ? 'bg-pink-50 border border-pink-200 shadow-sm'
                          : 'bg-white border border-slate-200 hover:border-pink-200 hover:bg-pink-50/40'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={enabledItems.has(tool.name)}
                        onChange={() => handleToggle(tool.name)}
                        className="mt-0.5 w-4 h-4 rounded border-slate-300 text-pink-500 focus:ring-pink-200"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-900 font-mono">
                          {tool.name}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {tool.description || '暂无描述'}
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
        <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-pink-100 bg-pink-50/30">
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
                保存配置
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
