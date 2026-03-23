"""
用户认证模块
支持用户名密码 + JWT Token 认证
用户数据存储在 Qdrant
"""
import uuid
import time
import logging
import warnings
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# 自定义异常
class UserExistsError(Exception):
    """用户名已存在"""
    pass

class AuthError(Exception):
    """认证相关错误"""
    pass


# JWT 和密码哈希依赖
try:
    # 抑制 bcrypt 版本警告（passlib 与新版 bcrypt 的兼容性问题）
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from jose import JWTError, jwt
        from passlib.context import CryptContext
        import bcrypt  # 直接使用 bcrypt 绕过 passlib 的版本检测问题
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    logger.warning("python-jose or passlib not installed. Run: pip install python-jose[cryptography] passlib[bcrypt]")


@dataclass
class User:
    """用户数据模型"""
    id: str
    username: str
    password_hash: str
    created_at: str
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            id=data["id"],
            username=data["username"],
            password_hash=data["password_hash"],
            created_at=data["created_at"],
            is_active=data.get("is_active", True)
        )


class UserManager:
    """用户管理器 - 使用 Qdrant 存储用户数据"""

    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333,
                 collection_name: str = "toymagic_users"):
        if not AUTH_AVAILABLE:
            self.client = None
            logger.warning("UserManager initialized but auth dependencies not available")
            return

        # Qdrant 客户端
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
            self.collection_name = collection_name

            # 确保集合存在
            self._ensure_collection()

            logger.info(f"UserManager initialized with Qdrant at {qdrant_host}:{qdrant_port}")
        except Exception as e:
            self.client = None
            logger.error(f"Failed to initialize UserManager: {e}")

    def _ensure_collection(self):
        """确保用户集合存在"""
        try:
            from qdrant_client.http import models

            collections = self.client.get_collections().collections
            names = [c.name for c in collections]

            if self.collection_name not in names:
                # 创建集合，使用简单的向量配置（实际不需要向量搜索，但 Qdrant 要求）
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=1,  # 最小维度
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created users collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")

    def is_available(self) -> bool:
        """检查用户管理功能是否可用"""
        return self.client is not None and AUTH_AVAILABLE

    def get_password_hash(self, password: str) -> str:
        """生成密码哈希（bcrypt 限制72字节，截断处理）"""
        # bcrypt 最多支持72字节，截断以避免错误
        password_bytes = password.encode('utf-8')[:72]
        # 直接使用 bcrypt 库
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    def create_user(self, username: str, password: str) -> User:
        """创建新用户，失败时抛出异常"""
        if not self.is_available():
            raise AuthError("UserManager not available")

        # 检查用户名是否已存在
        if self.get_user_by_username(username):
            raise UserExistsError(f"Username already exists: {username}")

        try:
            user = User(
                id=str(uuid.uuid4()),
                username=username,
                password_hash=self.get_password_hash(password),
                created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                is_active=True
            )

            # 存储到 Qdrant (使用假向量)
            from qdrant_client.http import models as qdrant_models

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    qdrant_models.PointStruct(
                        id=user.id,
                        vector=[0.0],  # 假向量，不用于搜索
                        payload=user.to_dict()
                    )
                ]
            )

            logger.info(f"Created user: {username} ({user.id})")
            return user
        except UserExistsError:
            raise  # 重新抛出用户已存在异常
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise AuthError(f"Failed to create user: {e}")

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        if not self.is_available():
            return None

        try:
            from qdrant_client.http import models as qdrant_models

            # 使用过滤条件搜索
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="username",
                            match=qdrant_models.MatchValue(value=username)
                        )
                    ]
                ),
                limit=1
            )

            if results and results[0]:
                point = results[0][0]
                return User.from_dict(point.payload)

            return None
        except Exception as e:
            logger.error(f"Failed to get user by username: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 获取用户"""
        if not self.is_available():
            return None

        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[user_id]
            )

            if points:
                return User.from_dict(points[0].payload)

            return None
        except Exception as e:
            logger.error(f"Failed to get user by id: {e}")
            return None

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """验证用户凭据"""
        user = self.get_user_by_username(username)

        if not user:
            return None

        if not user.is_active:
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        return user

    def list_users(self) -> List[User]:
        """列出所有用户"""
        if not self.is_available():
            return []

        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000
            )

            if results and results[0]:
                return [User.from_dict(p.payload) for p in results[0]]

            return []
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        if not self.is_available():
            return False

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[user_id]
            )
            logger.info(f"Deleted user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            return False


class JWTManager:
    """JWT Token 管理器"""

    def __init__(self, secret_key: str, algorithm: str = "HS256",
                 expire_minutes: int = 1440):
        if not AUTH_AVAILABLE:
            self.secret_key = None
            self.algorithm = None
            self.expire_minutes = None
            return

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def is_available(self) -> bool:
        """检查 JWT 功能是否可用"""
        return AUTH_AVAILABLE and self.secret_key is not None

    def create_access_token(self, user: User) -> Optional[str]:
        """创建访问令牌"""
        if not self.is_available():
            return None

        try:
            expire = time.time() + self.expire_minutes * 60

            payload = {
                "sub": user.id,
                "username": user.username,
                "exp": expire
            }

            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            logger.error(f"Failed to create token: {e}")
            return None

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌，返回用户信息"""
        if not self.is_available():
            return None

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 检查是否过期
            if payload.get("exp", 0) < time.time():
                return None

            return {
                "user_id": payload.get("sub"),
                "username": payload.get("username")
            }
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None


# 全局实例（延迟初始化）
_USER_MANAGER: Optional[UserManager] = None
_JWT_MANAGER: Optional[JWTManager] = None


def init_auth(qdrant_host: str = "localhost", qdrant_port: int = 6333,
              users_collection: str = "toymagic_users",
              jwt_secret: str = "change-me", jwt_algorithm: str = "HS256",
              expire_minutes: int = 1440) -> bool:
    """初始化认证模块"""
    global _USER_MANAGER, _JWT_MANAGER

    if not AUTH_AVAILABLE:
        logger.warning("Auth dependencies not available")
        return False

    _USER_MANAGER = UserManager(
        qdrant_host=qdrant_host,
        qdrant_port=qdrant_port,
        collection_name=users_collection
    )

    _JWT_MANAGER = JWTManager(
        secret_key=jwt_secret,
        algorithm=jwt_algorithm,
        expire_minutes=expire_minutes
    )

    return _USER_MANAGER.is_available() and _JWT_MANAGER.is_available()


def get_user_manager() -> Optional[UserManager]:
    """获取用户管理器实例"""
    return _USER_MANAGER


def get_jwt_manager() -> Optional[JWTManager]:
    """获取 JWT 管理器实例"""
    return _JWT_MANAGER