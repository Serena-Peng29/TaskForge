import { useState } from 'react';

interface LoginModalProps {
  onLogin: (username: string, password: string) => Promise<unknown>;
  onRegister: (username: string, password: string) => Promise<unknown>;
  isLoading: boolean;
  error: string | null;
  authAvailable: boolean;
}

export function LoginModal({ onLogin, onRegister, isLoading, error, authAvailable }: LoginModalProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (!username.trim()) {
      setLocalError('请输入用户名');
      return;
    }

    if (!password) {
      setLocalError('请输入密码');
      return;
    }

    if (mode === 'register' && password !== confirmPassword) {
      setLocalError('两次输入的密码不一致');
      return;
    }

    if (mode === 'register' && password.length < 6) {
      setLocalError('密码至少需要6个字符');
      return;
    }

    try {
      if (mode === 'login') {
        await onLogin(username, password);
      } else {
        await onRegister(username, password);
      }
    } catch {
      // Error is handled by parent component
    }
  };

  const switchMode = () => {
    setMode(mode === 'login' ? 'register' : 'login');
    setLocalError(null);
    setPassword('');
    setConfirmPassword('');
  };

  if (!authAvailable) {
    return (
      <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
        <div className="bg-gray-900 rounded-lg p-8 max-w-md w-full mx-4 text-center">
          <div className="text-yellow-500 text-5xl mb-4">!</div>
          <h2 className="text-xl font-bold text-gray-100 mb-2">认证系统不可用</h2>
          <p className="text-gray-400 mb-4">
            用户认证功能需要安装 python-jose 和 passlib 库。
          </p>
          <p className="text-gray-500 text-sm mb-6">
            请运行: pip install "python-jose[cryptography]" "passlib[bcrypt]"
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg p-8 max-w-md w-full mx-4">
        <h2 className="text-2xl font-bold text-gray-100 mb-6 text-center">
          {mode === 'login' ? '登录' : '注册'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-100 focus:outline-none focus:border-blue-500"
              placeholder="输入用户名"
              disabled={isLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-100 focus:outline-none focus:border-blue-500"
              placeholder="输入密码"
              disabled={isLoading}
            />
          </div>

          {mode === 'register' && (
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                确认密码
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-100 focus:outline-none focus:border-blue-500"
                placeholder="再次输入密码"
                disabled={isLoading}
              />
            </div>
          )}

          {(localError || error) && (
            <div className="text-red-400 text-sm bg-red-900/30 px-3 py-2 rounded">
              {localError || error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? '处理中...' : (mode === 'login' ? '登录' : '注册')}
          </button>
        </form>

        <div className="mt-4 text-center text-gray-400 text-sm">
          {mode === 'login' ? (
            <>
              还没有账号？{' '}
              <button
                onClick={switchMode}
                className="text-blue-400 hover:text-blue-300"
              >
                立即注册
              </button>
            </>
          ) : (
            <>
              已有账号？{' '}
              <button
                onClick={switchMode}
                className="text-blue-400 hover:text-blue-300"
              >
                立即登录
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}