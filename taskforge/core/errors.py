"""
统一异常处理模块
"""
from functools import wraps
from typing import Callable, Any, TypeVar, Optional
import traceback
import logging

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class AgentError(Exception):
    """Agent 基础异常"""
    pass


class ConfigurationError(AgentError):
    """配置错误"""
    pass


class ToolExecutionError(AgentError):
    """工具执行错误"""
    def __init__(self, tool_name: str, message: str, original_error: Optional[Exception] = None):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class APIError(AgentError):
    """API 调用错误"""
    def __init__(self, message: str, status_code: Optional[int] = None, retry_after: Optional[int] = None):
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(message)


class SecurityError(AgentError):
    """安全相关错误"""
    pass


class PathValidationError(SecurityError):
    """路径验证错误"""
    def __init__(self, path: str, reason: str = "Path escapes workspace"):
        self.path = path
        super().__init__(f"{reason}: {path}")


class CommandBlockedError(SecurityError):
    """命令被阻止错误"""
    def __init__(self, command: str, pattern: str):
        self.command = command
        self.pattern = pattern
        super().__init__(f"Command blocked: matches pattern '{pattern}'")


def handle_errors(default_return: Any = None, reraise: bool = False):
    """
    统一异常处理装饰器

    Args:
        default_return: 发生异常时的默认返回值
        reraise: 是否重新抛出异常
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except AgentError as e:
                logger.error(f"Agent error in {func.__name__}: {e}")
                if reraise:
                    raise
                return default_return
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}\n{traceback.format_exc()}")
                if reraise:
                    raise
                return default_return
        return wrapper  # type: ignore
    return decorator


def handle_api_errors(max_retries: int = 3, backoff_factor: float = 1.0):
    """
    API 调用异常处理装饰器（带重试）

    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子
    """
    import time

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except APIError as e:
                    last_error = e
                    if e.status_code in (401, 403):  # 认证错误不重试
                        raise

                    if attempt < max_retries - 1:
                        delay = backoff_factor * (2 ** attempt)
                        if e.retry_after:
                            delay = max(delay, e.retry_after)
                        logger.warning(
                            f"API error (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)

            raise last_error or APIError("Unknown API error")
        return wrapper  # type: ignore
    return decorator


class ErrorContext:
    """错误上下文管理器"""

    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.error: Optional[Exception] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.error = exc_val
            logger.error(
                f"Error in {self.operation}: {exc_val}\n"
                f"Context: {self.context}\n"
                f"Traceback: {traceback.format_exc()}"
            )
        return False  # 不抑制异常

    def __repr__(self):
        return f"ErrorContext(operation={self.operation!r}, error={self.error!r})"