"""
长期记忆管理 API 路由
"""
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from spark.services.memory import get_memory
from api.schemas import MemoryAddRequest, MemorySearchRequest, MemoryUpdateRequest
from api.deps import get_current_user_optional

MEMORY = get_memory()
router = APIRouter(prefix="/api/memories", tags=["memories"])


def _check_available():
    if not MEMORY.is_long_term_memory_available():
        raise HTTPException(status_code=503, detail="Long-term memory service not available. Check Qdrant connection.")


@router.get("")
async def get_memories(current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    _check_available()
    user_id = current_user["user_id"] if current_user else "default"
    memories = MEMORY.get_all_memories(user_id)
    return {"user_id": user_id, "count": len(memories), "memories": memories}


@router.post("")
async def add_memory(request: MemoryAddRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    _check_available()
    user_id = current_user["user_id"] if current_user else request.user_id
    result = MEMORY.add_memory(request.content, user_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to add memory")
    return {"status": "added", "content": request.content, "user_id": user_id, "result": result}


@router.post("/search")
async def search_memories(request: MemorySearchRequest, current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    _check_available()
    user_id = current_user["user_id"] if current_user else request.user_id
    results = MEMORY.search_memories(request.query, user_id, request.limit)
    return {"query": request.query, "user_id": user_id, "count": len(results), "results": results}


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    _check_available()
    if not MEMORY.delete_memory(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found or delete failed")
    return {"status": "deleted", "memory_id": memory_id}


@router.put("/{memory_id}")
async def update_memory(memory_id: str, request: MemoryUpdateRequest):
    _check_available()
    if not MEMORY.update_memory(memory_id, request.content):
        raise HTTPException(status_code=404, detail="Memory not found or update failed")
    return {"status": "updated", "memory_id": memory_id, "content": request.content}
