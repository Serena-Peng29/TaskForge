"""
工具系统抽象基类和注册表
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
import json


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.content if self.success else f"Error: {self.error or self.content}"


class BaseTool(ABC):
    """工具抽象基类"""

    name: str = ""
    description: str = ""

    @abstractmethod
    def get_schema(self) -> dict:
        """返回工具的 JSON Schema 定义"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass

    def validate_args(self, args: dict) -> bool:
        """验证参数（可选实现）"""
        return True


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        if not tool.name:
            raise ValueError("Tool must have a name")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def get_all_schemas(self) -> List[dict]:
        """获取所有工具的 Schema"""
        return [tool.get_schema() for tool in self._tools.values()]

    def get_descriptions(self) -> str:
        """获取所有工具描述"""
        return "\n".join(
            f"- {name}: {tool.description}"
            for name, tool in self._tools.items()
        )

    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def execute(self, name: str, args: dict) -> ToolResult:
        """执行指定工具"""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                content="",
                error=f"Unknown tool: {name}"
            )

        try:
            return tool.execute(**args)
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )


# 全局工具注册表
TOOLS = ToolRegistry()


def tool(name: str, description: str):
    """装饰器：快速创建函数式工具"""
    def decorator(func: Callable):
        class FunctionTool(BaseTool):
            def __init__(self):
                self.name = name
                self.description = description
                self._func = func

            def get_schema(self) -> dict:
                # 简化的 schema，实际应根据函数签名生成
                import inspect
                sig = inspect.signature(func)
                properties = {}
                required = []
                for param_name, param in sig.parameters.items():
                    param_type = "string"
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation == int:
                            param_type = "integer"
                        elif param.annotation == bool:
                            param_type = "boolean"
                        elif param.annotation == float:
                            param_type = "number"
                    properties[param_name] = {"type": param_type}
                    if param.default == inspect.Parameter.empty:
                        required.append(param_name)

                return {
                    "type": "function",
                    "function": {
                        "name": self.name,
                        "description": self.description,
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required
                        }
                    }
                }

            def execute(self, **kwargs) -> ToolResult:
                result = self._func(**kwargs)
                if isinstance(result, ToolResult):
                    return result
                return ToolResult(success=True, content=str(result))

        tool_instance = FunctionTool()
        TOOLS.register(tool_instance)
        return func
    return decorator