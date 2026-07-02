"""
任务管理器测试
"""
import pytest
from todo_manager import TodoManager


class TestTodoManager:
    """任务管理器测试"""

    def setup_method(self):
        self.manager = TodoManager()

    def test_empty_todos(self):
        """测试空任务列表"""
        assert self.manager.render() == "No todos."

    def test_add_todos(self):
        """测试添加任务"""
        result = self.manager.update([
            {"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"},
            {"content": "Task 2", "status": "completed", "activeForm": "Doing task 2"},
        ])

        assert "[ ] Task 1" in result
        assert "[✅] Task 2" in result
        assert "1/2 done" in result

    def test_in_progress_limit(self):
        """测试同时只能有一个进行中任务"""
        with pytest.raises(ValueError, match="Only one task can be in_progress"):
            self.manager.update([
                {"content": "Task 1", "status": "in_progress", "activeForm": "Doing task 1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "Doing task 2"},
            ])

    def test_invalid_status(self):
        """测试无效状态"""
        with pytest.raises(ValueError, match="invalid status"):
            self.manager.update([
                {"content": "Task 1", "status": "invalid", "activeForm": "Doing task 1"},
            ])

    def test_missing_content(self):
        """测试缺少内容"""
        with pytest.raises(ValueError, match="content is required"):
            self.manager.update([
                {"status": "pending", "activeForm": "Doing task"},
            ])

    def test_get_current_task(self):
        """测试获取当前任务"""
        self.manager.update([
            {"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Doing task 2"},
        ])

        current = self.manager.get_current_task()
        assert current is not None
        assert current.content == "Task 2"

    def test_max_items(self):
        """测试最大任务数限制"""
        items = [
            {"content": f"Task {i}", "status": "pending", "activeForm": f"Doing task {i}"}
            for i in range(30)
        ]
        self.manager.update(items)
        assert len(self.manager.items) == self.manager.MAX_ITEMS