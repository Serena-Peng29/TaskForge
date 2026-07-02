"""
工具系统测试
"""
import pytest
from pathlib import Path
from tools.base import BaseTool, ToolResult, ToolRegistry
from tools.builtin import EditFileTool, WriteFileTool


class MockTool(BaseTool):
    """测试用模拟工具"""

    name = "mock_tool"
    description = "A mock tool for testing"

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"}
                    },
                    "required": ["input"]
                }
            }
        }

    def execute(self, input: str) -> ToolResult:
        if input == "error":
            return ToolResult(success=False, content="", error="Test error")
        return ToolResult(success=True, content=f"Processed: {input}")


class TestToolRegistry:
    """工具注册表测试"""

    def test_register_tool(self):
        """测试工具注册"""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        assert registry.get("mock_tool") == tool
        assert "mock_tool" in registry.list_tools()

    def test_unregister_tool(self):
        """测试工具注销"""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        assert registry.unregister("mock_tool") is True
        assert registry.get("mock_tool") is None

    def test_execute_tool(self):
        """测试工具执行"""
        registry = ToolRegistry()
        registry.register(MockTool())

        result = registry.execute("mock_tool", {"input": "test"})
        assert result.success is True
        assert result.content == "Processed: test"

    def test_execute_tool_error(self):
        """测试工具执行错误"""
        registry = ToolRegistry()
        registry.register(MockTool())

        result = registry.execute("mock_tool", {"input": "error"})
        assert result.success is False
        assert result.error == "Test error"

    def test_unknown_tool(self):
        """测试未知工具"""
        registry = ToolRegistry()

        result = registry.execute("unknown", {})
        assert result.success is False
        assert "Unknown tool" in result.error


class TestToolResult:
    """工具结果测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = ToolResult(success=True, content="Done")
        assert str(result) == "Done"

    def test_error_result(self):
        """测试错误结果"""
        result = ToolResult(success=False, content="", error="Failed")
        assert str(result) == "Error: Failed"


class TestWorkspaceFileTools:
    """工作区文件工具测试"""

    def test_write_file_writes_inside_workspace(self, tmp_path: Path):
        tool = WriteFileTool(tmp_path)

        result = tool.execute("src/example.txt", "hello")

        assert result.success is True
        assert (tmp_path / "src" / "example.txt").read_text(encoding="utf-8") == "hello"

    def test_edit_file_edits_workspace_file(self, tmp_path: Path):
        target = tmp_path / "app.py"
        target.write_text("print('old')", encoding="utf-8")
        tool = EditFileTool(tmp_path)

        result = tool.execute("app.py", "old", "new")

        assert result.success is True
        assert target.read_text(encoding="utf-8") == "print('new')"

    def test_write_file_rejects_path_escape(self, tmp_path: Path):
        tool = WriteFileTool(tmp_path)

        result = tool.execute("../outside.txt", "nope")

        assert result.success is False
        assert "Path escapes workspace" in result.error
