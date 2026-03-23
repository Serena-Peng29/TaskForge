from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TodoItem:
    """待办事项"""
    content: str
    status: str  # pending, in_progress, completed
    active_form: str


class TodoManager:
    """任务管理器"""

    VALID_STATUSES = {"pending", "in_progress", "completed"}
    MAX_ITEMS = 20

    def __init__(self):
        self.items: List[TodoItem] = []

    def update(self, items: List[dict]) -> str:
        """更新任务列表"""
        validated = []
        in_progress_count = 0

        for i, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower()
            active_form = str(item.get("activeForm", "")).strip()

            # 兼容 active_form 和 activeForm
            if not active_form:
                active_form = str(item.get("active_form", "")).strip()

            if not content:
                raise ValueError(f"Item {i}: content is required")
            if not active_form:
                raise ValueError(f"Item {i}: activeForm is required")
            if status not in self.VALID_STATUSES:
                raise ValueError(f"Item {i}: invalid status '{status}', must be one of {self.VALID_STATUSES}")
            if status == "in_progress":
                in_progress_count += 1

            validated.append(TodoItem(content=content, status=status, active_form=active_form))

        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress at a time")

        self.items = validated[:self.MAX_ITEMS]
        return self.render()

    def render(self) -> str:
        """渲染任务列表"""
        if not self.items:
            return "No todos."

        lines = []
        for item in self.items:
            if item.status == "completed":
                mark = "[✅]"
            elif item.status == "in_progress":
                mark = "[>]"
            else:
                mark = "[ ]"
            lines.append(f"{mark} {item.content}")

        done = sum(1 for t in self.items if t.status == "completed")
        return "\n".join(lines) + f"\n({done}/{len(self.items)} done)"

    def get_current_task(self) -> Optional[TodoItem]:
        """获取当前进行中的任务"""
        for item in self.items:
            if item.status == "in_progress":
                return item
        return None

    def clear(self) -> None:
        """清空任务列表"""
        self.items = []

    def to_dict(self) -> List[dict]:
        """转换为字典列表"""
        return [
            {
                "content": item.content,
                "status": item.status,
                "activeForm": item.active_form
            }
            for item in self.items
        ]

    @classmethod
    def from_dict(cls, data: List[dict]) -> "TodoManager":
        """从字典列表创建"""
        manager = cls()
        if data:
            manager.update(data)
        return manager


TODO = TodoManager()