import { useState, useCallback, useEffect } from 'react';
import { User, AuthStatus } from '../types';
import * as api from '../api/client';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 检查认证系统状态
  const checkAuthStatus = useCallback(async () => {
    try {
      const status = await api.getAuthStatus();
      setAuthStatus(status);
      return status;
    } catch (err) {
      console.error('Failed to check auth status:', err);
      return null;
    }
  }, []);

  // 检查是否已登录
  const checkAuth = useCallback(async () => {
    setIsLoading(true);
    try {
      // 先检查认证系统状态
      const status = await checkAuthStatus();

      // 如果认证系统不可用，直接进入应用
      if (!status || !status.available) {
        setIsAuthenticated(true);
        setIsLoading(false);
        return;
      }

      // 如果有 token，验证并获取用户信息
      const token = api.getAuthToken();
      if (token) {
        const userData = await api.getCurrentUser();
        setUser(userData);
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      // Token 无效，清除
      api.logout();
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, [checkAuthStatus]);

  // 登录
  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.login(username, password);
      setUser({
        id: response.user_id,
        username: response.username,
        created_at: '',
        is_active: true,
      });
      setIsAuthenticated(true);
      return response;
    } catch (err: any) {
      const message = err.message || '登录失败';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 注册
  const register = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const user = await api.register(username, password);
      // 注册成功后自动登录
      await login(username, password);
      return user;
    } catch (err: any) {
      const message = err.message || '注册失败';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [login]);

  // 登出
  const logout = useCallback(() => {
    api.logout();
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  // 初始化检查
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return {
    user,
    isLoading,
    isAuthenticated,
    authStatus,
    error,
    login,
    register,
    logout,
    checkAuth,
    checkAuthStatus,
  };
}