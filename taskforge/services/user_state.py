"""
多用户状态管理模块
替代全局 AppState，按用户隔离状态
"""
import time
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field

from taskforge.config import Config, get_config
from taskforge.core.agents import AgentClient
from taskforge.integrations.mcp_manager import MCPManager

logger = logging.getLogger(__name__)


@dataclass
class UserState:
    """单个用户的状态"""
    user_id: str
    history: List[dict] = field(default_factory=list)
    agent_client: Optional[AgentClient] = None
    current_session_id: Optional[str] = None
    enabled_tools: List[str] = field(default_factory=list)  # 空列表表示所有工具
    enabled_skills: List[str] = field(default_factory=list)  # 空列表表示所有技能
    current_model: Optional[str] = None
    # 高级配置
    temperature: float = 0.7
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    # 自定义 system prompt
    custom_system_prompt: Optional[str] = None
    # MCP 管理器
    mcp_manager: Optional[MCPManager] = None
    # 最后活动时间
    last_active: float = 0.0

    def __post_init__(self):
        self.last_active = time.time()

    def touch(self):
        """更新最后活动时间"""
        self.last_active = time.time()

    def reset_runtime(self, config: Config) -> None:
        """根据当前配置重建 Agent 和 MCP 运行时"""
        self.agent_client = AgentClient(config)
        self.current_model = config.model
        mcp_config_path = config.workdir / "mcp_config.json"
        self.mcp_manager = MCPManager(mcp_config_path)


class StateManager:
    """
    多用户状态管理器
    管理所有用户的 state 实例，支持过期清理
    """

    def __init__(self, config: Config = None, expire_minutes: int = 60):
        self.config = config or get_config()
        self._states: Dict[str, UserState] = {}
        self._expire_minutes = expire_minutes

    def get_state(self, user_id: str) -> UserState:
        """获取用户状态，如果不存在则创建"""
        if user_id not in self._states:
            state = UserState(user_id=user_id)
            state.history = []
            state.reset_runtime(self.config)

            self._states[user_id] = state
            logger.info(f"Created new state for user: {user_id}")

        state = self._states[user_id]
        state.touch()
        return state

    def remove_state(self, user_id: str) -> bool:
        """移除用户状态"""
        if user_id in self._states:
            del self._states[user_id]
            logger.info(f"Removed state for user: {user_id}")
            return True
        return False

    def cleanup_expired(self) -> int:
        """清理过期状态，返回清理数量"""
        now = time.time()
        expire_seconds = self._expire_minutes * 60

        expired_users = [
            user_id for user_id, state in self._states.items()
            if now - state.last_active > expire_seconds
        ]

        for user_id in expired_users:
            self.remove_state(user_id)

        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired user states")

        return len(expired_users)

    def get_active_users(self) -> List[str]:
        """获取活跃用户列表"""
        return list(self._states.keys())

    def get_user_count(self) -> int:
        """获取用户数量"""
        return len(self._states)


# 全局状态管理器（延迟初始化）
_STATE_MANAGER: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """获取全局状态管理器"""
    global _STATE_MANAGER
    if _STATE_MANAGER is None:
        _STATE_MANAGER = StateManager()
    return _STATE_MANAGER


def get_user_state(user_id: str) -> UserState:
    """获取用户状态的便捷方法"""
    return get_state_manager().get_state(user_id)
