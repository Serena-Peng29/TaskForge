"""
配置、Prompt、工具、技能、模型 API 路由
"""
import os
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse

from configurable import get_config
from skill_loader import SKILLS
from agents import AGENT_TYPES, TOKEN_USAGE
from tools.base import TOOLS
from api.schemas import (
    SkillInfo, ToolInfo, ModelInfo, ConfigUpdate, PromptUpdate,
    AppConfigResponse, StatusResponse, UploadResponse
)
from api.deps import (
    get_current_user_optional, get_state_for_user, set_current_state, get_system_prompt,
    DEFAULT_SYSTEM_PROMPT
)

CONFIG = get_config()

AVAILABLE_MODELS = [
    ModelInfo(id="global.anthropic.claude-opus-4-5-20251101-v1:0", name="Claude Opus 4.5", provider="anthropic"),
    ModelInfo(id="global.anthropic.claude-sonnet-4-5-20250514-v1:0", name="Claude Sonnet 4.5", provider="anthropic"),
    ModelInfo(id="global.anthropic.claude-haiku-3-5-20241022-v1:0", name="Claude Haiku 3.5", provider="anthropic"),
    ModelInfo(id="gpt-4o", name="GPT-4o", provider="openai"),
    ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", provider="openai"),
]

UPLOAD_DIR = CONFIG.workdir / "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
    ".md", ".html", ".css", ".xml", ".csv", ".sh", ".bash", ".sql",
    ".c", ".cpp", ".h", ".hpp", ".java", ".go", ".rs", ".rb", ".php",
    ".swift", ".kt", ".scala", ".lua", ".r", ".m", ".toml", ".ini", ".env",
    ".docx"
}

router = APIRouter(tags=["config"])


@router.get("/api/files/{filename:path}")
async def get_file(filename: str):
    import mimetypes
    file_path = CONFIG.workdir / filename
    try:
        file_path.resolve().relative_to(CONFIG.workdir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(path=file_path, media_type=mime_type or "application/octet-stream", filename=filename)


@router.get("/api/skills", response_model=List[SkillInfo])
async def get_skills_list(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    return [
        SkillInfo(name=name, description=skill["description"],
                  enabled=not current_state.enabled_skills or name in current_state.enabled_skills)
        for name, skill in SKILLS.skills.items()
    ]


@router.get("/api/tools", response_model=List[ToolInfo])
async def get_tools_list(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    return [
        ToolInfo(
            name=s["function"]["name"],
            description=s["function"]["description"],
            enabled=not current_state.enabled_tools or s["function"]["name"] in current_state.enabled_tools
        )
        for s in TOOLS.get_all_schemas()
    ]


@router.get("/api/agents")
async def get_agents():
    return [{"name": name, "description": agent.description} for name, agent in AGENT_TYPES.items()]


@router.get("/api/models", response_model=List[ModelInfo])
async def get_models_list():
    return AVAILABLE_MODELS


@router.get("/api/status", response_model=StatusResponse)
async def get_status(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    return StatusResponse(
        token_usage={"input": TOKEN_USAGE.total_input, "output": TOKEN_USAGE.total_output, "calls": TOKEN_USAGE.call_count},
        message_count=len(current_state.history),
        skills=SKILLS.list_skills(),
        current_session=current_state.current_session_id,
        current_model=current_state.current_model or CONFIG.model
    )


@router.get("/api/history")
async def get_history(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    messages = [msg for msg in current_state.history if msg.get("role") != "system"]
    return {"messages": messages, "count": len(messages)}


@router.post("/api/clear")
async def clear_history(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    set_current_state(current_state)
    current_state.history = [{"role": "system", "content": get_system_prompt()}]
    return {"status": "cleared"}


@router.get("/api/config", response_model=AppConfigResponse)
async def get_app_config(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    return AppConfigResponse(
        model=current_state.current_model or CONFIG.model,
        enabled_tools=current_state.enabled_tools,
        enabled_skills=current_state.enabled_skills,
        available_models=AVAILABLE_MODELS,
        temperature=current_state.temperature,
        api_key=None,
        base_url=current_state.base_url or CONFIG.base_url
    )


@router.post("/api/config")
async def update_app_config(request: ConfigUpdate, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    if request.model:
        current_state.current_model = request.model
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
        if current_state.agent_client:
            current_state.agent_client.client.api_key = request.api_key
    if request.base_url is not None:
        current_state.base_url = request.base_url
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


@router.get("/api/prompt")
async def get_prompt(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    set_current_state(current_state)
    return {
        "default_prompt": DEFAULT_SYSTEM_PROMPT,
        "custom_prompt": current_state.custom_system_prompt,
        "current_prompt": get_system_prompt()
    }


@router.post("/api/prompt")
async def update_prompt(request: PromptUpdate, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    current_state.custom_system_prompt = request.custom_prompt
    set_current_state(current_state)
    if current_state.history and current_state.history[0].get("role") == "system":
        current_state.history[0]["content"] = get_system_prompt()
    return {"status": "updated", "custom_prompt": current_state.custom_system_prompt, "current_prompt": get_system_prompt()}


@router.post("/api/prompt/reset")
async def reset_prompt(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    current_state = get_state_for_user(current_user)
    current_state.custom_system_prompt = None
    set_current_state(current_state)
    if current_state.history and current_state.history[0].get("role") == "system":
        current_state.history[0]["content"] = get_system_prompt()
    return {"status": "reset", "current_prompt": get_system_prompt()}


def _validate_file(filename: str, size: int) -> tuple[bool, str]:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    if size > MAX_FILE_SIZE:
        return False, f"File size ({size / 1024 / 1024:.2f}MB) exceeds limit ({MAX_FILE_SIZE / 1024 / 1024}MB)"
    return True, ""


@router.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    content_bytes = await file.read()
    size = len(content_bytes)
    valid, error_msg = _validate_file(file.filename or "unknown", size)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)

    ext = os.path.splitext(file.filename or "")[1].lower()
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
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    return UploadResponse(filename=file.filename or "unknown", content=content, size=size, type=ext)
