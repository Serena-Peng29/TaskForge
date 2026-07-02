"""
会话历史管理模块
支持多会话管理，每个会话独立存储
"""
from pathlib import Path
import json
import time
from typing import List, Optional, Dict, Any
import logging
import uuid
import re

logger = logging.getLogger(__name__)

class SessionInfo:
    """会话元信息"""
    def __init__(self, id: str, title: str, created_at: str, updated_at: str, message_count: int = 0):
        self.id = id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.message_count = message_count

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionInfo":
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            message_count=data.get("message_count", 0)
        )


class MemoryManager:
    """对话历史管理器 - 负责加载和保存本地会话历史"""

    # 默认用户ID（向后兼容无认证模式）
    DEFAULT_USER = "default"

    def __init__(self, memory_dir: Path = None):
        self.memory_dir = Path(memory_dir) if memory_dir else Path.cwd() / "memory"
        self.users_dir = self.memory_dir / "users"
        self.history_file = self.memory_dir / "conversation_history.json"
        self._ensure_memory_dir()

    def _ensure_memory_dir(self):
        """确保 memory 目录存在"""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.users_dir.mkdir(parents=True, exist_ok=True)
        # 迁移旧数据到新结构
        self._migrate_legacy_sessions()

    def _migrate_legacy_sessions(self):
        """迁移旧会话数据到用户隔离结构"""
        import shutil

        # 检查是否有旧的会话目录
        legacy_sessions_dir = self.memory_dir / "sessions"
        legacy_index_file = self.memory_dir / "sessions_index.json"
        legacy_last_session = self.memory_dir / "last_session.json"
        legacy_history = self.memory_dir / "conversation_history.json"

        # 如果用户目录已经存在数据，跳过迁移
        default_user_dir = self._get_user_dir(self.DEFAULT_USER)
        default_index = self._get_user_index_file(self.DEFAULT_USER)

        if default_index.exists():
            return  # 已迁移过

        # 迁移会话索引
        if legacy_index_file.exists():
            try:
                shutil.move(str(legacy_index_file), str(default_index))
                logger.info(f"Migrated legacy session index to user directory")
            except Exception as e:
                logger.warning(f"Failed to migrate session index: {e}")

        # 迁移会话文件
        if legacy_sessions_dir.exists():
            default_sessions_dir = self._get_user_sessions_dir(self.DEFAULT_USER)
            try:
                # 移动所有会话文件
                for session_file in legacy_sessions_dir.glob("*.json"):
                    shutil.move(str(session_file), str(default_sessions_dir / session_file.name))
                # 删除旧的空目录
                if legacy_sessions_dir.exists() and not any(legacy_sessions_dir.iterdir()):
                    legacy_sessions_dir.rmdir()
                logger.info(f"Migrated legacy sessions to user directory")
            except Exception as e:
                logger.warning(f"Failed to migrate sessions: {e}")

        # 迁移最后会话文件
        if legacy_last_session.exists():
            try:
                shutil.move(str(legacy_last_session), str(self._get_user_last_session_file(self.DEFAULT_USER)))
                logger.info(f"Migrated legacy last session file")
            except Exception as e:
                logger.warning(f"Failed to migrate last session file: {e}")

        # 迁移历史文件
        if legacy_history.exists():
            try:
                shutil.move(str(legacy_history), str(default_user_dir / "conversation_history.json"))
                logger.info(f"Migrated legacy conversation history")
            except Exception as e:
                logger.warning(f"Failed to migrate conversation history: {e}")

    def _get_user_dir(self, user_id: str) -> Path:
        """获取用户目录"""
        user_dir = self.users_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _get_user_sessions_dir(self, user_id: str) -> Path:
        """获取用户的会话目录"""
        sessions_dir = self._get_user_dir(user_id) / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir

    def _get_user_index_file(self, user_id: str) -> Path:
        """获取用户的会话索引文件"""
        return self._get_user_dir(user_id) / "sessions_index.json"

    def _get_user_last_session_file(self, user_id: str) -> Path:
        """获取用户的最后会话文件"""
        return self._get_user_dir(user_id) / "last_session.json"

    # ==================== 多会话管理 ====================

    def _load_index(self, user_id: str = None) -> Dict[str, dict]:
        """加载会话索引"""
        user_id = user_id or self.DEFAULT_USER
        index_file = self._get_user_index_file(user_id)
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load session index for user {user_id}: {e}")
        return {}

    def _save_index(self, index: Dict[str, dict], user_id: str = None):
        """保存会话索引"""
        user_id = user_id or self.DEFAULT_USER
        index_file = self._get_user_index_file(user_id)
        try:
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session index for user {user_id}: {e}")

    def _generate_title(self, messages: List[dict]) -> str:
        """根据第一条用户消息生成会话标题"""
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                # 取前50个字符作为标题
                title = content[:50]
                if len(content) > 50:
                    title += "..."
                # 清理换行和多余空格
                title = re.sub(r'\s+', ' ', title).strip()
                return title or "New Chat"
        return "New Chat"

    def list_sessions(self, user_id: str = None) -> List[SessionInfo]:
        """列出用户的所有历史会话"""
        user_id = user_id or self.DEFAULT_USER
        index = self._load_index(user_id)
        sessions = []
        for session_id, meta in index.items():
            try:
                sessions.append(SessionInfo.from_dict({"id": session_id, **meta}))
            except Exception as e:
                logger.warning(f"Invalid session metadata for {session_id}: {e}")
        # 按更新时间倒序排列
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def create_session(self, title: str = None, user_id: str = None) -> str:
        """创建新会话，返回会话ID"""
        user_id = user_id or self.DEFAULT_USER
        session_id = str(uuid.uuid4())[:8]
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        index = self._load_index(user_id)
        index[session_id] = {
            "title": title or "New Chat",
            "created_at": now,
            "updated_at": now,
            "message_count": 0
        }
        self._save_index(index, user_id)

        # 创建空的会话文件
        sessions_dir = self._get_user_sessions_dir(user_id)
        session_path = sessions_dir / f"{session_id}.json"
        session_data = {
            "id": session_id,
            "created_at": now,
            "messages": []
        }
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Created new session: {session_id} for user: {user_id}")
        return session_id

    def get_session(self, session_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """获取指定会话的完整数据"""
        user_id = user_id or self.DEFAULT_USER
        sessions_dir = self._get_user_sessions_dir(user_id)
        session_path = sessions_dir / f"{session_id}.json"
        if not session_path.exists():
            logger.warning(f"Session not found: {session_id} for user: {user_id}")
            return None

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def save_session_by_id(self, session_id: str, messages: List[dict], user_id: str = None) -> bool:
        """保存指定会话"""
        if not messages:
            return False

        user_id = user_id or self.DEFAULT_USER

        try:
            saveable_messages = self._prepare_messages_for_save(messages)

            # 读取现有会话数据
            sessions_dir = self._get_user_sessions_dir(user_id)
            session_path = sessions_dir / f"{session_id}.json"
            if session_path.exists():
                with open(session_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                created_at = existing.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                created_at = time.strftime("%Y-%m-%d %H:%M:%S")

            now = time.strftime("%Y-%m-%d %H:%M:%S")
            title = self._generate_title(saveable_messages)

            session_data = {
                "id": session_id,
                "title": title,
                "created_at": created_at,
                "updated_at": now,
                "message_count": len(saveable_messages),
                "messages": saveable_messages
            }

            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            # 更新索引
            index = self._load_index(user_id)
            index[session_id] = {
                "title": title,
                "created_at": created_at,
                "updated_at": now,
                "message_count": len(saveable_messages)
            }
            self._save_index(index, user_id)

            logger.info(f"Session {session_id} saved: {len(saveable_messages)} messages for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            return False

    def delete_session(self, session_id: str, user_id: str = None) -> bool:
        """删除指定会话"""
        user_id = user_id or self.DEFAULT_USER
        try:
            # 删除会话文件
            sessions_dir = self._get_user_sessions_dir(user_id)
            session_path = sessions_dir / f"{session_id}.json"
            if session_path.exists():
                session_path.unlink()

            # 从索引中移除
            index = self._load_index(user_id)
            if session_id in index:
                del index[session_id]
                self._save_index(index, user_id)

            logger.info(f"Session {session_id} deleted for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def rename_session(self, session_id: str, title: str, user_id: str = None) -> bool:
        """重命名会话"""
        user_id = user_id or self.DEFAULT_USER
        try:
            index = self._load_index(user_id)
            if session_id not in index:
                logger.warning(f"Session not found for rename: {session_id} for user: {user_id}")
                return False

            index[session_id]["title"] = title
            index[session_id]["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self._save_index(index, user_id)

            # 同时更新会话文件
            sessions_dir = self._get_user_sessions_dir(user_id)
            session_path = sessions_dir / f"{session_id}.json"
            if session_path.exists():
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["title"] = title
                with open(session_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Session {session_id} renamed to: {title} for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to rename session {session_id}: {e}")
            return False

    def load_last_session(self, user_id: str = None) -> Optional[List[dict]]:
        """
        启动钩子: 加载上次对话历史
        Returns: 上次对话的消息列表，如果没有则返回 None
        """
        user_id = user_id or self.DEFAULT_USER
        session_file = self._get_user_last_session_file(user_id)
        if not session_file.exists():
            logger.info(f"No previous session found for user: {user_id}")
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            messages = data.get("messages", [])
            timestamp = data.get("timestamp", "unknown")
            logger.info(f"Loaded previous session from {timestamp} ({len(messages)} messages) for user: {user_id}")
            return messages
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse session file: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def save_session(self, messages: List[dict], user_id: str = None) -> bool:
        """
        退出钩子: 保存当前对话历史
        Returns: 是否保存成功
        """
        if not messages:
            logger.info("No messages to save")
            return False

        user_id = user_id or self.DEFAULT_USER

        try:
            # 过滤掉 system prompt，只保存实际对话
            saveable_messages = self._prepare_messages_for_save(messages)

            session_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "message_count": len(saveable_messages),
                "messages": saveable_messages
            }

            # 保存当前会话
            session_file = self._get_user_last_session_file(user_id)
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Session saved: {len(saveable_messages)} messages for user: {user_id}")

            # 同时追加到历史记录
            self._append_to_history(saveable_messages, user_id)

            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def _prepare_messages_for_save(self, messages: List[dict]) -> List[dict]:
        """
        准备消息用于保存
        - 移除 system prompt
        - 清理工具调用的详细输出（可选，保持简洁）
        """
        saveable = []
        for msg in messages:
            if msg.get("role") == "system":
                continue  # 跳过 system prompt

            # 处理 assistant 消息
            if msg.get("role") == "assistant":
                saved_msg = {
                    "role": "assistant",
                    "content": msg.get("content", "")
                }
                # 保存工具调用信息（简化版本）
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    saved_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                elif "tool_calls" in msg:
                    saved_msg["tool_calls"] = msg["tool_calls"]
                saveable.append(saved_msg)
            else:
                # user 和 tool 消息直接保存
                saveable.append(dict(msg))

        return saveable

    def _append_to_history(self, messages: List[dict], user_id: str = None):
        """追加到完整历史记录"""
        user_id = user_id or self.DEFAULT_USER
        user_history_file = self._get_user_dir(user_id) / "conversation_history.json"
        try:
            # 加载现有历史
            history = []
            if user_history_file.exists():
                with open(user_history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)

            # 添加新会话
            history.append({
                "session_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "messages": messages
            })

            # 只保留最近 50 个会话
            history = history[-50:]

            with open(user_history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

            logger.debug(f"Appended to history ({len(history)} sessions) for user: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to append to history: {e}")

    def clear_session(self, user_id: str = None):
        """清除当前会话"""
        user_id = user_id or self.DEFAULT_USER
        session_file = self._get_user_last_session_file(user_id)
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Session cleared for user: {user_id}")

    def get_session_info(self, user_id: str = None) -> str:
        """获取会话信息"""
        user_id = user_id or self.DEFAULT_USER
        session_file = self._get_user_last_session_file(user_id)
        if not session_file.exists():
            return f"No saved session for user: {user_id}"

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return f"Last session: {data.get('timestamp', 'unknown')} ({data.get('message_count', 0)} messages) for user: {user_id}"
        except:
            return f"Session file exists but unreadable for user: {user_id}"


# 延迟初始化
_MEMORY = None

def get_memory():
    """获取内存管理器实例"""
    global _MEMORY
    if _MEMORY is None:
        from spark.config import get_config
        config = get_config()
        _MEMORY = MemoryManager(
            memory_dir=config.workdir / "memory"
        )
    return _MEMORY

# 向后兼容
MEMORY = None
