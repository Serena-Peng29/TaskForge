"""
工作区 API 路由
"""
import platform
import subprocess
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user_optional, get_state_for_user, get_system_prompt, set_current_state
from api.schemas import DirectoryPickResponse, WorkspaceCreate, WorkspaceInfo, WorkspaceUpdate
from taskforge.config import get_config, logger
from taskforge.services.memory import get_memory
from taskforge.services.workspaces import WorkspaceStore


CONFIG = get_config()
MEMORY = get_memory()
router = APIRouter(tags=["workspaces"])


def _store() -> WorkspaceStore:
    return WorkspaceStore(CONFIG)


def _get_user_id(user: Optional[Dict[str, Any]]) -> str:
    return user["user_id"] if user else "default"


def _pick_directory_native() -> str | None:
    """打开本机目录选择弹窗，返回选择的 POSIX 路径。"""
    if platform.system() == "Darwin":
        script = 'POSIX path of (choose folder with prompt "选择工作区文件夹")'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        if "User canceled" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or "Failed to open directory picker")

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="选择工作区文件夹")
        root.destroy()
        return path or None
    except Exception as e:
        raise RuntimeError(str(e)) from e


def _apply_workspace(workspace_id: str, current_user: Optional[Dict[str, Any]]) -> dict[str, Any]:
    store = _store()
    current_state = get_state_for_user(current_user)
    user_id = _get_user_id(current_user)
    if current_state.current_session_id and len(current_state.history) > 1:
        MEMORY.save_session_by_id(current_state.current_session_id, current_state.history, user_id)

    try:
        workspace = store.get(workspace_id)
        path = CONFIG.set_workspace(workspace.path)
        CONFIG.set_permission(workspace.permission_mode, workspace.allowed_tools)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    current_state.reset_runtime(CONFIG)
    workspace_sessions = [
        session for session in MEMORY.list_sessions(user_id)
        if session.workspace_id == workspace_id
    ]
    current_session_id = workspace_sessions[0].id if workspace_sessions else None
    current_state.current_session_id = current_session_id
    set_current_state(current_state)
    if current_session_id:
        session_data = MEMORY.get_session(current_session_id, user_id)
        current_state.history = [{"role": "system", "content": get_system_prompt()}] + (session_data or {}).get("messages", [])
    else:
        current_state.history = [{"role": "system", "content": get_system_prompt()}]
    logger.info(f"Activated workspace {workspace.name}: {path}")
    return workspace.to_dict(path)


@router.get("/api/workspaces", response_model=List[WorkspaceInfo])
async def list_workspaces(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    store = _store()
    store.ensure_active()
    return store.list_dicts()


@router.post("/api/workspaces/pick-directory", response_model=DirectoryPickResponse)
async def pick_workspace_directory():
    try:
        path = _pick_directory_native()
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Directory picker timed out")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return DirectoryPickResponse(path=path, cancelled=path is None)


@router.post("/api/workspaces", response_model=WorkspaceInfo)
async def add_workspace(
    request: WorkspaceCreate,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    try:
        workspace = _store().add(
            path=request.path,
            name=request.name,
            permission_mode=request.permission_mode,
            allowed_tools=request.allowed_tools,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _apply_workspace(workspace.id, current_user)


@router.post("/api/workspaces/{workspace_id}/activate", response_model=WorkspaceInfo)
async def activate_workspace(
    workspace_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    return _apply_workspace(workspace_id, current_user)


@router.patch("/api/workspaces/{workspace_id}", response_model=WorkspaceInfo)
async def update_workspace(
    workspace_id: str,
    request: WorkspaceUpdate,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    try:
        workspace = _store().update(
            workspace_id,
            name=request.name,
            permission_mode=request.permission_mode,
            allowed_tools=request.allowed_tools,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    active_path = CONFIG.workspace_dir or CONFIG.workdir
    is_active = workspace.to_dict(active_path)["is_active"]
    if is_active:
        CONFIG.set_permission(workspace.permission_mode, workspace.allowed_tools)
        current_state = get_state_for_user(current_user)
        if current_state.agent_client:
            current_state.agent_client.config.set_permission(workspace.permission_mode, workspace.allowed_tools)
    return workspace.to_dict(active_path)


@router.delete("/api/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str):
    try:
        _store().delete(workspace_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"status": "deleted"}
