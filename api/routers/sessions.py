"""
会话管理 API 路由
"""
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from spark.services.memory import get_memory
from api.schemas import SessionInfo, SessionCreate, SessionUpdate
from api.deps import get_current_user_optional, get_state_for_user, set_current_state, get_system_prompt

MEMORY = get_memory()
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _get_user_id(user: Optional[Dict[str, Any]]) -> str:
    return user["user_id"] if user else "default"


@router.get("", response_model=List[SessionInfo])
async def list_sessions(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = _get_user_id(current_user)
    sessions = MEMORY.list_sessions(user_id)
    return [
        SessionInfo(id=s.id, title=s.title, created_at=s.created_at, updated_at=s.updated_at, message_count=s.message_count)
        for s in sessions
    ]


@router.get("/{session_id}")
async def get_session(session_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = _get_user_id(current_user)
    session = MEMORY.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/new", response_model=SessionInfo)
async def create_new_session(request: SessionCreate = None, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = _get_user_id(current_user)
    title = request.title if request else None
    session_id = MEMORY.create_session(title, user_id)
    for s in MEMORY.list_sessions(user_id):
        if s.id == session_id:
            return SessionInfo(id=s.id, title=s.title, created_at=s.created_at, updated_at=s.updated_at, message_count=s.message_count)
    raise HTTPException(status_code=500, detail="Failed to create session")


@router.post("/{session_id}/switch")
async def switch_session(session_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = _get_user_id(current_user)
    current_state = get_state_for_user(current_user)
    session = MEMORY.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_state.current_session_id and len(current_state.history) > 1:
        MEMORY.save_session_by_id(current_state.current_session_id, current_state.history, user_id)

    current_state.current_session_id = session_id
    set_current_state(current_state)
    current_state.history = [{"role": "system", "content": get_system_prompt()}] + session.get("messages", [])

    return {"status": "switched", "session_id": session_id, "message_count": len(session.get("messages", []))}


@router.delete("/{session_id}")
async def delete_session(session_id: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = _get_user_id(current_user)
    current_state = get_state_for_user(current_user)
    if session_id == current_state.current_session_id:
        raise HTTPException(status_code=400, detail="Cannot delete current session")

    if not MEMORY.delete_session(session_id, user_id):
        raise HTTPException(status_code=404, detail="Session not found or delete failed")

    return {"status": "deleted", "session_id": session_id}


@router.patch("/{session_id}")
async def update_session(session_id: str, request: SessionUpdate, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    user_id = _get_user_id(current_user)
    if request.title:
        if not MEMORY.rename_session(session_id, request.title, user_id):
            raise HTTPException(status_code=404, detail="Session not found or rename failed")
    return {"status": "updated", "session_id": session_id}
