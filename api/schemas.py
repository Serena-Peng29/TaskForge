"""
Pydantic 请求/响应模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


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
    custom_prompt: Optional[str] = None


class HistoryResponse(BaseModel):
    messages: List[dict]
    count: int


class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
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


class UploadResponse(BaseModel):
    filename: str
    content: str
    size: int
    type: str


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
    config: dict
