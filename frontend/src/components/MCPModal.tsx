import { useState, useEffect } from 'react';
import { X, Server, Play, Square, Trash2, Upload, Check, AlertCircle, Loader2 } from 'lucide-react';

interface MCPServer {
  name: string;
  status: string;
  error: string | null;
  tools: string[];
  command: string;
  env: Record<string, string>;
}

interface MCPModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MCPModal({ isOpen, onClose }: MCPModalProps) {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [configText, setConfigText] = useState('');
  const [showImport, setShowImport] = useState(false);
  const [newServerName, setNewServerName] = useState('');
  const [newServerCommand, setNewServerCommand] = useState('');
  const [connecting, setConnecting] = useState<string | null>(null);

  // 加载服务器列表
  const loadServers = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/mcp/servers');
      if (response.ok) {
        const data = await response.json();
        setServers(data);
      }
    } catch (error) {
      console.error('Failed to load MCP servers:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadServers();
    }
  }, [isOpen]);

  // 连接服务器
  const handleConnect = async (name: string) => {
    setConnecting(name);
    try {
      const response = await fetch(`/api/mcp/servers/${encodeURIComponent(name)}/connect`, {
        method: 'POST',
      });
      if (response.ok) {
        await loadServers();
      } else {
        const error = await response.json();
        alert(`连接失败: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to connect:', error);
      alert('连接失败');
    } finally {
      setConnecting(null);
    }
  };

  // 断开服务器
  const handleDisconnect = async (name: string) => {
    setConnecting(name);
    try {
      const response = await fetch(`/api/mcp/servers/${encodeURIComponent(name)}/disconnect`, {
        method: 'POST',
      });
      if (response.ok) {
        await loadServers();
      }
    } catch (error) {
      console.error('Failed to disconnect:', error);
    } finally {
      setConnecting(null);
    }
  };

  // 删除服务器
  const handleDelete = async (name: string) => {
    if (!confirm(`确定要删除服务器 "${name}" 吗？`)) {
      return;
    }

    try {
      const response = await fetch(`/api/mcp/servers/${encodeURIComponent(name)}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await loadServers();
      }
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  // 导入配置
  const handleImport = async () => {
    if (!configText.trim()) {
      alert('请输入配置内容');
      return;
    }

    try {
      const config = JSON.parse(configText);
      const response = await fetch('/api/mcp/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config }),
      });

      if (response.ok) {
        const result = await response.json();
        setShowImport(false);
        setConfigText('');
        await loadServers();

        // 显示连接结果
        const errors = result.errors || {};
        const errorNames = Object.keys(errors);
        if (errorNames.length > 0) {
          alert(`部分服务器连接失败:\n${errorNames.map(n => `${n}: ${errors[n]}`).join('\n')}`);
        }
      } else {
        const error = await response.json();
        alert(`导入失败: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to import:', error);
      alert('配置格式错误，请检查 JSON 格式');
    }
  };

  // 添加服务器
  const handleAddServer = async () => {
    if (!newServerName.trim() || !newServerCommand.trim()) {
      alert('请填写服务器名称和命令');
      return;
    }

    try {
      const response = await fetch('/api/mcp/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newServerName,
          command: newServerCommand,
          env: {},
        }),
      });

      if (response.ok) {
        setNewServerName('');
        setNewServerCommand('');
        await loadServers();
      } else {
        const error = await response.json();
        alert(`添加失败: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to add server:', error);
    }
  };

  if (!isOpen) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-700';
      case 'connecting': return 'text-yellow-700';
      case 'error': return 'text-red-600';
      default: return 'text-slate-500';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'connected': return 'bg-green-50 border-green-100';
      case 'connecting': return 'bg-yellow-50 border-yellow-100';
      case 'error': return 'bg-red-50 border-red-100';
      default: return 'bg-white border-slate-200';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm" onClick={onClose} />

      <div className="relative bg-white/95 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[85vh] flex flex-col border border-pink-100">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-pink-100">
          <div className="flex items-center gap-2">
            <Server className="w-5 h-5 text-pink-500" />
            <h2 className="text-lg font-semibold text-slate-900">MCP Servers</h2>
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
          {/* 操作按钮 */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex gap-2">
              <button
                onClick={() => setShowImport(!showImport)}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-pink-600 hover:text-pink-700 border border-pink-200 rounded-lg hover:bg-pink-50 transition-colors"
              >
                <Upload className="w-4 h-4" />
                导入配置
              </button>
            </div>
            <span className="text-xs text-slate-500">
              {servers.filter(s => s.status === 'connected').length}/{servers.length} 已连接
            </span>
          </div>

          {/* 导入面板 */}
          {showImport && (
            <div className="mb-4 p-3 bg-pink-50/50 rounded-lg border border-pink-100">
              <p className="text-xs text-slate-500 mb-2">
                粘贴 Claude Desktop 格式的配置（JSON）:
              </p>
              <textarea
                value={configText}
                onChange={(e) => setConfigText(e.target.value)}
                placeholder={`{
  "mcpServers": {
    "server-name": {
      "command": "npx -y mcp-remote https://...",
      "env": {}
    }
  }
}`}
                className="w-full h-32 bg-white border border-slate-200 rounded-lg p-2 text-sm text-slate-900 font-mono resize-none focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70"
              />
              <div className="flex justify-end gap-2 mt-2">
                <button
                  onClick={() => { setShowImport(false); setConfigText(''); }}
                  className="px-3 py-1 text-sm text-slate-500 hover:text-slate-800"
                >
                  取消
                </button>
                <button
                  onClick={handleImport}
                  className="flex items-center gap-1 px-3 py-1 text-sm text-white bg-pink-500 hover:bg-pink-600 rounded-lg"
                >
                  <Check className="w-4 h-4" />
                  导入
                </button>
              </div>
            </div>
          )}

          {/* 添加服务器 */}
          <div className="mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <p className="text-xs text-slate-500 mb-2">添加新服务器:</p>
            <div className="flex gap-2">
              <input
                type="text"
                value={newServerName}
                onChange={(e) => setNewServerName(e.target.value)}
                placeholder="名称 (如: tavily)"
                className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:border-pink-300"
              />
              <input
                type="text"
                value={newServerCommand}
                onChange={(e) => setNewServerCommand(e.target.value)}
                placeholder="命令 (如: npx -y mcp-remote https://...)"
                className="flex-[2] bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 font-mono text-xs focus:outline-none focus:border-pink-300"
              />
              <button
                onClick={handleAddServer}
                className="px-3 py-1.5 text-sm text-white bg-pink-500 hover:bg-pink-600 rounded-lg"
              >
                添加
              </button>
            </div>
          </div>

          {/* 服务器列表 */}
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-pink-500 animate-spin" />
            </div>
          ) : servers.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <Server className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>暂无 MCP 服务器配置</p>
              <p className="text-xs mt-1">点击"导入配置"添加服务器</p>
            </div>
          ) : (
            <div className="space-y-2">
              {servers.map((server) => (
                <div
                  key={server.name}
                  className={`p-3 rounded-lg border ${getStatusBg(server.status)} transition-colors`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900">{server.name}</span>
                      <span className={`text-xs ${getStatusColor(server.status)}`}>
                        {server.status === 'connected' ? '已连接' :
                         server.status === 'connecting' ? '连接中' :
                         server.status === 'error' ? '错误' : '未连接'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      {server.status === 'connected' ? (
                        <button
                          onClick={() => handleDisconnect(server.name)}
                          disabled={connecting === server.name}
                          className="p-1.5 text-yellow-700 hover:bg-yellow-100 rounded-lg transition-colors disabled:opacity-50"
                          title="断开连接"
                        >
                          {connecting === server.name ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Square className="w-4 h-4" />
                          )}
                        </button>
                      ) : (
                        <button
                          onClick={() => handleConnect(server.name)}
                          disabled={connecting === server.name}
                          className="p-1.5 text-green-700 hover:bg-green-100 rounded-lg transition-colors disabled:opacity-50"
                          title="连接"
                        >
                          {connecting === server.name ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Play className="w-4 h-4" />
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(server.name)}
                        className="p-1.5 text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* 命令 */}
                  <div className="mt-2">
                    <code className="text-xs text-slate-500 font-mono break-all">
                      {server.command}
                    </code>
                  </div>

                  {/* 错误信息 */}
                  {server.error && (
                    <div className="mt-2 flex items-start gap-1 text-red-600">
                      <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                      <span className="text-xs">{server.error}</span>
                    </div>
                  )}

                  {/* 工具列表 */}
                  {server.status === 'connected' && server.tools.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-slate-500 mb-1">工具 ({server.tools.length}):</p>
                      <div className="flex flex-wrap gap-1">
                        {server.tools.map((tool) => (
                          <span
                            key={tool}
                            className="px-1.5 py-0.5 text-xs bg-white border border-slate-200 rounded text-slate-600 font-mono"
                          >
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 底部说明 */}
        <div className="px-5 py-4 border-t border-pink-100 bg-pink-50/30 text-xs text-slate-500">
          MCP (Model Context Protocol) 允许连接外部工具服务。
          配置格式兼容 Claude Desktop。
        </div>
      </div>
    </div>
  );
}
