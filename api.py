"""
Spark Agent Web API
FastAPI 服务器，提供 SSE 流式响应
"""
import json
import asyncio
from typing import AsyncGenerator, List, Optional, Dict, Any
from dataclasses import asdict
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# 初始化配置
from configurable import get_config, init_config, logger
CONFIG = get_config()

from SkillLoader import get_skills, SKILLS as _SKILLS
SKILLS = _SKILLS or get_skills()

from Agents import AgentClient, AGENT_TYPES, TOKEN_USAGE
from memory import get_memory, MEMORY as _MEMORY
MEMORY = _MEMORY or get_memory()
from tools.base import TOOLS
from mcp_manager import get_mcp_manager, MCPManager

# 用户认证模块
from auth import init_auth, get_user_manager, get_jwt_manager, UserManager, JWTManager, AUTH_AVAILABLE
from user_state import StateManager, UserState, get_state_manager, get_user_state

# 当前请求的用户状态上下文变量
_current_user_state: ContextVar[Optional[UserState]] = ContextVar('current_user_state', default=None)


# 认证安全方案
security = HTTPBearer(auto_error=False)


# 全局状态管理器
state_manager = StateManager(CONFIG)


# 用于无需认证的默认用户状态（向后兼容）
class AppState:
    history: List[dict] = []
    agent_client: Optional[AgentClient] = None
    current_session_id: Optional[str] = None
    enabled_tools: List[str] = []  # 空列表表示所有工具
    enabled_skills: List[str] = []  # 空列表表示所有技能
    current_model: Optional[str] = None
    # 高级配置
    temperature: float = 0.7
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    # 自定义 system prompt
    custom_system_prompt: Optional[str] = None
    # MCP 管理器
    mcp_manager: Optional[MCPManager] = None


state = AppState()


# ==================== 认证依赖 ====================

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    """可选的用户认证 - 无 token 时返回 None"""
    if not credentials:
        return None

    jwt_manager = get_jwt_manager()
    if not jwt_manager or not jwt_manager.is_available():
        return None

    token = credentials.credentials
    return jwt_manager.verify_token(token)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """必需的用户认证 - 无 token 时返回 401"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_manager = get_jwt_manager()
    if not jwt_manager or not jwt_manager.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )

    token = credentials.credentials
    user = jwt_manager.verify_token(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_state_for_user(user: Optional[Dict[str, Any]] = None) -> UserState:
    """获取用户状态，无用户时返回默认状态（向后兼容）"""
    if user:
        return state_manager.get_state(user["user_id"])
    # 向后兼容：无认证时使用全局 state
    return state


def get_current_state() -> Any:
    """获取当前请求的状态（优先使用上下文变量中的用户状态）"""
    user_state = _current_user_state.get()
    if user_state:
        return user_state
    return state


def set_current_state(user_state: Optional[UserState]):
    """设置当前请求的用户状态"""
    _current_user_state.set(user_state)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化默认用户状态（向后兼容无认证模式）
    state.agent_client = AgentClient(CONFIG)
    state.history = [{"role": "system", "content": get_system_prompt()}]
    state.current_model = CONFIG.model

    # 初始化 MCP 管理器
    mcp_config_path = CONFIG.workdir / "mcp_config.json"
    state.mcp_manager = get_mcp_manager(mcp_config_path)
    logger.info(f"MCP Manager initialized, available: {state.mcp_manager.is_available()}")

    # 初始化认证模块
    if AUTH_AVAILABLE:
        auth_initialized = init_auth(
            qdrant_host=CONFIG.memory_config.qdrant_host,
            qdrant_port=CONFIG.memory_config.qdrant_port,
            users_collection=CONFIG.auth_config.users_collection,
            jwt_secret=CONFIG.auth_config.jwt_secret,
            jwt_algorithm=CONFIG.auth_config.jwt_algorithm,
            expire_minutes=CONFIG.auth_config.access_token_expire_minutes
        )
        logger.info(f"Auth module initialized: {auth_initialized}")
    else:
        logger.warning("Auth dependencies not available, authentication disabled")

    # 为默认用户创建初始会话或加载上次会话
    default_user_id = "default"
    sessions = MEMORY.list_sessions(default_user_id)
    if sessions:
        # 加载最近的会话
        last_session = sessions[0]
        state.current_session_id = last_session.id
        session_data = MEMORY.get_session(last_session.id, default_user_id)
        if session_data:
            state.history = [{"role": "system", "content": get_system_prompt()}] + session_data.get("messages", [])
            logger.info(f"Loaded session {last_session.id} with {len(session_data.get('messages', []))} messages for default user")
    else:
        # 创建新会话
        state.current_session_id = MEMORY.create_session(None, default_user_id)
        logger.info(f"Created new session: {state.current_session_id} for default user")

    yield

    # 关闭时保存默认用户的会话
    if state.current_session_id and len(state.history) > 1:
        MEMORY.save_session_by_id(state.current_session_id, state.history, default_user_id)
        logger.info(f"Session {state.current_session_id} saved for default user")


# 创建 FastAPI 应用
app = FastAPI(
    title="Spark Agent API",
    description="AI Coding Assistant API with SSE streaming",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    """获取系统提示"""
    from Agents import get_agent_descriptions

    current_state = get_current_state()
    # 使用自定义 prompt 或默认 prompt
    template = current_state.custom_system_prompt or DEFAULT_SYSTEM_PROMPT

    # 替换动态变量
    return template.format(
        workdir=str(CONFIG.workdir),
        skills=SKILLS.get_descriptions(),
        agents=get_agent_descriptions()
    )


def get_memory_context(message: str, user_id: str = "default") -> str:
    """获取与当前消息相关的记忆上下文"""
    if not MEMORY.is_long_term_memory_available():
        return ""

    try:
        # 搜索相关记忆
        memories = MEMORY.search_memories(message, user_id, limit=5)
        if not memories:
            return ""

        # 格式化记忆
        memory_text = "\n".join([
            f"- {m.get('memory', str(m))}"
            for m in memories
        ])

        return f"\n\n[User Memories (remember these across all sessions)]:\n{memory_text}\n"
    except Exception as e:
        logger.error(f"Failed to get memory context: {e}")
        return ""


# Pydantic 模型
class ChatRequest(BaseModel):
    message: str
    stream: bool = True
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    content: str
    tool_calls: List[dict] = []


class SkillInfo(BaseModel):
    name: str
    description: str
    enabled: bool = True


class ToolInfo(BaseModel):
    name: str
    description: str
    enabled: bool = True


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str = "openai"


class SessionInfo(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionUpdate(BaseModel):
    title: Optional[str] = None


class ConfigUpdate(BaseModel):
    model: Optional[str] = None
    enabled_tools: Optional[List[str]] = None
    enabled_skills: Optional[List[str]] = None
    temperature: Optional[float] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class PromptUpdate(BaseModel):
    custom_prompt: Optional[str] = None  # None 表示恢复默认


class HistoryResponse(BaseModel):
    messages: List[dict]
    count: int


class MemoryItem(BaseModel):
    id: str
    memory: str
    user_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MemoryAddRequest(BaseModel):
    content: str
    user_id: str = "default"


class MemorySearchRequest(BaseModel):
    query: str
    user_id: str = "default"
    limit: int = 10


class MemoryUpdateRequest(BaseModel):
    content: str


# ==================== 认证相关模型 ====================

class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒
    user_id: str
    username: str


class UserInfo(BaseModel):
    id: str
    username: str
    created_at: str
    is_active: bool


class StatusResponse(BaseModel):
    token_usage: dict
    message_count: int
    skills: List[str]
    current_session: Optional[str] = None
    current_model: str


class AppConfigResponse(BaseModel):
    model: str
    enabled_tools: List[str]
    enabled_skills: List[str]
    available_models: List[ModelInfo]
    temperature: float = 0.7
    api_key: Optional[str] = None
    base_url: Optional[str] = None


# ==================== 认证 API 端点 ====================

@app.post("/api/auth/register", response_model=UserInfo)
async def register(request: UserRegister):
    """用户注册"""
    from auth import UserExistsError, AuthError

    user_manager = get_user_manager()
    if not user_manager or not user_manager.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User registration service not available"
        )

    # 验证用户名和密码
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # 创建用户
    try:
        user = user_manager.create_user(request.username, request.password)
    except UserExistsError:
        raise HTTPException(status_code=400, detail="Username already exists")
    except AuthError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return UserInfo(
        id=user.id,
        username=user.username,
        created_at=user.created_at,
        is_active=user.is_active
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: UserLogin):
    """用户登录"""
    user_manager = get_user_manager()
    jwt_manager = get_jwt_manager()

    if not user_manager or not user_manager.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )

    if not jwt_manager or not jwt_manager.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token service not available"
        )

    # 验证用户
    user = user_manager.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建 token
    token = jwt_manager.create_access_token(user)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token"
        )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=CONFIG.auth_config.access_token_expire_minutes * 60,
        user_id=user.id,
        username=user.username
    )


@app.get("/api/auth/me", response_model=UserInfo)
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """获取当前用户信息"""
    user_manager = get_user_manager()
    if not user_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service not available"
        )

    user = user_manager.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserInfo(
        id=user.id,
        username=user.username,
        created_at=user.created_at,
        is_active=user.is_active
    )


@app.get("/api/auth/status")
async def get_auth_status():
    """获取认证服务状态"""
    user_manager = get_user_manager()
    jwt_manager = get_jwt_manager()

    return {
        "available": AUTH_AVAILABLE and (user_manager is not None and user_manager.is_available()),
        "user_manager": user_manager is not None and user_manager.is_available(),
        "jwt_manager": jwt_manager is not None and jwt_manager.is_available()
    }


# API 端点
@app.get("/api/files/{filename:path}")
async def get_file(filename: str):
    """获取工作目录中的文件（如截图）"""
    import mimetypes
    from pathlib import Path as PathLib

    file_path = CONFIG.workdir / filename
    logger.info(f"File request: {filename}, workdir: {CONFIG.workdir}, resolved path: {file_path}, exists: {file_path.exists()}")

    # 安全检查：确保文件在工作目录内
    try:
        file_path.resolve().relative_to(CONFIG.workdir.resolve())
    except ValueError:
        logger.warning(f"Access denied for path: {file_path}")
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # 获取 MIME 类型
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=filename
    )


@app.get("/api/skills", response_model=List[SkillInfo])
async def get_skills_list(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取可用技能列表"""
    current_state = get_state_for_user(current_user)
    skills = []
    for name, skill in SKILLS.skills.items():
        enabled = not current_state.enabled_skills or name in current_state.enabled_skills
        skills.append(SkillInfo(name=name, description=skill["description"], enabled=enabled))
    return skills


@app.get("/api/history", response_model=HistoryResponse)
async def get_history(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取历史会话"""
    current_state = get_state_for_user(current_user)
    # 过滤掉系统消息
    messages = [
        msg for msg in current_state.history
        if msg.get("role") != "system"
    ]
    return HistoryResponse(messages=messages, count=len(messages))


@app.post("/api/clear")
async def clear_history(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """清除当前会话历史"""
    current_state = get_state_for_user(current_user)
    set_current_state(current_state)
    current_state.history = [{"role": "system", "content": get_system_prompt()}]
    return {"status": "cleared"}


@app.get("/api/status", response_model=StatusResponse)
async def get_status(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取当前状态"""
    current_state = get_state_for_user(current_user)
    return StatusResponse(
        token_usage={
            "input": TOKEN_USAGE.total_input,
            "output": TOKEN_USAGE.total_output,
            "calls": TOKEN_USAGE.call_count
        },
        message_count=len(current_state.history),
        skills=SKILLS.list_skills(),
        current_session=current_state.current_session_id,
        current_model=current_state.current_model or CONFIG.model
    )


@app.get("/api/agents")
async def get_agents():
    """获取可用代理类型"""
    return [
        {"name": name, "description": agent.description}
        for name, agent in AGENT_TYPES.items()
    ]


# ==================== 会话管理 API ====================

def _get_user_id(user: Optional[Dict[str, Any]]) -> str:
    """获取用户ID，无用户时返回默认值"""
    return user["user_id"] if user else "default"


@app.get("/api/sessions", response_model=List[SessionInfo])
async def list_sessions(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取用户的会话列表"""
    user_id = _get_user_id(current_user)
    sessions = MEMORY.list_sessions(user_id)
    return [
        SessionInfo(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=s.message_count
        )
        for s in sessions
    ]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取指定会话"""
    user_id = _get_user_id(current_user)
    session = MEMORY.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/api/sessions/new", response_model=SessionInfo)
async def create_new_session(request: SessionCreate = None, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """创建新会话"""
    user_id = _get_user_id(current_user)
    title = request.title if request else None
    session_id = MEMORY.create_session(title, user_id)
    sessions = MEMORY.list_sessions(user_id)
    for s in sessions:
        if s.id == session_id:
            return SessionInfo(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=s.message_count
            )
    raise HTTPException(status_code=500, detail="Failed to create session")


@app.post("/api/sessions/{session_id}/switch")
async def switch_session(session_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """切换到指定会话"""
    user_id = _get_user_id(current_user)
    current_state = get_state_for_user(current_user)
    session = MEMORY.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 保存当前会话
    if current_state.current_session_id and len(current_state.history) > 1:
        MEMORY.save_session_by_id(current_state.current_session_id, current_state.history, user_id)

    # 切换会话
    current_state.current_session_id = session_id
    set_current_state(current_state)
    current_state.history = [{"role": "system", "content": get_system_prompt()}] + session.get("messages", [])

    return {
        "status": "switched",
        "session_id": session_id,
        "message_count": len(session.get("messages", []))
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """删除指定会话"""
    user_id = _get_user_id(current_user)
    current_state = get_state_for_user(current_user)
    if session_id == current_state.current_session_id:
        raise HTTPException(status_code=400, detail="Cannot delete current session")

    success = MEMORY.delete_session(session_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or delete failed")

    return {"status": "deleted", "session_id": session_id}


@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, request: SessionUpdate, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """更新会话（重命名）"""
    user_id = _get_user_id(current_user)
    if request.title:
        success = MEMORY.rename_session(session_id, request.title, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or rename failed")

    return {"status": "updated", "session_id": session_id}


# ==================== 长期记忆管理 API ====================

@app.get("/api/memories")
async def get_memories(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取所有长期记忆"""
    if not MEMORY.is_long_term_memory_available():
        raise HTTPException(status_code=503, detail="Long-term memory service not available. Check Qdrant connection.")

    # 使用当前用户ID
    user_id = current_user["user_id"] if current_user else "default"
    memories = MEMORY.get_all_memories(user_id)
    return {
        "user_id": user_id,
        "count": len(memories),
        "memories": memories
    }


@app.post("/api/memories")
async def add_memory(request: MemoryAddRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """手动添加长期记忆"""
    if not MEMORY.is_long_term_memory_available():
        raise HTTPException(status_code=503, detail="Long-term memory service not available. Check Qdrant connection.")

    # 使用当前用户ID（优先使用认证用户ID）
    user_id = current_user["user_id"] if current_user else request.user_id
    result = MEMORY.add_memory(request.content, user_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to add memory")

    return {
        "status": "added",
        "content": request.content,
        "user_id": user_id,
        "result": result
    }


@app.post("/api/memories/search")
async def search_memories(request: MemorySearchRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """语义搜索长期记忆"""
    if not MEMORY.is_long_term_memory_available():
        raise HTTPException(status_code=503, detail="Long-term memory service not available. Check Qdrant connection.")

    # 使用当前用户ID（优先使用认证用户ID）
    user_id = current_user["user_id"] if current_user else request.user_id
    results = MEMORY.search_memories(request.query, user_id, request.limit)
    return {
        "query": request.query,
        "user_id": user_id,
        "count": len(results),
        "results": results
    }


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """删除指定长期记忆"""
    if not MEMORY.is_long_term_memory_available():
        raise HTTPException(status_code=503, detail="Long-term memory service not available. Check Qdrant connection.")

    success = MEMORY.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found or delete failed")

    return {"status": "deleted", "memory_id": memory_id}


@app.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, request: MemoryUpdateRequest):
    """更新指定长期记忆"""
    if not MEMORY.is_long_term_memory_available():
        raise HTTPException(status_code=503, detail="Long-term memory service not available. Check Qdrant connection.")

    success = MEMORY.update_memory(memory_id, request.content)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found or update failed")

    return {"status": "updated", "memory_id": memory_id, "content": request.content}


# ==================== 工具管理 API ====================

@app.get("/api/tools", response_model=List[ToolInfo])
async def get_tools_list(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取可用工具列表"""
    current_state = get_state_for_user(current_user)
    tools = []
    for schema in TOOLS.get_all_schemas():
        name = schema["function"]["name"]
        description = schema["function"]["description"]
        enabled = not current_state.enabled_tools or name in current_state.enabled_tools
        tools.append(ToolInfo(name=name, description=description, enabled=enabled))
    return tools


# ==================== 模型管理 API ====================

# 预定义的模型列表（可从配置文件扩展）
AVAILABLE_MODELS = [
    ModelInfo(id="global.anthropic.claude-opus-4-5-20251101-v1:0", name="Claude Opus 4.5", provider="anthropic"),
    ModelInfo(id="global.anthropic.claude-sonnet-4-5-20250514-v1:0", name="Claude Sonnet 4.5", provider="anthropic"),
    ModelInfo(id="global.anthropic.claude-haiku-3-5-20241022-v1:0", name="Claude Haiku 3.5", provider="anthropic"),
    ModelInfo(id="gpt-4o", name="GPT-4o", provider="openai"),
    ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", provider="openai"),
]


# ==================== 文件上传配置 ====================

UPLOAD_DIR = CONFIG.workdir / "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
    ".md", ".html", ".css", ".xml", ".csv", ".sh", ".bash", ".sql",
    ".c", ".cpp", ".h", ".hpp", ".java", ".go", ".rs", ".rb", ".php",
    ".swift", ".kt", ".scala", ".lua", ".r", ".m", ".toml", ".ini", ".env",
    ".docx"
}


class UploadResponse(BaseModel):
    filename: str
    content: str
    size: int
    type: str


def validate_file(filename: str, size: int) -> tuple[bool, str]:
    """验证文件类型和大小"""
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' is not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    if size > MAX_FILE_SIZE:
        return False, f"File size ({size / 1024 / 1024:.2f}MB) exceeds limit ({MAX_FILE_SIZE / 1024 / 1024}MB)"
    return True, ""


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文件并返回内容"""
    import os

    # 读取文件内容
    content_bytes = await file.read()
    size = len(content_bytes)

    # 验证文件
    valid, error_msg = validate_file(file.filename or "unknown", size)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # 获取文件类型
    ext = os.path.splitext(file.filename or "")[1].lower()

    # 根据文件类型解析内容
    if ext == ".docx":
        try:
            from docx import Document
            import io
            doc = Document(io.BytesIO(content_bytes))
            content = "\n".join([para.text for para in doc.paragraphs])
        except ImportError:
            raise HTTPException(status_code=500, detail="python-docx not installed. Run: pip install python-docx")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse docx: {str(e)}")
    else:
        # 普通文本文件
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    return UploadResponse(
        filename=file.filename or "unknown",
        content=content,
        size=size,
        type=ext
    )


@app.get("/api/models", response_model=List[ModelInfo])
async def get_models_list():
    """获取可用模型列表"""
    return AVAILABLE_MODELS


# ==================== 配置管理 API ====================

@app.get("/api/config", response_model=AppConfigResponse)
async def get_config(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取当前配置"""
    current_state = get_state_for_user(current_user)
    return AppConfigResponse(
        model=current_state.current_model or CONFIG.model,
        enabled_tools=current_state.enabled_tools,
        enabled_skills=current_state.enabled_skills,
        available_models=AVAILABLE_MODELS,
        temperature=current_state.temperature,
        api_key=current_state.api_key,
        base_url=current_state.base_url or CONFIG.base_url
    )


@app.post("/api/config")
async def update_config(request: ConfigUpdate, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """更新配置"""
    current_state = get_state_for_user(current_user)
    if request.model:
        current_state.current_model = request.model
        # 更新 agent client 的模型
        if current_state.agent_client:
            current_state.agent_client.config.model = request.model

    if request.enabled_tools is not None:
        current_state.enabled_tools = request.enabled_tools

    if request.enabled_skills is not None:
        current_state.enabled_skills = request.enabled_skills

    if request.temperature is not None:
        current_state.temperature = request.temperature
        if current_state.agent_client:
            current_state.agent_client.config.temperature = request.temperature

    if request.api_key is not None:
        current_state.api_key = request.api_key
        # 需要重新创建客户端
        if current_state.agent_client:
            current_state.agent_client.client.api_key = request.api_key

    if request.base_url is not None:
        current_state.base_url = request.base_url
        # 需要重新创建客户端
        if current_state.agent_client:
            current_state.agent_client.client.base_url = request.base_url

    return {
        "status": "updated",
        "model": current_state.current_model,
        "enabled_tools": current_state.enabled_tools,
        "enabled_skills": current_state.enabled_skills,
        "temperature": current_state.temperature,
        "api_key": "***" if current_state.api_key else None,
        "base_url": current_state.base_url
    }


# ==================== Prompt 管理 API ====================

@app.get("/api/prompt")
async def get_prompt(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取当前 system prompt 配置"""
    current_state = get_state_for_user(current_user)
    set_current_state(current_state)
    return {
        "default_prompt": DEFAULT_SYSTEM_PROMPT,
        "custom_prompt": current_state.custom_system_prompt,
        "current_prompt": get_system_prompt()
    }


@app.post("/api/prompt")
async def update_prompt(request: PromptUpdate, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """更新自定义 system prompt"""
    current_state = get_state_for_user(current_user)
    current_state.custom_system_prompt = request.custom_prompt
    set_current_state(current_state)

    # 更新当前历史中的 system prompt
    if current_state.history and current_state.history[0].get("role") == "system":
        current_state.history[0]["content"] = get_system_prompt()

    return {
        "status": "updated",
        "custom_prompt": current_state.custom_system_prompt,
        "current_prompt": get_system_prompt()
    }


@app.post("/api/prompt/reset")
async def reset_prompt(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """重置为默认 prompt"""
    current_state = get_state_for_user(current_user)
    current_state.custom_system_prompt = None
    set_current_state(current_state)

    # 更新当前历史中的 system prompt
    if current_state.history and current_state.history[0].get("role") == "system":
        current_state.history[0]["content"] = get_system_prompt()

    return {
        "status": "reset",
        "current_prompt": get_system_prompt()
    }


# ==================== MCP 管理 API ====================

class MCPServerInfo(BaseModel):
    name: str
    status: str
    error: Optional[str] = None
    tools: List[str] = []
    command: str = ""
    env: Dict[str, str] = {}


class MCPServerAddRequest(BaseModel):
    name: str
    command: str
    env: Dict[str, str] = {}


class MCPConfigImportRequest(BaseModel):
    config: dict  # Claude Desktop 格式的配置


@app.get("/api/mcp/status")
async def get_mcp_status(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取 MCP 功能状态"""
    current_state = get_state_for_user(current_user)
    if not current_state.mcp_manager:
        return {
            "available": False,
            "message": "MCP Manager not initialized"
        }
    return {
        "available": current_state.mcp_manager.is_available(),
        "servers_count": len(current_state.mcp_manager.list_servers()),
        "tools_count": len(current_state.mcp_manager.get_all_tools())
    }


@app.get("/api/mcp/servers", response_model=List[MCPServerInfo])
async def get_mcp_servers(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取所有 MCP servers 及状态"""
    current_state = get_state_for_user(current_user)
    if not current_state.mcp_manager:
        return []

    servers_info = []
    # 从配置文件获取所有已配置的服务器
    config = current_state.mcp_manager.load_config_from_file()
    configured_servers = config.get("mcpServers", {})

    for name, server_cfg in configured_servers.items():
        status = current_state.mcp_manager.get_server_status(name)
        servers_info.append(MCPServerInfo(
            name=name,
            status=status.status if status else "disconnected",
            error=status.error if status else None,
            tools=status.tools if status else [],
            command=server_cfg.get("command", ""),
            env=server_cfg.get("env", {})
        ))

    return servers_info


@app.post("/api/mcp/servers")
async def add_mcp_server(request: MCPServerAddRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """添加 MCP server 配置"""
    current_state = get_state_for_user(current_user)
    if not current_state.mcp_manager:
        raise HTTPException(status_code=503, detail="MCP Manager not initialized")

    # 加载现有配置
    config = current_state.mcp_manager.load_config_from_file()
    mcp_servers = config.get("mcpServers", {})

    # 添加新服务器
    mcp_servers[request.name] = {
        "command": request.command,
        "env": request.env
    }
    config["mcpServers"] = mcp_servers

    # 保存配置
    if not current_state.mcp_manager.save_config(config):
        raise HTTPException(status_code=500, detail="Failed to save MCP config")

    return {"status": "added", "name": request.name}


@app.delete("/api/mcp/servers/{name}")
async def delete_mcp_server(name: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """删除 MCP server"""
    current_state = get_state_for_user(current_user)
    if not current_state.mcp_manager:
        raise HTTPException(status_code=503, detail="MCP Manager not initialized")

    # 先断开连接
    if current_state.mcp_manager.has_server(name):
        await current_state.mcp_manager.disconnect_server(name)

    # 从配置中删除
    config = current_state.mcp_manager.load_config_from_file()
    mcp_servers = config.get("mcpServers", {})

    if name not in mcp_servers:
        raise HTTPException(status_code=404, detail="Server not found in config")

    del mcp_servers[name]
    config["mcpServers"] = mcp_servers

    if not current_state.mcp_manager.save_config(config):
        raise HTTPException(status_code=500, detail="Failed to save MCP config")

    return {"status": "deleted", "name": name}


@app.post("/api/mcp/servers/{name}/connect")
async def connect_mcp_server(name: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """连接 MCP server"""
    current_state = get_state_for_user(current_user)
    if not current_state.mcp_manager:
        raise HTTPException(status_code=503, detail="MCP Manager not initialized")

    # 获取配置
    config = current_state.mcp_manager.load_config_from_file()
    mcp_servers = config.get("mcpServers", {})

    if name not in mcp_servers:
        raise HTTPException(status_code=404, detail="Server not found in config")

    server_config = mcp_servers[name]

    # 连接
    status = await current_state.mcp_manager.connect_server(name, server_config)

    return {
        "status": status.status,
        "name": name,
        "error": status.error,
        "tools": status.tools
    }


@app.post("/api/mcp/servers/{name}/disconnect")
async def disconnect_mcp_server(name: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """断开 MCP server"""
    current_state = get_state_for_user(current_user)
    if not current_state.mcp_manager:
        raise HTTPException(status_code=503, detail="MCP Manager not initialized")

    success = await current_state.mcp_manager.disconnect_server(name)

    if not success:
        raise HTTPException(status_code=404, detail="Server not connected")

    return {"status": "disconnected", "name": name}


@app.get("/api/mcp/tools")
async def get_mcp_tools(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """获取所有 MCP 工具"""
    current_state = get_state_for_user(current_user)
    if not current_state.mcp_manager:
        return {"tools": [], "count": 0}

    tools = current_state.mcp_manager.get_tool_schemas()
    return {
        "tools": tools,
        "count": len(tools)
    }


@app.post("/api/mcp/import")
async def import_mcp_config(request: MCPConfigImportRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """导入 Claude Desktop 格式的 MCP 配置"""
    current_state = get_state_for_user(current_user)
    if not current_state.mcp_manager:
        raise HTTPException(status_code=503, detail="MCP Manager not initialized")

    # 保存配置
    if not current_state.mcp_manager.save_config(request.config):
        raise HTTPException(status_code=500, detail="Failed to save MCP config")

    # 尝试连接所有服务器
    results = await current_state.mcp_manager.load_config(request.config)

    return {
        "status": "imported",
        "servers": {name: status.status for name, status in results.items()},
        "errors": {name: status.error for name, status in results.items() if status.error}
    }


def get_filtered_tools() -> List[dict]:
    """根据配置过滤可用工具"""
    current_state = get_current_state()
    all_tools = TOOLS.get_all_schemas()

    # 添加 MCP 工具
    if current_state.mcp_manager and current_state.mcp_manager.is_available():
        mcp_tools = current_state.mcp_manager.get_tool_schemas()
        all_tools.extend(mcp_tools)

    if not current_state.enabled_tools:
        return all_tools
    return [t for t in all_tools if t["function"]["name"] in current_state.enabled_tools]


def extract_memories_from_conversation(user_message: str, assistant_message: str) -> List[str]:
    """
    从对话中提取值得记忆的信息
    返回提取的记忆列表
    """
    memories = []

    # 简单规则：检测用户偏好、重要事实等
    # 可以扩展为调用 LLM 进行更智能的提取

    # 1. 检测用户偏好声明
    preference_patterns = [
        r"我(?:喜欢|偏爱|偏好|习惯)(.+)",
        r"我(?:的)?(?:偏好|习惯)是(.+)",
        r"请(?:记住|记得)(.+)",
        r"我(?:想|要)(?:你|你们)(.+)",
    ]

    import re
    for pattern in preference_patterns:
        matches = re.findall(pattern, user_message)
        for match in matches:
            memory = f"用户偏好: {match.strip()}"
            if len(memory) > 10:  # 过滤太短的内容
                memories.append(memory)

    # 2. 检测重要事实（用户明确陈述的信息）
    fact_patterns = [
        r"我(?:是|在|有)(.+)",
        r"我的(.+)",
        r"我们(?:的)?(.+)",
    ]

    for pattern in fact_patterns:
        matches = re.findall(pattern, user_message)
        for match in matches:
            # 避免重复和无关内容
            if len(match) > 5 and "你" not in match:
                memory = f"用户信息: {match.strip()}"
                if memory not in memories:
                    memories.append(memory)

    return memories


def auto_save_memories():
    """自动保存提取的记忆（从历史记录中提取）"""
    if not CONFIG.memory_config.enable_auto_extract:
        return

    if not MEMORY.is_long_term_memory_available():
        return

    try:
        current_state = get_current_state()
        # 从历史记录中提取最近的对话
        user_message = ""
        assistant_message = ""

        # 从后往前找最近的消息
        for msg in reversed(current_state.history):
            if msg.get("role") == "user" and not user_message:
                user_message = msg.get("content", "")
            elif msg.get("role") == "assistant" and not assistant_message:
                assistant_message = msg.get("content", "") or ""
            if user_message and assistant_message:
                break

        if not user_message:
            return

        # 直接把对话内容传给 mem0，让它自动提取记忆
        # mem0 内部会使用 LLM 分析并提取重要信息
        conversation_text = f"用户: {user_message}\n助手: {assistant_message}"
        # 使用当前用户的 ID
        user_id = getattr(current_state, 'user_id', 'default') or 'default'
        result = MEMORY.add_memory(conversation_text, user_id=user_id)

        if result and result.get("results"):
            logger.info(f"Auto-extracted memories: {len(result.get('results', []))} items")
        else:
            logger.debug(f"No new memories extracted from conversation")
    except Exception as e:
        logger.error(f"Failed to auto-save memories: {e}")


def auto_save_session():
    """自动保存当前会话"""
    current_state = get_current_state()
    if not current_state.current_session_id:
        return

    user_id = getattr(current_state, 'user_id', 'default') or 'default'

    try:
        MEMORY.save_session_by_id(current_state.current_session_id, current_state.history, user_id)
        logger.debug(f"Auto-saved session {current_state.current_session_id} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to auto-save session: {e}")


async def stream_chat_response(message: str) -> AsyncGenerator[dict, None]:
    """流式生成聊天响应"""
    from openai.types.chat import ChatCompletionMessageToolCall

    current_state = get_current_state()
    # 获取相关记忆上下文，使用当前用户ID
    user_id = getattr(current_state, 'user_id', 'default') or 'default'
    memory_context = get_memory_context(message, user_id)

    # 如果有记忆上下文，注入为系统消息
    if memory_context:
        current_state.history.append({
            "role": "system",
            "content": memory_context.strip()
        })

    # 添加用户消息
    current_state.history.append({"role": "user", "content": message})
    logger.info(f"User input: {message[:100]}...")

    # 发送开始事件
    yield {"event": "start", "data": json.dumps({"message": message})}

    try:
        # 获取过滤后的工具列表
        tools = get_filtered_tools()

        # 验证历史消息格式
        validated_history = validate_history_messages(current_state.history)

        # 调用 API（流式）
        response = current_state.agent_client.api_call_with_retry(
            validated_history,
            tools,
            stream=True
        )
        # print(f"---------------->\n{response}")

        collected_content = ""
        tool_calls_data = {}

        for chunk in response:
            # 跳过没有 choices 的块（如 usage 信息块）
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # 处理文本内容
            if delta.content:
                collected_content += delta.content
                yield {
                    "event": "content",
                    "data": json.dumps({"content": delta.content})
                }

            # 处理工具调用
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {
                            "id": tc.id,
                            "name": "",
                            "arguments": ""
                        }
                        yield {
                            "event": "tool_start",
                            "data": json.dumps({"index": idx, "id": tc.id})
                        }

                    if tc.function:
                        if tc.function.name:
                            tool_calls_data[idx]["name"] = tc.function.name
                            yield {
                                "event": "tool_name",
                                "data": json.dumps({
                                    "index": idx,
                                    "name": tc.function.name
                                })
                            }
                        if tc.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc.function.arguments
                            yield {
                                "event": "tool_args",
                                "data": json.dumps({
                                    "index": idx,
                                    "args": tc.function.arguments
                                })
                            }

        # 发送内容完成事件
        if collected_content:
            yield {
                "event": "content_done",
                "data": json.dumps({"content": collected_content})
            }

        # 执行工具调用
        if tool_calls_data:
            # 构建工具调用对象
            tool_calls = []
            for idx in sorted(tool_calls_data.keys()):
                data = tool_calls_data[idx]
                tool_calls.append(ChatCompletionMessageToolCall(
                    id=data["id"],
                    function={
                        "name": data["name"],
                        "arguments": data["arguments"]
                    },
                    type="function"
                ))

            # 构建 assistant 消息（使用字典格式，便于 JSON 序列化）
            assistant_message = {
                "role": "assistant",
                "content": collected_content,
                "tool_calls": [{
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in tool_calls]
            }
            current_state.history.append(assistant_message)

            # 执行每个工具
            for tool_call in tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                func_name = tool_call.function.name

                yield {
                    "event": "tool_execute",
                    "data": json.dumps({
                        "name": func_name,
                        "args": args
                    })
                }

                # 执行工具
                result = current_state.agent_client.execute_tool(func_name, args)

                # 发送工具结果
                preview = result[:500] + "..." if len(result) > 500 else result
                yield {
                    "event": "tool_result",
                    "data": json.dumps({
                        "name": func_name,
                        "result": preview
                    })
                }

                # 添加工具结果到历史
                current_state.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

            # 继续循环 - 获取下一轮响应
            async for event in stream_agent_loop():
                yield event

        else:
            # 没有工具调用，直接完成
            current_state.history.append({"role": "assistant", "content": collected_content})
            # 自动提取记忆
            auto_save_memories()
            # 自动保存会话
            auto_save_session()
            yield {"event": "done", "data": json.dumps({"content": collected_content})}

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        yield {"event": "error", "data": json.dumps({"error": str(e)})}


def validate_history_messages(messages: List[dict]) -> List[dict]:
    """验证并修复历史消息格式"""
    validated = []
    for msg in messages:
        msg_copy = dict(msg)

        if "tool_calls" in msg_copy and msg_copy["tool_calls"]:
            valid_tool_calls = []
            for tc in msg_copy["tool_calls"]:
                if isinstance(tc, dict):
                    func = tc.get("function", {})
                    args = func.get("arguments", "")

                    # 确保 arguments 是有效 JSON
                    if args:
                        try:
                            json.loads(args)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping message with invalid tool_call arguments")
                            continue

                    valid_tool_calls.append(tc)
                elif hasattr(tc, 'id') and hasattr(tc, 'function'):
                    # 转换 Pydantic 对象为字典
                    valid_tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": getattr(tc.function, 'name', ''),
                            "arguments": getattr(tc.function, 'arguments', '{}')
                        }
                    })

            msg_copy["tool_calls"] = valid_tool_calls

        validated.append(msg_copy)

    return validated


async def stream_agent_loop() -> AsyncGenerator[dict, None]:
    """Agent 循环，处理工具调用后的继续响应"""
    from openai.types.chat import ChatCompletionMessageToolCall

    current_state = get_current_state()
    # 获取过滤后的工具列表
    tools = get_filtered_tools()

    # 验证历史消息格式
    validated_history = validate_history_messages(current_state.history)

    response = current_state.agent_client.api_call_with_retry(
        validated_history,
        tools,
        stream=True
    )

    collected_content = ""
    tool_calls_data = {}

    for chunk in response:
        # 跳过没有 choices 的块（如 usage 信息块）
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        if delta.content:
            collected_content += delta.content
            yield {
                "event": "content",
                "data": json.dumps({"content": delta.content})
            }

        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_calls_data:
                    tool_calls_data[idx] = {
                        "id": tc.id,
                        "name": "",
                        "arguments": ""
                    }
                    yield {
                        "event": "tool_start",
                        "data": json.dumps({"index": idx, "id": tc.id})
                    }

                if tc.function:
                    if tc.function.name:
                        tool_calls_data[idx]["name"] = tc.function.name
                        yield {
                            "event": "tool_name",
                            "data": json.dumps({
                                "index": idx,
                                "name": tc.function.name
                            })
                        }
                    if tc.function.arguments:
                        tool_calls_data[idx]["arguments"] += tc.function.arguments
                        yield {
                            "event": "tool_args",
                            "data": json.dumps({
                                "index": idx,
                                "args": tc.function.arguments
                            })
                        }

    if collected_content:
        yield {
            "event": "content_done",
            "data": json.dumps({"content": collected_content})
        }

    if tool_calls_data:
        # 第一遍：验证并过滤有效的 tool_calls
        valid_tool_calls = []
        for idx in sorted(tool_calls_data.keys()):
            data = tool_calls_data[idx]
            # 打印完整的 arguments 而不是截断的
            logger.info(f"Tool call {idx}: name={data['name']}, arguments={data['arguments']}")

            # 验证 arguments 是否是有效的 JSON
            if not data['arguments']:
                logger.warning(f"Skipping tool_call {idx} ({data['name']}): empty arguments")
                continue

            try:
                json.loads(data['arguments'])
                valid_tool_calls.append(ChatCompletionMessageToolCall(
                    id=data["id"],
                    function={
                        "name": data["name"],
                        "arguments": data["arguments"]
                    },
                    type="function"
                ))
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping tool_call {idx} ({data['name']}): invalid JSON - {e}")
                continue

        if not valid_tool_calls:
            # 没有有效的 tool_calls，当作普通回复处理
            current_state.history.append({"role": "assistant", "content": collected_content})
            yield {"event": "done", "data": json.dumps({"content": collected_content})}
            return

        # 使用字典格式，避免 JSON 序列化问题
        assistant_message = {
            "role": "assistant",
            "content": collected_content,
            "tool_calls": [{
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            } for tc in valid_tool_calls]
        }
        current_state.history.append(assistant_message)

        for tool_call in valid_tool_calls:
            args = json.loads(tool_call.function.arguments)  # 已验证过，必定有效
            func_name = tool_call.function.name

            logger.info(f"Executing tool {func_name} with args: {args}")

            yield {
                "event": "tool_execute",
                "data": json.dumps({
                    "name": func_name,
                    "args": args
                })
            }

            result = current_state.agent_client.execute_tool(func_name, args)

            preview = result[:500] + "..." if len(result) > 500 else result
            yield {
                "event": "tool_result",
                "data": json.dumps({
                    "name": func_name,
                    "result": preview
                })
            }

            current_state.history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

        # 递归继续
        async for event in stream_agent_loop():
            yield event
    else:
        current_state.history.append({"role": "assistant", "content": collected_content})
        # 自动提取记忆
        auto_save_memories()
        # 自动保存会话
        auto_save_session()
        yield {"event": "done", "data": json.dumps({"content": collected_content})}


@app.post("/api/chat")
async def chat(request: ChatRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """聊天端点 - SSE 流式响应"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # 设置当前用户状态
    user_state = get_state_for_user(current_user)
    set_current_state(user_state)

    if request.stream:
        return EventSourceResponse(stream_chat_response(request.message))
    else:
        # 非流式响应（收集所有内容）
        full_content = ""
        async for event in stream_chat_response(request.message):
            if event.get("event") == "content":
                full_content += json.loads(event["data"])["content"]
            elif event.get("event") in ("done", "error"):
                break

        return {"content": full_content}


@app.post("/api/load")
async def load_session(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """加载最近的会话"""
    user_id = _get_user_id(current_user)
    current_state = get_state_for_user(current_user)
    sessions = MEMORY.list_sessions(user_id)
    if sessions:
        session = sessions[0]
        session_data = MEMORY.get_session(session.id, user_id)
        if session_data:
            current_state.current_session_id = session.id
            set_current_state(current_state)
            current_state.history = [{"role": "system", "content": get_system_prompt()}] + session_data.get("messages", [])
            return {"status": "loaded", "session_id": session.id, "message_count": len(session_data.get("messages", []))}
    return {"status": "no_session"}


@app.post("/api/save")
async def save_session(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """保存当前会话"""
    user_id = _get_user_id(current_user)
    current_state = get_state_for_user(current_user)
    if current_state.current_session_id and MEMORY.save_session_by_id(current_state.current_session_id, current_state.history, user_id):
        return {"status": "saved", "session_id": current_state.current_session_id}
    return {"status": "error", "message": "Failed to save session"}


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """运行服务器"""
    import uvicorn
    print(f"\nStarting Spark Agent Web Server...")
    print(f"  API: http://{host}:{port}")
    print(f"  Docs: http://{host}:{port}/docs")
    print(f"  Model: {CONFIG.model}")
    print(f"  Skills: {', '.join(SKILLS.list_skills()) or 'none'}")
    print()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()