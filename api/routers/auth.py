"""
认证相关 API 路由
"""
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status

from taskforge.services.auth import get_user_manager, get_jwt_manager, AUTH_AVAILABLE
from taskforge.config import get_config
from api.schemas import UserRegister, UserLogin, TokenResponse, UserInfo
from api.deps import get_current_user_optional, get_current_user

CONFIG = get_config()
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserInfo)
async def register(request: UserRegister):
    from taskforge.services.auth import UserExistsError, AuthError

    user_manager = get_user_manager()
    if not user_manager or not user_manager.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User registration service not available"
        )
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    try:
        user = user_manager.create_user(request.username, request.password)
    except UserExistsError:
        raise HTTPException(status_code=400, detail="Username already exists")
    except AuthError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return UserInfo(id=user.id, username=user.username, created_at=user.created_at, is_active=user.is_active)


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin):
    user_manager = get_user_manager()
    jwt_manager = get_jwt_manager()

    if not user_manager or not user_manager.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service not available")
    if not jwt_manager or not jwt_manager.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Token service not available")

    user = user_manager.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = jwt_manager.create_access_token(user)
    if not token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create access token")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=CONFIG.auth_config.access_token_expire_minutes * 60,
        user_id=user.id,
        username=user.username
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_manager = get_user_manager()
    if not user_manager:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="User service not available")

    user = user_manager.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserInfo(id=user.id, username=user.username, created_at=user.created_at, is_active=user.is_active)


@router.get("/status")
async def get_auth_status():
    user_manager = get_user_manager()
    jwt_manager = get_jwt_manager()
    return {
        "available": AUTH_AVAILABLE and (user_manager is not None and user_manager.is_available()),
        "user_manager": user_manager is not None and user_manager.is_available(),
        "jwt_manager": jwt_manager is not None and jwt_manager.is_available()
    }
