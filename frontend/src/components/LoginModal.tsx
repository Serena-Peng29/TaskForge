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
      <div className="fixed inset-0 bg-[#fff7fb]/90 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl border border-pink-100 p-8 max-w-md w-full mx-4 text-center shadow-2xl">
          <div className="text-yellow-500 text-5xl mb-4">!</div>
          <h2 className="text-xl font-bold text-slate-900 mb-2">认证系统不可用</h2>
          <p className="text-slate-500 mb-4">
            用户认证功能需要安装 python-jose 和 passlib 库。
          </p>
          <p className="text-slate-400 text-sm mb-6">
            请运行: pip install "python-jose[cryptography]" "passlib[bcrypt]"
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-pink-500 text-white rounded-lg hover:bg-pink-600"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-[#fff7fb] taskforge-canvas-bg flex items-center justify-center z-50">
      <div className="bg-white/90 rounded-2xl border border-pink-100 p-8 max-w-md w-full mx-4 shadow-2xl backdrop-blur">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-pink-100 text-2xl font-bold text-pink-600">
            T
          </div>
        <h2 className="text-2xl font-bold text-slate-900">
          {mode === 'login' ? '登录' : '注册'}
        </h2>
          <p className="mt-1 text-sm text-slate-500">进入 TaskForge 编程工作台</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70"
              placeholder="输入用户名"
              disabled={isLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70"
              placeholder="输入密码"
              disabled={isLoading}
            />
          </div>

          {mode === 'register' && (
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">
                确认密码
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-pink-300 focus:ring-4 focus:ring-pink-100/70"
                placeholder="再次输入密码"
                disabled={isLoading}
              />
            </div>
          )}

          {(localError || error) && (
            <div className="text-red-600 text-sm bg-red-50 border border-red-100 px-3 py-2 rounded-lg">
              {localError || error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 bg-pink-500 text-white rounded-lg hover:bg-pink-600 disabled:bg-pink-200 disabled:cursor-not-allowed transition-colors font-semibold"
          >
            {isLoading ? '处理中...' : (mode === 'login' ? '登录' : '注册')}
          </button>
        </form>

        <div className="mt-4 text-center text-slate-500 text-sm">
          {mode === 'login' ? (
            <>
              还没有账号？{' '}
              <button
                onClick={switchMode}
                className="text-pink-500 hover:text-pink-600"
              >
                立即注册
              </button>
            </>
          ) : (
            <>
              已有账号？{' '}
              <button
                onClick={switchMode}
                className="text-pink-500 hover:text-pink-600"
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
