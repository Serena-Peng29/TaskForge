"""
共享依赖：认证、状态获取、system prompt
"""
from contextvars import ContextVar
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth import get_jwt_manager, AUTH_AVAILABLE
from configurable import get_config
from skill_loader import SKILLS
from user_state import StateManager, UserState, get_state_manager

CONFIG = get_config()

security = HTTPBearer(auto_error=False)

_current_user_state: ContextVar[Optional[UserState]] = ContextVar('current_user_state', default=None)

state_manager = StateManager(CONFIG)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    if not credentials:
        return None
    jwt_manager = get_jwt_manager()
    if not jwt_manager or not jwt_manager.is_available():
        return None
    return jwt_manager.verify_token(credentials.credentials)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jwt_manager = get_jwt_manager()
    if not jwt_manager or not jwt_manager.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service not available")
    user = jwt_manager.verify_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_state_for_user(user: Optional[Dict[str, Any]] = None) -> UserState:
    from api.app import state
    if user:
        return state_manager.get_state(user["user_id"])
    return state


def get_current_state() -> Any:
    user_state = _current_user_state.get()
    if user_state:
        return user_state
    from api.app import state
    return state


def set_current_state(user_state: Optional[UserState]):
    _current_user_state.set(user_state)


DEFAULT_SYSTEM_PROMPT = """You are a coding agent at {workdir}.

Loop: plan -> act with tools -> report.

**Skills available** (invoke with Skill tool when task matches):
{skills}

**Subagents available** (invoke with Task tool for focused subtasks):
{agents}

Rules:
- Use Skill tool IMMEDIATELY when a task matches a skill description
- Use Task tool for subtasks needing focused exploration or implementation
- Use TodoWrite to track multi-step work
- Prefer tools over prose. Act, don't just explain.
- After finishing, summarize what changed."""


def get_system_prompt() -> str:
    from agents import get_agent_descriptions
    current_state = get_current_state()
    template = current_state.custom_system_prompt or DEFAULT_SYSTEM_PROMPT
    return template.format(
        workdir=str(CONFIG.workdir),
        skills=SKILLS.get_descriptions(),
        agents=get_agent_descriptions()
    )
