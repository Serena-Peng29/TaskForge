"""
FastAPI 应用入口 — 组装所有路由
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from spark.config import get_config, logger
from spark.skills.loader import SKILLS
from spark.core.agents import AgentClient
from spark.services.memory import get_memory
from spark.integrations.mcp_manager import get_mcp_manager
from spark.services.auth import init_auth, AUTH_AVAILABLE
from spark.services.user_state import StateManager, UserState

CONFIG = get_config()
MEMORY = get_memory()

# 向后兼容的无认证全局状态
class AppState:
    history = []
    agent_client = None
    current_session_id = None
    enabled_tools = []
    enabled_skills = []
    current_model = None
    temperature = 0.7
    api_key = None
    base_url = None
    custom_system_prompt = None
    mcp_manager = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.deps import get_system_prompt

    state.agent_client = AgentClient(CONFIG)
    state.history = [{"role": "system", "content": get_system_prompt()}]
    state.current_model = CONFIG.model

    mcp_config_path = CONFIG.workdir / "mcp_config.json"
    state.mcp_manager = get_mcp_manager(mcp_config_path)
    logger.info(f"MCP Manager initialized, available: {state.mcp_manager.is_available()}")

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

    default_user_id = "default"
    sessions = MEMORY.list_sessions(default_user_id)
    if sessions:
        last_session = sessions[0]
        state.current_session_id = last_session.id
        session_data = MEMORY.get_session(last_session.id, default_user_id)
        if session_data:
            state.history = [{"role": "system", "content": get_system_prompt()}] + session_data.get("messages", [])
            logger.info(f"Loaded session {last_session.id} for default user")
    else:
        state.current_session_id = MEMORY.create_session(None, default_user_id)
        logger.info(f"Created new session: {state.current_session_id} for default user")

    yield

    if state.current_session_id and len(state.history) > 1:
        MEMORY.save_session_by_id(state.current_session_id, state.history, default_user_id)
        logger.info(f"Session {state.current_session_id} saved for default user")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Spark Agent API",
        description="AI Coding Assistant API with SSE streaming",
        version="1.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from api.routers.auth import router as auth_router
    from api.routers.sessions import router as sessions_router
    from api.routers.memories import router as memories_router
    from api.routers.mcp import router as mcp_router
    from api.routers.general import router as general_router
    from api.routers.chat import router as chat_router

    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(memories_router)
    app.include_router(mcp_router)
    app.include_router(general_router)
    app.include_router(chat_router)

    return app


app = create_app()


def run_server(host: str = "0.0.0.0", port: int = 8000):
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
