"""
MCP 管理 API 路由
"""
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from api.schemas import MCPServerInfo, MCPServerAddRequest, MCPConfigImportRequest
from api.deps import get_current_user_optional, get_state_for_user

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


def _get_manager(current_user):
    state = get_state_for_user(current_user)
    if not state.mcp_manager:
        raise HTTPException(status_code=503, detail="MCP Manager not initialized")
    return state.mcp_manager


@router.get("/status")
async def get_mcp_status(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    state = get_state_for_user(current_user)
    if not state.mcp_manager:
        return {"available": False, "message": "MCP Manager not initialized"}
    mgr = state.mcp_manager
    return {
        "available": mgr.is_available(),
        "servers_count": len(mgr.list_servers()),
        "tools_count": len(mgr.get_all_tools())
    }


@router.get("/servers", response_model=List[MCPServerInfo])
async def get_mcp_servers(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    state = get_state_for_user(current_user)
    if not state.mcp_manager:
        return []

    mgr = state.mcp_manager
    config = mgr.load_config_from_file()
    servers_info = []
    for name, server_cfg in config.get("mcpServers", {}).items():
        s = mgr.get_server_status(name)
        servers_info.append(MCPServerInfo(
            name=name,
            status=s.status if s else "disconnected",
            error=s.error if s else None,
            tools=s.tools if s else [],
            command=server_cfg.get("command", ""),
            env=server_cfg.get("env", {})
        ))
    return servers_info


@router.post("/servers")
async def add_mcp_server(request: MCPServerAddRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    mgr = _get_manager(current_user)
    config = mgr.load_config_from_file()
    mcp_servers = config.get("mcpServers", {})
    mcp_servers[request.name] = {"command": request.command, "env": request.env}
    config["mcpServers"] = mcp_servers
    if not mgr.save_config(config):
        raise HTTPException(status_code=500, detail="Failed to save MCP config")
    return {"status": "added", "name": request.name}


@router.delete("/servers/{name}")
async def delete_mcp_server(name: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    mgr = _get_manager(current_user)
    if mgr.has_server(name):
        await mgr.disconnect_server(name)
    config = mgr.load_config_from_file()
    mcp_servers = config.get("mcpServers", {})
    if name not in mcp_servers:
        raise HTTPException(status_code=404, detail="Server not found in config")
    del mcp_servers[name]
    config["mcpServers"] = mcp_servers
    if not mgr.save_config(config):
        raise HTTPException(status_code=500, detail="Failed to save MCP config")
    return {"status": "deleted", "name": name}


@router.post("/servers/{name}/connect")
async def connect_mcp_server(name: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    mgr = _get_manager(current_user)
    config = mgr.load_config_from_file()
    mcp_servers = config.get("mcpServers", {})
    if name not in mcp_servers:
        raise HTTPException(status_code=404, detail="Server not found in config")
    s = await mgr.connect_server(name, mcp_servers[name])
    return {"status": s.status, "name": name, "error": s.error, "tools": s.tools}


@router.post("/servers/{name}/disconnect")
async def disconnect_mcp_server(name: str, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    mgr = _get_manager(current_user)
    if not await mgr.disconnect_server(name):
        raise HTTPException(status_code=404, detail="Server not connected")
    return {"status": "disconnected", "name": name}


@router.get("/tools")
async def get_mcp_tools(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    state = get_state_for_user(current_user)
    if not state.mcp_manager:
        return {"tools": [], "count": 0}
    tools = state.mcp_manager.get_tool_schemas()
    return {"tools": tools, "count": len(tools)}


@router.post("/import")
async def import_mcp_config(request: MCPConfigImportRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    mgr = _get_manager(current_user)
    if not mgr.save_config(request.config):
        raise HTTPException(status_code=500, detail="Failed to save MCP config")
    results = await mgr.load_config(request.config)
    return {
        "status": "imported",
        "servers": {name: s.status for name, s in results.items()},
        "errors": {name: s.error for name, s in results.items() if s.error}
    }
